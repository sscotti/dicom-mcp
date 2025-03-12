"""
DICOM MCP Server resource definitions.

Resources provide direct access to specific DICOM entities by their unique identifiers.
For search/query functionality, use the tools instead.
"""

import json
from typing import Dict, Any

from pydicom.dataset import Dataset
from pynetdicom.sop_class import (
    PatientRootQueryRetrieveInformationModelFind, 
    StudyRootQueryRetrieveInformationModelFind
)

from mcp.server.fastmcp import Context
from mcp.server.models import ErrorResponse

from .utils import dataset_to_dict
from .attributes import get_attributes_for_level


def register_resources(mcp_server):
    """Register all resource handlers with the MCP server.
    
    Args:
        mcp_server: FastMCP server instance
    """
    
    @mcp_server.resource("dicom://config")
    def get_dicom_config(ctx: Context) -> str:
        """Get the current DICOM server configuration."""
        dicom_ctx = ctx.lifespan_context
        config = dicom_ctx.config
        
        return json.dumps(config.to_dict())


    @mcp_server.resource("patient://{patient_id}")
    def get_patient(patient_id: str, ctx: Context) -> str:
        """Get patient information by Patient ID.
        
        Args:
            patient_id: The Patient ID to query
            
        Returns:
            JSON string with patient information
        """
        dicom_ctx = ctx.lifespan_context
        ae = dicom_ctx.ae
        config = dicom_ctx.config
        
        # Create C-FIND dataset for Patient-level query
        ds = Dataset()
        ds.PatientID = patient_id
        ds.QueryRetrieveLevel = "PATIENT"
        
        # Add extended attributes for maximum information
        attrs = get_attributes_for_level("patient", "extended")
        for attr in attrs:
            if not hasattr(ds, attr):
                setattr(ds, attr, "")
        
        # Associate with the DICOM server
        assoc = ae.associate(config.host, config.port, ae_title=config.ae_title)
        
        result = {}
        if assoc.is_established:
            # Send C-FIND request
            responses = assoc.send_c_find(ds, PatientRootQueryRetrieveInformationModelFind)
            
            for (status, dataset) in responses:
                if status and status.Status == 0xFF00:  # Pending
                    if dataset:
                        result = dataset_to_dict(dataset)
                        break  # We only expect one patient with this ID
            
            assoc.release()
        else:
            raise ErrorResponse(f"Failed to associate with DICOM server at {config.host}:{config.port}")
        
        return json.dumps(result)


    @mcp_server.resource("study://{study_instance_uid}")
    def get_study(study_instance_uid: str, ctx: Context) -> str:
        """Get study information by Study Instance UID.
        
        Args:
            study_instance_uid: The Study Instance UID to query
            
        Returns:
            JSON string with study information
        """
        dicom_ctx = ctx.lifespan_context
        ae = dicom_ctx.ae
        config = dicom_ctx.config
        
        # Create C-FIND dataset for Study-level query
        ds = Dataset()
        ds.StudyInstanceUID = study_instance_uid
        ds.QueryRetrieveLevel = "STUDY"
        
        # Add extended attributes for maximum information
        attrs = get_attributes_for_level("study", "extended")
        for attr in attrs:
            if not hasattr(ds, attr):
                setattr(ds, attr, "")
        
        # Associate with the DICOM server
        assoc = ae.associate(config.host, config.port, ae_title=config.ae_title)
        
        result = {}
        if assoc.is_established:
            # Send C-FIND request
            responses = assoc.send_c_find(ds, StudyRootQueryRetrieveInformationModelFind)
            
            for (status, dataset) in responses:
                if status and status.Status == 0xFF00:  # Pending
                    if dataset:
                        result = dataset_to_dict(dataset)
                        break  # We only expect one study with this UID
            
            assoc.release()
        else:
            raise ErrorResponse(f"Failed to associate with DICOM server at {config.host}:{config.port}")
        
        return json.dumps(result)


    @mcp_server.resource("series://{series_instance_uid}")
    def get_series(series_instance_uid: str, ctx: Context) -> str:
        """Get series information by Series Instance UID.
        
        Args:
            series_instance_uid: The Series Instance UID to query
            
        Returns:
            JSON string with series information
        """
        dicom_ctx = ctx.lifespan_context
        ae = dicom_ctx.ae
        config = dicom_ctx.config
        
        # Create C-FIND dataset for Series-level query
        ds = Dataset()
        ds.SeriesInstanceUID = series_instance_uid
        ds.QueryRetrieveLevel = "SERIES"
        
        # Add extended attributes for maximum information
        attrs = get_attributes_for_level("series", "extended")
        for attr in attrs:
            if not hasattr(ds, attr):
                setattr(ds, attr, "")
        
        # Associate with the DICOM server
        assoc = ae.associate(config.host, config.port, ae_title=config.ae_title)
        
        result = {}
        if assoc.is_established:
            # Send C-FIND request
            responses = assoc.send_c_find(ds, StudyRootQueryRetrieveInformationModelFind)
            
            for (status, dataset) in responses:
                if status and status.Status == 0xFF00:  # Pending
                    if dataset:
                        result = dataset_to_dict(dataset)
                        break  # We only expect one series with this UID
            
            assoc.release()
        else:
            raise ErrorResponse(f"Failed to associate with DICOM server at {config.host}:{config.port}")
        
        return json.dumps(result)


    @mcp_server.resource("instance://{sop_instance_uid}")
    def get_instance(sop_instance_uid: str, ctx: Context) -> str:
        """Get instance information by SOP Instance UID.
        
        Args:
            sop_instance_uid: The SOP Instance UID to query
            
        Returns:
            JSON string with instance information
        """
        dicom_ctx = ctx.lifespan_context
        ae = dicom_ctx.ae
        config = dicom_ctx.config
        
        # Create C-FIND dataset for Instance-level query
        ds = Dataset()
        ds.SOPInstanceUID = sop_instance_uid
        ds.QueryRetrieveLevel = "IMAGE"
        
        # Add extended attributes for maximum information
        attrs = get_attributes_for_level("instance", "extended")
        for attr in attrs:
            if not hasattr(ds, attr):
                setattr(ds, attr, "")
        
        # Associate with the DICOM server
        assoc = ae.associate(config.host, config.port, ae_title=config.ae_title)
        
        result = {}
        if assoc.is_established:
            # Send C-FIND request
            responses = assoc.send_c_find(ds, StudyRootQueryRetrieveInformationModelFind)
            
            for (status, dataset) in responses:
                if status and status.Status == 0xFF00:  # Pending
                    if dataset:
                        result = dataset_to_dict(dataset)
                        break  # We only expect one instance with this UID
            
            assoc.release()
        else:
            raise ErrorResponse(f"Failed to associate with DICOM server at {config.host}:{config.port}")
        
        return json.dumps(result)