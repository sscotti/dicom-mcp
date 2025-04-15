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
        """List all configured DICOM nodes and their connection information.
        
        This tool returns information about all configured DICOM nodes in the system
        and shows which node is currently selected for operations. It also provides
        information about available calling AE titles.
        
        Returns:
            Dictionary containing:
            - current_node: The currently selected DICOM node name
            - nodes: List of all configured node names
            - current_calling_aet: The currently selected calling AE title
            - calling_aets: List of all configured calling AE title names
        
        Example:
            {
                "current_node": "pacs1",
                "nodes": ["pacs1", "pacs2", "orthanc"],
                "current_calling_aet": "client1",
                "calling_aets": ["client1", "client2"]
            }
        """
        dicom_ctx = ctx.request_context.lifespan_context
        config = dicom_ctx.config
        
        return {
            "current_node": config.current_node,
            "nodes": list(config.nodes.keys()),
            "current_calling_aet": config.current_calling_aet,
            "calling_aets": list(config.calling_aets.keys())
        }
    
    @mcp.tool()
    def extract_pdf_text_from_dicom(
        study_instance_uid: str,
        series_instance_uid: str,
        sop_instance_uid: str,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Retrieve a DICOM instance with encapsulated PDF and extract its text content.
        
        This tool retrieves a DICOM instance containing an encapsulated PDF document,
        extracts the PDF, and converts it to text. This is particularly useful for
        medical reports stored as PDFs within DICOM format (e.g., radiology reports,
        clinical documents).
        
        Args:
            study_instance_uid: The unique identifier for the study (required)
            series_instance_uid: The unique identifier for the series within the study (required)
            sop_instance_uid: The unique identifier for the specific DICOM instance (required)
        
        Returns:
            Dictionary containing:
            - success: Boolean indicating if the operation was successful
            - message: Description of the operation result or error
            - text_content: The extracted text from the PDF (if successful)
            - file_path: Path to the temporary DICOM file (for debugging purposes)
        
        Example:
            {
                "success": true,
                "message": "Successfully extracted text from PDF in DICOM",
                "text_content": "Patient report contents...",
                "file_path": "/tmp/tmpdir123/1.2.3.4.5.6.7.8.dcm"
            }
        """
        dicom_ctx = ctx.request_context.lifespan_context
        client:DicomClient = dicom_ctx.client
        
        return client.extract_pdf_text_from_dicom(
            study_instance_uid=study_instance_uid,
            series_instance_uid=series_instance_uid,
            sop_instance_uid=sop_instance_uid
        )

    @mcp.tool()
    def switch_dicom_node(node_name: str, ctx: Context = None) -> Dict[str, Any]:
        """Switch the active DICOM node connection to a different configured node.
        
        This tool changes which DICOM node (PACS, workstation, etc.) subsequent operations
        will connect to. The node must be defined in the configuration file.
        
        Args:
            node_name: The name of the node to switch to, must match a name in the configuration
        
        Returns:
            Dictionary containing:
            - success: Boolean indicating if the switch was successful
            - message: Description of the operation result or error
        
        Example:
            {
                "success": true,
                "message": "Switched to DICOM node: orthanc"
            }
        
        Raises:
            ValueError: If the specified node name is not found in configuration
        """        
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
        """Switch to a different configured calling AE title.
        
        This tool changes which Application Entity (AE) title will be used as the calling
        AE title in subsequent DICOM operations. The AE title must be defined in the configuration file.
        
        Args:
            aet_name: The name of the AE title configuration to switch to
        
        Returns:
            Dictionary containing:
            - success: Boolean indicating if the switch was successful
            - message: Description of the operation result or error
        
        Example:
            {
                "success": true,
                "message": "Switched to calling AE title: clientA (CLIENTA_AET)"
            }
        
        Raises:
            ValueError: If the specified AE title is not found in configuration
        """
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
        """Verify connectivity to the current DICOM node using C-ECHO.
        
        This tool performs a DICOM C-ECHO operation (similar to a network ping) to check
        if the currently selected DICOM node is reachable and responds correctly. This is
        useful to troubleshoot connection issues before attempting other operations.
        
        Returns:
            A message describing the connection status, including host, port, and AE titles
        
        Example:
            "Connection successful to 192.168.1.100:104 (Called AE: ORTHANC, Calling AE: CLIENT)"
        """
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
        """Query patients matching the specified criteria from the DICOM node.
        
        This tool performs a DICOM C-FIND operation at the PATIENT level to find patients
        matching the provided search criteria. All search parameters are optional and can
        be combined for more specific queries.
        
        Args:
            name_pattern: Patient name pattern (can include wildcards * and ?), e.g., "SMITH*"
            patient_id: Patient ID to search for, e.g., "12345678"
            birth_date: Patient birth date in YYYYMMDD format, e.g., "19700101"
            attribute_preset: Controls which attributes to include in results:
                - "minimal": Only essential attributes
                - "standard": Common attributes (default)
                - "extended": All available attributes
            additional_attributes: List of specific DICOM attributes to include beyond the preset
            exclude_attributes: List of DICOM attributes to exclude from the results
        
        Returns:
            List of dictionaries, each representing a matched patient with their attributes
        
        Example:
            [
                {
                    "PatientID": "12345",
                    "PatientName": "SMITH^JOHN",
                    "PatientBirthDate": "19700101",
                    "PatientSex": "M"
                }
            ]
        
        Raises:
            Exception: If there is an error communicating with the DICOM node
        """
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
        """Query studies matching the specified criteria from the DICOM node.
        
        This tool performs a DICOM C-FIND operation at the STUDY level to find studies
        matching the provided search criteria. All search parameters are optional and can
        be combined for more specific queries.
        
        Args:
            patient_id: Patient ID to search for, e.g., "12345678"
            study_date: Study date or date range in DICOM format:
                - Single date: "20230101"
                - Date range: "20230101-20230131"
            modality_in_study: Filter by modalities present in study, e.g., "CT" or "MR"
            study_description: Study description text (can include wildcards), e.g., "CHEST*"
            accession_number: Medical record accession number
            study_instance_uid: Unique identifier for a specific study
            attribute_preset: Controls which attributes to include in results:
                - "minimal": Only essential attributes
                - "standard": Common attributes (default)
                - "extended": All available attributes
            additional_attributes: List of specific DICOM attributes to include beyond the preset
            exclude_attributes: List of DICOM attributes to exclude from the results
        
        Returns:
            List of dictionaries, each representing a matched study with its attributes
        
        Example:
            [
                {
                    "StudyInstanceUID": "1.2.840.113619.2.1.1.322.1600364094.412.1009",
                    "StudyDate": "20230215",
                    "StudyDescription": "CHEST CT",
                    "PatientID": "12345",
                    "PatientName": "SMITH^JOHN",
                    "ModalitiesInStudy": "CT"
                }
            ]
        
        Raises:
            Exception: If there is an error communicating with the DICOM node
        """
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
        """Query series within a study from the DICOM node.
        
        This tool performs a DICOM C-FIND operation at the SERIES level to find series
        within a specified study. The study_instance_uid is required, and additional
        parameters can be used to filter the results.
        
        Args:
            study_instance_uid: Unique identifier for the study (required)
            modality: Filter by imaging modality, e.g., "CT", "MR", "US", "CR"
            series_number: Filter by series number
            series_description: Series description text (can include wildcards), e.g., "AXIAL*"
            series_instance_uid: Unique identifier for a specific series
            attribute_preset: Controls which attributes to include in results:
                - "minimal": Only essential attributes
                - "standard": Common attributes (default)
                - "extended": All available attributes
            additional_attributes: List of specific DICOM attributes to include beyond the preset
            exclude_attributes: List of DICOM attributes to exclude from the results
        
        Returns:
            List of dictionaries, each representing a matched series with its attributes
        
        Example:
            [
                {
                    "SeriesInstanceUID": "1.2.840.113619.2.1.1.322.1600364094.412.2005",
                    "SeriesNumber": "2",
                    "SeriesDescription": "AXIAL 2.5MM",
                    "Modality": "CT",
                    "NumberOfSeriesRelatedInstances": "120"
                }
            ]
        
        Raises:
            Exception: If there is an error communicating with the DICOM node
        """
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
        """Query individual DICOM instances (images) within a series.
        
        This tool performs a DICOM C-FIND operation at the IMAGE level to find individual
        DICOM instances within a specified series. The series_instance_uid is required,
        and additional parameters can be used to filter the results.
        
        Args:
            series_instance_uid: Unique identifier for the series (required)
            instance_number: Filter by specific instance number within the series
            sop_instance_uid: Unique identifier for a specific instance
            attribute_preset: Controls which attributes to include in results:
                - "minimal": Only essential attributes
                - "standard": Common attributes (default)
                - "extended": All available attributes
            additional_attributes: List of specific DICOM attributes to include beyond the preset
            exclude_attributes: List of DICOM attributes to exclude from the results
        
        Returns:
            List of dictionaries, each representing a matched instance with its attributes
        
        Example:
            [
                {
                    "SOPInstanceUID": "1.2.840.113619.2.1.1.322.1600364094.412.3001",
                    "SOPClassUID": "1.2.840.10008.5.1.4.1.1.2",
                    "InstanceNumber": "45",
                    "ContentDate": "20230215",
                    "ContentTime": "152245"
                }
            ]
        
        Raises:
            Exception: If there is an error communicating with the DICOM node
        """
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
        """Get all available attribute presets for DICOM queries.
        
        This tool returns the defined attribute presets that can be used with the
        query_* functions. It shows which DICOM attributes are included in each
        preset (minimal, standard, extended) for each query level.
        
        Returns:
            Dictionary organized by query level (patient, study, series, instance),
            with each level containing the attribute presets and their associated
            DICOM attributes.
        
        Example:
            {
                "patient": {
                    "minimal": ["PatientID", "PatientName"],
                    "standard": ["PatientID", "PatientName", "PatientBirthDate", "PatientSex"],
                    "extended": ["PatientID", "PatientName", "PatientBirthDate", "PatientSex", ...]
                },
                "study": {
                    "minimal": ["StudyInstanceUID", "StudyDate"],
                    "standard": ["StudyInstanceUID", "StudyDate", "StudyDescription", ...],
                    "extended": ["StudyInstanceUID", "StudyDate", "StudyDescription", ...]
                },
                ...
            }
        """
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