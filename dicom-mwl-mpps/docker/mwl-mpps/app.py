from pynetdicom import AE, evt, debug_logger, AllStoragePresentationContexts
from pynetdicom.sop_class import ModalityWorklistInformationFind, ModalityPerformedProcedureStep
from pydicom.uid import ExplicitVRLittleEndian, ImplicitVRLittleEndian, ExplicitVRBigEndian
import logging
import os
import sys
import mysql.connector
from pydicom.dataset import Dataset
from pydicom import dcmread
from io import BytesIO
import traceback
from datetime import datetime
from pydicom.filebase import DicomFileLike
from pydicom.filewriter import dcmwrite

logging.basicConfig(level=logging.INFO)

def get_DB():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "mysql_db"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", "root"),
        database=os.environ.get("DB_NAME", "orthanc_ris"),
    )

def dataset_to_bytes(dataset):
    """Convert DICOM dataset to bytes"""
    with BytesIO() as buffer:
        memory_dataset = DicomFileLike(buffer)
        dcmwrite(memory_dataset, dataset)
        memory_dataset.seek(0)
        return memory_dataset.read()

def bytes_to_dataset(blob):
    """Convert DICOM blob to dataset"""
    try:
        dataset = dcmread(BytesIO(blob), force=True)
        return dataset
    except Exception as e:
        logging.error(f"Failed to convert blob to dataset: {e}")
        raise

def matches_query(mwl_ds, query_ds):
    """Check if MWL dataset matches the query dataset"""
    for elem in query_ds:
        if elem.tag.group == 0x0000:
            continue  # Skip group length elements
        query_value = getattr(query_ds, elem.keyword, None)
        if query_value not in [None, '', []]:
            mwl_value = getattr(mwl_ds, elem.keyword, None)
            if mwl_value != query_value:
                logging.info(f"Query mismatch: {elem.keyword} query='{query_value}' vs mwl='{mwl_value}'")
                return False
    return True

def handle_mwl(event):
    """Handle C-FIND requests for Modality Worklist"""
    logging.info("Received MWL C-FIND request")
    query_ds = event.identifier
    
    try:
        conn = get_DB()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT Dataset FROM mwl WHERE completed = 0")
        rows = cursor.fetchall()
        logging.info(f"Fetched {len(rows)} rows from DB")
        
        match_count = 0
        for row in rows:
            mwl_blob = row["Dataset"]
            mwl_ds = bytes_to_dataset(mwl_blob)
            logging.info(f"Processing dataset with AccessionNumber: {getattr(mwl_ds, 'AccessionNumber', 'N/A')}")
            
            # Check if this dataset matches the query
            if matches_query(mwl_ds, query_ds):
                logging.info("Dataset matches query, yielding...")
                yield 0xFF00, mwl_ds  # Pending status, dataset
                match_count += 1
            else:
                logging.info("Dataset does not match query, skipping...")
                
        cursor.close()
        conn.close()
        logging.info(f"Finished processing all datasets. Found {match_count} matches.")
        
    except Exception as e:
        logging.error(f"MWL DB query failed: {e}")
        traceback.print_exc()

def handle_n_create(event):
    """Handle MPPS N-CREATE requests (procedure start)"""
    logging.info("Received MPPS N-CREATE")
    
    try:
        # Get the request information
        sop_instance_uid = event.request.AffectedSOPInstanceUID
        dataset = event.attribute_list
        
        logging.info(f"N-CREATE for SOP Instance UID: {sop_instance_uid}")
        logging.info(f"Dataset keys: {list(dataset.keys()) if dataset else 'None'}")
        
        # Extract key information from dataset
        accession_number = getattr(dataset, 'AccessionNumber', None)
        study_instance_uid = getattr(dataset, 'StudyInstanceUID', None)
        patient_id = getattr(dataset, 'PatientID', None)
        
        # Map DICOM status values to database enum values
        raw_status = getattr(dataset, 'PerformedProcedureStepStatus', 'IN PROGRESS')
        status_mapping = {
            'IN PROGRESS': 'IN_PROGRESS',
            'COMPLETED': 'COMPLETED', 
            'DISCONTINUED': 'DISCONTINUED'
        }
        pps_status = status_mapping.get(raw_status, 'IN_PROGRESS')
        
        pps_id = getattr(dataset, 'PerformedProcedureStepID', None)
        performed_station_ae = getattr(dataset, 'PerformedStationAETitle', None)
        
        logging.info(f"Extracted data - AccessionNumber: {accession_number}, StudyUID: {study_instance_uid}")
        logging.info(f"Raw status: '{raw_status}' -> Mapped status: '{pps_status}'")
        
        # Connect to database
        conn = get_DB()
        cursor = conn.cursor(dictionary=True)
        
        # Try to find related MWL entry
        mwl_id = None
        if accession_number:
            cursor.execute(
                "SELECT id FROM mwl WHERE AccessionNumber = %s AND completed = 0",
                (accession_number,)
            )
            mwl_row = cursor.fetchone()
            if mwl_row:
                mwl_id = mwl_row['id']
                logging.info(f"Found related MWL with ID: {mwl_id}")
        
        # Convert dataset to bytes for storage
        dataset_bytes = dataset_to_bytes(dataset)
        
        # Check if we're using the new schema or old schema
        cursor.execute("SHOW TABLES LIKE 'mpps'")
        new_schema = cursor.fetchone() is not None
        
        if new_schema:
            # Use new simplified schema
            sql = """
                INSERT INTO mpps
                (sop_instance_uid, mwl_id, AccessionNumber, StudyInstanceUID, PatientID,
                 status, performed_procedure_step_id, performed_station_ae_title, dataset_blob)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                sop_instance_uid,
                mwl_id,
                accession_number,
                study_instance_uid,
                patient_id,
                pps_status,  # Use the mapped status
                pps_id,
                performed_station_ae,
                dataset_bytes
            )
            logging.info(f"Inserting with status: '{pps_status}'")
        else:
            # Use old schema (fallback)
            import json
            dataset_json = {}
            for elem in dataset:
                if elem.tag.group != 0x0000:  # Skip command group
                    try:
                        dataset_json[elem.keyword] = str(elem.value) if elem.value is not None else ""
                    except:
                        pass
            
            sql = """
                INSERT INTO n_create 
                (AccessionNumber, StudyInstanceUID, MessageID, dataset_in, mwl, dataset_out, named_tags)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                accession_number,
                study_instance_uid,
                event.request.MessageID,
                json.dumps(dataset_json),
                json.dumps({"mwl_id": mwl_id}) if mwl_id else None,
                json.dumps(dataset_json),
                json.dumps(dataset_json)
            )
        
        logging.info(f"Executing SQL: {sql}")
        logging.info(f"Values: {values}")
        cursor.execute(sql, values)
        conn.commit()
        record_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        
        logging.info(f"Successfully created MPPS record with ID: {record_id}")
        return 0x0000, dataset  # Success
        
    except Exception as e:
        logging.error(f"Error handling N-CREATE: {e}")
        traceback.print_exc()
        return 0xC000, None  # Failure status

# Also update handle_n_set with similar status mapping
def handle_n_set(event):
    """Handle MPPS N-SET requests (procedure update/completion)"""
    logging.info("Received MPPS N-SET")
    
    try:
        # Get the request information
        sop_instance_uid = event.request.AffectedSOPInstanceUID
        modification_list = event.modification_list
        
        # If SOP Instance UID is not in request, get it from the modification list
        if sop_instance_uid is None and modification_list:
            sop_instance_uid = getattr(modification_list, 'SOPInstanceUID', None)
        
        logging.info(f"N-SET for SOP Instance UID: {sop_instance_uid}")
        logging.info(f"Modification List: {modification_list}")
        
        if sop_instance_uid is None:
            logging.error("No SOP Instance UID found in N-SET request")
            return 0xC000, None
        
        # Map DICOM status to database enum
        raw_status = getattr(modification_list, 'PerformedProcedureStepStatus', None)
        status_mapping = {
            'IN PROGRESS': 'IN_PROGRESS',
            'COMPLETED': 'COMPLETED',
            'DISCONTINUED': 'DISCONTINUED'
        }
        procedure_step_status = status_mapping.get(raw_status, raw_status) if raw_status else None
        
        logging.info(f"Raw status: '{raw_status}' -> Mapped status: '{procedure_step_status}'")
        
        # Connect to database
        conn = get_DB()
        cursor = conn.cursor(dictionary=True)
        
        # Check if we're using new schema or old schema
        cursor.execute("SHOW TABLES LIKE 'mpps'")
        new_schema = cursor.fetchone() is not None
        
        if new_schema:
            # Update MPPS record with new schema
            dataset_bytes = dataset_to_bytes(modification_list) if modification_list else None
            
            if dataset_bytes:
                sql = """
                    UPDATE mpps 
                    SET status = %s, completed_at = NOW(), dataset_blob = %s 
                    WHERE sop_instance_uid = %s
                """
                values = (procedure_step_status, dataset_bytes, sop_instance_uid)
            else:
                sql = """
                    UPDATE mpps 
                    SET status = %s, completed_at = NOW() 
                    WHERE sop_instance_uid = %s
                """
                values = (procedure_step_status, sop_instance_uid)
            
            logging.info(f"Executing UPDATE with SOP Instance UID: {sop_instance_uid}")
            cursor.execute(sql, values)
            rows_affected = cursor.rowcount
            logging.info(f"UPDATE affected {rows_affected} rows")
            
            # If completed, mark related MWL as completed
            if procedure_step_status in ['COMPLETED', 'DISCONTINUED'] and rows_affected > 0:
                cursor.execute(
                    "SELECT AccessionNumber FROM mpps WHERE sop_instance_uid = %s",
                    (sop_instance_uid,)
                )
                mpps_row = cursor.fetchone()
                
                if mpps_row and mpps_row['AccessionNumber']:
                    cursor.execute(
                        "UPDATE mwl SET completed = 1 WHERE AccessionNumber = %s",
                        (mpps_row['AccessionNumber'],)
                    )
                    logging.info(f"Marked MWL as completed for AccessionNumber: {mpps_row['AccessionNumber']}")
        else:
            # Use old schema (fallback)
            import json
            mod_list_json = {}
            for elem in modification_list:
                if elem.tag.group != 0x0000:  # Skip command group
                    try:
                        mod_list_json[elem.keyword] = str(elem.value) if elem.value is not None else ""
                    except:
                        pass
            
            sql = """
                INSERT INTO n_set 
                (AffectedSOPInstanceUID, MessageID, managed_instance, mod_list, response, response_status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (
                sop_instance_uid,
                event.request.MessageID,
                json.dumps({"sop_instance_uid": sop_instance_uid}),
                json.dumps(mod_list_json),
                json.dumps(mod_list_json),
                '0000'
            )
            cursor.execute(sql, values)
            rows_affected = cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        if rows_affected > 0:
            logging.info(f"Successfully updated MPPS status to: {procedure_step_status}")
            return 0x0000, modification_list  # Success
        else:
            logging.error(f"No MPPS record found with SOP Instance UID: {sop_instance_uid}")
            return 0xC001, None  # No such object instance
        
    except Exception as e:
        logging.error(f"Error handling N-SET: {e}")
        traceback.print_exc()
        return 0xC000, None  # Failure status

handlers = [
    (evt.EVT_C_FIND, handle_mwl),
    (evt.EVT_N_CREATE, handle_n_create),
    (evt.EVT_N_SET, handle_n_set),
]

ae = AE()
ae.add_supported_context(
    ModalityWorklistInformationFind,
    [ExplicitVRLittleEndian, ImplicitVRLittleEndian, ExplicitVRBigEndian]
)
ae.add_supported_context(
    ModalityPerformedProcedureStep,
    [ExplicitVRLittleEndian, ImplicitVRLittleEndian, ExplicitVRBigEndian]
)

ae.start_server(('0.0.0.0', 104), evt_handlers=handlers, block=True)