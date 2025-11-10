"""
DICOM MCP Server main implementation.
"""

import logging
import os
import requests
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Dict, List, Any, AsyncIterator, Optional, Tuple

from mcp.server.fastmcp import FastMCP, Context
from pydicom.uid import generate_uid

from .attributes import ATTRIBUTE_PRESETS
from .dicom_client import DicomClient
from .fhir_client import FhirClient
from .mysql_client import MiniRisClient, MiniRisConnectionSettings
from .config import DicomConfiguration, load_config
from .virtual_cr import VirtualCRDevice

# Configure logging
logger = logging.getLogger("dicom_mcp")


@dataclass
class DicomContext:
    """Context for the DICOM MCP server."""
    config: DicomConfiguration
    client: DicomClient
    fhir_client: Optional[FhirClient] = None
    mini_ris_client: Optional[MiniRisClient] = None


def create_dicom_mcp_server(config_path: str, name: str = "DICOM MCP") -> FastMCP:
    """Create and configure a DICOM MCP server."""
    
    # Define a simple lifespan function
    @asynccontextmanager
    async def lifespan(server: FastMCP) -> AsyncIterator[DicomContext]:
        # Load config
        config = load_config(config_path)
        
        # Get the current node and calling AE title
        current_node = config.nodes[config.current_node]
        
        # Create DICOM client
        client = DicomClient(
            host=current_node.host,
            port=current_node.port,
            calling_aet=config.calling_aet,
            called_aet=current_node.ae_title
        )
        
        logger.info(f"DICOM client initialized: {config.current_node} (calling AE: {config.calling_aet})")
        
        # Create FHIR client if configured
        # Support multiple FHIR servers (new) or single fhir (legacy)
        fhir_client = None
        fhir_config = None
        
        if config.fhir_servers and config.current_fhir:
            # Multiple FHIR servers configured
            if config.current_fhir in config.fhir_servers:
                fhir_config = config.fhir_servers[config.current_fhir]
            else:
                logger.warning(f"Current FHIR server '{config.current_fhir}' not found, using first available")
                if config.fhir_servers:
                    config.current_fhir = list(config.fhir_servers.keys())[0]
                    fhir_config = config.fhir_servers[config.current_fhir]
        elif config.fhir:
            # Legacy single FHIR server configuration
            fhir_config = config.fhir
            logger.info("Using legacy single FHIR server configuration")
        
        if fhir_config:
            api_key = fhir_config.api_key or os.getenv("SIIM_API_KEY")
            fhir_client = FhirClient(
                base_url=fhir_config.base_url,
                api_key=api_key
            )
            logger.info(f"FHIR client initialized: {fhir_config.base_url} (server: {config.current_fhir or 'default'})")
        
        mini_ris_client: Optional[MiniRisClient] = None

        if config.mini_ris:
            try:
                mini_ris_settings = MiniRisConnectionSettings(
                    host=config.mini_ris.host,
                    port=config.mini_ris.port,
                    user=config.mini_ris.user,
                    password=config.mini_ris.password,
                    database=config.mini_ris.database,
                    pool_size=config.mini_ris.pool_size,
                )
                mini_ris_client = MiniRisClient(mini_ris_settings)
                # Optional connectivity check
                mini_ris_client.ping()
                logger.info(
                    "Mini-RIS MySQL client initialized (host=%s, db=%s)",
                    config.mini_ris.host,
                    config.mini_ris.database,
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Failed to initialize Mini-RIS client: %s", exc)

        try:
            yield DicomContext(
                config=config,
                client=client,
                fhir_client=fhir_client,
                mini_ris_client=mini_ris_client,
            )
        finally:
            pass
    
    # Create server
    mcp = FastMCP(name, lifespan=lifespan)
    
    # Register tools
    @mcp.tool()
    def list_dicom_nodes(ctx: Context = None) -> Dict[str, Any]:
        """List all configured DICOM nodes and their connection information.
        
        This tool returns information about all configured DICOM nodes in the system
        and shows which node is currently selected for operations.
        
        Returns:
            Dictionary containing current node and available nodes
        """
        dicom_ctx = ctx.request_context.lifespan_context
        config = dicom_ctx.config
        
        return {
            "current_node": config.current_node,
            "nodes": list(config.nodes.keys()),
            "status": "success"
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
        
        # Replace the client with a new instance
        dicom_ctx.client = DicomClient(
            host=current_node.host,
            port=current_node.port,
            calling_aet=config.calling_aet,
            called_aet=current_node.ae_title
        )
        
        return {
            "success": True,
            "message": f"Switched to DICOM node: {node_name}"
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
        additional_attributes: Optional[List[str]] = None,
        exclude_attributes: Optional[List[str]] = None, 
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
                additional_attrs=additional_attributes or [],
                exclude_attrs=exclude_attributes or []
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
        additional_attributes: Optional[List[str]] = None,
        exclude_attributes: Optional[List[str]] = None, 
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
                additional_attrs=additional_attributes or [],
                exclude_attrs=exclude_attributes or []
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
        additional_attributes: Optional[List[str]] = None,
        exclude_attributes: Optional[List[str]] = None, 
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
                additional_attrs=additional_attributes or [],
                exclude_attrs=exclude_attributes or []
            )
        except Exception as e:
            raise Exception(f"Error querying series: {str(e)}")

    @mcp.tool()
    def query_instances(
        series_instance_uid: str, 
        instance_number: str = "", 
        sop_instance_uid: str = "",
        attribute_preset: str = "standard", 
        additional_attributes: Optional[List[str]] = None,
        exclude_attributes: Optional[List[str]] = None, 
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
                additional_attrs=additional_attributes or [],
                exclude_attrs=exclude_attributes or []
            )
        except Exception as e:
            raise Exception(f"Error querying instances: {str(e)}")
        
    @mcp.tool()
    def move_series(
        destination_node: str,
        series_instance_uid: str,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Move a DICOM series to another DICOM node.
        
        This tool transfers a specific series from the current DICOM server to a 
        destination DICOM node.
        
        Args:
            destination_node: Name of the destination node as defined in the configuration
            series_instance_uid: The unique identifier for the series to be moved
        
        Returns:
            Dictionary containing:
            - success: Boolean indicating if the operation was successful
            - message: Description of the operation result or error
            - completed: Number of successfully transferred instances
            - failed: Number of failed transfers
            - warning: Number of transfers with warnings
        
        Example:
            {
                "success": true,
                "message": "C-MOVE operation completed successfully",
                "completed": 120,
                "failed": 0,
                "warning": 0
            }
        """
        dicom_ctx = ctx.request_context.lifespan_context
        config = dicom_ctx.config
        client = dicom_ctx.client
        
        # Check if destination node exists
        if destination_node not in config.nodes:
            raise ValueError(f"Destination node '{destination_node}' not found in configuration")
        
        # Get the destination AE title
        destination_ae = config.nodes[destination_node].ae_title
        
        # Execute the move operation
        result = client.move_series(
            destination_ae=destination_ae,
            series_instance_uid=series_instance_uid
        )
        
        return result

    @mcp.tool()
    def move_study(
        destination_node: str,
        study_instance_uid: str,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Move a DICOM study to another DICOM node.
        
        This tool transfers an entire study from the current DICOM server to a 
        destination DICOM node.
        
        Args:
            destination_node: Name of the destination node as defined in the configuration
            study_instance_uid: The unique identifier for the study to be moved
        
        Returns:
            Dictionary containing:
            - success: Boolean indicating if the operation was successful
            - message: Description of the operation result or error
            - completed: Number of successfully transferred instances
            - failed: Number of failed transfers
            - warning: Number of transfers with warnings
        
        Example:
            {
                "success": true,
                "message": "C-MOVE operation completed successfully",
                "completed": 256,
                "failed": 0,
                "warning": 0
            }
        """
        dicom_ctx = ctx.request_context.lifespan_context
        config = dicom_ctx.config
        client = dicom_ctx.client
        
        # Check if destination node exists
        if destination_node not in config.nodes:
            raise ValueError(f"Destination node '{destination_node}' not found in configuration")
        
        # Get the destination AE title
        destination_ae = config.nodes[destination_node].ae_title
        
        # Execute the move operation
        result = client.move_study(
            destination_ae=destination_ae,
            study_instance_uid=study_instance_uid
        )
        
        return result


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
    
    # FHIR Tools (only registered if FHIR client is configured)
    @mcp.tool()
    def verify_fhir_connection(ctx: Context = None) -> str:
        """Verify connectivity to the FHIR server.
        
        This tool checks if the FHIR server is reachable and returns
        metadata about the server, including FHIR version.
        
        Returns:
            A message describing the FHIR server connection status
        
        Raises:
            ValueError: If FHIR is not configured
        """
        dicom_ctx = ctx.request_context.lifespan_context
        if not dicom_ctx.fhir_client:
            raise ValueError("FHIR server is not configured. Add 'fhir_servers' section to configuration.yaml")
        
        success, message = dicom_ctx.fhir_client.verify_connection()
        return message
    
    @mcp.tool()
    def fhir_search_patient(
        name: Optional[str] = None,
        identifier: Optional[str] = None,
        birthdate: Optional[str] = None,
        gender: Optional[str] = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Search for Patient resources in the FHIR server.
        
        Args:
            name: Patient name to search for (can include partial matches)
            identifier: Patient identifier (e.g., MRN)
            birthdate: Patient birth date (YYYY-MM-DD format)
            gender: Patient gender (male, female, other, unknown)
        
        Returns:
            FHIR Bundle containing matching Patient resources
        
        Example:
            {
                "resourceType": "Bundle",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Patient",
                            "id": "example",
                            "name": [{"family": "Smith", "given": ["John"]}]
                        }
                    }
                ]
            }
        """
        dicom_ctx = ctx.request_context.lifespan_context
        if not dicom_ctx.fhir_client:
            raise ValueError("FHIR server is not configured. Add 'fhir_servers' section to configuration.yaml")
        
        params = {}
        if name:
            params["name"] = name
        if identifier:
            params["identifier"] = identifier
        if birthdate:
            params["birthdate"] = birthdate
        if gender:
            params["gender"] = gender
        
        try:
            return dicom_ctx.fhir_client.search_resource("Patient", params)
        except Exception as e:
            raise Exception(f"Error searching FHIR patients: {str(e)}")
    
    @mcp.tool()
    def fhir_search_imaging_study(
        patient_id: Optional[str] = None,
        modality: Optional[str] = None,
        study_date: Optional[str] = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Search for ImagingStudy resources in the FHIR server.
        
        Args:
            patient_id: Patient ID to filter by
            modality: Imaging modality (e.g., CT, MR, US)
            study_date: Study date (YYYY-MM-DD format or range like "2024-01-01:2024-12-31")
        
        Returns:
            FHIR Bundle containing matching ImagingStudy resources
        """
        dicom_ctx = ctx.request_context.lifespan_context
        if not dicom_ctx.fhir_client:
            raise ValueError("FHIR server is not configured. Add 'fhir_servers' section to configuration.yaml")
        
        params = {}
        if patient_id:
            params["patient"] = patient_id
        if modality:
            params["modality"] = modality
        if study_date:
            params["date"] = study_date
        
        try:
            return dicom_ctx.fhir_client.search_resource("ImagingStudy", params)
        except Exception as e:
            raise Exception(f"Error searching FHIR ImagingStudy: {str(e)}")
    
    @mcp.tool()
    def fhir_read_resource(
        resource_type: str,
        resource_id: str,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Read a specific FHIR resource by type and ID.
        
        Args:
            resource_type: FHIR resource type (e.g., "Patient", "ImagingStudy", "Observation")
            resource_id: The logical ID of the resource
        
        Returns:
            The requested FHIR resource
        """
        dicom_ctx = ctx.request_context.lifespan_context
        if not dicom_ctx.fhir_client:
            raise ValueError("FHIR server is not configured. Add 'fhir_servers' section to configuration.yaml")
        
        try:
            return dicom_ctx.fhir_client.read_resource(resource_type, resource_id)
        except Exception as e:
            raise Exception(f"Error reading FHIR resource {resource_type}/{resource_id}: {str(e)}")
    
    @mcp.tool()
    def list_fhir_servers(ctx: Context = None) -> Dict[str, Any]:
        """List all configured FHIR servers and show which one is currently active.
        
        Returns:
            Dictionary containing current FHIR server and available servers
        """
        dicom_ctx = ctx.request_context.lifespan_context
        config = dicom_ctx.config
        
        servers = {}
        if config.fhir_servers:
            for name, server_config in config.fhir_servers.items():
                servers[name] = {
                    "base_url": server_config.base_url,
                    "description": server_config.description,
                    "has_api_key": bool(server_config.api_key)
                }
        elif config.fhir:
            # Legacy single server
            servers["default"] = {
                "base_url": config.fhir.base_url,
                "description": config.fhir.description,
                "has_api_key": bool(config.fhir.api_key)
            }
        
        return {
            "current_fhir": config.current_fhir or "default",
            "servers": servers,
            "status": "success"
        }
    
    @mcp.tool()
    def list_mini_ris_patients(
        mrn: Optional[str] = None,
        name_query: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
        ctx: Context = None,
    ) -> Dict[str, Any]:
        """Retrieve patient demographics from the mini-RIS MySQL database.

        Args:
            mrn: Optional exact MRN filter (e.g., ``MRN1001``).
            name_query: Optional substring filter applied to given and family names.
            limit: Maximum number of rows to return (1-100).
            offset: Pagination offset for the query.

        Returns:
            Dictionary containing the patient rows and query metadata. If the
            mini-RIS database is not configured, an informative error response
            is returned instead of raising.
        """

        dicom_ctx = ctx.request_context.lifespan_context

        if dicom_ctx.mini_ris_client is None:
            return {
                "success": False,
                "message": "Mini-RIS database is not configured. Add the 'mini_ris' section to configuration.yaml.",
            }

        return dicom_ctx.mini_ris_client.list_patients(
            mrn=mrn,
            name_query=name_query,
            limit=limit,
            offset=offset,
        )

    @mcp.tool()
    def create_mwl_from_order(
        order_id: int,
        scheduled_station_aet: str = "ORTHANC",
        mwl_api_url: str = "http://localhost:8000",
        ctx: Context = None,
    ) -> Dict[str, Any]:
        """Create a DICOM Modality Worklist entry from an existing mini-RIS order.
        
        This tool is typically used when a patient arrives at the imaging center and
        the technician is ready to perform the procedure. It converts an order from
        the mini-RIS into a DICOM MWL entry that modalities can query via C-FIND.
        
        The workflow is:
        1. Patient arrives → Technician verifies demographics
        2. Ready for imaging → Call this tool to create MWL
        3. Modality queries MWL → Gets worklist via C-FIND
        4. Study acquired → MPPS updates status
        
        Args:
            order_id: The mini-RIS order ID to convert to MWL
            scheduled_station_aet: The AE Title of the acquisition station (default: ORTHANC)
            mwl_api_url: Base URL of the MWL API service (default: http://localhost:8000)
            
        Returns:
            Dictionary with MWL creation status, accession number, patient info, and MWL ID
        """
        dicom_ctx = ctx.request_context.lifespan_context
        
        if dicom_ctx.mini_ris_client is None:
            return {
                "success": False,
                "message": "Mini-RIS database is not configured. Add the 'mini_ris' section to configuration.yaml.",
            }
        
        # Query order with all related data
        try:
            order_data = dicom_ctx.mini_ris_client.get_order_for_mwl(order_id)
        except Exception as e:
            return {
                "success": False,
                "message": f"Error querying order: {str(e)}",
                "order_id": order_id,
            }
        
        if not order_data:
            return {
                "success": False,
                "message": f"Order {order_id} not found in mini-RIS database",
                "order_id": order_id,
            }
        
        # Validate required data
        if not order_data.get('scheduled_start'):
            return {
                "success": False,
                "message": f"Order {order_id} has no scheduled start time. Cannot create MWL.",
                "order_id": order_id,
                "order_status": order_data.get('order_status'),
            }
        
        # Build DICOM patient name (Family^Given)
        patient_name = f"{order_data['family_name']}^{order_data['given_name']}"
        
        # Build performing physician name if available
        performing_physician_name = None
        if order_data.get('performing_physician_family') and order_data.get('performing_physician_given'):
            performing_physician_name = f"{order_data['performing_physician_family']}^{order_data['performing_physician_given']}"
        
        # Build Scheduled Procedure Step Sequence (proper DICOM structure)
        scheduled_dt = order_data['scheduled_start']
        scheduled_procedure_step = {
            "Modality": order_data['modality_code'],
            "ScheduledStationAETitle": scheduled_station_aet,
            "ScheduledProcedureStepStartDate": scheduled_dt.strftime('%Y%m%d'),
            "ScheduledProcedureStepStartTime": scheduled_dt.strftime('%H%M%S'),
            "ScheduledProcedureStepDescription": order_data['procedure_description'],
            "ScheduledProcedureStepID": f"SPS{order_data['order_id']}",
        }
        
        # Add optional performing physician to SPS
        if performing_physician_name:
            scheduled_procedure_step["ScheduledPerformingPhysicianName"] = performing_physician_name
        
        # Build complete MWL payload with proper DICOM structure
        mwl_payload = {
            "AccessionNumber": order_data['accession_number'],
            "PatientID": order_data['mrn'],
            "PatientName": patient_name,
            "PatientBirthDate": order_data['date_of_birth'].strftime('%Y%m%d'),
            "PatientSex": order_data['sex'],
            "StudyInstanceUID": generate_uid(),  # Generate unique Study UID
            "RequestedProcedureDescription": order_data['procedure_description'],
            "RequestedProcedureID": order_data['order_number'],
            "ScheduledProcedureStepSequence": [scheduled_procedure_step],  # SPS as sequence
        }
        
        # Add optional top-level fields
        if order_data.get('reason_description'):
            mwl_payload["RequestedProcedureComments"] = order_data['reason_description']
        
        # POST to mwl-api
        try:
            response = requests.post(
                f"{mwl_api_url}/mwl/create_from_json",
                json=mwl_payload,
                timeout=10
            )
            response.raise_for_status()
            mwl_result = response.json()
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "message": f"Error calling MWL API: {str(e)}",
                "order_id": order_id,
                "accession_number": order_data['accession_number'],
                "mwl_api_url": mwl_api_url,
                "hint": "Ensure mwl-api service is running: docker compose up -d mwl-api",
            }
        
        return {
            "success": True,
            "message": f"MWL created successfully for order {order_id}",
            "order_id": order_id,
            "accession_number": order_data['accession_number'],
            "patient_name": f"{order_data['given_name']} {order_data['family_name']}",
            "patient_id": order_data['mrn'],
            "procedure": order_data['procedure_description'],
            "modality": order_data['modality_code'],
            "scheduled_time": scheduled_dt.strftime('%Y-%m-%d %H:%M:%S'),
            "scheduled_station_aet": scheduled_station_aet,
            "mwl_id": mwl_result.get('id'),
            "mwl_api_response": mwl_result,
        }

    @mcp.tool()
    def create_synthetic_cr_study(
        accession_number: str,
        image_mode: str = "auto",
        image_description: str = "normal",
        send_to_pacs: bool = True,
        ctx: Context = None,
    ) -> Dict[str, Any]:
        """Create a synthetic CR DICOM study and optionally send to PACS.
        
        Simulates a virtual CR device performing an imaging exam. This creates
        realistic synthetic DICOM images for development, testing, and training.
        
        **IMPORTANT**: Synthetic images are for development/testing only.
        NOT for clinical use or diagnosis. NOT based on real patient data.
        
        Workflow:
        1. Queries MWL for the accession number
        2. Generates synthetic images based on procedure
        3. Creates proper DICOM CR instances with all metadata
        4. Optionally sends to PACS (Orthanc)
        
        Image modes:
        - "auto": Use AI if OpenAI key available, fallback to simple
        - "ai": Generate realistic images with DALL-E (requires OPENAI_API_KEY)
        - "simple": Generate basic test images (no API key needed)
        - "sample": Use pre-made sample images from library
        
        Args:
            accession_number: Accession number from MWL entry
            image_mode: Image generation mode (auto, ai, simple, sample)
            image_description: Description for AI (e.g., "pneumonia right lower lobe")
            send_to_pacs: Whether to send images to PACS after creation
            
        Returns:
            Dictionary with study creation results, DICOM files, and PACS send status
        """
        dicom_ctx = ctx.request_context.lifespan_context
        
        if dicom_ctx.mini_ris_client is None:
            return {
                "success": False,
                "message": "Mini-RIS database is not configured.",
            }
        
        # Query MWL for this accession number
        try:
            conn = dicom_ctx.mini_ris_client._pool.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Get order data with procedure info
            cursor.execute("""
                SELECT 
                    o.order_id, o.accession_number, o.modality_code,
                    p.mrn, p.given_name, p.family_name, p.date_of_birth, p.sex,
                    CONCAT(p.family_name, '^', p.given_name) as patient_name,
                    op.procedure_description,
                    proc.body_part_code, proc.typical_views, proc.typical_image_count
                FROM orders o
                JOIN patients p ON o.patient_id = p.patient_id
                JOIN order_procedures op ON o.order_id = op.order_id
                LEFT JOIN procedures proc ON op.procedure_code = proc.procedure_code
                WHERE o.accession_number = %s
                LIMIT 1
            """, (accession_number,))
            
            order_data = cursor.fetchone()
            cursor.close()
            conn.close()
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error querying order: {str(e)}",
                "accession_number": accession_number,
            }
        
        if not order_data:
            return {
                "success": False,
                "message": f"No order found for accession number: {accession_number}",
                "accession_number": accession_number,
                "hint": "Create MWL entry first using create_mwl_from_order()"
            }
        
        # Create virtual CR device
        openai_key = os.getenv("OPENAI_API_KEY")
        virtual_cr = VirtualCRDevice(openai_api_key=openai_key)
        
        # Generate study
        try:
            study_result = virtual_cr.create_study(
                mwl_data=order_data,
                image_mode=image_mode,
                image_description=image_description
            )
        except Exception as e:
            return {
                "success": False,
                "message": f"Error creating synthetic images: {str(e)}",
                "accession_number": accession_number,
                "image_mode": image_mode,
                "hint": "If using 'ai' mode, ensure OPENAI_API_KEY is set in .env"
            }
        
        result = {
            "success": True,
            "message": f"Created synthetic CR study with {study_result['num_images']} images",
            "accession_number": accession_number,
            "patient_name": f"{order_data['given_name']} {order_data['family_name']}",
            "patient_id": order_data['mrn'],
            "procedure": order_data['procedure_description'],
            "modality": order_data['modality_code'],
            "study_uid": study_result['study_uid'],
            "series_uid": study_result['series_uid'],
            "num_images": study_result['num_images'],
            "image_mode": study_result['image_mode'],
            "images": [
                {"instance": f['instance_number'], "view": f['view']} 
                for f in study_result['files']
            ]
        }
        
        # Send to PACS if requested
        if send_to_pacs:
            try:
                current_node = dicom_ctx.config.nodes[dicom_ctx.config.current_node]
                pacs_result = virtual_cr.send_to_pacs(
                    dicom_files=study_result['files'],
                    pacs_host=current_node.host,
                    pacs_port=current_node.port,
                    pacs_aet=current_node.ae_title,
                    calling_aet="VIRTUALCR",
                    use_tls=current_node.use_tls
                )
                
                result["pacs_send"] = {
                    "success": pacs_result['success'],
                    "sent": pacs_result['sent'],
                    "total": pacs_result['total'],
                    "destination": f"{current_node.host}:{current_node.port} ({current_node.ae_title})"
                }
                
                if pacs_result['success']:
                    result["message"] += f" and sent to PACS ({pacs_result['sent']}/{pacs_result['total']})"
                else:
                    result["message"] += f" but PACS send failed ({pacs_result['sent']}/{pacs_result['total']} sent)"
                    
            except Exception as e:
                result["pacs_send"] = {
                    "success": False,
                    "error": str(e)
                }
                result["message"] += " but PACS send failed"
        
        return result

    @mcp.tool()
    def fhir_create_resource(
        resource: Dict[str, Any],
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Create a new FHIR resource on the server.
        
        This tool allows you to create any FHIR resource type (Patient, ImagingStudy,
        ServiceRequest, DiagnosticReport, etc.). The resource must include a
        "resourceType" field.
        
        Args:
            resource: The FHIR resource to create as a dictionary. Must include
                     "resourceType" field. Optionally include "id" for client-assigned IDs.
        
        Returns:
            The created FHIR resource with server-assigned ID and metadata
        
        Example:
            Create a Patient:
            {
                "resourceType": "Patient",
                "identifier": [{"system": "http://hospital.example.org/mrn", "value": "MRN001"}],
                "name": [{"family": "Smith", "given": ["John"]}],
                "birthDate": "1985-03-15",
                "gender": "male"
            }
        """
        dicom_ctx = ctx.request_context.lifespan_context
        if not dicom_ctx.fhir_client:
            raise ValueError("FHIR server is not configured. Add 'fhir_servers' section to configuration.yaml")
        
        try:
            return dicom_ctx.fhir_client.create_resource(resource)
        except Exception as e:
            raise Exception(f"Error creating FHIR resource: {str(e)}")
    
    @mcp.tool()
    def fhir_update_resource(
        resource: Dict[str, Any],
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Update an existing FHIR resource on the server.
        
        This tool allows you to update any FHIR resource. The resource must include
        both "resourceType" and "id" fields to identify the resource to update.
        
        Args:
            resource: The FHIR resource to update as a dictionary. Must include
                     both "resourceType" and "id" fields.
        
        Returns:
            The updated FHIR resource with server metadata
        
        Example:
            Update a Patient's name:
            {
                "resourceType": "Patient",
                "id": "patient-mrn001",
                "identifier": [{"system": "http://hospital.example.org/mrn", "value": "MRN001"}],
                "name": [{"family": "Smith", "given": ["John", "Robert"]}],
                "birthDate": "1985-03-15",
                "gender": "male"
            }
        """
        dicom_ctx = ctx.request_context.lifespan_context
        if not dicom_ctx.fhir_client:
            raise ValueError("FHIR server is not configured. Add 'fhir_servers' section to configuration.yaml")
        
        try:
            return dicom_ctx.fhir_client.update_resource(resource)
        except Exception as e:
            raise Exception(f"Error updating FHIR resource: {str(e)}")
    
    return mcp