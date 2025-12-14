# MCP Naming Scheme for Development Data

This document describes the naming convention used throughout the mini-RIS database to clearly identify all data as **development/synthetic data** for the DICOM MCP project.

## Purpose

All identifiers, names, and codes are prefixed or suffixed with "MCP" to:
- **Clearly mark data as synthetic/development data**
- **Prevent confusion with real patient data**
- **Make it obvious this is test data for MCP development**
- **Ensure data is never mistaken for production/clinical data**

## Naming Patterns

### Identifiers

| Type | Pattern | Example |
|------|---------|---------|
| **MRN** | `MCP-MRN-####` | `MCP-MRN-0001` |
| **Accession Number** | `MCP-ACC-YY-####` | `MCP-ACC-25-0001` (15 chars, fits DICOM SH VR limit) |
| **Order Number** | `MCP-ORD-YYYY-####` | `MCP-ORD-2025-0001` |
| **Encounter Number** | `MCP-ENC-####` | `MCP-ENC-5001` |
| **Report Number** | `MCP-RPT-{ACC}-{TIMESTAMP}` | `MCP-RPT-MCP-ACC-2025-0001-20250601120000` |
| **NPI** | `MCP-NPI-####` | `MCP-NPI-0001` |
| **SPS ID** | `MCP-SPS#` | `MCP-SPS1` |

### Patient Names

- **Database Format**: 
  - Given Name: `Alex`
  - Family Name: `Johnson-MCP`
  
- **DICOM Format**: `Family-MCP^Given`
  - Example: `Johnson-MCP^Alex`
  
- **Full Display**: `Alex Johnson-MCP`

### Physician/Provider Names

- **Database Format**:
  - Given Name: `MCP-Emily`
  - Family Name: `Chen`
  
- **DICOM Format**: `MCP-Given^Family`
  - Example: `MCP-Emily^Chen`
  
- **Full Display**: `MCP-Emily Chen`

### Email Addresses

- Pattern: `{name}.mcp@dev.{domain}`
- Example: `alex.johnson.mcp@dev.example.org`

### Locations

- Pattern: `MCP {Location Name}`
- Example: `MCP Radiology Check-In`

### Notes/Descriptions

- Include `(MCP Dev Data)` or `(MCP Dev)` suffix where appropriate
- Example: `Chest pain evaluation (MCP Dev Data)`

## Database Constraints

The schema includes validation constraints to enforce the MCP naming scheme:

```sql
-- MRN must match MCP pattern
CONSTRAINT chk_patient_mrn CHECK (mrn REGEXP '^MCP-MRN-[0-9]{4,}$')

-- Accession number must match MCP pattern
CONSTRAINT chk_order_accession CHECK (accession_number REGEXP '^MCP-ACC-[0-9]{4}-[0-9]{4}$')
```

## Code Generation

When generating new identifiers in code:

- **Report Numbers**: Automatically prefixed with `MCP-RPT-`
- **Patient Names**: Family name includes `-MCP` suffix
- **Physician Names**: Given name prefixed with `MCP-`

## Examples

### Complete Patient Record

```
MRN: MCP-MRN-0001
Name: Alex Johnson-MCP
DICOM Name: Johnson-MCP^Alex
Email: alex.johnson.mcp@dev.example.org
```

### Complete Order Record

```
Order Number: MCP-ORD-2025-0001
Accession: MCP-ACC-2025-0001
Patient: MCP-MRN-0001 (Alex Johnson-MCP)
Ordering Physician: MCP-Emily Chen (MCP-NPI-0001)
Performing Physician: MCP-Casey Wells (MCP-NPI-0003)
```

### DICOM MWL Entry

```
PatientID: MCP-MRN-0001
PatientName: Johnson-MCP^Alex
AccessionNumber: MCP-ACC-2025-0001
RequestedProcedureID: MCP-ORD-2025-0001
ScheduledPerformingPhysicianName: MCP-Casey^Wells
ScheduledProcedureStepID: MCP-SPS1
```

## Benefits

1. **Clear Identification**: Instantly recognizable as development data
2. **Safety**: Prevents accidental use in production systems
3. **Consistency**: Uniform pattern across all data types
4. **Traceability**: Easy to filter/search for MCP data
5. **Documentation**: Self-documenting naming convention

## Migration Notes

If you have existing data without MCP prefixes, you'll need to:

1. Update MRNs: `MRN1001` → `MCP-MRN-0001`
2. Update Accession Numbers: `ACC-2025-0001` → `MCP-ACC-2025-0001`
3. Update Patient Names: Add `-MCP` to family names
4. Update Physician Names: Add `MCP-` prefix to given names
5. Update all related identifiers in orders, encounters, reports, etc.

## See Also

- `mysql/mini_ris.sql` - Complete schema with MCP naming
- `src/dicom_mcp/server.py` - Code that generates MCP identifiers

