"""
Configuration management for DICOM MCP Server.
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional


@dataclass
class DicomServerConfig:
    """Configuration for connecting to a DICOM server."""
    host: str = "127.0.0.1"
    port: int = 11112
    ae_title: str = "MCPSCU"
    timeout: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert config to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DicomServerConfig":
        """Create config from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> "DicomServerConfig":
        """Create config from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    @classmethod
    def from_env(cls, prefix: str = "DICOM_") -> "DicomServerConfig":
        """
        Create config from environment variables.
        
        Environment variables should be prefixed with DICOM_ (or specified prefix)
        For example: DICOM_HOST, DICOM_PORT, DICOM_AE_TITLE, DICOM_TIMEOUT
        """
        config = cls()
        
        if f"{prefix}HOST" in os.environ:
            config.host = os.environ[f"{prefix}HOST"]
            
        if f"{prefix}PORT" in os.environ:
            try:
                config.port = int(os.environ[f"{prefix}PORT"])
            except ValueError:
                pass
            
        if f"{prefix}AE_TITLE" in os.environ:
            config.ae_title = os.environ[f"{prefix}AE_TITLE"]
            
        if f"{prefix}TIMEOUT" in os.environ:
            try:
                config.timeout = int(os.environ[f"{prefix}TIMEOUT"])
            except ValueError:
                pass
            
        return config
    
    def save_to_file(self, filepath: str) -> None:
        """Save config to a JSON file."""
        with open(filepath, 'w') as f:
            f.write(self.to_json())
    
    @classmethod
    def load_from_file(cls, filepath: str) -> Optional["DicomServerConfig"]:
        """Load config from a JSON file."""
        try:
            with open(filepath, 'r') as f:
                return cls.from_json(f.read())
        except (FileNotFoundError, json.JSONDecodeError):
            return None