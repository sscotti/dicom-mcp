# Orchestration Workflows

This document describes how to use the DICOM MCP server to orchestrate end-to-end radiology workflows combining FHIR and DICOM operations.

## Overview

The MCP server provides tools for both FHIR (Fast Healthcare Interoperability Resources) and DICOM operations, enabling you to orchestrate complete radiology workflows:

1. **Order Entry**: Create ServiceRequest (order) in FHIR
2. **Scheduling**: Query DICOM Modality Worklist (MWL) or create schedule
3. **Image Acquisition**: Modality performs study and sends to Orthanc
4. **Study Storage**: DICOM study stored in Orthanc
5. **Linking**: Create ImagingStudy in FHIR linked to DICOM study
6. **Reporting**: Create DiagnosticReport with findings
7. **Billing**: Update ServiceRequest status to completed

## Prerequisites

1. **Local HAPI FHIR Server**: Running and accessible

   ```bash
   docker-compose -f tests/docker-compose-fhir.yaml up -d
   ```

2. **Populate Synthetic Data**: Load test data

   ```bash
   python tests/populate_synthetic_fhir_data.py
   ```

3. **Orthanc DICOM Server**: Running with test data

   ```bash
   docker-compose -f tests/docker-compose.yaml up -d
   ```

4. **Configure MCP**: Set `current_fhir: "hapi_local"` in `configuration.yaml`

## Workflow Examples

### Example 1: Order-to-Study Workflow

**Goal**: Create an order, perform the study, link DICOM to FHIR, and generate a report.

**Steps**:

1. **Create ServiceRequest (Order)**

   ```
   Use: fhir_create_resource
   Resource: ServiceRequest with patient, study description, modality, requested date
   ```

2. **Verify DICOM Connection**

   ```
   Use: verify_dicom_connection
   Ensures Orthanc is accessible
   ```

3. **Query for Patient's DICOM Studies**

   ```
   Use: query_studies_by_patient
   Find existing studies for the patient
   ```

4. **Move Study (if needed)**

   ```
   Use: move_study_to_node
   Transfer study from one node to another
   ```

5. **Create ImagingStudy in FHIR**

   ```
   Use: fhir_create_resource
   Resource: ImagingStudy linked to Patient and ServiceRequest
   Include StudyInstanceUID from DICOM
   ```

6. **Create DiagnosticReport**

   ```
   Use: fhir_create_resource
   Resource: DiagnosticReport with findings, linked to ImagingStudy
   ```

7. **Update ServiceRequest Status**

   ```
   Use: fhir_update_resource
   Change status from "active" to "completed"
   ```

### Example 2: Patient Search and Study Retrieval

**Goal**: Find a patient, retrieve their imaging studies, and extract report text.

**Steps**:

1. **Search for Patient**

   ```
   Use: fhir_search_patient
   Search by name, MRN, or birthdate
   ```

2. **Search ImagingStudies**

   ```
   Use: fhir_search_imaging_study
   Filter by patient_id, modality, or date
   ```

3. **Extract StudyInstanceUID**

   ```
   From ImagingStudy resource, get the DICOM StudyInstanceUID
   ```

4. **Query DICOM for Study Details**

   ```
   Use: query_study_by_uid
   Get detailed DICOM metadata
   ```

5. **Extract PDF Report (if present)**

   ```
   Use: extract_pdf_text_from_dicom
   Extract structured report text from DICOM
   ```

### Example 3: Quality Assurance Workflow

**Goal**: Find studies without reports, verify completeness, and flag missing data.

**Steps**:

1. **Search All ImagingStudies**

   ```
   Use: fhir_search_imaging_study
   Get all studies for a date range
   ```

2. **For Each Study**:
   - Check for DiagnosticReport
   - Verify DICOM study exists in Orthanc
   - Check for required metadata

3. **Generate Report**

   ```
   Create summary of studies missing reports or data
   ```

## MCP Tool Reference for Orchestration

### FHIR Tools

| Tool | Purpose | Use Case |
|------|---------|----------|
| `verify_fhir_connection` | Check FHIR server connectivity | Verify setup |
| `fhir_search_patient` | Find patients by name/MRN/date | Patient lookup |
| `fhir_search_imaging_study` | Find imaging studies | Study discovery |
| `fhir_read_resource` | Read any FHIR resource | Get full resource details |
| `fhir_create_resource` | Create new FHIR resource | Order entry, study registration |
| `fhir_update_resource` | Update existing resource | Status updates |
| `list_fhir_servers` | List configured servers | Switch between servers |

### DICOM Tools

| Tool | Purpose | Use Case |
|------|---------|----------|
| `verify_dicom_connection` | Check DICOM server connectivity | Verify setup |
| `query_studies_by_patient` | Find studies by patient ID | Patient study lookup |
| `query_study_by_uid` | Get study by StudyInstanceUID | Study details |
| `query_series_by_study` | Get series in a study | Series enumeration |
| `move_study_to_node` | Transfer study between nodes | Study routing |
| `extract_pdf_text_from_dicom` | Extract PDF report text | Report retrieval |

## Orchestration Patterns

### Pattern 1: Linear Workflow

Execute steps sequentially, one after another:

```
Order → Schedule → Acquire → Store → Link → Report → Bill
```

Use MCP tools in sequence, with each tool's output feeding into the next.

### Pattern 2: Parallel Operations

Execute independent operations simultaneously:

- Search multiple patients in parallel
- Query multiple studies concurrently
- Update multiple resources

The LLM can orchestrate parallel tool calls when appropriate.

### Pattern 3: Conditional Workflows

Make decisions based on data:

- If patient exists, use existing; else create new
- If study complete, generate report; else wait
- If report exists, update; else create new

Use LLM reasoning to determine workflow branches.

## Best Practices

1. **Error Handling**: Always verify connections before operations
2. **Data Consistency**: Link FHIR resources using proper references
3. **Patient Matching**: Use identifiers (MRN) for reliable patient matching
4. **StudyInstanceUID**: Use this as the bridge between FHIR and DICOM
5. **Status Management**: Keep ServiceRequest status updated throughout workflow
6. **Idempotency**: Design workflows to be safely re-runnable

## Future Enhancements

- **DICOM Modality Worklist (MWL)**: Query and update scheduled studies
- **DICOMWeb**: RESTful API for DICOM operations
- **Workflow Templates**: Pre-defined orchestration patterns
- **Event-Driven**: Trigger workflows on DICOM store events
- **FHIR Subscriptions**: React to FHIR resource changes

## Example MCP Jam Prompts

### Create a Complete Order-to-Report Workflow

```
Create a new radiology order for patient MRN001 for a chest X-ray. 
Then verify the DICOM study exists, create an ImagingStudy in FHIR 
linked to the order, and generate a diagnostic report with normal findings.
```

### Find and Summarize Patient Studies

```
Find all imaging studies for patient John Smith (MRN001) from the last 
month. For each study, extract the DICOM metadata and any PDF reports, 
and provide a summary of findings.
```

### Quality Assurance Check

```
Check all imaging studies from the last week. Identify which studies 
have diagnostic reports and which don't. For studies without reports, 
check if the DICOM data is available in Orthanc.
```

## Notes

- **Write Access**: The local HAPI FHIR server supports create/update operations. Public servers (Firely, SIIM) may be read-only.
- **Data Persistence**: Synthetic data persists in the Docker volume. Restart the container to reset.
- **Testing**: Use synthetic data for development. Always verify workflows before production use.
