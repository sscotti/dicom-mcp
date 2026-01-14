# DICOM MCP Server - Medical Imaging AI Integration 🏥

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Python SDK](https://img.shields.io/badge/MCP-Python%20SDK-blue)](https://github.com/modelcontextprotocol/python-sdk)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.0-blue)](https://github.com/jlowin/fastmcp)
[![MCP JAM](https://img.shields.io/badge/MCP-JAM-orange)](https://www.mcpjam.com)

This version uses [MCP Jam](https://www.mcpjam.com) exclusively for development, testing, and LLM integration. Note that if you are using the Cursor IDE, or others, you can configure the IDE to also access the server in some cases, in `~/.cursor/mcp.json`, etc. See <https://cursor.com/docs/context/mcp#what-is-mcp> for details.

Enables AI assistants to query, read, and move data on PACS using the standard Model Context Protocol (MCP), with Orthanc as the reference implementation.  You can use your own APIKEY (e.g. for ChatGPT) and run it locally for development using ChatGPT as the LLM.  Also integrated with FHIR and a mini-RIS DB.

## ✨ Core Capabilities

`dicom-mcp` provides tools to:

* **🔍 Query DICOM**: Search for patients, studies, series, and instances using various criteria
* **📄 Read DICOM Reports (PDF)**: Retrieve DICOM instances containing encapsulated PDFs (e.g., clinical reports) and extract the text content
* **📄 Create Radiology Reports**: Generate radiology reports in PDF format and attach to PACS
* **➡️ Send DICOM Images**: Send series or studies to other DICOM destinations, e.g. AI endpoints for image segmentation, classification, etc.
* **⚙️ FHIR Integration**: Query and manage FHIR resources (Patient, ImagingStudy, ServiceRequest, etc.)
* **⚙️ Mini-RIS**: Manage radiology orders, worklists, and reporting workflows
* **⚙️ MWL/MPPS**: Modality Worklist and Modality Performed Procedure Step services
* **⚙️ Utilities**: Manage connections, switch servers, and understand query options

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

`dicom-mcp` requires a YAML configuration file (`configuration.yaml` or similar) defining DICOM nodes and calling AE titles. Adapt the configuration or keep as is for compatibility with the sample Orthanc server.

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

# FHIR server configuration (optional)
# You can configure multiple FHIR servers and switch between them
fhir_servers:
  firely:
    base_url: "https://server.fire.ly"
    description: "Firely FHIR Test Server (public, no API key needed)"
  
  siim:
    base_url: "https://hackathon.siim.org/fhir"
    api_key: "${SIIM_API_KEY}"  # Set in .env file
    description: "SIIM Hackathon FHIR server"
  
  # Uncomment to use a local HAPI FHIR server
  hapi_local:
    base_url: "http://localhost:8080/fhir"
    description: "Local HAPI FHIR server"

current_fhir: "hapi_local"  # Active FHIR server: firely, siim, or hapi_local, make sure to start the local hapi fhir server before starting the MCP server

# The server will expose all DICOM tools and FHIR tools via standard MCP protocol

# Mini-RIS MySQL database configuration (optional)
mini_ris:
  host: "localhost"
  port: 3306
  user: "orthanc_ris_app"
  password: "${MINI_RIS_DB_PASSWORD}"
  database: "orthanc_ris"
  pool_size: 5
```

> [!WARNING]
> DICOM-MCP is not meant for clinical use, and should not be connected with live hospital databases or databases with patient-sensitive data. Doing so could lead to both loss of patient data, and leakage of patient data onto the internet. DICOM-MCP can be used with locally hosted open-weight LLMs for complete data privacy.
>
> [!NOTE]
> This project uses **MCP Jam** for development, testing, and LLM integration needs. The `mcp-config.example.json` file is provided as a template with relative paths that you can adapt to your setup.  That can be imported as JSON into MCPJAM to configure the interface.

### Docker Container Setup (Orthancs, FHIR, PostGres and MySQL)

```bash
docker-compose up -d
dotenv run -- pytest # uploads dummy pdf data to ORTHANC server
```

UI at [https://localhost:8042](https://localhost:8042) and [https://localhost:8043](https://localhost:8043), note that the repo is configured with TLS certs, so https.

HAPI FHIR will be available at [http://localhost:8080/fhir](http://localhost:8080/fhir)

See [FHIR Servers Guide](FHIR_SERVERS.md) for detailed configuration options including Firely test server and SIIM integration.

### 🔌 Using with MCP Jam (Recommended)

**MCP Jam** is an alternative tool for testing and exploring your DICOM MCP server. It offers a web interface with **Guest Mode** for immediate testing without any setup. For a self-contained solution, use the Custom Web UI above!

> **Note**: MCP Jam Guest Mode may have limitations on certain features like the Resources panel. Resources are still fully accessible via the `list_saved_resources` and `get_saved_resource` tools, which work in Guest Mode. For full Resources panel support, you may need to use an account.

**Start MCP Jam:**

```bash
# Navigate to your dicom-mcp directory
cd /path/to/dicom-mcp

# Activate your virtual environment
source venv/bin/activate

# Start MCP Jam (use latest or beta)
npx -y @mcpjam/inspector@latest
# or
npx -y @mcpjam/inspector@beta
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

**Using Your OpenAI API Key in Cursor IDE:**

> **Note**: For MCP server development and testing, **MCP Jam is recommended**. Cursor is better for general code development with MCP tools available in context.

If you want to use Cursor IDE with ChatGPT for coding tasks:

1. **Get your API key from `.env`** (if stored there):

   ```bash
   grep OPENAI_API_KEY .env
   ```

2. **Configure in Cursor**:
   * Open Cursor Settings (Cmd+Shift+J / Ctrl+Shift+J)
   * Navigate to **Models** section
   * Paste your OpenAI API key and verify
   * Select your preferred GPT model (GPT-4, GPT-4 Turbo, etc.)

> **Note**: Cursor requires the API key to be entered in its settings UI - it doesn't automatically read from `.env` files. Copy the value from your `.env` file and paste it into Cursor's settings.

This gives you ChatGPT-powered AI in Cursor with persistent system prompts and full codebase integration. See [CURSOR_SETUP.md](CURSOR_SETUP.md) for complete setup instructions.

**System Prompt:**

For better LLM interactions, you can configure a system prompt:

* **In MCP Jam**: Copy the content from `system_prompt.txt` into the system prompt field in the Playground tab when starting a new session.
* **In Cursor IDE**: Set the system prompt in Cursor's settings (persists between sessions) - see [CURSOR_SETUP.md](CURSOR_SETUP.md) for details.
* **Via Tool**: Use the `get_system_prompt` tool in either interface to retrieve the prompt text automatically.

> **Note**: MCP Jam Guest Mode may not persist system prompts between sessions. Cursor IDE settings persist. Keep `system_prompt.txt` handy or use the `get_system_prompt` tool for quick access.

**MCP Jam Features:**

* ✅ **Guest Mode**: No account required - start testing immediately
* ✅ **Beautiful UI**: Modern interface with AI provider logos
* ✅ **Easy Setup**: Simple server configuration with clear forms
* ✅ **Real-time Testing**: Interactive tool execution with immediate results
* ✅ **Full Functionality**: Access to all DICOM, FHIR, RIS, and reporting tools
* ✅ **LLM Playground**: Test your DICOM server with various LLMs
* ✅ **Community Driven**: Active development with regular updates

**Note on Resources**: Resources are registered with FastMCP and accessible via:

* **Tools** (works in Guest Mode): Use `list_saved_resources` and `get_saved_resource` tools to access resources
* **Resources Panel** (may require account): Native MCP resources protocol - visible in Resources tab if supported by your MCP Jam mode

**MCP Jam Tabs:**

* **Servers Tab**: Manage and connect to your DICOM MCP server
* **Tools Tab**: Browse and test all available tools interactively
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
* `switch_fhir_server` - Switch to a different FHIR server without restarting
* `fhir_search_patient` - Search for Patient resources
* `fhir_search_imaging_study` - Search for ImagingStudy resources
* `fhir_read_resource` - Read any FHIR resource by type and ID
* `fhir_create_resource` - Create new FHIR resources (Patient, ImagingStudy, ServiceRequest, etc.)
* `fhir_update_resource` - Update existing FHIR resources

See [FHIR_SERVERS.md](FHIR_SERVERS.md) for configuration details.

**Mini-RIS Tools (when MySQL is configured):**

* `list_mini_ris_patients` - Browse patient demographics stored in the mini-RIS schema (filter by MRN or name)
* `create_mwl_from_order` - Create a DICOM Modality Worklist entry from an existing mini-RIS order
* `create_synthetic_cr_study` - Generate synthetic CR DICOM images and send to PACS (virtual modality)

**Radiology Reporting Tools (when MySQL is configured):**

* `get_study_for_report` - Retrieve complete study information for radiology reporting
* `list_radiologists` - List available radiologists with credentials
* `create_radiology_report` - Create structured radiology report with findings and impression
* `generate_report_pdf` - Generate professional PDF from report (base64 encoded)
* `attach_report_to_pacs` - Upload report PDF to PACS as DICOM Encapsulated PDF

**Mini-RIS Database Schema:**

The `mini_ris.sql` schema provides a complete radiology information system with:

* **Core Entities**: Patients, Providers, Encounters, Orders, Imaging Studies, Reports
* **Reference Tables**:
  * `dicom_tags` - 50 essential DICOM tag definitions for MWL/MPPS validation
  * `procedures` - 14 CR/XR procedure codes with typical views and image counts
  * `modalities` - Standard DICOM modality codes
  * `body_parts` - Anatomical regions for imaging
* **MWL/MPPS Support**: Tables for Modality Worklist and Modality Performed Procedure Step tracking

**MCP Naming Scheme:**

All data in the mini-RIS uses a consistent "MCP-" prefix/suffix naming scheme to clearly mark it as **development/synthetic data**:

* MRNs: `MCP-MRN-0001`
* Accession Numbers: `MCP-ACC-2025-0001`
* Patient Names: `Johnson-MCP^Alex` (DICOM format)
* Physician Names: `MCP-Emily^Chen` (DICOM format)

See [MCP_NAMING_SCHEME.md](MCP_NAMING_SCHEME.md) for complete details.

**Setup:**

1. Launch the MySQL service:

   ```bash
   docker compose up -d mysql
   ```

2. Initialize the database (automatic on first start, or manually):

   ```bash
   docker exec -i dicom-mcp-mysql-1 mysql -uorthanc_ris_app -porthanc_ris_app orthanc_ris < mysql/mini_ris.sql
   ```

3. Configure environment variables in `.env`:

   ```bash
   MINI_RIS_DB_PASSWORD=orthanc_ris_app
   ```

4. Verify `configuration.yaml` contains the `mini_ris` block.

**Included CR Procedures:**

The database includes 14 common Computed Radiography (CR) procedures optimized for single-image study workflows:

* Chest (1 or 2 views)
* Abdomen (1 or 2 views)
* Pelvis, Cervical/Lumbar Spine
* Upper Extremity: Hand, Wrist, Shoulder
* Lower Extremity: Knee, Ankle, Foot
* Skull

Each procedure includes typical view projections (AP, PA, Lateral, Oblique) and expected image counts for realistic test data generation.

**MWL/MPPS Services:**

The project includes integrated Modality Worklist (MWL) and Modality Performed Procedure Step (MPPS) services for managing imaging workflow:

* **mwl-mpps** (port 4104) - DICOM SCP for MWL queries and MPPS N-CREATE/N-SET operations
* **mwl-api** (port 8000) - FastAPI REST interface for creating and managing MWL entries from mini-RIS orders

**Environment Variables:**

Both services share the same MySQL database configuration via:

```bash
MINI_RIS_DB_PASSWORD=orthanc_ris_app  # Default password for orthanc_ris_app user
```

**Usage:**

1. Start the MWL/MPPS services:

   ```bash
   docker compose up -d mwl-mpps mwl-api
   ```

2. Query worklist via DICOM C-FIND:

   ```bash
   # Use -W for Modality Worklist queries (not -P for Patient Root)
   findscu -v -W -k 0008,0050="" -k 0010,0020="" localhost 4104
   
   # Or query by specific accession number:
   findscu -v -W -k 0008,0050="ACC-2025-0001" localhost 4104
   ```

3. Create MWL entries via REST API:

   ```bash
   curl -X POST http://localhost:8000/mwl/create_from_json \
     -H "Content-Type: application/json" \
     -d @mwl_payload.json
   ```

4. View MWL records in web dashboard:

   ```bash
   open http://localhost:8000/mwl
   # Or visit http://localhost:8000 for the main dashboard
   ```

The MWL/MPPS tables (`mwl`, `mpps`, `mwl_tasks`) in the mini-RIS database store all worklist items and procedure step statuses, enabling full traceability from order to completed exam.

**Creating MWLs from Orders (via MCP Tool):**

The `create_mwl_from_order` tool automates MWL creation from mini-RIS orders:

```python
# Example: Patient arrives, technician creates MWL from order
# In MCP Jam or via LLM:
create_mwl_from_order(
    order_id=1,
    scheduled_station_aet="ORTHANC"
)

# Returns:
{
  "success": true,
  "message": "MWL created successfully for order 1",
  "accession_number": "ACC-2025-0001",
  "patient_name": "Alex Johnson",
  "patient_id": "MRN1001",
  "procedure": "Chest X-Ray 2 Views",
  "modality": "CR",
  "scheduled_time": "2025-06-01 09:15:00",
  "mwl_id": 42
}
```

This enables LLM-driven workflows like:

* "Create a worklist entry for order 1"
* "Patient MRN1001 has arrived, set up their chest x-ray"
* "List all scheduled orders and create MWLs for today's patients"

**Virtual CR Device** 🆕

The project includes a virtual CR (Computed Radiography) device that generates synthetic DICOM images for complete workflow demonstrations:

```python
# Example: Complete imaging workflow
# 1. Create MWL from order
create_mwl_from_order(order_id=1)

# 2. Simulate CR device acquiring images
create_synthetic_cr_study(
    accession_number="ACC-2025-0001",
    image_mode="simple",  # or "ai" with OpenAI key
    send_to_pacs=True
)

# Result: 2 CR images created and sent to Orthanc!
```

**Image Generation Modes:**

1. **`simple`** (No API key required) - Basic synthetic images with anatomical outlines
2. **`ai`** (Requires `OPENAI_API_KEY`) - Realistic AI-generated images via OpenAI `gpt-image-1` model
3. **`auto`** (Default) - Uses AI if key available, falls back to simple
4. **`sample`** - Uses pre-made sample images from library

⚠️ **IMPORTANT**:

* Synthetic images are for development/testing/training only. NOT for clinical use.
* AI mode uses OpenAI's `gpt-image-1` model (~30-40 seconds per image)
* Multi-view studies (2+ images) may timeout in MCP clients but **still complete successfully**
  * Images are created and sent to PACS even if you see a timeout error
  * Check Orthanc to verify the images arrived
* For faster generation or reliable testing, use `image_mode="simple"` instead of "auto"

**Configuration:**

Add to `.env` (optional for AI mode):

```bash
OPENAI_API_KEY=sk-proj-xxxxx  # Optional - enables AI-generated images
```

**LLM-Driven Workflow Examples:**

```txt
User: "Patient Johnson completed their chest x-ray, create the study"
LLM: Calls create_synthetic_cr_study(accession_number="MCP-ACC-2025-0001", image_mode="simple")
Result: 2-view chest study appears in Orthanc instantly!

User: "Generate a realistic chest x-ray showing pneumonia in the right lung"
LLM: Calls with image_mode="ai", image_description="pneumonia right lower lobe"
Result: gpt-image-1 generates photorealistic pneumonia appearance (~40 seconds)
Note: May show timeout error but images still arrive in PACS
```

**Workflow Consistency with Order-Based Prompts** 🆕

Orders can now include prompts for both image generation and report creation, creating a closed-loop workflow:

1. **Image Generation Prompt** (`image_generation_prompt`): Describes what the images should show
2. **Report Findings Description** (`report_findings_description`): Describes expected findings for reports

This enables consistent workflows where:

* Images are generated based on the order's `image_generation_prompt`
* Reports can use the order's `report_findings_description` as a starting point
* The entire workflow (Order → Images → Report) is internally consistent

```python
# Example: Order with prompts
# Order MCP-ORD-2025-0001 has:
#   image_generation_prompt: "Chest X-ray showing subtle patchy opacity in right lower lobe"
#   report_findings_description: "Subtle patchy opacity in right lower lobe consistent with early pneumonia"

# 1. Generate images using order prompt (automatically used if available)
create_synthetic_cr_study(
    accession_number="MCP-ACC-2025-0001",
    image_mode="ai"  # Will use order's image_generation_prompt
)

# 2. Create report using order findings (optional)
create_radiology_report(
    accession_number="MCP-ACC-2025-0001",
    findings="",  # Empty - will use order's report_findings_description
    impression="Early pneumonia",
    use_order_findings=True  # Use order's report_findings_description
)
```

**Benefits:**

* **Consistency**: Images and reports match the original order intent
* **Automation**: Prompts stored in orders enable fully automated workflows
* **Testing**: Easy to test how well AI-generated images match expected findings
* **Traceability**: Complete audit trail from order → images → report

This completes the full RIS/PACS workflow:

```txt
Order → MWL → Virtual Device → DICOM Images → PACS Storage → Viewing → Reporting
```

**Radiology Reporting** 🆕

Create professional radiology reports and attach them as DICOM Encapsulated PDFs to studies in your PACS:

```python
# Complete reporting workflow
# 1. Get study information for reporting
study_info = get_study_for_report(accession_number="MCP-ACC-2025-0001")

# 2. List available radiologists
radiologists = list_radiologists()

# 3. Create a radiology report
# Option A: Manual findings
report = create_radiology_report(
    accession_number="MCP-ACC-2025-0001",
    findings="""
    The heart is normal in size. The mediastinum is unremarkable.
    Both lungs are clear without focal consolidation, pleural effusion, or pneumothorax.
    No acute bony abnormality is identified.
    """,
    impression="Normal chest radiograph. No acute cardiopulmonary process.",
    author_provider_id=3,  # Dr. MCP-Casey Wells (from list_radiologists)
    report_status="Final"
)

# Option B: Use order's report_findings_description (if available)
report = create_radiology_report(
    accession_number="MCP-ACC-2025-0001",
    findings="",  # Empty - will use order's report_findings_description
    impression="Early pneumonia",
    author_provider_id=3,
    report_status="Final",
    use_order_findings=True  # Use order's report_findings_description
)

# 4. Generate PDF preview (optional)
pdf_data = generate_report_pdf(report_id=report['report_id'])
# Returns base64 encoded PDF for preview/download

# 5. Attach report to PACS as DICOM Encapsulated PDF
result = attach_report_to_pacs(report_id=report['report_id'])
# Report PDF now appears as a DOC series in Orthanc!
```

**Report Workflow Features:**

* **Database Storage**: Reports saved in mini-RIS `reports` table with full audit trail
* **Professional PDF**: Generated with ReportLab (default) - institutional header, demographics, findings, impression, signature
* **Alternative PDF Library**: WeasyPrint is also installed as an option for HTML/CSS-based PDF generation (useful for web-based report templates)
* **DICOM Standard**: Encapsulated PDF (SOP Class: `1.2.840.10008.5.1.4.1.1.104.1`)
* **PACS Integration**: PDF attached to original study as new series (Modality: DOC, Series #9999)
* **Status Tracking**: Preliminary → Final → Amended → Cancelled
* **Provider Attribution**: Links to radiologist in mini-RIS providers table

**LLM-Driven Reporting Examples:**

```txt
User: "Create a final report for accession ACC-2025-0001. Normal chest x-ray."
LLM: → get_study_for_report() to fetch patient/study data
     → list_radiologists() to get available radiologists
     → create_radiology_report() with structured findings/impression
     → attach_report_to_pacs() to send PDF to PACS
Result: Complete report in database + PDF in PACS!

User: "Generate a preliminary report for the knee study showing a tibial fracture"
LLM: → Creates report with report_status="Preliminary"
     → Structures findings describing the fracture
     → Generates and attaches PDF to PACS
Result: Preliminary report available for review

User: "Show me the PDF for report ID 5"
LLM: → generate_report_pdf(report_id=5)
     → Returns base64 PDF for display/download
```

**Report Status Workflow:**

```txt
Preliminary → Final → [Amended] → [Cancelled]
```

Each status change creates a new audit trail entry with timestamp.

**Database Schema:**

```sql
reports:
  - report_id (PK)
  - imaging_study_id (FK to imaging_studies)
  - report_number (unique, e.g., "RPT-ACC-2025-0001-20250601120000")
  - author_provider_id (FK to providers - radiologist)
  - report_status (enum: Preliminary, Final, Amended, Cancelled)
  - report_datetime (timestamp)
  - report_text (LONGTEXT - findings)
  - impression (TEXT - clinical impression)
  - dicom_sop_instance_uid (populated after PACS attachment)
  - dicom_series_instance_uid (populated after PACS attachment)
```

**Complete Imaging + Reporting Workflow:**

```txt
┌─────────────────────────────────────────────────────────┐
│ 1. Order Management (Mini-RIS)                          │
│    create_mwl_from_order(order_id=1)                    │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│ 2. Image Acquisition (Virtual CR Device)                │
│    create_synthetic_cr_study(accession="ACC-2025-0001") │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│ 3. PACS Storage (Orthanc)                               │
│    Images viewable at http://localhost:8042             │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│ 4. Radiology Reporting                                  │
│    create_radiology_report(...)                         │
│    attach_report_to_pacs(report_id=1)                   │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│ 5. Complete Study in PACS                               │
│    - CR Images (Series 1, 2)                            │
│    - Report PDF (Series 9999, Modality DOC)             │
└─────────────────────────────────────────────────────────┘
```

### 🧪 Synthetic Data for Testing

To test orchestration workflows, populate your local HAPI FHIR server with synthetic data:

```bash
# Populate synthetic data
python tests/populate_synthetic_fhir_data.py
```

This creates:

* 5 test patients with realistic demographics
* ServiceRequests (orders) for imaging studies
* ImagingStudies linked to patients
* DiagnosticReports with findings

### 🔄 Orchestration Workflows

The MCP server enables end-to-end radiology workflows combining FHIR and DICOM:

* **Order Entry**: Create ServiceRequest in FHIR
* **Study Acquisition**: Link DICOM studies to FHIR ImagingStudies
* **Reporting**: Generate DiagnosticReports from DICOM PDFs
* **Workflow Management**: Track orders through completion

### 🔧 Development & Debugging

**MCP Jam** is the recommended tool for development, testing, and debugging your DICOM MCP server.

**Development Workflow:**

1. **Start Docker**: `docker-compose up -d`
2. **Load test data**: `dotenv run -- pytest` (uploads sample DICOM data)
3. **Start MCP Jam**: `npx -y @mcpjam/inspector@latest` or `npx -y @mcpjam/inspector@beta`
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

### 🎨 Custom Web UI (Self-Contained, experimental !)

**Your own custom web interface** - All in this repo, no external dependencies!

```bash
# Activate virtual environment
source venv/bin/activate

# Start the custom web UI, experimental !!
python start_web_ui.py

# Or directly with uvicorn
uvicorn dicom_mcp.web_ui:app --host 127.0.0.1 --port 8080
```

The web UI will be available at **<http://127.0.0.1:8080>**

**Features:**

* ✅ **LLM-Powered Chat** - Intelligent chat with OpenAI integration for natural language queries
* ✅ **Tool Browser** - Browse and explore all 28 available DICOM/FHIR/RIS tools
* ✅ **Prompt Management** - Edit and save system prompts optimized for medical imaging
* ✅ **Tool Execution** - Execute tools directly from chat or UI
* ✅ **Medical Imaging Focus** - Customized for DICOM and FHIR workflows
* ✅ **Self-Contained** - Everything in your repo, no external services needed
* ✅ **Dark Theme** - Beautiful, modern dark UI
* ✅ **Saved Resources** - Curated reference files (e.g., Orthanc OpenAPI) live in `resources/manifest.yaml`, accessible via the Resources panel or new `list_saved_resources` / `get_saved_resource` MCP tools.

**LLM Integration:**

Enable OpenAI-powered chat by setting your API key:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

The LLM will:

* Understand natural language queries about medical imaging
* Automatically select and execute appropriate DICOM/FHIR tools
* Format results in a clinical, readable format
* Use the medical imaging system prompt for context-aware responses

**Example Queries:**

* "List all available DICOM nodes"
* "Find patients with last name Smith"
* "Show me studies from last week"
* "Verify connection to PACS"
* "What tools are available for FHIR?"

## 🙏 Acknowledgments

* Built using [FastMCP](https://github.com/jlowin/fastmcp) - The fast, Pythonic way to build MCP servers
* Built using [pynetdicom](https://github.com/pydicom/pynetdicom) for DICOM network communication
* Uses [pypdf](https://pypi.org/project/pypdf/) for PDF text extraction
