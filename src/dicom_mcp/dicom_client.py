"""
DICOM Client.

This module provides a clean interface to pynetdicom functionality,
abstracting the details of DICOM networking.
"""
from typing import Dict, List, Any, Tuple

from pydicom.dataset import Dataset
from pynetdicom import AE
from pynetdicom.sop_class import (
    PatientRootQueryRetrieveInformationModelFind,
    StudyRootQueryRetrieveInformationModelFind,
    PatientRootQueryRetrieveInformationModelGet,
    PatientRootQueryRetrieveInformationModelMove,
    StudyRootQueryRetrieveInformationModelGet,
    StudyRootQueryRetrieveInformationModelMove,
    Verification
)
import os
from pydicom.dataset import Dataset
import os
from pydicom.dataset import Dataset
from pynetdicom.sop_class import PatientRootQueryRetrieveInformationModelMove
from pynetdicom import StoragePresentationContexts, AE, evt
import os
import time
from pydicom.dataset import Dataset
from pynetdicom.sop_class import PatientRootQueryRetrieveInformationModelMove
from pynetdicom import StoragePresentationContexts, AE, evt
from .attributes import get_attributes_for_level

class DicomClient:
    """DICOM networking client that handles communication with DICOM nodes."""
    
    def __init__(self, host: str, port: int, calling_aet: str, called_aet: str):
        """Initialize DICOM client.
        
        Args:
            host: DICOM node hostname or IP
            port: DICOM node port
            calling_aet: Local AE title (our AE title)
            called_aet: Remote AE title (the node we're connecting to)
        """
        self.host = host
        self.port = port
        self.called_aet = called_aet
        self.calling_aet = calling_aet
        
        # Create the Application Entity
        self.ae = AE(ae_title=calling_aet)
        
        # Add the necessary presentation contexts
        self.ae.add_requested_context(Verification)
        self.ae.add_requested_context(PatientRootQueryRetrieveInformationModelFind)
        self.ae.add_requested_context(PatientRootQueryRetrieveInformationModelGet)
        self.ae.add_requested_context(PatientRootQueryRetrieveInformationModelMove)
        self.ae.add_requested_context(StudyRootQueryRetrieveInformationModelFind)
        self.ae.add_requested_context(StudyRootQueryRetrieveInformationModelGet)
        self.ae.add_requested_context(StudyRootQueryRetrieveInformationModelMove)

    def retrieve_instance_move(
        self, 
        study_instance_uid: str,
        series_instance_uid: str,
        sop_instance_uid: str,
        output_dir: str = "./retrieved_files"
    ) -> Dict[str, Any]:
        """Retrieve a specific DICOM instance using C-MOVE.
        
        Args:
            study_instance_uid: Study Instance UID
            series_instance_uid: Series Instance UID
            sop_instance_uid: SOP Instance UID
            output_dir: Directory to save the retrieved instance to
            
        Returns:
            Dictionary with information about the retrieval operation
        """

        
        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Create a temporary Storage SCP to receive the instances
        storage_ae = AE(ae_title=self.calling_aet)
        
        # Add all possible storage SOP classes and transfer syntaxes
        storage_ae.supported_contexts = StoragePresentationContexts
        
        # Create event handler for receiving instances
        received_files = []
        store_errors = []
        
        def handle_store(event):
            """Handle a C-STORE request"""
            try:
                # Extract relevant information
                ds = event.dataset
                sop_class = event.context.abstract_syntax
                sop_instance = ds.SOPInstanceUID if hasattr(ds, 'SOPInstanceUID') else "unknown"
                
                print(f"Received C-STORE for {sop_class}: {sop_instance}")
                
                # Save the dataset to a file
                file_path = os.path.join(output_dir, f"{sop_instance}.dcm")
                ds.save_as(file_path, write_like_original=False)
                received_files.append(file_path)
                
                return 0x0000  # Success
            except Exception as e:
                store_errors.append(str(e))
                print(f"Error in C-STORE handler: {e}")
                return 0xC000  # Failed - Unable to process
        
        # Start the Storage SCP on a fixed port
        # Use 0.0.0.0 to listen on all interfaces
        storage_port = 11112  # This should match the port configured in Orthanc
        storage_handlers = [(evt.EVT_C_STORE, handle_store)]
        
        try:
            scp = storage_ae.start_server(("0.0.0.0", storage_port), block=False, evt_handlers=storage_handlers)
            print(f"Storage SCP started on port {storage_port} with AE Title {self.calling_aet}")
            
            # Create query dataset
            ds = Dataset()
            ds.QueryRetrieveLevel = "IMAGE"
            ds.StudyInstanceUID = study_instance_uid
            ds.SeriesInstanceUID = series_instance_uid
            ds.SOPInstanceUID = sop_instance_uid
            
            # Associate with the DICOM node
            assoc = self.ae.associate(self.host, self.port, ae_title=self.called_aet)
            
            if not assoc.is_established:
                return {
                    "success": False,
                    "message": f"Failed to associate with DICOM node at {self.host}:{self.port}"
                }
            
            try:
                # Tell the server to move the instance to our Storage SCP
                print(f"Sending C-MOVE with destination AE: {self.calling_aet}")
                responses = assoc.send_c_move(
                    ds, 
                    self.calling_aet,  # Move destination AE Title 
                    PatientRootQueryRetrieveInformationModelMove
                )
                
                success = False
                message = "C-MOVE operation failed"
                
                for (status, dataset) in responses:
                    if status:
                        status_int = status.Status if hasattr(status, 'Status') else 0
                        print(f"C-MOVE response status: 0x{status_int:04x}")
                        
                        if status_int == 0x0000:  # Success
                            success = True
                            message = "C-MOVE operation completed successfully"
                        elif status_int == 0xFF00:  # Pending
                            success = True  # Still processing
                            message = "C-MOVE operation in progress"
                
                # Give some time for the SCP to receive files 
                # (in case there's a delay in network communication)
                time.sleep(2)
                
                # Report the results
                if received_files:
                    return {
                        "success": True,
                        "message": f"Retrieved {len(received_files)} instances",
                        "file_path": received_files[0] if received_files else ""
                    }
                
                if store_errors:
                    return {
                        "success": False,
                        "message": f"C-STORE errors: {'; '.join(store_errors)}",
                        "file_path": ""
                    }
                
                return {
                    "success": success,
                    "message": message,
                    "file_path": ""
                }
            
            finally:
                # Release the association
                assoc.release()
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error during C-MOVE operation: {str(e)}",
                "file_path": ""
            }
        finally:
            # Stop the storage SCP
            scp.shutdown()

    def verify_connection(self) -> Tuple[bool, str]:
        """Verify connectivity to the DICOM node using C-ECHO.
        
        Returns:
            Tuple of (success, message)
        """
        # Associate with the DICOM node
        assoc = self.ae.associate(self.host, self.port, ae_title=self.called_aet)
        
        if assoc.is_established:
            # Send C-ECHO request
            status = assoc.send_c_echo()
            
            # Release the association
            assoc.release()
            
            if status and status.Status == 0:
                return True, f"Connection successful to {self.host}:{self.port} (Called AE: {self.called_aet}, Calling AE: {self.calling_aet})"
            else:
                return False, f"C-ECHO failed with status: {status.Status if status else 'None'}"
        else:
            return False, f"Failed to associate with DICOM node at {self.host}:{self.port} (Called AE: {self.called_aet}, Calling AE: {self.calling_aet})"
    
    def find(self, query_dataset: Dataset, query_model) -> List[Dict[str, Any]]:
        """Execute a C-FIND request.
        
        Args:
            query_dataset: Dataset containing query parameters
            query_model: DICOM query model (Patient/StudyRoot)
        
        Returns:
            List of dictionaries containing query results
        
        Raises:
            Exception: If association fails
        """
        # Associate with the DICOM node
        assoc = self.ae.associate(self.host, self.port, ae_title=self.called_aet)
        
        if not assoc.is_established:
            raise Exception(f"Failed to associate with DICOM node at {self.host}:{self.port} (Called AE: {self.called_aet}, Calling AE: {self.calling_aet})")
        
        results = []
        
        try:
            # Send C-FIND request
            responses = assoc.send_c_find(query_dataset, query_model)
            
            for (status, dataset) in responses:
                if status and status.Status == 0xFF00:  # Pending
                    if dataset:
                        results.append(self._dataset_to_dict(dataset))
        finally:
            # Always release the association
            assoc.release()
        
        return results
    
    def query_patient(self, patient_id: str = None, name_pattern: str = None, 
                     birth_date: str = None, attribute_preset: str = "standard",
                     additional_attrs: List[str] = None, exclude_attrs: List[str] = None) -> List[Dict[str, Any]]:
        """Query for patients matching criteria.
        
        Args:
            patient_id: Patient ID
            name_pattern: Patient name pattern (can include wildcards * and ?)
            birth_date: Patient birth date (YYYYMMDD)
            attribute_preset: Attribute preset (minimal, standard, extended)
            additional_attrs: Additional attributes to include
            exclude_attrs: Attributes to exclude
            
        Returns:
            List of matching patient records
        """
        # Create query dataset
        ds = Dataset()
        ds.QueryRetrieveLevel = "PATIENT"
        
        # Add query parameters if provided
        if patient_id:
            ds.PatientID = patient_id
            
        if name_pattern:
            ds.PatientName = name_pattern
            
        if birth_date:
            ds.PatientBirthDate = birth_date
        
        # Add attributes based on preset
        attrs = get_attributes_for_level("patient", attribute_preset, additional_attrs, exclude_attrs)
        for attr in attrs:
            if not hasattr(ds, attr):
                setattr(ds, attr, "")
        
        # Execute query
        return self.find(ds, PatientRootQueryRetrieveInformationModelFind)
    
    def query_study(self, patient_id: str = None, study_date: str = None, 
                   modality: str = None, study_description: str = None, 
                   accession_number: str = None, study_instance_uid: str = None,
                   attribute_preset: str = "standard", additional_attrs: List[str] = None, 
                   exclude_attrs: List[str] = None) -> List[Dict[str, Any]]:
        """Query for studies matching criteria.
        
        Args:
            patient_id: Patient ID
            study_date: Study date or range (YYYYMMDD or YYYYMMDD-YYYYMMDD)
            modality: Modalities in study
            study_description: Study description (can include wildcards)
            accession_number: Accession number
            study_instance_uid: Study Instance UID
            attribute_preset: Attribute preset (minimal, standard, extended)
            additional_attrs: Additional attributes to include
            exclude_attrs: Attributes to exclude
            
        Returns:
            List of matching study records
        """
        # Create query dataset
        ds = Dataset()
        ds.QueryRetrieveLevel = "STUDY"
        
        # Add query parameters if provided
        if patient_id:
            ds.PatientID = patient_id
            
        if study_date:
            ds.StudyDate = study_date
            
        if modality:
            ds.ModalitiesInStudy = modality
            
        if study_description:
            ds.StudyDescription = study_description
            
        if accession_number:
            ds.AccessionNumber = accession_number
            
        if study_instance_uid:
            ds.StudyInstanceUID = study_instance_uid
        
        # Add attributes based on preset
        attrs = get_attributes_for_level("study", attribute_preset, additional_attrs, exclude_attrs)
        for attr in attrs:
            if not hasattr(ds, attr):
                setattr(ds, attr, "")
        
        # Execute query
        return self.find(ds, StudyRootQueryRetrieveInformationModelFind)
    
    def query_series(self, study_instance_uid: str, series_instance_uid: str = None,
                    modality: str = None, series_number: str = None, 
                    series_description: str = None, attribute_preset: str = "standard",
                    additional_attrs: List[str] = None, exclude_attrs: List[str] = None) -> List[Dict[str, Any]]:
        """Query for series matching criteria.
        
        Args:
            study_instance_uid: Study Instance UID (required)
            series_instance_uid: Series Instance UID
            modality: Modality (e.g. "CT", "MR")
            series_number: Series number
            series_description: Series description (can include wildcards)
            attribute_preset: Attribute preset (minimal, standard, extended)
            additional_attrs: Additional attributes to include
            exclude_attrs: Attributes to exclude
            
        Returns:
            List of matching series records
        """
        # Create query dataset
        ds = Dataset()
        ds.QueryRetrieveLevel = "SERIES"
        ds.StudyInstanceUID = study_instance_uid
        
        # Add query parameters if provided
        if series_instance_uid:
            ds.SeriesInstanceUID = series_instance_uid
            
        if modality:
            ds.Modality = modality
            
        if series_number:
            ds.SeriesNumber = series_number
            
        if series_description:
            ds.SeriesDescription = series_description
        
        # Add attributes based on preset
        attrs = get_attributes_for_level("series", attribute_preset, additional_attrs, exclude_attrs)
        for attr in attrs:
            if not hasattr(ds, attr):
                setattr(ds, attr, "")
        
        # Execute query
        return self.find(ds, StudyRootQueryRetrieveInformationModelFind)
    
    def query_instance(self, series_instance_uid: str, sop_instance_uid: str = None,
                      instance_number: str = None, attribute_preset: str = "standard",
                      additional_attrs: List[str] = None, exclude_attrs: List[str] = None) -> List[Dict[str, Any]]:
        """Query for instances matching criteria.
        
        Args:
            series_instance_uid: Series Instance UID (required)
            sop_instance_uid: SOP Instance UID
            instance_number: Instance number
            attribute_preset: Attribute preset (minimal, standard, extended)
            additional_attrs: Additional attributes to include
            exclude_attrs: Attributes to exclude
            
        Returns:
            List of matching instance records
        """
        # Create query dataset
        ds = Dataset()
        ds.QueryRetrieveLevel = "IMAGE"
        ds.SeriesInstanceUID = series_instance_uid
        
        # Add query parameters if provided
        if sop_instance_uid:
            ds.SOPInstanceUID = sop_instance_uid
            
        if instance_number:
            ds.InstanceNumber = instance_number
        
        # Add attributes based on preset
        attrs = get_attributes_for_level("instance", attribute_preset, additional_attrs, exclude_attrs)
        for attr in attrs:
            if not hasattr(ds, attr):
                setattr(ds, attr, "")
        
        # Execute query
        return self.find(ds, StudyRootQueryRetrieveInformationModelFind)
    
    @staticmethod
    def _dataset_to_dict(dataset: Dataset) -> Dict[str, Any]:
        """Convert a DICOM dataset to a dictionary.
        
        Args:
            dataset: DICOM dataset
            
        Returns:
            Dictionary representation of the dataset
        """
        if hasattr(dataset, "is_empty") and dataset.is_empty():
            return {}
        
        result = {}
        for elem in dataset:
            if elem.VR == "SQ":
                # Handle sequences
                result[elem.keyword] = [DicomClient._dataset_to_dict(item) for item in elem.value]
            else:
                # Handle regular elements
                if hasattr(elem, "keyword"):
                    try:
                        if elem.VM > 1:
                            # Multiple values
                            result[elem.keyword] = list(elem.value)
                        else:
                            # Single value
                            result[elem.keyword] = elem.value
                    except Exception:
                        # Fall back to string representation
                        result[elem.keyword] = str(elem.value)
        
        return result

    