# DICOM MCP Test Environment

A minimal test environment for testing DICOM Model Context Protocol server with Orthanc DICOM server.

## Setup

1. Start Orthanc DICOM server with Docker Compose:

```bash
docker-compose up -d
```

2. Install test dependencies:

```bash
uv pip install -r pyproject.toml --extra dev
```

## Running Tests

Run tests using pytest:

```bash
pytest test_dicom_mcp.py
```

## Test Environment

### Orthanc DICOM Server
- Default URL: http://localhost:8042
- Default DICOM port: 4242

### Configuration

The test environment uses these environment variables (with defaults):

- `ORTHANC_HOST`: Hostname of Orthanc (default: "localhost")
- `ORTHANC_PORT`: DICOM port of Orthanc (default: "4242")
- `ORTHANC_WEB_PORT`: Web UI port of Orthanc (default: "8042")
- `ORTHANC_AET`: AE Title of Orthanc (default: "ORTHANC")

For the DICOM MCP server:
- `DICOM_HOST`: Connection target (defaults to ORTHANC_HOST) 
- `DICOM_PORT`: Connection port (defaults to ORTHANC_PORT)
- `DICOM_AE_TITLE`: Target AE title (defaults to ORTHANC_AET)

## What the Tests Do

1. Verify Orthanc is running
2. Perform a DICOM C-ECHO verification
3. Upload a minimal test DICOM dataset
4. Test the DICOM MCP server tools:
   - verify_connection
   - query_patients
   - query_studies
   - query_series
   - query_instances
   - get_attribute_presets
