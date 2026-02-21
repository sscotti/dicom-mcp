# Adding MCP UI Components to dicom-mcp

This guide shows how to add MCP UI components to your Python FastMCP server **without needing React or Vue.js**. MCP UI components are just HTML files served as MCP resources.

## What Are MCP UI Components?

MCP UI components are HTML files that:
- Are served as MCP resources with special MIME type `application/vnd.mcp.ui`
- Can be referenced by tools via `_meta.ui.resourceUri`
- Work in MCP Jam, Claude Desktop, and other MCP-compatible clients
- Use vanilla JavaScript (no framework required!)

## Step 1: Create UI Component Directory

```bash
mkdir -p src/dicom_mcp/ui_components
```

## Step 2: Create a Sample UI Component

Create `src/dicom_mcp/ui_components/patient-query.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>DICOM Patient Query - dicom-mcp</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { 
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
      background: #0d1117; 
      color: #e6edf3; 
      padding: 16px; 
    }
    .header { 
      display: flex; 
      align-items: center; 
      justify-content: space-between;
      margin-bottom: 16px; 
      padding-bottom: 12px; 
      border-bottom: 2px solid #30363d; 
    }
    .header h1 { font-size: 20px; font-weight: 700; color: #58a6ff; }
    .search-form {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 16px;
    }
    .form-group {
      margin-bottom: 12px;
    }
    label {
      display: block;
      font-size: 13px;
      font-weight: 600;
      color: #8b949e;
      margin-bottom: 6px;
    }
    input {
      width: 100%;
      padding: 8px 12px;
      background: #0d1117;
      border: 1px solid #30363d;
      border-radius: 6px;
      color: #e6edf3;
      font-size: 14px;
    }
    input:focus {
      outline: none;
      border-color: #58a6ff;
    }
    button {
      background: #238636;
      color: white;
      border: none;
      padding: 10px 20px;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 600;
      font-size: 14px;
    }
    button:hover {
      background: #2ea043;
    }
    button:disabled {
      background: #30363d;
      cursor: not-allowed;
    }
    .results {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 16px;
    }
    .patient-card {
      background: #0d1117;
      border: 1px solid #30363d;
      border-radius: 6px;
      padding: 12px;
      margin-bottom: 8px;
    }
    .patient-name {
      font-weight: 600;
      color: #58a6ff;
      margin-bottom: 4px;
    }
    .patient-details {
      font-size: 13px;
      color: #8b949e;
    }
    .loading {
      text-align: center;
      padding: 40px;
      color: #8b949e;
    }
    .error {
      background: #da3633;
      color: white;
      padding: 12px;
      border-radius: 6px;
      margin-bottom: 16px;
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>🔍 DICOM Patient Query</h1>
  </div>
  
  <div class="search-form">
    <div class="form-group">
      <label for="name-pattern">Patient Name Pattern</label>
      <input type="text" id="name-pattern" placeholder="e.g., SMITH* or *JOHN*" />
    </div>
    <div class="form-group">
      <label for="patient-id">Patient ID</label>
      <input type="text" id="patient-id" placeholder="e.g., 12345678" />
    </div>
    <div class="form-group">
      <label for="birth-date">Birth Date (YYYYMMDD)</label>
      <input type="text" id="birth-date" placeholder="e.g., 19700101" />
    </div>
    <button id="search-btn">Search Patients</button>
  </div>

  <div id="error-container"></div>
  <div id="results-container" class="results">
    <div class="loading">Enter search criteria and click "Search Patients"</div>
  </div>

  <script type="module">
    // Note: This is a simplified example
    // In a real implementation, you'd use the MCP SDK to communicate with the server
    const searchBtn = document.getElementById('search-btn');
    const namePattern = document.getElementById('name-pattern');
    const patientId = document.getElementById('patient-id');
    const birthDate = document.getElementById('birth-date');
    const resultsContainer = document.getElementById('results-container');
    const errorContainer = document.getElementById('error-container');

    searchBtn.addEventListener('click', async () => {
      errorContainer.innerHTML = '';
      resultsContainer.innerHTML = '<div class="loading">Searching...</div>';
      searchBtn.disabled = true;

      try {
        // In MCP UI components, you'd use the MCP SDK to call tools
        // For now, this is a placeholder showing the structure
        const params = {
          name_pattern: namePattern.value || '',
          patient_id: patientId.value || '',
          birth_date: birthDate.value || '',
          attribute_preset: 'standard'
        };

        // This would be replaced with actual MCP tool call
        // const result = await mcpApp.callServerTool({
        //   name: 'query_patients',
        //   arguments: params
        // });

        // For demonstration, showing expected structure:
        resultsContainer.innerHTML = `
          <div class="patient-card">
            <div class="patient-name">SMITH^JOHN</div>
            <div class="patient-details">
              Patient ID: 12345<br>
              Birth Date: 19700101<br>
              Sex: M
            </div>
          </div>
        `;
      } catch (error) {
        errorContainer.innerHTML = `<div class="error">Error: ${error.message}</div>`;
        resultsContainer.innerHTML = '';
      } finally {
        searchBtn.disabled = false;
      }
    });
  </script>
</body>
</html>
```

## Step 3: Register UI Components as MCP Resources

Modify `src/dicom_mcp/server.py` to register UI components:

```python
from pathlib import Path
from mcp.server.fastmcp.resources.static import StaticResource
from pydantic import AnyUrl

def register_ui_components(mcp: FastMCP, config_path: Path):
    """Register MCP UI components as resources."""
    ui_dir = config_path.parent / "src" / "dicom_mcp" / "ui_components"
    
    if not ui_dir.exists():
        logger.warning(f"UI components directory not found: {ui_dir}")
        return
    
    ui_components = {
        "patient-query": {
            "file": "patient-query.html",
            "name": "Patient Query UI",
            "description": "Interactive UI for querying DICOM patients"
        },
        # Add more UI components here
    }
    
    for component_id, component_info in ui_components.items():
        html_file = ui_dir / component_info["file"]
        if html_file.exists():
            try:
                content = html_file.read_text(encoding="utf-8")
                uri = AnyUrl(f"ui://dicom-mcp/{component_id}")
                
                # Register as MCP resource with UI MIME type
                resource = StaticResource(
                    uri=uri,
                    name=component_info["name"],
                    description=component_info["description"],
                    mime_type="application/vnd.mcp.ui",  # Special MIME type for UI components
                    text=content
                )
                
                # Add to resource manager
                resource_manager = getattr(mcp, '_resource_manager', None)
                if resource_manager:
                    resource_manager.add_resource(resource)
                    logger.info(f"Registered UI component: {component_id}")
            except Exception as e:
                logger.warning(f"Failed to register UI component {component_id}: {e}")
```

## Step 4: Enhance Tools to Reference UI Components

Modify your `query_patients` tool to reference the UI component:

```python
@mcp.tool()
def query_patients(
    name_pattern: str = "", 
    patient_id: str = "", 
    birth_date: str = "", 
    attribute_preset: str = "standard", 
    additional_attributes: Optional[List[str]] = None,
    exclude_attributes: Optional[List[str]] = None, 
    ctx: Context = None
) -> Dict[str, Any]:
    """Query patients matching the specified criteria from the DICOM node.
    
    This tool performs a DICOM C-FIND operation at the PATIENT level to find patients
    matching the provided search criteria.
    
    Args:
        name_pattern: Patient name pattern (can include wildcards * and ?), e.g., "SMITH*"
        patient_id: Patient ID to search for, e.g., "12345678"
        birth_date: Patient birth date in YYYYMMDD format, e.g., "19700101"
        attribute_preset: Controls which attributes to include in results
        additional_attributes: List of specific DICOM attributes to include
        exclude_attributes: List of DICOM attributes to exclude
    
    Returns:
        Dictionary with 'result' key containing a list of patient dictionaries.
    """
    # ... existing implementation ...
    
    # The tool metadata can reference the UI component
    # This is done via FastMCP's tool metadata system
    pass

# After tool definition, you can add metadata (if FastMCP supports it):
# Note: FastMCP may handle this differently - check FastMCP docs for _meta support
```

## Step 5: Using MCP SDK in UI Components (Full Implementation)

For a complete implementation, UI components need to communicate with the MCP server. Here's how:

```html
<script type="module">
  // Import MCP SDK (when available for Python servers)
  // For now, this shows the pattern you'd follow
  
  // In a real implementation with MCP SDK:
  // import { App } from "@modelcontextprotocol/ext-apps";
  // const app = new App({ name: "DICOM Patient Query", version: "1.0.0" });
  
  // app.ontoolresult = (result) => {
  //   // Handle tool result and render UI
  //   const data = JSON.parse(result.content[0].text);
  //   renderPatients(data.result);
  // };
  
  // async function searchPatients(params) {
  //   const result = await app.callServerTool({
  //     name: "query_patients",
  //     arguments: params
  //   });
  //   return result;
  // }
  
  // app.connect();
</script>
```

## Step 6: Integration with Your FastAPI Web UI

Your existing `web_ui.py` can also serve these UI components! Add a route:

```python
@app.get("/ui/{component_id}")
async def serve_ui_component(component_id: str):
    """Serve MCP UI components via FastAPI."""
    ui_dir = Path(__file__).parent / "ui_components"
    html_file = ui_dir / f"{component_id}.html"
    
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text())
    else:
        raise HTTPException(status_code=404, detail="UI component not found")
```

## Benefits of This Approach

✅ **No React/Vue Required** - Pure HTML/CSS/JS  
✅ **Works with MCP Jam** - UI components appear in MCP Jam's UI panel  
✅ **Works with Claude Desktop** - Native MCP UI support  
✅ **Backward Compatible** - Your existing tools still work  
✅ **Progressive Enhancement** - Tools work with or without UI  

## Next Steps

1. Create UI components for your most-used tools:
   - `patient-query.html` - Patient search
   - `study-viewer.html` - Study details viewer
   - `dicom-move.html` - DICOM transfer interface
   - `report-viewer.html` - PDF report viewer

2. Enhance your FastAPI web UI to embed these components

3. Test in MCP Jam to see UI components in action

## Resources

- [MCP UI Components Spec](https://modelcontextprotocol.io/docs/extensions/ui-components)
- [FastMCP Resources](https://github.com/modelcontextprotocol/python-sdk/tree/main/src/mcp/server/fastmcp/resources)
- Your existing `resources.py` module for reference
