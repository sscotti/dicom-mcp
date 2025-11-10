import os
import mysql.connector
import logging
from io import BytesIO
from pydicom.filebase import DicomFileLike
from pydicom.filewriter import dcmwrite

def get_DB():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
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

def extract_mwl_fields(dataset):
    """Extract key fields from DICOM dataset for indexing"""
    return {
        'AccessionNumber': getattr(dataset, 'AccessionNumber', None),
        'StudyInstanceUID': getattr(dataset, 'StudyInstanceUID', None),
        'PatientID': getattr(dataset, 'PatientID', None),
        'PatientName': str(getattr(dataset, 'PatientName', '')),
        'ScheduledProcedureStepStartDate': None,
        'ScheduledStationAETitle': None
    }

def extract_scheduled_fields(dataset):
    """Extract scheduled procedure step fields"""
    scheduled_date = None
    scheduled_aet = None
    
    # Extract from ScheduledProcedureStepSequence if present
    if hasattr(dataset, 'ScheduledProcedureStepSequence') and dataset.ScheduledProcedureStepSequence:
        sps = dataset.ScheduledProcedureStepSequence[0]
        scheduled_date = getattr(sps, 'ScheduledProcedureStepStartDate', None)
        scheduled_aet = getattr(sps, 'ScheduledStationAETitle', None)
    
    return scheduled_date, scheduled_aet

def insert_mwl_record(json_data, dataset):
    """Insert MWL record using simplified schema"""
    conn = None
    cursor = None
    try:
        conn = get_DB()
        cursor = conn.cursor()
        
        # Extract key fields
        fields = extract_mwl_fields(dataset)
        scheduled_date, scheduled_aet = extract_scheduled_fields(dataset)
        
        # Convert dataset to bytes
        dataset_bytes = dataset_to_bytes(dataset)
        
        sql = """
            INSERT INTO mwl
            (completed, AccessionNumber, StudyInstanceUID, PatientID, PatientName,
             ScheduledProcedureStepStartDate, ScheduledStationAETitle, Dataset)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        values = (
            0,  # not completed
            fields['AccessionNumber'],
            fields['StudyInstanceUID'],
            fields['PatientID'],
            fields['PatientName'],
            scheduled_date,
            scheduled_aet,
            dataset_bytes
        )
        
        logging.info(f"Inserting MWL record for AccessionNumber: {fields['AccessionNumber']}")
        cursor.execute(sql, values)
        conn.commit()
        row_id = cursor.lastrowid
        logging.info(f"Inserted MWL record with id {row_id}")
        return row_id
        
    except Exception as e:
        logging.error(f"Error inserting MWL record: {str(e)}")
        if conn:
            conn.rollback()
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_mwl_by_accession(accession_number):
    """Get MWL record by AccessionNumber"""
    conn = None
    cursor = None
    try:
        conn = get_DB()
        cursor = conn.cursor(dictionary=True)
        
        sql = "SELECT * FROM mwl WHERE AccessionNumber = %s AND completed = 0"
        cursor.execute(sql, (accession_number,))
        
        return cursor.fetchone()
        
    except Exception as e:
        logging.error(f"Error fetching MWL record: {str(e)}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def mark_mwl_completed(accession_number):
    """Mark MWL as completed"""
    conn = None
    cursor = None
    try:
        conn = get_DB()
        cursor = conn.cursor()
        
        sql = "UPDATE mwl SET completed = 1 WHERE AccessionNumber = %s"
        cursor.execute(sql, (accession_number,))
        conn.commit()
        
        logging.info(f"Marked MWL as completed for AccessionNumber: {accession_number}")
        return cursor.rowcount > 0
        
    except Exception as e:
        logging.error(f"Error marking MWL completed: {str(e)}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def insert_mpps_record(sop_instance_uid, dataset, mwl_id=None):
    """Insert MPPS record"""
    conn = None
    cursor = None
    try:
        conn = get_DB()
        cursor = conn.cursor()
        
        # Extract key fields
        accession_number = getattr(dataset, 'AccessionNumber', None)
        study_instance_uid = getattr(dataset, 'StudyInstanceUID', None)
        patient_id = getattr(dataset, 'PatientID', None)
        pps_status = getattr(dataset, 'PerformedProcedureStepStatus', 'IN_PROGRESS')
        pps_id = getattr(dataset, 'PerformedProcedureStepID', None)
        performed_station_ae = getattr(dataset, 'PerformedStationAETitle', None)
        
        # Convert dataset to bytes
        dataset_bytes = dataset_to_bytes(dataset)
        
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
            pps_status,
            pps_id,
            performed_station_ae,
            dataset_bytes
        )
        
        logging.info(f"Inserting MPPS record for SOP Instance UID: {sop_instance_uid}")
        cursor.execute(sql, values)
        conn.commit()
        row_id = cursor.lastrowid
        logging.info(f"Inserted MPPS record with id {row_id}")
        return row_id
        
    except Exception as e:
        logging.error(f"Error inserting MPPS record: {str(e)}")
        if conn:
            conn.rollback()
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def update_mpps_status(sop_instance_uid, status, dataset=None):
    """Update MPPS status and optionally dataset"""
    conn = None
    cursor = None
    try:
        conn = get_DB()
        cursor = conn.cursor()
        
        if dataset:
            dataset_bytes = dataset_to_bytes(dataset)
            sql = """
                UPDATE mpps 
                SET status = %s, completed_at = NOW(), dataset_blob = %s 
                WHERE sop_instance_uid = %s
            """
            values = (status, dataset_bytes, sop_instance_uid)
        else:
            sql = """
                UPDATE mpps 
                SET status = %s, completed_at = NOW() 
                WHERE sop_instance_uid = %s
            """
            values = (status, sop_instance_uid)
        
        cursor.execute(sql, values)
        conn.commit()
        
        logging.info(f"Updated MPPS status to {status} for SOP Instance UID: {sop_instance_uid}")
        return cursor.rowcount > 0
        
    except Exception as e:
        logging.error(f"Error updating MPPS status: {str(e)}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()