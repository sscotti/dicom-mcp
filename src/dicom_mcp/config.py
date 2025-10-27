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


class OpenAIConfig(BaseModel):
    """OpenAI configuration"""
    api_key: str
    model: str = "gpt-4o"
    max_tokens: int = 4000
    temperature: float = 0.1


class DicomConfiguration(BaseModel):
    """Complete DICOM configuration"""
    nodes: Dict[str, DicomNodeConfig]
    current_node: str
    calling_aet: str
    openai: Optional[OpenAIConfig] = None

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
    
    try:
        return DicomConfiguration(**data)
    except Exception as e:
        raise ValueError(f"Invalid configuration in {path}: {str(e)}")