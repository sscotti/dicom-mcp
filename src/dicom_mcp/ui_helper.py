"""
Helper functions for registering MCP UI components.
"""

from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger("dicom_mcp")


def register_ui_component(
    resource_manager,
    component_id: str,
    html_path: Path,
    name: str,
    description: str = ""
) -> bool:
    """
    Register an HTML UI component as an MCP resource.
    
    Args:
        resource_manager: FastMCP ResourceManager instance
        component_id: Unique identifier for the component (e.g., "patient-query")
        html_path: Path to the HTML file
        name: Display name for the component
        description: Description of what the component does
    
    Returns:
        True if registration succeeded, False otherwise
    """
    try:
        from pydantic import AnyUrl
        
        if not html_path.exists():
            logger.warning(f"UI component file not found: {html_path}")
            return False
        
        content = html_path.read_text(encoding="utf-8")
        uri = AnyUrl(f"ui://dicom-mcp/{component_id}")
        
        # Try to import StaticResource from FastMCP
        try:
            from mcp.server.fastmcp.resources.static import StaticResource
            
            resource = StaticResource(
                uri=uri,
                name=name,
                description=description,
                mime_type="application/vnd.mcp.ui",  # Special MIME type for UI components
                text=content
            )
            
            resource_manager.add_resource(resource)
            logger.info(f"Registered UI component: {component_id} ({name})")
            return True
            
        except ImportError:
            # Fallback: Try to use the base Resource class
            try:
                from mcp.server.fastmcp.resources.base import Resource
                
                class UIComponentResource(Resource):
                    def __init__(self, uri, name, description, content):
                        super().__init__(uri=uri, name=name, description=description)
                        self._content = content
                        self._mime_type = "application/vnd.mcp.ui"
                    
                    async def read(self, context=None):
                        return self._content
                
                resource = UIComponentResource(
                    uri=uri,
                    name=name,
                    description=description,
                    content=content
                )
                
                resource_manager.add_resource(resource)
                logger.info(f"Registered UI component (fallback): {component_id} ({name})")
                return True
                
            except Exception as e:
                logger.warning(f"Failed to register UI component {component_id}: {e}")
                return False
                
    except Exception as e:
        logger.warning(f"Error registering UI component {component_id}: {e}")
        return False


def register_ui_components_from_manifest(
    resource_manager,
    config_path: Path,
    manifest_resources: Dict
) -> int:
    """
    Register UI components from manifest resources.
    
    Args:
        resource_manager: FastMCP ResourceManager instance
        config_path: Path to configuration file (used to resolve relative paths)
        manifest_resources: Dictionary of resources from manifest.yaml
    
    Returns:
        Number of UI components successfully registered
    """
    registered_count = 0
    resources_dir = config_path.parent / "resources"
    ui_components_dir = config_path.parent / "src" / "dicom_mcp" / "ui_components"
    
    for resource_id, resource_data in manifest_resources.items():
        # Check if it's a UI component (has application/vnd.mcp.ui MIME type)
        if resource_data.get("media_type") == "application/vnd.mcp.ui":
            filename = resource_data.get("filename", "")
            
            # Resolve path (could be relative to resources/ or ui_components/)
            if filename.startswith("../"):
                # Relative to resources directory
                html_path = resources_dir.parent / filename.lstrip("../")
            else:
                # Try ui_components directory first
                html_path = ui_components_dir / filename
            
            if not html_path.exists():
                logger.warning(f"UI component file not found: {html_path}")
                continue
            
            success = register_ui_component(
                resource_manager=resource_manager,
                component_id=resource_id,
                html_path=html_path,
                name=resource_data.get("name", resource_id),
                description=resource_data.get("description", "")
            )
            
            if success:
                registered_count += 1
    
    return registered_count
