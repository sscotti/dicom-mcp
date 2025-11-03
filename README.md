# DICOM MCP Server - Medical Imaging AI Integration 🏥

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![PyPI Version](https://img.shields.io/pypi/v/dicom-mcp.svg)](https://pypi.org/project/dicom-mcp/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/dicom-mcp.svg)](https://pypi.org/project/dicom-mcp/)  
[![MCP Python SKD]](https://github.com/modelcontextprotocol/python-sdk)
[![MCP JAM]](https://www.mcpjam.com) npx -y @mcpjam/inspector@latest

Forked from:  <https://github.com/ChristianHinge/dicom-mcp>

The forked version uses [MCP Jam](https://www.mcpjam.com) exclusively for development, testing, and LLM integration.

TO DO:  Integrate SIIM Orthanc and FHIR server and build toolset for FHIR and DIcomWeb ?

The `dicom-mcp` server enables AI assistants to query, read, and move data on DICOM servers (PACS, VNA, etc.) using the standard Model Context Protocol (MCP), with Orthanc as the reference implementation.

```text
---------------------------------------------------------------------
🧑‍⚕️ User: "Any significant findings in John Doe's previous CT report?"

🧠 LLM → ⚙️ Tools:
   query_patients → query_studies → query_series → extract_pdf_text_from_dicom

💬 LLM Response: "The report from 2025-03-26 mentions a history of splenomegaly (enlarged spleen)"

🧑‍⚕️ User: "What's the volume of his spleen at the last scan and the scan today?"

🧠 LLM → ⚙️ Tools:
   (query_studies → query_series → move_series → query_series → extract_pdf_text_from_dicom) x2
   (The move_series tool sends the latest CT to a DICOM segmentation node, which returns volume PDF report)

💬 LLM Response: "last year 2024-03-26: 412cm³, today 2025-04-10: 350cm³"
---------------------------------------------------------------------
```

## ✨ Core Capabilities

`dicom-mcp` provides tools to:

* **🔍 Query Metadata**: Search for patients, studies, series, and instances using various criteria.
* **📄 Read DICOM Reports (PDF)**: Retrieve DICOM instances containing encapsulated PDFs (e.g., clinical reports) and extract the text content.
* **➡️ Send DICOM Images**: Send series or studies to other DICOM destinations, e.g. AI endpoints for image segmentation, classification, etc.
* **⚙️ Utilities**: Manage connections and understand query options.

## 🚀 Quick Start

### 📥 Installation

Install using pip by cloning the repository:

```bash
# Clone and set up development environment
gh repo clone sscotti/dicom-mcp
cd dicom-mcp

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install with dependencies
pip install -e ".[dev]"
```

### ⚙️ Configuration

`dicom-mcp` requires a YAML configuration file (`configuration.yaml` or similar) defining DICOM nodes and calling AE titles. Adapt the configuration or keep as is for compatibility with the sample ORTHANC  Server.

```yaml
# DICOM nodes configuration
nodes:
  main:
    host: "localhost"
    port: 4242
    ae_title: "ORTHANC"
    description: "Local Orthanc DICOM server (Primary)"
  
  secondary:
    host: "localhost"
    port: 4243
    ae_title: "ORTHANC2"
    description: "Local Orthanc DICOM server (Secondary)"

current_node: "main"
calling_aet: "MCPSCU" 
```

> [!WARNING]
> DICOM-MCP is not meant for clinical use, and should not be connected with live hospital databases or databases with patient-sensitive data. Doing so could lead to both loss of patient data, and leakage of patient data onto the internet. DICOM-MCP can be used with locally hosted open-weight LLMs for complete data privacy.
>
> [!NOTE]
> This project uses **MCP Jam exclusively** for all development, testing, and LLM integration needs. The `mcp-config.example.json` file is provided as a template with relative paths that you can adapt to your setup.

### (Optional) Sample ORTHANC server

If you don't have a DICOM server available, you can run a local ORTHANC server using Docker:

```bash
cd tests
docker-compose up -d
cd ..
pytest # uploads dummy pdf data to ORTHANC server
```

UI at [http://localhost:8042](http://localhost:8042)

### (Optional) Local HAPI FHIR Server

For local FHIR testing, you can run a HAPI FHIR server:

```bash
cd tests
docker-compose -f docker-compose-fhir.yaml up -d
```

HAPI FHIR will be available at [http://localhost:8080/fhir](http://localhost:8080/fhir)

See [FHIR Servers Guide](tests/FHIR_SERVERS.md) for detailed configuration options including Firely test server and SIIM integration.

### 🔌 Using with MCP Jam

**MCP Jam** is the recommended tool for testing and exploring your DICOM MCP server. It offers a beautiful interface with **Guest Mode** for immediate testing without any setup.

**Start MCP Jam:**

```bash
# Navigate to your dicom-mcp directory
cd /path/to/dicom-mcp

# Activate your virtual environment
source venv/bin/activate

# Start MCP Jam
npx -y @mcpjam/inspector@latest
```

**Setup Server in MCP Jam:**

1. **Click "Guest Mode"** in the MCP Jam interface (no account required)
2. **Add Server Manually** with these settings, or import `mcp-config.example.json` as a template:
   * **Server Name**: `DICOM MCP`
   * **Command**: `{path_to_venv}/bin/python` (e.g., `venv/bin/python` or absolute path)
   * **Arguments**: `-m dicom_mcp configuration.yaml --transport stdio`
   * **Environment Variables**:
     * Name: `PYTHONPATH`
     * Value: `src` (relative) or absolute path to `src` directory
   * **Working Directory**: Path to your dicom-mcp project root

**Example Configuration (macOS/Linux):**

* **Command**: `/absolute/path/to/dicom-mcp/venv/bin/python`
* **Arguments**: `-m dicom_mcp configuration.yaml --transport stdio`
* **Environment Variable**: `PYTHONPATH` = `/absolute/path/to/dicom-mcp/src`

**MCP Jam Interface:**

![MCP JAM Interface](images/mcpjam.jpg)

**Configure LLM in MCP Jam:**

1. Go to the **Settings** tab
2. Add your API keys for LLM providers:
   * **OpenAI** - For GPT-4, GPT-4o, o1, etc.
   * **Anthropic** - For Claude 3.5 Sonnet, Claude Opus, etc.
   * **Google Gemini** - For Gemini 2.5 Pro, Flash, etc.
   * **Deepseek** - For Deepseek Chat, Reasoner
   * **Ollama** - Auto-detects local models (no API key needed)
3. Go to the **Playground** tab to start chatting with your DICOM server

**System Prompt:**

For better LLM interactions, you can configure a system prompt in MCP Jam's Playground tab. A template is available in `system_prompt.txt` - copy it into the system prompt field when starting a new session.

> **Note**: MCP Jam Guest Mode may not persist system prompts between sessions. Keep `system_prompt.txt` handy to copy-paste when needed.

**MCP Jam Features:**

* ✅ **Guest Mode**: No account required - start testing immediately
* ✅ **Beautiful UI**: Modern interface with AI provider logos
* ✅ **Easy Setup**: Simple server configuration with clear forms
* ✅ **Real-time Testing**: Interactive tool execution with immediate results
* ✅ **Full Functionality**: Access to all 11 DICOM tools
* ✅ **LLM Playground**: Test your DICOM server with various LLMs
* ✅ **Community Driven**: Active development with regular updates

**MCP Jam Tabs:**

* **Servers Tab**: Manage and connect to your DICOM MCP server
* **Tools Tab**: Browse and test all 11 DICOM tools interactively
* **Playground Tab**: Chat with your DICOM server using configured LLMs
* **Settings Tab**: Configure API keys and LLM providers

**Available DICOM Tools:**

* `verify_connection` - Test DICOM connectivity
* `list_dicom_nodes` - Show configured servers
* `query_patients` - Search for patients
* `query_studies` - Find studies by criteria
* `query_series` - Locate series within studies
* `query_instances` - Find individual DICOM images
* `extract_pdf_text_from_dicom` - Extract text from DICOM PDFs
* `move_series` / `move_study` - Transfer DICOM data
* `switch_dicom_node` - Change active server
* `get_attribute_presets` - Show query detail levels

**Available FHIR Tools (when FHIR is configured):**

* `verify_fhir_connection` - Test FHIR server connectivity
* `list_fhir_servers` - List configured FHIR servers
* `fhir_search_patient` - Search for Patient resources
* `fhir_search_imaging_study` - Search for ImagingStudy resources
* `fhir_read_resource` - Read any FHIR resource by type and ID

See [FHIR Servers Guide](tests/FHIR_SERVERS.md) for configuration details.

## 🛠️ Tools Overview

`dicom-mcp` provides four categories of tools for interaction with DICOM servers and DICOM data.

### 🔍 Query Metadata

* **`query_patients`**: Search for patients based on criteria like name, ID, or birth date.
* **`query_studies`**: Find studies using patient ID, date, modality, description, accession number, or Study UID.
* **`query_series`**: Locate series within a specific study using modality, series number/description, or Series UID.
* **`query_instances`**: Find individual instances (images/objects) within a series using instance number or SOP Instance UID

### 📄 Read DICOM Reports (PDF)

* **`extract_pdf_text_from_dicom`**: Retrieve a specific DICOM instance containing an encapsulated PDF and extract its text content.

### ➡️ Send DICOM Images

* **`move_series`**: Send a specific DICOM series to another configured DICOM node using C-MOVE.
* **`move_study`**: Send an entire DICOM study to another configured DICOM node using C-MOVE.

### ⚙️ Utilities

* **`list_dicom_nodes`**: Show the currently active DICOM node and list all configured nodes.
* **`switch_dicom_node`**: Change the active DICOM node for subsequent operations.
* **`verify_connection`**: Test the DICOM network connection to the currently active node using C-ECHO.
* **`get_attribute_presets`**: List the available levels of detail (minimal, standard, extended) for metadata query results.

### Example interaction

The tools can be chained together to answer complex questions:

<div align="center">
<img src="images/example.png" alt="My Awesome Diagram" width="700">
</div>

## 📈 Contributing

### Running Tests

Tests require a running Orthanc DICOM server. You can use Docker:

```bash
# Navigate to the directory containing docker-compose.yml (e.g., tests/)
cd tests
docker-compose up -d
```

Run tests using pytest:

```bash
# From the project root directory
pytest
```

Stop the Orthanc container:

```bash
cd tests
docker-compose down
```

### 🔧 Development & Debugging

**MCP Jam** is the recommended tool for development, testing, and debugging your DICOM MCP server.

**Development Workflow:**

1. **Start Orthanc**: `cd tests && docker-compose up -d`
2. **Load test data**: `pytest` (uploads sample DICOM data)
3. **Start MCP Jam**: `npx -y @mcpjam/inspector@latest`
4. **Test tools**: Use the Tools tab to test all DICOM operations interactively
5. **Test with LLMs**: Use the Playground tab to test natural language interactions
6. **Debug issues**: Check Server Notifications for errors and detailed logging

**Benefits of MCP Jam for Development:**

* ✅ **Guest Mode** - No account required, works immediately
* ✅ **Real-time testing** of all DICOM tools with immediate feedback
* ✅ **Interactive interface** for exploring DICOM data and responses
* ✅ **LLM integration** - Test how AI assistants interact with your server
* ✅ **Debug logging** - View detailed server notifications and errors
* ✅ **Tool browser** - Easily discover and test all available tools

## 🙏 Acknowledgments

* Built using [pynetdicom](https://github.com/pydicom/pynetdicom)
* Uses [PyPDF2](https://pypi.org/project/PyPDF2/) for PDF text extraction
