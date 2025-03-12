"""
DICOM Model Context Protocol Server

A Model Context Protocol implementation for interacting with DICOM servers.
"""

from .server import create_dicom_mcp_server

__version__ = "0.1.0"
__all__ = ["create_dicom_mcp_server"]