# Enhanced DICOM MCP Test Environment

A comprehensive test environment with enhanced Orthanc DICOM servers featuring multiple plugins for advanced DICOM workflows.

## 🔌 Enhanced Features

### **Enabled Plugins:**

- **PostgreSQL Plugin** - High-performance database (both instances)
- **DICOMweb Plugin** - RESTful DICOM services (WADO-RS, STOW-RS, QIDO-RS)
- **OHIF Plugin** - Modern web-based DICOM viewer
- **Stone Web Viewer Plugin** - Fast, lightweight DICOM viewer
- **VolView Plugin** - 3D volume rendering and visualization
- **Explorer2 Plugin** - Modern web interface for Orthanc
- **Python Plugin** - Custom scripting and automation
- **Transfers Plugin** - Accelerated DICOM transfers

## 🚀 Setup

1. Start enhanced Orthanc DICOM servers with Docker Compose:

```bash
docker-compose up -d
```

2. Install test dependencies:

```bash
uv pip install -r pyproject.toml --extra dev
```

## 🧪 Running Tests

Run tests using pytest:

```bash
pytest test_dicom_mcp.py
```

## 🌐 Access Points

### **Orthanc 1 (Primary - PostgreSQL Database: orthanc1):**

- **Web UI**: <http://localhost:8042>
- **Explorer2**: <http://localhost:8042/ui/app/>
- **OHIF Viewer**: <http://localhost:8042/ohif/>
- **Stone Viewer**: <http://localhost:8042/stone-webviewer/>
- **VolView (3D)**: <http://localhost:8042/volview/>
- **DICOMweb API**: <http://localhost:8042/dicom-web>
- **DICOM Port**: 4242

### **Orthanc 2 (Secondary - PostgreSQL Database: orthanc2):**

- **Web UI**: <http://localhost:8043>
- **Explorer2**: <http://localhost:8043/ui/app/>
- **OHIF Viewer**: <http://localhost:8043/ohif/>
- **Stone Viewer**: <http://localhost:8043/stone-webviewer/>
- **VolView (3D)**: <http://localhost:8043/volview/>
- **DICOMweb API**: <http://localhost:8043/dicom-web>
- **DICOM Port**: 4243

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
