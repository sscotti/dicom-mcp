"""Static resource registry for the MCP server."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass
class StaticResource:
    """Metadata for a saved resource in the repo."""

    id: str
    name: str
    description: str
    path: Optional[Path]
    media_type: str = "text/plain"
    tags: List[str] = field(default_factory=list)
    homepage: Optional[str] = None

    def to_dict(self, include_content: bool = False) -> Dict[str, object]:
        size = self.path.stat().st_size if self.path and self.path.exists() else 0
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "media_type": self.media_type,
            "tags": self.tags,
            "homepage": self.homepage,
            "relative_path": str(self.path.name) if self.path else None,
            "size_bytes": size,
            "has_local_content": bool(self.path and self.path.exists()),
        }
        if include_content and self.path and self.path.exists():
            if self.media_type.endswith("json"):
                try:
                    data["content"] = json.loads(self.path.read_text(encoding="utf-8"))
                except Exception:
                    data["content"] = self.path.read_text(encoding="utf-8")
            else:
                data["content"] = self.path.read_text(encoding="utf-8", errors="replace")
        return data


def load_resource_catalog(resources_dir: Path) -> Dict[str, StaticResource]:
    """Load resources from manifest.yaml in the given directory."""
    catalog: Dict[str, StaticResource] = {}
    manifest_path = resources_dir / "manifest.yaml"
    if not manifest_path.exists():
        return catalog

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f) or {}

    for entry in manifest.get("resources", []):
        try:
            resource_id = entry["id"]
            filename = entry.get("filename")
            path = resources_dir / filename if filename else None
            catalog[resource_id] = StaticResource(
                id=resource_id,
                name=entry.get("name", resource_id),
                description=entry.get("description", ""),
                path=path,
                media_type=entry.get("media_type", "text/plain"),
                tags=entry.get("tags", []),
                homepage=entry.get("homepage"),
            )
        except KeyError:
            continue  # Skip malformed entries silently

    return catalog

