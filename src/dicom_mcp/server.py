"""
DICOM MCP Server main implementation.
"""

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Dict, List, Any, AsyncIterator

from mcp.server.fastmcp import FastMCP, Context

from .attributes import ATTRIBUTE_PRESETS
from .dicom_client import DicomClient
from .config import DicomConfiguration, load_config

# Configure logging
logger = logging.getLogger("dicom_mcp")


@dataclass
class DicomContext:
    """Context for the DICOM MCP server."""
    config: DicomConfiguration
    client: DicomClient


def create_dicom_mcp_server(config_path: str, name: str = "DICOM MCP") -> FastMCP:
    """Create and configure a DICOM MCP server."""
    
    # Define a simple lifespan function
    @asynccontextmanager
    async def lifespan(server: FastMCP) -> AsyncIterator[DicomContext]:
        # Load config
        config = load_config(config_path)
        
        # Get the current node and calling AE title
        current_node = config.nodes[config.current_node]
        current_aet = config.calling_aets[config.current_calling_aet]
        
        # Create client
        client = DicomClient(
            host=current_node.host,
            port=current_node.port,
            calling_aet=current_aet.ae_title,
            called_aet=current_node.ae_title
        )
        
        logger.info(f"DICOM client initialized: {config.current_node} (calling AE: {current_aet.ae_title})")
        
        try:
            yield DicomContext(config=config, client=client)
        finally:
            pass
    
    # Create server
    mcp = FastMCP(name, lifespan=lifespan)
    
    # Register tools
    @mcp.tool()
    def list_dicom_nodes(ctx: Context = None) -> Dict[str, Any]:
        """List all configured DICOM nodes and show which one is currently selected."""
        dicom_ctx = ctx.request_context.lifespan_context
        config = dicom_ctx.config
        
        return {
            "current_node": config.current_node,
            "nodes": list(config.nodes.keys()),
            "current_calling_aet": config.current_calling_aet,
            "calling_aets": list(config.calling_aets.keys())
        }
    
    @mcp.tool()
    def retrieve_instance(
        study_instance_uid: str,
        series_instance_uid: str,
        sop_instance_uid: str,
        output_directory: str = "./retrieved_files",
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Retrieve a specific DICOM instance and save it to the local filesystem.
        
        Args:
            study_instance_uid: Study Instance UID
            series_instance_uid: Series Instance UID
            sop_instance_uid: SOP Instance UID
            output_directory: Directory to save the retrieved instance to
            ctx: Context object
            
        Returns:
            Dictionary with information about the retrieval operation
        """
        dicom_ctx = ctx.request_context.lifespan_context
        client:DicomClient = dicom_ctx.client
        
        return client.retrieve_instance(
            study_instance_uid=study_instance_uid,
            series_instance_uid=series_instance_uid,
            sop_instance_uid=sop_instance_uid,
            output_dir=output_directory
        )


    @mcp.tool()
    def switch_dicom_node(node_name: str, ctx: Context = None) -> Dict[str, Any]:
        """Switch to a different configured DICOM node."""
        dicom_ctx = ctx.request_context.lifespan_context
        config = dicom_ctx.config
        
        # Check if node exists
        if node_name not in config.nodes:
            raise ValueError(f"Node '{node_name}' not found in configuration")
        
        # Update configuration
        config.current_node = node_name
        
        # Create a new client with the updated configuration
        current_node = config.nodes[config.current_node]
        current_aet = config.calling_aets[config.current_calling_aet]
        
        # Replace the client with a new instance
        dicom_ctx.client = DicomClient(
            host=current_node.host,
            port=current_node.port,
            calling_aet=current_aet.ae_title,
            called_aet=current_node.ae_title
        )
        
        return {
            "success": True,
            "message": f"Switched to DICOM node: {node_name}"
        }

    @mcp.tool()
    def switch_calling_aet(aet_name: str, ctx: Context = None) -> Dict[str, Any]:
        """Switch to a different configured calling AE title."""
        dicom_ctx = ctx.request_context.lifespan_context
        config = dicom_ctx.config
        
        # Check if calling AE title exists
        if aet_name not in config.calling_aets:
            raise ValueError(f"Calling AE title '{aet_name}' not found in configuration")
        
        # Update configuration
        config.current_calling_aet = aet_name
        
        # Create a new client with the updated configuration
        current_node = config.nodes[config.current_node]
        current_aet = config.calling_aets[config.current_calling_aet]
        
        # Replace the client with a new instance
        dicom_ctx.client = DicomClient(
            host=current_node.host,
            port=current_node.port,
            calling_aet=current_aet.ae_title,
            called_aet=current_node.ae_title
        )
        
        return {
            "success": True,
            "message": f"Switched to calling AE title: {aet_name} ({current_aet.ae_title})"
        }

    @mcp.tool()
    def verify_connection(ctx: Context = None) -> str:
        """Verify connectivity to the DICOM node using C-ECHO."""
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
        client = dicom_ctx.client
        
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

This DICOM Model Context Protocol (MCP) server allows you to interact with medical imaging data from DICOM nodes.

## Node Management
1. View available DICOM nodes and calling AE titles:
   ```
   list_dicom_nodes()
   ```

2. Switch to a different node:
   ```
   switch_dicom_node(node_name="research")
   ```

3. Switch to a different calling AE title:
   ```
   switch_calling_aet(aet_name="modality")
   ```

4. Verify the connection:
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