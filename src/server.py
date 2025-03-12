"""
DICOM MCP Server main implementation.
"""

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Optional

from pynetdicom import AE
from pynetdicom.sop_class import (
    PatientRootQueryRetrieveInformationModelFind,
    PatientRootQueryRetrieveInformationModelGet,
    PatientRootQueryRetrieveInformationModelMove,
    StudyRootQueryRetrieveInformationModelFind,
    StudyRootQueryRetrieveInformationModelGet,
    StudyRootQueryRetrieveInformationModelMove,
    Verification,
)

from mcp.server.fastmcp import FastMCP

from .config import DicomServerConfig
from .resources import register_resources
from .tools import register_tools

# Configure logging
logger = logging.getLogger("dicom_mcp")


@dataclass
class DicomMCPContext:
    """Context for the DICOM MCP server."""
    config: DicomServerConfig
    ae: AE


@asynccontextmanager
async def dicom_lifespan(server: FastMCP) -> AsyncIterator[DicomMCPContext]:
    """Initialize and clean up the DICOM AE for the MCP server.
    
    This function is called when the MCP server starts and stops.
    """
    # Initialize configuration - try environment variables first, then defaults
    config = DicomServerConfig.from_env()
    
    # Create the Application Entity
    ae = AE(ae_title="MCPSCU")
    
    # Add the necessary presentation contexts
    ae.add_requested_context(Verification)
    ae.add_requested_context(PatientRootQueryRetrieveInformationModelFind)
    ae.add_requested_context(PatientRootQueryRetrieveInformationModelGet)
    ae.add_requested_context(PatientRootQueryRetrieveInformationModelMove)
    ae.add_requested_context(StudyRootQueryRetrieveInformationModelFind)
    ae.add_requested_context(StudyRootQueryRetrieveInformationModelGet)
    ae.add_requested_context(StudyRootQueryRetrieveInformationModelMove)
    
    logger.info(f"DICOM AE initialized with AE title: {ae.ae_title}")
    logger.info(f"Default DICOM server: {config.host}:{config.port}")
    
    try:
        # Yield the context to the server
        yield DicomMCPContext(config=config, ae=ae)
    finally:
        # Clean up the AE
        logger.info("Cleaning up DICOM AE")


def create_dicom_mcp_server(name: str = "DICOM MCP") -> FastMCP:
    """Create and configure a DICOM MCP server.
    
    Args:
        name: Name of the MCP server
        
    Returns:
        Configured FastMCP server instance
    """
    # Create the MCP server
    mcp = FastMCP(name, lifespan=dicom_lifespan)
    
    # Register resources and tools
    register_resources(mcp)
    register_tools(mcp)
    
    # Register prompts
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
    
    return mcp


# Run the server if executed directly
if __name__ == "__main__":
    mcp = create_dicom_mcp_server()
    mcp.run()