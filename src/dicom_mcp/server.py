"""
DICOM MCP Server main implementation.

This implementation provides a Model Context Protocol interface
for interacting with DICOM servers via pynetdicom.
"""

import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Dict, List, Any, Optional

from mcp.server.fastmcp import FastMCP, Context

from .attributes import ATTRIBUTE_PRESETS
from .config import DicomConfig
from .dicom_api import DicomClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dicom_mcp")


@dataclass
class DicomContext:
    """Context for the DICOM MCP server."""
    config: DicomConfig
    client: DicomClient


@asynccontextmanager
async def dicom_lifespan(server: FastMCP) -> AsyncIterator[DicomContext]:
    """Initialize and clean up the DICOM client for the MCP server."""
    # Initialize configuration from environment variables
    config = DicomConfig.from_env()
    
    # Create the DICOM client
    client = DicomClient(
        host=config.host,
        port=config.port,
        ae_title=config.ae_title
    )
    
    logger.info(f"DICOM client initialized")
    logger.info(f"Default DICOM server: {config.host}:{config.port}")
    
    try:
        # Yield the context to the server
        yield DicomContext(config=config, client=client)
    finally:
        # Clean up (no specific cleanup needed for DicomClient)
        logger.info("Cleaning up DICOM client")


# Resources

def register_resources(mcp: FastMCP) -> None:
    """Register all resource handlers with the MCP server."""
    
    # @mcp.resource("dicom://config")
    # def get_dicom_config() -> str:
    #     """Get the current DICOM server configuration."""
    #     dicom_ctx = ctx.lifespan_context
    #     config = dicom_ctx.config
        
    #     return json.dumps({
    #         "host": config.host,
    #         "port": config.port,
    #         "ae_title": config.ae_title
    #     })

    # @mcp.resource("patient://{patient_id}")
    # def get_patient(patient_id: str) -> str:
    #     """Get patient information by Patient ID."""
    #     dicom_ctx = ctx.lifespan_context
    #     client = dicom_ctx.client
        
    #     try:
    #         # Get the specific patient
    #         result = client.get_entity_by_id("patient", patient_id)
    #         return json.dumps(result)
    #     except Exception as e:
    #         raise Exception(f"Error querying patient: {str(e)}")

    # @mcp.resource("study://{study_instance_uid}")
    # def get_study(study_instance_uid: str) -> str:
    #     """Get study information by Study Instance UID."""
    #     dicom_ctx = ctx.lifespan_context
    #     client = dicom_ctx.client
        
    #     try:
    #         # Get the specific study
    #         result = client.get_entity_by_id("study", study_instance_uid)
    #         return json.dumps(result)
    #     except Exception as e:
    #         raise Exception(f"Error querying study: {str(e)}")

    # @mcp.resource("series://{series_instance_uid}")
    # def get_series(series_instance_uid: str) -> str:
    #     """Get series information by Series Instance UID."""
    #     dicom_ctx = ctx.lifespan_context
    #     client = dicom_ctx.client
        
    #     try:
    #         # Get the specific series
    #         result = client.get_entity_by_id("series", series_instance_uid)
    #         return json.dumps(result)
    #     except Exception as e:
    #         raise Exception(f"Error querying series: {str(e)}")

    # @mcp.resource("instance://{sop_instance_uid}")
    # def get_instance(sop_instance_uid: str,) -> str:
    #     """Get instance information by SOP Instance UID."""
    #     dicom_ctx = ctx.lifespan_context
    #     client = dicom_ctx.client
        
    #     try:
    #         # Get the specific instance
    #         result = client.get_entity_by_id("instance", sop_instance_uid)
    #         return json.dumps(result)
    #     except Exception as e:
    #         raise Exception(f"Error querying instance: {str(e)}")


# Tools

def register_tools(mcp: FastMCP) -> None:
    """Register all tool handlers with the MCP server."""
    
    @mcp.tool()
    def configure_dicom_server(
        host: str, 
        port: int, 
        ae_title: str = "MCPSCU", 
        ctx: Context = None,
    ) -> str:
        """Configure the DICOM server connection."""
        dicom_ctx = ctx.lifespan_context
        config = dicom_ctx.config
        client = dicom_ctx.client
        
        # Update configuration
        config.host = host
        config.port = port
        config.ae_title = ae_title
        
        # Update client
        client.host = host
        client.port = port
        client.ae_title = ae_title
        
        return f"DICOM server configuration updated: {host}:{port} (AET: {ae_title})"

    @mcp.tool()
    def verify_connection(ctx: Context = None) -> str:
        """Verify connectivity to the DICOM server using C-ECHO."""
        dicom_ctx = ctx.lifespan_context
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
        dicom_ctx = ctx.lifespan_context
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
        dicom_ctx = ctx.lifespan_context
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
        dicom_ctx = ctx.lifespan_context
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
        dicom_ctx = ctx.lifespan_context
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


# Prompts

def register_prompts(mcp: FastMCP) -> None:
    """Register all prompts with the MCP server."""
    
    @mcp.prompt()
    def dicom_query_guide() -> str:
        """Prompt for guiding users on how to query DICOM data."""
        return """
DICOM Query Guide

This DICOM Model Context Protocol (MCP) server allows you to interact with medical imaging data from a DICOM server.

## Server Configuration
1. Configure your DICOM server connection:
   ```
   configure_dicom_server(host="192.168.1.100", port=11112, ae_title="MYPACSAET")
   ```

2. Verify the connection:
   ```
   verify_connection()
   ```

## Direct Entity Access (Resources)
For retrieving specific entities by ID:

- Get patient details:
  ```
  await ctx.read_resource(f"patient://{patient_id}")
  ```

- Get study details:
  ```
  await ctx.read_resource(f"study://{study_instance_uid}")
  ```

- Get series details:
  ```
  await ctx.read_resource(f"series://{series_instance_uid}")
  ```

- Get instance details:
  ```
  await ctx.read_resource(f"instance://{sop_instance_uid}")
  ```

## Search Queries (Tools)
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


def create_dicom_mcp_server(name: str = "DICOM MCP") -> FastMCP:
    """Create and configure a DICOM MCP server."""
    # Create the MCP server
    mcp = FastMCP(name, lifespan=dicom_lifespan)
    
    # Register resources, tools, and prompts
    register_resources(mcp)
    register_tools(mcp)
    register_prompts(mcp)
    
    return mcp
