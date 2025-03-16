"""
Main entry point for the DICOM MCP Server.
"""
from .server import create_dicom_mcp_server
import sys

def main():
    # Create and run the server
    config_path = sys.argv[1]
    mcp = create_dicom_mcp_server(config_path)
    mcp.run()
    
if __name__ == "__main__":
    main()