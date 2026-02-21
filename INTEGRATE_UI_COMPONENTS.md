# Quick Integration Guide: Adding UI Components to dicom-mcp

## What You Get

✅ **No React/Vue Required** - Pure HTML/CSS/JavaScript  
✅ **Works in MCP Jam** - UI components appear automatically  
✅ **Works in Claude Desktop** - Native MCP UI support  
✅ **Backward Compatible** - Your existing tools still work  

## Step 1: Files Already Created

I've created:
- ✅ `src/dicom_mcp/ui_components/patient-query.html` - Sample UI component
- ✅ `src/dicom_mcp/ui_helper.py` - Helper functions for registration
- ✅ Updated `resources/manifest.yaml` - Added UI component entry

## Step 2: Integrate into server.py

Add this import at the top of `src/dicom_mcp/server.py`:

```python
from .ui_helper import register_ui_components_from_manifest
```

Then, in the `create_dicom_mcp_server` function, after your existing resource registration code (around line 280-330), add:

```python
# Register UI components from manifest
try:
    ui_count = register_ui_components_from_manifest(
        resource_manager=resource_manager,
        config_path=config_path_obj,
        manifest_resources={res.id: res.to_dict() for res in resource_catalog.values()}
    )
    if ui_count > 0:
        logger.info(f"Registered {ui_count} UI component(s)")
except Exception as e:
    logger.warning(f"Could not register UI components: {e}")
```

## Step 3: Test in MCP Jam

1. Start your MCP server:
   ```bash
   python -m dicom_mcp configuration.yaml --transport stdio
   ```

2. In MCP Jam:
   - Go to **Resources** tab
   - You should see "Patient Query UI" listed
   - Click on it to view the HTML component

3. In **Playground** tab:
   - Ask: "Show me the patient query UI"
   - Or call the `query_patients` tool - MCP Jam may automatically show the UI if configured

## Step 4: Enhance Your FastAPI Web UI

Your existing `web_ui.py` can serve these components! Add this route:

```python
@app.get("/ui/{component_id}")
async def serve_ui_component(component_id: str):
    """Serve MCP UI components via FastAPI."""
    from pathlib import Path
    ui_dir = Path(__file__).parent / "ui_components"
    html_file = ui_dir / f"{component_id}.html"
    
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text())
    else:
        raise HTTPException(status_code=404, detail="UI component not found")
```

Then embed in your web UI:
```html
<iframe src="/ui/patient-query" style="width: 100%; height: 600px; border: none;"></iframe>
```

## Step 5: Create More UI Components

Copy the pattern from `patient-query.html` to create:
- `study-viewer.html` - Display study details
- `dicom-move.html` - DICOM transfer interface  
- `report-viewer.html` - PDF report viewer
- `fhir-search.html` - FHIR resource search

Add each to `manifest.yaml`:
```yaml
  - id: "study-viewer-ui"
    name: "Study Viewer UI"
    description: "Interactive UI for viewing DICOM studies"
    filename: "../src/dicom_mcp/ui_components/study-viewer.html"
    media_type: "application/vnd.mcp.ui"
    tags: ["ui", "dicom", "study"]
```

## How It Works

1. **HTML Files** - Your UI components are plain HTML files
2. **MCP Resources** - Registered with MIME type `application/vnd.mcp.ui`
3. **Tool Integration** - Tools can reference UI via `_meta.ui.resourceUri` (when FastMCP supports it)
4. **MCP Clients** - MCP Jam/Claude Desktop automatically render UI components

## Next Steps

1. ✅ Test the patient query UI in MCP Jam
2. Create UI components for your most-used tools
3. Enhance your FastAPI web UI to embed components
4. Consider adding MCP SDK JavaScript to components for full interactivity

## Resources

- See `MCP_UI_COMPONENTS_GUIDE.md` for detailed documentation
- Check `src/dicom_mcp/ui_helper.py` for helper functions
- Look at `patient-query.html` as a template for new components
