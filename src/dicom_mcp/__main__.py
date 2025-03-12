"""
Main entry point for the DICOM MCP Server.
"""

from .server import create_dicom_mcp_server

if __name__ == "__main__":
    # Create and run the server
    mcp = create_dicom_mcp_server()
    mcp.run()