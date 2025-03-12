"""
Configuration management for DICOM MCP Server.
"""

import os
from dataclasses import dataclass


@dataclass
class DicomConfig:
    """Simple configuration for DICOM server connection."""
    host: str = "127.0.0.1"
    port: int = 11112
    ae_title: str = "MCPSCU"
    
    @classmethod
    def from_env(cls) -> 'DicomConfig':
        """Create config from environment variables.
        
        Uses DICOM_HOST, DICOM_PORT, and DICOM_AE_TITLE environment variables.
        Falls back to defaults if not specified.
        """
        host = os.environ.get("DICOM_HOST", "127.0.0.1")
        
        try:
            port = int(os.environ.get("DICOM_PORT", "11112"))
        except ValueError:
            port = 11112
            
        ae_title = os.environ.get("DICOM_AE_TITLE", "MCPSCU")
        
        return cls(host=host, port=port, ae_title=ae_title)