"""
Core plugin management system for the Financial Terminal
"""
import os
import importlib
import logging
from typing import Dict, List, Optional, Type
from pathlib import Path


class PluginManager:
    """
    Central plugin management system
    Handles discovery, loading, and lifecycle of all plugins
    """
    
    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = Path(plugins_dir)
        self.plugins: Dict[str, Dict] = {
            'data_providers': {},
            'widgets': {},
            'analytics': {},
            'themes': {},
            'integrations': {}
        }
        self.enabled_plugins: set = set()
        self.plugin_metadata: Dict = {}
        
    def discover_plugins(self):
        """
        Auto-discover all plugins in the plugins directory
        """
        logging.info("Discovering plugins...")
        
        for plugin_type in self.plugins.keys():
            type_dir = self.plugins_dir / plugin_type
            
            if not type_dir.exists():
                logging.warning(f"Plugin directory not found: {type_dir}")
                continue
            
            # Find all Python files in the directory
            for plugin_path in type_dir.glob("*.py"):
                if plugin_path.name.startswith("__"):
                    continue
                
                plugin_name = plugin_path.stem
                try:
                    self._load_plugin(plugin_type, plugin_name)
                except Exception as e:
                    logging.error(f"Failed to load plugin {plugin_name}: {e}")
        
        logging.info(f"Discovered {sum(len(p) for p in self.plugins.values())} plugins")
    
    def _load_plugin(self, plugin_type: str, plugin_name: str):
        """
        Load a specific plugin module
        """
        module_path = f"plugins.{plugin_type}.{plugin_name}"
        
        try:
            module = importlib.import_module(module_path)
            
            # Look for concrete plugin class (not abstract base classes)
            from abc import ABC
            from plugins.base import BasePlugin, DataProviderPlugin, WidgetPlugin, AnalyticsPlugin, ThemePlugin, IntegrationPlugin
            
            # Base classes to exclude
            base_classes = {BasePlugin, DataProviderPlugin, WidgetPlugin, AnalyticsPlugin, ThemePlugin, IntegrationPlugin}
            
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BasePlugin) and 
                    attr not in base_classes and
                    not getattr(attr, '__abstractmethods__', None)):  # Skip if still has abstract methods
                    plugin_class = attr
                    break
            
            if plugin_class is None:
                logging.warning(f"No plugin class found in {module_path}")
                return
            
            # Instantiate the plugin
            plugin_instance = plugin_class()
            
            # Store plugin
            self.plugins[plugin_type][plugin_name] = plugin_instance
            self.enabled_plugins.add(f"{plugin_type}.{plugin_name}")
            
            # Store metadata - use method calls instead of attributes
            self.plugin_metadata[f"{plugin_type}.{plugin_name}"] = {
                'name': plugin_instance.get_name() if hasattr(plugin_instance, 'get_name') else plugin_name,
                'version': plugin_instance.get_version() if hasattr(plugin_instance, 'get_version') else '1.0.0',
                'description': plugin_instance.get_description() if hasattr(plugin_instance, 'get_description') else '',
                'author': plugin_instance.get_author() if hasattr(plugin_instance, 'get_author') else 'Unknown',
                'type': plugin_type
            }
            
            logging.info(f"Loaded plugin: {plugin_type}.{plugin_name}")
            
        except Exception as e:
            logging.error(f"Error loading plugin {module_path}: {e}")
            raise
    
    def get_plugin(self, plugin_type: str, plugin_name: str):
        """
        Get a specific plugin instance
        """
        plugin_key = f"{plugin_type}.{plugin_name}"
        
        if plugin_key not in self.enabled_plugins:
            raise ValueError(f"Plugin {plugin_key} is not enabled")
        
        return self.plugins.get(plugin_type, {}).get(plugin_name)
    
    def get_enabled_plugin(self, plugin_type: str, preferred: str = None):
        """
        Get first enabled plugin of specified type
        If preferred plugin is specified and enabled, return it
        Otherwise return first enabled plugin of that type
        
        Args:
            plugin_type: Type of plugin (data_providers, analytics, etc.)
            preferred: Preferred plugin name (optional)
            
        Returns:
            Plugin instance or None if no enabled plugin found
        """
        # Try preferred plugin first
        if preferred and preferred in self.plugins.get(plugin_type, {}):
            plugin_key = f"{plugin_type}.{preferred}"
            if plugin_key in self.enabled_plugins:
                return self.plugins[plugin_type][preferred]
        
        # Return first enabled plugin of this type
        for name, instance in self.plugins.get(plugin_type, {}).items():
            plugin_key = f"{plugin_type}.{name}"
            if plugin_key in self.enabled_plugins:
                return instance
        
        return None
    
    def list_plugins(self, plugin_type: Optional[str] = None) -> Dict:
        """
        List all available plugins, optionally filtered by type
        """
        if plugin_type:
            return {
                k: v for k, v in self.plugin_metadata.items()
                if v['type'] == plugin_type
            }
        return self.plugin_metadata
    
    def enable_plugin(self, plugin_type: str, plugin_name: str):
        """
        Enable a disabled plugin
        """
        plugin_key = f"{plugin_type}.{plugin_name}"
        
        if plugin_key in self.enabled_plugins:
            logging.warning(f"Plugin {plugin_key} is already enabled")
            return
        
        # Try to load the plugin if not already loaded
        if plugin_name not in self.plugins.get(plugin_type, {}):
            self._load_plugin(plugin_type, plugin_name)
        
        self.enabled_plugins.add(plugin_key)
        logging.info(f"Enabled plugin: {plugin_key}")
    
    def disable_plugin(self, plugin_type: str, plugin_name: str):
        """
        Disable an active plugin
        """
        plugin_key = f"{plugin_type}.{plugin_name}"
        
        if plugin_key not in self.enabled_plugins:
            logging.warning(f"Plugin {plugin_key} is not enabled")
            return
        
        self.enabled_plugins.discard(plugin_key)
        logging.info(f"Disabled plugin: {plugin_key}")
    
    def reload_plugin(self, plugin_type: str, plugin_name: str):
        """
        Hot-reload a plugin (useful for development)
        """
        self.disable_plugin(plugin_type, plugin_name)
        
        # Remove from plugins dict
        if plugin_name in self.plugins.get(plugin_type, {}):
            del self.plugins[plugin_type][plugin_name]
        
        # Remove metadata
        plugin_key = f"{plugin_type}.{plugin_name}"
        if plugin_key in self.plugin_metadata:
            del self.plugin_metadata[plugin_key]
        
        # Reload module
        module_path = f"plugins.{plugin_type}.{plugin_name}"
        if module_path in importlib.import_module.__globals__:
            importlib.reload(importlib.import_module(module_path))
        
        # Re-enable
        self.enable_plugin(plugin_type, plugin_name)
        logging.info(f"Reloaded plugin: {plugin_key}")
    
    def get_data_providers(self) -> List[str]:
        """
        Get list of all data provider plugins
        """
        return list(self.plugins['data_providers'].keys())
    
    def get_widgets(self) -> List[str]:
        """
        Get list of all widget plugins
        """
        return list(self.plugins['widgets'].keys())
    
    def call_plugin_method(self, plugin_type: str, plugin_name: str, 
                          method_name: str, *args, **kwargs):
        """
        Call a method on a specific plugin
        """
        plugin = self.get_plugin(plugin_type, plugin_name)
        
        if not hasattr(plugin, method_name):
            raise AttributeError(
                f"Plugin {plugin_type}.{plugin_name} has no method {method_name}"
            )
        
        method = getattr(plugin, method_name)
        return method(*args, **kwargs)


# Global plugin manager instance
plugin_manager = None


def init_plugin_manager(plugins_dir: str = "plugins"):
    """
    Initialize the global plugin manager
    """
    global plugin_manager
    plugin_manager = PluginManager(plugins_dir)
    plugin_manager.discover_plugins()
    return plugin_manager


def get_plugin_manager() -> PluginManager:
    """
    Get the global plugin manager instance
    """
    global plugin_manager
    if plugin_manager is None:
        raise RuntimeError("Plugin manager not initialized. Call init_plugin_manager() first.")
    return plugin_manager
