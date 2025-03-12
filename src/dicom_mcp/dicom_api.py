"""
DICOM API layer for MCP Server.

This module provides a clean interface to pynetdicom functionality,
abstracting the details of DICOM networking.
"""

from typing import Dict, List, Any, Optional, Tuple

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

from .attributes import get_attributes_for_level


class DicomClient:
    """DICOM networking client that handles communication with DICOM servers."""
    
    def __init__(self, host: str, port: int, ae_title: str = "MCPSCU"):
        """Initialize DICOM client.
        
        Args:
            host: DICOM server hostname or IP
            port: DICOM server port
            ae_title: Called AE title
        """
        self.host = host
        self.port = port
        self.ae_title = ae_title
        
        # Create the Application Entity
        self.ae = AE(ae_title="MCPSCU")
        
        # Add the necessary presentation contexts
        self.ae.add_requested_context(Verification)
        self.ae.add_requested_context(PatientRootQueryRetrieveInformationModelFind)
        self.ae.add_requested_context(PatientRootQueryRetrieveInformationModelGet)
        self.ae.add_requested_context(PatientRootQueryRetrieveInformationModelMove)
        self.ae.add_requested_context(StudyRootQueryRetrieveInformationModelFind)
        self.ae.add_requested_context(StudyRootQueryRetrieveInformationModelGet)
        self.ae.add_requested_context(StudyRootQueryRetrieveInformationModelMove)
    
    def verify_connection(self) -> Tuple[bool, str]:
        """Verify connectivity to the DICOM server using C-ECHO.
        
        Returns:
            Tuple of (success, message)
        """
        # Associate with the DICOM server
        assoc = self.ae.associate(self.host, self.port, ae_title=self.ae_title)
        
        if assoc.is_established:
            # Send C-ECHO request
            status = assoc.send_c_echo()
            
            # Release the association
            assoc.release()
            
            if status and status.Status == 0:
                return True, f"Connection successful to {self.host}:{self.port}"
            else:
                return False, f"C-ECHO failed with status: {status.Status if status else 'None'}"
        else:
            return False, f"Failed to associate with DICOM server at {self.host}:{self.port}"
    
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
        # Associate with the DICOM server
        assoc = self.ae.associate(self.host, self.port, ae_title=self.ae_title)
        
        if not assoc.is_established:
            raise Exception(f"Failed to associate with DICOM server at {self.host}:{self.port}")
        
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
    
    def get_entity_by_id(self, level: str, uid: str, attribute_preset: str = "extended") -> Dict[str, Any]:
        """Get entity by its unique identifier.
        
        Args:
            level: Entity level (patient, study, series, instance)
            uid: Unique identifier for the entity
            attribute_preset: Attribute preset to use
            
        Returns:
            Dictionary with entity data or empty dict if not found
        """
        if level == "patient":
            results = self.query_patient(patient_id=uid, attribute_preset=attribute_preset)
        elif level == "study":
            results = self.query_study(study_instance_uid=uid, attribute_preset=attribute_preset)
        elif level == "series":
            # First find which study this series belongs to
            ds = Dataset()
            ds.QueryRetrieveLevel = "SERIES"
            ds.SeriesInstanceUID = uid
            ds.StudyInstanceUID = ""
            
            # Get the study UID
            assoc = self.ae.associate(self.host, self.port, ae_title=self.ae_title)
            study_uid = None
            
            if assoc.is_established:
                responses = assoc.send_c_find(ds, StudyRootQueryRetrieveInformationModelFind)
                for (status, dataset) in responses:
                    if status and status.Status == 0xFF00 and dataset and hasattr(dataset, "StudyInstanceUID"):
                        study_uid = dataset.StudyInstanceUID
                        break
                assoc.release()
            
            if not study_uid:
                return {}
                
            # Now get the series details
            results = self.query_series(
                study_instance_uid=study_uid,
                series_instance_uid=uid,
                attribute_preset=attribute_preset
            )
        elif level == "instance":
            # First find which series this instance belongs to
            ds = Dataset()
            ds.QueryRetrieveLevel = "IMAGE"
            ds.SOPInstanceUID = uid
            ds.SeriesInstanceUID = ""
            
            # Get the series UID
            assoc = self.ae.associate(self.host, self.port, ae_title=self.ae_title)
            series_uid = None
            
            if assoc.is_established:
                responses = assoc.send_c_find(ds, StudyRootQueryRetrieveInformationModelFind)
                for (status, dataset) in responses:
                    if status and status.Status == 0xFF00 and dataset and hasattr(dataset, "SeriesInstanceUID"):
                        series_uid = dataset.SeriesInstanceUID
                        break
                assoc.release()
            
            if not series_uid:
                return {}
                
            # Now get the instance details
            results = self.query_instance(
                series_instance_uid=series_uid,
                sop_instance_uid=uid,
                attribute_preset=attribute_preset
            )
        else:
            raise ValueError(f"Unknown level: {level}")
        
        # Return the first result or empty dict
        return results[0] if results else {}
    
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
                result[elem.name] = [DicomClient._dataset_to_dict(item) for item in elem.value]
            else:
                # Handle regular elements
                if hasattr(elem, "name"):
                    try:
                        if elem.VM > 1:
                            # Multiple values
                            result[elem.name] = list(elem.value)
                        else:
                            # Single value
                            result[elem.name] = elem.value
                    except Exception:
                        # Fall back to string representation
                        result[elem.name] = str(elem.value)
        
        return result