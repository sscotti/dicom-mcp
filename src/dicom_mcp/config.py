"""
DICOM configuration using Pydantic.
"""

import yaml
from pathlib import Path
from typing import Dict
from pydantic import BaseModel


class DicomNodeConfig(BaseModel):
    """Configuration for a DICOM node"""
    host: str
    port: int
    ae_title: str
    description: str = ""


class CallingAETitleConfig(BaseModel):
    """Configuration for a calling AE title"""
    ae_title: str
    description: str = ""


class DicomConfiguration(BaseModel):
    """Complete DICOM configuration"""
    nodes: Dict[str, DicomNodeConfig]
    calling_aets: Dict[str, CallingAETitleConfig]
    current_node: str
    current_calling_aet: str


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
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file {path} not found")
    
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    
    try:
        return DicomConfiguration(**data)
    except Exception as e:
        raise ValueError(f"Invalid configuration in {path}: {str(e)}")