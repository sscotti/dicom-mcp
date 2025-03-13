"""
DICOM server configuration management.

Simple loader for DICOM server configurations from a YAML file.
"""

import yaml
from pathlib import Path
from typing import Dict, Optional


class ServerConfigManager:
    """Manages DICOM server configurations."""
    
    def __init__(self, config_path: str):
        """Initialize the server configuration manager.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = Path(config_path)
        self.servers = {}
        self.default_server = None
        self.current_server = None
        
        # Load configurations
        self._load_config()
        
        # Set current server to default from config
        self.current_server = self.default_server
    
    def _load_config(self) -> None:
        """Load server configurations from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file {self.config_path} not found. This file is required.")
        
        try:
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data or not isinstance(config_data, dict):
                raise ValueError(f"Invalid configuration format in {self.config_path}")
            
            # Load servers
            self.servers = config_data.get('servers', {})
            if not self.servers:
                raise ValueError(f"No servers defined in {self.config_path}")
            
            # Load default server
            self.default_server = config_data.get('current_server')
            
            # If default server is not in servers or None, set to first server
            if self.default_server not in self.servers and self.servers:
                self.default_server = next(iter(self.servers.keys()))
                
        except Exception as e:
            raise RuntimeError(f"Error loading configuration: {e}")
    
    def get_current_server(self) -> Optional[Dict]:
        """Get the currently selected server configuration.
        
        Returns:
            The current server configuration or None if not set
        """
        if not self.current_server or self.current_server not in self.servers:
            return None
        
        return self.servers[self.current_server]
    
    def set_current_server(self, server_name: str) -> bool:
        """Set the current server by name (in memory only, does not modify the config file).
        
        Args:
            server_name: Name of the server to set as current
            
        Returns:
            True if successful, False if server doesn't exist
        """
        if server_name not in self.servers:
            return False
        
        self.current_server = server_name
        return True
    
    def list_servers(self) -> Dict:
        """List all server configurations.
        
        Returns:
            Dictionary of server configurations
        """
        return self.servers