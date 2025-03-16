# dicom-mcp: A DICOM Model Context Protocol Server

## Overview

A Model Context Protocol server for DICOM (Digital Imaging and Communications in Medicine) interactions. This server provides tools to query and interact with DICOM servers, enabling Large Language Models to access and analyze medical imaging metadata.

dicom-mcp allows AI assistants to query patient information, studies, series, and instances from DICOM servers using standard DICOM networking protocols. It's built on pynetdicom and follows the Model Context Protocol specification.

### Tools

1. `configure_dicom_server`
   - Sets up connection parameters for the DICOM server
   - Inputs:
     - `host` (string): DICOM server hostname or IP address
     - `port` (number): DICOM server port
     - `ae_title` (string, optional): Application Entity title for DICOM communication
   - Returns: Confirmation of configuration update

2. `verify_connection`
   - Tests connectivity to the configured DICOM server using C-ECHO
   - Inputs: None
   - Returns: Success or failure message with details

3. `query_patients`
   - Search for patients matching specified criteria
   - Inputs:
     - `name_pattern` (string, optional): Patient name pattern (can include wildcards)
     - `patient_id` (string, optional): Patient ID
     - `birth_date` (string, optional): Patient birth date (YYYYMMDD)
     - `attribute_preset` (string, optional): Preset level of detail (minimal, standard, extended)
     - `additional_attributes` (string[], optional): Additional DICOM attributes to include
     - `exclude_attributes` (string[], optional): DICOM attributes to exclude
   - Returns: Array of matching patient records

4. `query_studies`
   - Search for studies matching specified criteria
   - Inputs:
     - `patient_id` (string, optional): Patient ID
     - `study_date` (string, optional): Study date or range (YYYYMMDD or YYYYMMDD-YYYYMMDD)
     - `modality_in_study` (string, optional): Modalities in study
     - `study_description` (string, optional): Study description (can include wildcards)
     - `accession_number` (string, optional): Accession number
     - `study_instance_uid` (string, optional): Study Instance UID
     - `attribute_preset` (string, optional): Preset level of detail
     - `additional_attributes` (string[], optional): Additional DICOM attributes to include
     - `exclude_attributes` (string[], optional): DICOM attributes to exclude
   - Returns: Array of matching study records

5. `query_series`
   - Search for series within a study
   - Inputs:
     - `study_instance_uid` (string): Study Instance UID (required)
     - `modality` (string, optional): Modality (e.g., "CT", "MR")
     - `series_number` (string, optional): Series number
     - `series_description` (string, optional): Series description
     - `series_instance_uid` (string, optional): Series Instance UID
     - `attribute_preset` (string, optional): Preset level of detail
     - `additional_attributes` (string[], optional): Additional DICOM attributes to include
     - `exclude_attributes` (string[], optional): DICOM attributes to exclude
   - Returns: Array of matching series records

6. `query_instances`
   - Search for instances within a series
   - Inputs:
     - `series_instance_uid` (string): Series Instance UID (required)
     - `instance_number` (string, optional): Instance number
     - `sop_instance_uid` (string, optional): SOP Instance UID
     - `attribute_preset` (string, optional): Preset level of detail
     - `additional_attributes` (string[], optional): Additional DICOM attributes to include
     - `exclude_attributes` (string[], optional): DICOM attributes to exclude
   - Returns: Array of matching instance records

7. `get_attribute_presets`
   - Lists available attribute presets for queries
   - Inputs: None
   - Returns: Dictionary of available presets and their attributes by level

## Installation

### Prerequisites

- Python 3.12 or higher
- A DICOM server to connect to (e.g., Orthanc, dcm4chee, etc.)

### Using uv (recommended)

Using [`uv`](https://docs.astral.sh/uv/) allows for easy installation:

```bash
uv add dicom-mcp
```

### Using pip

Alternatively, install via pip:

```bash
pip install dicom-mcp
```

## Usage

### Basic Command Line

Run the server directly with:

```bash
python -m dicom_mcp
```

Environment variables can be used to configure the default DICOM server:
- `DICOM_HOST`: DICOM server hostname or IP (default: 127.0.0.1)
- `DICOM_PORT`: DICOM server port (default: 11112)
- `DICOM_AE_TITLE`: Application Entity Title (default: MCPSCU)

### Configuration with Claude Desktop

Add this to your `claude_desktop_config.json`:

<details>
<summary>Using uv</summary>

```json
"mcpServers": {
  "dicom": {
    "command": "uvx",
    "args": ["dicom-mcp"],
    "env": {
      "DICOM_HOST": "192.168.1.100",
      "DICOM_PORT": "4242",
      "DICOM_AE_TITLE": "CLAUDESCP"
    }
  }
}
```
</details>

<details>
<summary>Using pip installation</summary>

```json
"mcpServers": {
  "dicom": {
    "command": "python",
    "args": ["-m", "dicom_mcp"],
    "env": {
      "DICOM_HOST": "192.168.1.100",
      "DICOM_PORT": "4242",
      "DICOM_AE_TITLE": "CLAUDESCP"
    }
  }
}
```
</details>

### Usage with Zed

Add to your Zed settings.json:

<details>
<summary>Using uvx</summary>

```json
"context_servers": [
  "dicom-mcp": {
    "command": {
      "path": "uvx",
      "args": ["dicom-mcp"]
    },
    "env": {
      "DICOM_HOST": "192.168.1.100",
      "DICOM_PORT": "4242",
      "DICOM_AE_TITLE": "ZEDSCP"
    }
  }
],
```
</details>

## Example Queries

### Configure the DICOM server

```python
configure_dicom_server(host="192.168.1.100", port=4242, ae_title="MYSCP")
```

### Verify connection

```python
verify_connection()
```

### Search for patients

```python
# Search by name pattern (using wildcard)
patients = query_patients(name_pattern="SMITH*")

# Search by patient ID
patients = query_patients(patient_id="12345678")

# Get detailed information
patients = query_patients(patient_id="12345678", attribute_preset="extended")
```

### Search for studies

```python
# Find all studies for a patient
studies = query_studies(patient_id="12345678")

# Find studies within a date range
studies = query_studies(study_date="20230101-20231231")

# Find studies by modality
studies = query_studies(modality_in_study="CT")
```

### Search for series in a study

```python
# Find all series in a study
series = query_series(study_instance_uid="1.2.840.10008.5.1.4.1.1.2.1.1")

# Find series by modality and description
series = query_series(
    study_instance_uid="1.2.840.10008.5.1.4.1.1.2.1.1",
    modality="CT",
    series_description="CHEST*"
)
```

### Search for instances in a series

```python
# Find all instances in a series
instances = query_instances(series_instance_uid="1.2.840.10008.5.1.4.1.1.2.1.2")

# Find a specific instance by number
instances = query_instances(
    series_instance_uid="1.2.840.10008.5.1.4.1.1.2.1.2",
    instance_number="1"
)
```

## Debugging

You can use the MCP inspector to debug the server:

```bash
npx @modelcontextprotocol/inspector uvx dicom-mcp
```

Or if you've installed the package in development mode:

```bash
cd path/to/dicom-mcp
npx @modelcontextprotocol/inspector python -m dicom_mcp
```

## Development

### Setup Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/dicom-mcp.git
   cd dicom-mcp
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -e .
   ```

### Project Structure

- `src/dicom_mcp/`: Main package
  - `__init__.py`: Package initialization
  - `__main__.py`: Entry point
  - `server.py`: MCP server implementation
  - `dicom_api.py`: DICOM client implementation
  - `attributes.py`: DICOM attribute presets
  - `config.py`: Configuration management

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built on [pynetdicom](https://github.com/pydicom/pynetdicom)
- Follows the [Model Context Protocol](https://modelcontextprotocol.io) specification
