"""
DICOM MCP Server tool definitions.
"""

from typing import Dict, Any, List, Optional

from pydicom.dataset import Dataset
from pynetdicom.sop_class import (
    PatientRootQueryRetrieveInformationModelFind,
    StudyRootQueryRetrieveInformationModelFind
)

from mcp.server.fastmcp import Context
from mcp.server.models import ErrorResponse

from .attributes import ATTRIBUTE_PRESETS, get_attributes_for_level
from .utils import dataset_to_dict, handle_c_find_response


def register_tools(mcp_server):
    """Register all tool handlers with the MCP server.
    
    Args:
        mcp_server: FastMCP server instance
    """
    
    @mcp_server.tool()
    def configure_dicom_server(
        host: str, 
        port: int, 
        ae_title: str = "MCPSCU", 
        timeout: int = 30, 
        ctx: Context = None
    ) -> str:
        """Configure the DICOM server connection.
        
        Args:
            host: DICOM server hostname or IP address
            port: DICOM server port
            ae_title: Called AE title
            timeout: Association timeout in seconds
            
        Returns:
            Success or error message
        """
        dicom_ctx = ctx.lifespan_context
        
        # Update configuration
        dicom_ctx.config.host = host
        dicom_ctx.config.port = port
        dicom_ctx.config.ae_title = ae_title
        dicom_ctx.config.timeout = timeout
        
        return f"DICOM server configuration updated: {host}:{port} (AET: {ae_title})"


    @mcp_server.tool()
    def verify_connection(ctx: Context = None) -> str:
        """Verify connectivity to the DICOM server using C-ECHO.
        
        Returns:
            Success or error message
        """
        dicom_ctx = ctx.lifespan_context
        ae = dicom_ctx.ae
        config = dicom_ctx.config
        
        # Associate with the DICOM server
        assoc = ae.associate(config.host, config.port, ae_title=config.ae_title)
        
        if assoc.is_established:
            # Send C-ECHO request
            status = assoc.send_c_echo()
            
            # Release the association
            assoc.release()
            
            if status and status.Status == 0:
                return f"Connection successful to {config.host}:{config.port} (AET: {config.ae_title})"
            else:
                return f"C-ECHO failed with status: {status.Status if status else 'None'}"
        else:
            return f"Failed to associate with DICOM server at {config.host}:{config.port}"


    @mcp_server.tool()
    def query_patients(
        name_pattern: str = "", 
        patient_id: str = "", 
        birth_date: str = "", 
        attribute_preset: str = "standard", 
        additional_attributes: List[str] = None,
        exclude_attributes: List[str] = None, 
        ctx: Context = None
    ) -> List[Dict[str, Any]]:
        """Query patients matching the specified criteria.
        
        Args:
            name_pattern: Patient name pattern (can include wildcards * and ?)
            patient_id: Patient ID
            birth_date: Patient birth date (YYYYMMDD)
            attribute_preset: Attribute preset (minimal, standard, extended)
            additional_attributes: Additional attributes to query
            exclude_attributes: Attributes to exclude from query results
            
        Returns:
            List of matching patient records
        """
        dicom_ctx = ctx.lifespan_context
        ae = dicom_ctx.ae
        config = dicom_ctx.config
        
        # Create query dataset
        ds = Dataset()
        ds.QueryRetrieveLevel = "PATIENT"
        
        # Add query parameters if provided
        if name_pattern:
            ds.PatientName = name_pattern
        
        if patient_id:
            ds.PatientID = patient_id
            
        if birth_date:
            ds.PatientBirthDate = birth_date
        
        # Add attributes based on preset
        attrs = get_attributes_for_level("patient", attribute_preset, additional_attributes, exclude_attributes)
        for attr in attrs:
            if not hasattr(ds, attr):
                setattr(ds, attr, "")
        
        # Associate with the DICOM server
        assoc = ae.associate(config.host, config.port, ae_title=config.ae_title)
        
        if assoc.is_established:
            # Send C-FIND request
            responses = assoc.send_c_find(ds, PatientRootQueryRetrieveInformationModelFind)
            results = handle_c_find_response(responses)
            assoc.release()
            return results
        else:
            raise ErrorResponse(f"Failed to associate with DICOM server at {config.host}:{config.port}")


    @mcp_server.tool()
    def query_studies(
        patient_id: str = "", 
        study_date: str = "", 
        modality_in_study: str = "",
        study_description: str = "", 
        accession_number: str = "", 
        study_instance_uid: str = "",
        attribute_preset: str = "standard", 
        additional_attributes: List[str] = None,
        exclude_attributes: List[str] = None, 
        ctx: Context = None
    ) -> List[Dict[str, Any]]:
        """Query studies matching the specified criteria.
        
        Args:
            patient_id: Patient ID
            study_date: Study date or date range (YYYYMMDD or YYYYMMDD-YYYYMMDD)
            modality_in_study: Modalities in study (e.g., "CT" or "CT\\MR")
            study_description: Study description (can include wildcards * and ?)
            accession_number: Accession number
            study_instance_uid: Study Instance UID
            attribute_preset: Attribute preset (minimal, standard, extended)
            additional_attributes: Additional attributes to query
            exclude_attributes: Attributes to exclude from query results
            
        Returns:
            List of matching study records
        """
        dicom_ctx = ctx.lifespan_context
        ae = dicom_ctx.ae
        config = dicom_ctx.config
        
        # Create query dataset
        ds = Dataset()
        ds.QueryRetrieveLevel = "STUDY"
        
        # Add query parameters if provided
        if patient_id:
            ds.PatientID = patient_id
        
        if study_date:
            ds.StudyDate = study_date
            
        if modality_in_study:
            ds.ModalitiesInStudy = modality_in_study
            
        if study_description:
            ds.StudyDescription = study_description
            
        if accession_number:
            ds.AccessionNumber = accession_number
            
        if study_instance_uid:
            ds.StudyInstanceUID = study_instance_uid
        
        # Add attributes based on preset
        attrs = get_attributes_for_level("study", attribute_preset, additional_attributes, exclude_attributes)
        for attr in attrs:
            if not hasattr(ds, attr):
                setattr(ds, attr, "")
        
        # Associate with the DICOM server
        assoc = ae.associate(config.host, config.port, ae_title=config.ae_title)
        
        if assoc.is_established:
            # Send C-FIND request
            responses = assoc.send_c_find(ds, StudyRootQueryRetrieveInformationModelFind)
            results = handle_c_find_response(responses)
            assoc.release()
            return results
        else:
            raise ErrorResponse(f"Failed to associate with DICOM server at {config.host}:{config.port}")


    @mcp_server.tool()
    def query_series(
        study_instance_uid: str, 
        modality: str = "", 
        series_number: str = "",
        series_description: str = "", 
        series_instance_uid: str = "",
        attribute_preset: str = "standard", 
        additional_attributes: List[str] = None,
        exclude_attributes: List[str] = None, 
        ctx: Context = None
    ) -> List[Dict[str, Any]]:
        """Query series matching the specified criteria within a study.
        
        Args:
            study_instance_uid: Study Instance UID
            modality: Modality (e.g., "CT", "MR")
            series_number: Series number
            series_description: Series description (can include wildcards * and ?)
            series_instance_uid: Series Instance UID
            attribute_preset: Attribute preset (minimal, standard, extended)
            additional_attributes: Additional attributes to query
            exclude_attributes: Attributes to exclude from query results
            
        Returns:
            List of matching series records
        """
        dicom_ctx = ctx.lifespan_context
        ae = dicom_ctx.ae
        config = dicom_ctx.config
        
        # Create query dataset
        ds = Dataset()
        ds.QueryRetrieveLevel = "SERIES"
        ds.StudyInstanceUID = study_instance_uid
        
        # Add query parameters if provided
        if modality:
            ds.Modality = modality
        
        if series_number:
            ds.SeriesNumber = series_number
            
        if series_description:
            ds.SeriesDescription = series_description
            
        if series_instance_uid:
            ds.SeriesInstanceUID = series_instance_uid
        
        # Add attributes based on preset
        attrs = get_attributes_for_level("series", attribute_preset, additional_attributes, exclude_attributes)
        for attr in attrs:
            if not hasattr(ds, attr):
                setattr(ds, attr, "")
        
        # Associate with the DICOM server
        assoc = ae.associate(config.host, config.port, ae_title=config.ae_title)
        
        if assoc.is_established:
            # Send C-FIND request
            responses = assoc.send_c_find(ds, StudyRootQueryRetrieveInformationModelFind)
            results = handle_c_find_response(responses)
            assoc.release()
            return results
        else:
            raise ErrorResponse(f"Failed to associate with DICOM server at {config.host}:{config.port}")


    @mcp_server.tool()
    def query_instances(
        series_instance_uid: str, 
        instance_number: str = "", 
        sop_instance_uid: str = "",
        attribute_preset: str = "standard", 
        additional_attributes: List[str] = None,
        exclude_attributes: List[str] = None, 
        ctx: Context = None
    ) -> List[Dict[str, Any]]:
        """Query instances matching the specified criteria within a series.
        
        Args:
            series_instance_uid: Series Instance UID
            instance_number: Instance number
            sop_instance_uid: SOP Instance UID
            attribute_preset: Attribute preset (minimal, standard, extended)
            additional_attributes: Additional attributes to query
            exclude_attributes: Attributes to exclude from query results
            
        Returns:
            List of matching instance records
        """
        dicom_ctx = ctx.lifespan_context
        ae = dicom_ctx.ae
        config = dicom_ctx.config
        
        # Create query dataset
        ds = Dataset()
        ds.QueryRetrieveLevel = "IMAGE"
        ds.SeriesInstanceUID = series_instance_uid
        
        # Add query parameters if provided
        if instance_number:
            ds.InstanceNumber = instance_number
        
        if sop_instance_uid:
            ds.SOPInstanceUID = sop_instance_uid
        
        # Add attributes based on preset
        attrs = get_attributes_for_level("instance", attribute_preset, additional_attributes, exclude_attributes)
        for attr in attrs:
            if not hasattr(ds, attr):
                setattr(ds, attr, "")
        
        # Associate with the DICOM server
        assoc = ae.associate(config.host, config.port, ae_title=config.ae_title)
        
        if assoc.is_established:
            # Send C-FIND request
            responses = assoc.send_c_find(ds, StudyRootQueryRetrieveInformationModelFind)
            results = handle_c_find_response(responses)
            assoc.release()
            return results
        else:
            raise ErrorResponse(f"Failed to associate with DICOM server at {config.host}:{config.port}")


    @mcp_server.tool()
    def get_attribute_presets() -> Dict[str, Dict[str, List[str]]]:
        """Get all available attribute presets for queries.
        
        Returns:
            Dictionary of attribute presets for each query level
        """
        return ATTRIBUTE_PRESETS