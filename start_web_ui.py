#!/usr/bin/env python3
"""
Start the MCP-FHIR-Orthanc Web UI.
Self-contained web interface with prompts, tools, and interactive chat.
"""
import os
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

import uvicorn
from dicom_mcp.web_ui import app

if __name__ == "__main__":
    # Set default config path if not in environment
    if "MCP_CONFIG_PATH" not in os.environ:
        config_path = project_root / "configuration.yaml"
        if config_path.exists():
            os.environ["MCP_CONFIG_PATH"] = str(config_path)
    
    # Start the server
    print("🚀 Starting MCP-FHIR-Orthanc Web UI...")
    print("📡 Server will be available at: http://127.0.0.1:8080")
    print("📝 Features:")
    print("   - Interactive chat with DICOM tools")
    print("   - Tool browser and explorer")
    print("   - System prompt management")
    print("   - Resource viewer")
    print("\nPress Ctrl+C to stop the server\n")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8080,
        log_level="info"
    )

