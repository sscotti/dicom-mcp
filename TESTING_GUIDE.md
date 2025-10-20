# DICOM MCP Testing Guide

This guide shows you how to test all the DICOM MCP tools using the MCP Inspector.

## Setup

### 1. Start Both Orthanc Servers

```bash
cd tests
docker-compose up -d
```

This starts two DICOM servers:

- **ORTHANC (Primary)**: localhost:4242 / Web: localhost:8042
- **ORTHANC2 (Secondary)**: localhost:4243 / Web: localhost:8043

### 2. Upload Test Data

```bash
cd ..
source venv/bin/activate
pytest tests/test_dicom_pdf.py::test_extract_pdf_text -v
```

This uploads:

- Patient: John Doe (ID: DLBCL2024) with 5 PET/CT studies with PDF reports
- Patient: TEST^PATIENT (ID: TEST123) for basic testing

### 3. Start MCP Inspector

```bash
npx @modelcontextprotocol/inspector python3 -m dicom_mcp configuration.yaml --transport stdio
```

## Testing Each Tool

### 🔍 Query Tools

#### 1. **list_dicom_nodes**

No parameters needed. Shows both configured nodes.

**Expected Result:**

```json
{
  "current_node": "main",
  "nodes": [
    {"main": "Local Orthanc DICOM server (Primary)"},
    {"secondary": "Local Orthanc DICOM server (Secondary)"}
  ]
}
```

#### 2. **verify_connection**

No parameters needed. Tests connection to current node.

**Expected Result:**

```json
{
  "result": "Connection successful to localhost:4242 (Called AE: ORTHANC, Calling AE: MCPSCU)"
}
```

#### 3. **query_patients**

Search for patients.

**Test 1 - Find all patients:**

```json
{
  "name_pattern": "",
  "patient_id": "",
  "birth_date": "",
  "attribute_preset": "standard"
}
```

**Test 2 - Find specific patient:**

```json
{
  "name_pattern": "Doe*",
  "patient_id": "",
  "birth_date": "",
  "attribute_preset": "standard"
}
```

#### 4. **query_studies**

Find studies for a patient.

**Test - Find all studies for John Doe:**

```json
{
  "patient_id": "DLBCL2024",
  "study_date": "",
  "modality_in_study": "",
  "study_description": "",
  "accession_number": "",
  "study_instance_uid": "",
  "attribute_preset": "standard"
}
```

**Expected:** 5 PET/CT studies

#### 5. **query_series**

List series within a study.

```json
{
  "study_instance_uid": "<use_study_uid_from_query_studies>",
  "modality": "",
  "series_number": "",
  "series_description": "",
  "series_instance_uid": "",
  "attribute_preset": "standard"
}
```

#### 6. **query_instances**

List instances within a series.

```json
{
  "series_instance_uid": "<use_series_uid_from_query_series>",
  "instance_number": "",
  "sop_instance_uid": "",
  "attribute_preset": "standard"
}
```

### 📄 PDF Extraction

#### 7. **extract_pdf_text_from_dicom**

Extract text from a PDF report.

**Steps:**

1. Use `query_patients` to find patient DLBCL2024
2. Use `query_studies` to get study UIDs
3. Use `query_series` to get series UIDs  
4. Use `query_instances` to get SOP instance UIDs
5. Extract the PDF:

```json
{
  "study_instance_uid": "<from_step_2>",
  "series_instance_uid": "<from_step_3>",
  "sop_instance_uid": "<from_step_4>"
}
```

**Expected:** Full text of the PET/CT report

### ➡️ C-MOVE Operations

#### 8. **switch_dicom_node**

Switch to the secondary server.

```json
{
  "node_name": "secondary"
}
```

#### 9. **move_series**

Move a series from primary to secondary.

**Steps:**

1. Switch back to main node: `switch_dicom_node` with `node_name: "main"`
2. Query a series to get its UID
3. Move it:

```json
{
  "destination_node": "ORTHANC2",
  "series_instance_uid": "<series_uid_from_query>"
}
```

**Expected:**

```json
{
  "success": true,
  "message": "C-MOVE operation completed successfully",
  "completed": <number>,
  "failed": 0,
  "warning": 0
}
```

**Verify:** Switch to secondary node and query to see the moved data!

#### 10. **move_study**

Move an entire study.

```json
{
  "destination_node": "ORTHANC2",
  "study_instance_uid": "<study_uid_from_query>"
}
```

### ⚙️ Utilities

#### 11. **get_attribute_presets**

No parameters needed. Shows available query detail levels.

**Expected:** Shows minimal, standard, and extended presets for each level.

## Web Interfaces

- **Orthanc 1**: <http://localhost:8042>
- **Orthanc 2**: <http://localhost:8043>

View uploaded data, verify C-MOVE operations worked, etc.

## Tips

1. **Copy UIDs:** Use the MCP Inspector's copy button to easily copy UIDs between queries
2. **Test in sequence:** Query patients → studies → series → instances flows naturally
3. **Verify moves:** After C-MOVE, switch nodes and query to verify data arrived
4. **Check web UI:** Use Orthanc Explorer to visually verify data

## Troubleshooting

### Port already in use

```bash
pkill -9 -f inspector
pkill -9 -f dicom_mcp
```

### Servers not responding

```bash
cd tests
docker-compose restart
```

### Re-upload test data

```bash
pytest tests/test_dicom_pdf.py::test_extract_pdf_text -v
```

## Cleanup

```bash
cd tests
docker-compose down
```
