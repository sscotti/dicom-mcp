"""
DICOM MCP Server main implementation.
"""

import os
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Dict, List, Any, AsyncIterator

from mcp.server.fastmcp import FastMCP, Context

from .attributes import ATTRIBUTE_PRESETS
from .dicom_api import DicomClient
from .server_config import ServerConfigManager

# Configure logging
logger = logging.getLogger("dicom_mcp")

# Get config file path from environment variable or use default


@dataclass
class DicomContext:
    """Context for the DICOM MCP server."""
    client: DicomClient
    config_manager: ServerConfigManager


def create_dicom_mcp_server(config_path:str, name: str = "DICOM MCP") -> FastMCP:
    """Create and configure a DICOM MCP server."""
    
    # Define a simple lifespan function
    @asynccontextmanager
    async def lifespan(server: FastMCP) -> AsyncIterator[DicomContext]:
        # Load config
        config_manager = ServerConfigManager(config_path)
        server_config = config_manager.get_current_server()
        
        if not server_config:
            raise RuntimeError(f"No current server configured in {config_path}")
        
        # Create client
        client = DicomClient(
            host=server_config.get('host'),
            port=server_config.get('port'),
            called_aet=server_config.get('ae_title')
        )
        
        logger.info(f"DICOM client initialized: {config_manager.current_server}")
        
        try:
            yield DicomContext(client=client, config_manager=config_manager)
        finally:
            pass
    
    # Create server
    mcp = FastMCP(name, lifespan=lifespan)
    
    # Register tools
    @mcp.tool()
    def list_dicom_servers(ctx: Context = None) -> Dict[str, Any]:
        """List all configured DICOM servers and show which one is currently selected."""
        dicom_ctx = ctx.request_context.lifespan_context
        config_manager = dicom_ctx.config_manager
        
        # Get current server name
        
        return {
            "current_server": config_manager.current_server,
            "servers": list(config_manager.servers.keys())
        }
    
    @mcp.tool()
    def switch_dicom_server(server_name: str, ctx: Context = None) -> Dict[str, Any]:
        """Switch to a different configured DICOM server."""
        dicom_ctx = ctx.request_context.lifespan_context
        config_manager = dicom_ctx.config_manager
        
        # Check if server exists
        if server_name not in config_manager.servers:
            raise ValueError(f"Server '{server_name}' not found in configuration")
        
        # Set the current server
        success = config_manager.set_current_server(server_name)
        if not success:
            raise RuntimeError(f"Failed to switch to server '{server_name}'")
        
        # Get the server configuration
        server_config = config_manager.get_current_server()
        
        # Update the client
        dicom_ctx.client.host = server_config.get('host')
        dicom_ctx.client.port = server_config.get('port')
        dicom_ctx.client.ae_title = server_config.get('ae_title')
        
        return {
            "success": True,
            "message": f"Switched to DICOM server: {server_name}"
        }

    @mcp.tool()
    def verify_connection(ctx: Context = None) -> str:
        """Verify connectivity to the DICOM server using C-ECHO."""
        dicom_ctx = ctx.request_context.lifespan_context
        client = dicom_ctx.client
        
        success, message = client.verify_connection()
        return message

    @mcp.tool()
    def query_patients(
        name_pattern: str = "", 
        patient_id: str = "", 
        birth_date: str = "", 
        attribute_preset: str = "standard", 
        additional_attributes: List[str] = None,
        exclude_attributes: List[str] = None, 
        ctx: Context = None
    ) -> List[Dict[str, Any]]:
        """Query patients matching the specified criteria."""
        dicom_ctx = ctx.request_context.lifespan_context
        client :DicomClient = dicom_ctx.client
        
        try:
            return client.query_patient(
                patient_id=patient_id,
                name_pattern=name_pattern,
                birth_date=birth_date,
                attribute_preset=attribute_preset,
                additional_attrs=additional_attributes,
                exclude_attrs=exclude_attributes
            )
        except Exception as e:
            raise Exception(f"Error querying patients: {str(e)}")

    @mcp.tool()
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
        """Query studies matching the specified criteria."""
        dicom_ctx = ctx.request_context.lifespan_context
        client = dicom_ctx.client
        
        try:
            return client.query_study(
                patient_id=patient_id,
                study_date=study_date,
                modality=modality_in_study,
                study_description=study_description,
                accession_number=accession_number,
                study_instance_uid=study_instance_uid,
                attribute_preset=attribute_preset,
                additional_attrs=additional_attributes,
                exclude_attrs=exclude_attributes
            )
        except Exception as e:
            raise Exception(f"Error querying studies: {str(e)}")

    @mcp.tool()
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
        """Query series matching the specified criteria within a study."""
        dicom_ctx = ctx.request_context.lifespan_context
        client = dicom_ctx.client
        
        try:
            return client.query_series(
                study_instance_uid=study_instance_uid,
                series_instance_uid=series_instance_uid,
                modality=modality,
                series_number=series_number,
                series_description=series_description,
                attribute_preset=attribute_preset,
                additional_attrs=additional_attributes,
                exclude_attrs=exclude_attributes
            )
        except Exception as e:
            raise Exception(f"Error querying series: {str(e)}")

    @mcp.tool()
    def query_instances(
        series_instance_uid: str, 
        instance_number: str = "", 
        sop_instance_uid: str = "",
        attribute_preset: str = "standard", 
        additional_attributes: List[str] = None,
        exclude_attributes: List[str] = None, 
        ctx: Context = None 
    ) -> List[Dict[str, Any]]:
        """Query instances matching the specified criteria within a series."""
        dicom_ctx = ctx.request_context.lifespan_context
        client = dicom_ctx.client
        
        try:
            return client.query_instance(
                series_instance_uid=series_instance_uid,
                sop_instance_uid=sop_instance_uid,
                instance_number=instance_number,
                attribute_preset=attribute_preset,
                additional_attrs=additional_attributes,
                exclude_attrs=exclude_attributes
            )
        except Exception as e:
            raise Exception(f"Error querying instances: {str(e)}")

    @mcp.tool()
    def get_attribute_presets() -> Dict[str, Dict[str, List[str]]]:
        """Get all available attribute presets for queries."""
        return ATTRIBUTE_PRESETS

    # Register prompt
    @mcp.prompt()
    def dicom_query_guide() -> str:
        """Prompt for guiding users on how to query DICOM data."""
        return """
DICOM Query Guide

This DICOM Model Context Protocol (MCP) server allows you to interact with medical imaging data from DICOM servers.

## Server Management
1. View available DICOM servers:
   ```
   list_dicom_servers()
   ```

2. Switch to a different server:
   ```
   switch_dicom_server(server_name="orthanc-research")
   ```

3. Verify the connection:
   ```
   verify_connection()
   ```

## Search Queries
For flexible search operations:

1. Search for patients:
   ```
   query_patients(name_pattern="SMITH*")
   ```

2. Search for studies:
   ```
   query_studies(patient_id="12345678", study_date="20230101-20231231")
   ```

3. Search for series:
   ```
   query_series(study_instance_uid="1.2.840.10008.5.1.4.1.1.2.1.1", modality="CT")
   ```

4. Search for instances:
   ```
   query_instances(series_instance_uid="1.2.840.10008.5.1.4.1.1.2.1.2")
   ```

## Attribute Presets
For all queries, you can specify an attribute preset:
- `minimal`: Basic identifiers only
- `standard`: Common clinical attributes
- `extended`: Comprehensive information

Example:
```
query_studies(patient_id="12345678", attribute_preset="extended")
```

You can also customize attributes:
```
query_studies(
    patient_id="12345678", 
    additional_attributes=["StudyComments"], 
    exclude_attributes=["AccessionNumber"]
)
```

To view available attribute presets:
```
get_attribute_presets()
```
"""
    
    return mcp