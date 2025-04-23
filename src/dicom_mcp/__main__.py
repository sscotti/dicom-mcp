"""
Main entry point for the DICOM MCP Server.
"""
import argparse

from .server import create_dicom_mcp_server

def main():
    # Simple argument parser
    parser = argparse.ArgumentParser(description="DICOM Model Context Protocol Server")
    parser.add_argument("config_path", help="Path to the DICOM configuration YAML file")
    parser.add_argument("--transport", help="MCP transport type ('sse' or 'stdio",default='stdio')

    args = parser.parse_args()
    
    # Create and run the server
    mcp = create_dicom_mcp_server(args.config_path)
    mcp.run(args.transport)
    #mcp.run()
    
if __name__ == "__main__":
    main()