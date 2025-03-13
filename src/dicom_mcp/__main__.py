"""
Main entry point for the DICOM MCP Server.
"""
from .server import create_dicom_mcp_server, CONFIG_PATH

def main():
    # Create and run the server
    mcp = create_dicom_mcp_server()
    mcp.run()
    
if __name__ == "__main__":
    main()