"""
DICOM configuration using Pydantic.
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel
from dotenv import load_dotenv


class DicomNodeConfig(BaseModel):
    """Configuration for a DICOM node"""
    host: str
    port: int
    ae_title: str
    description: str = ""


# OpenAI config removed - using standard MCP protocol instead


class FhirServerConfig(BaseModel):
    """Configuration for a FHIR server"""
    base_url: str
    api_key: Optional[str] = None
    description: str = ""


class DicomConfiguration(BaseModel):
    """Complete DICOM configuration"""
    nodes: Dict[str, DicomNodeConfig]
    current_node: str
    calling_aet: str
    fhir_servers: Optional[Dict[str, FhirServerConfig]] = None
    current_fhir: Optional[str] = None
    # Legacy: support old single fhir config for backwards compatibility
    fhir: Optional[FhirServerConfig] = None
    # openai config removed - using standard MCP protocol

def load_config(config_path: str) -> DicomConfiguration:
    """Load DICOM configuration from YAML file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Parsed DicomConfiguration object
        
    Raises:
        FileNotFoundError: If the configuration file doesn't exist
        ValueError: If the configuration is invalid
    """
    # Load environment variables from .env file if it exists
    config_dir = Path(config_path).parent
    env_file = config_dir / '.env'
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ Loaded environment variables from {env_file}")
    else:
        # Try to load from current directory
        if Path('.env').exists():
            load_dotenv('.env')
            print("✅ Loaded environment variables from .env")
    
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file {path} not found")
    
    with open(path, 'r') as f:
        content = f.read()
        # Expand environment variables
        content = os.path.expandvars(content)
        data = yaml.safe_load(content)
    
    # Expand FHIR API keys from environment variables
    # Handle legacy single fhir config
    if data.get("fhir") and data["fhir"].get("api_key"):
        fhir_api_key = data["fhir"]["api_key"]
        if fhir_api_key.startswith("${") and fhir_api_key.endswith("}"):
            env_var = fhir_api_key[2:-1]
            data["fhir"]["api_key"] = os.getenv(env_var) or fhir_api_key
    
    # Handle multiple FHIR servers
    if data.get("fhir_servers"):
        for server_name, server_config in data["fhir_servers"].items():
            if server_config.get("api_key"):
                fhir_api_key = server_config["api_key"]
                if fhir_api_key.startswith("${") and fhir_api_key.endswith("}"):
                    env_var = fhir_api_key[2:-1]
                    server_config["api_key"] = os.getenv(env_var) or fhir_api_key
    
    try:
        return DicomConfiguration(**data)
    except Exception as e:
        raise ValueError(f"Invalid configuration in {path}: {str(e)}")