"""
Development auto-reload utility for MCP server.

This module provides auto-reload functionality during development by:
1. Watching for file changes in the lab_testing package
2. Reloading modules when they change
3. Maintaining a cache of module modification times

Usage:
    Set environment variable: MCP_DEV_MODE=1
    Or use: python -m lab_testing.server.dev_reload
"""

import importlib
import os
import sys
import time
from pathlib import Path
from typing import Dict, Optional

# Track module modification times
_module_mtimes: Dict[str, float] = {}


def _get_module_file(module_name: str) -> Optional[Path]:
    """Get the file path for a module"""
    try:
        module = sys.modules.get(module_name)
        if module and hasattr(module, "__file__") and module.__file__:
            return Path(module.__file__)
    except Exception:
        pass
    return None


def _should_reload_module(module_name: str) -> bool:
    """Check if a module should be reloaded based on file modification time"""
    module_file = _get_module_file(module_name)
    if not module_file or not module_file.exists():
        return False
    
    current_mtime = module_file.stat().st_mtime
    cached_mtime = _module_mtimes.get(module_name)
    
    if cached_mtime is None or current_mtime > cached_mtime:
        _module_mtimes[module_name] = current_mtime
        return cached_mtime is not None  # Only reload if we've seen it before
    
    return False


def reload_if_changed(module_name: str) -> bool:
    """
    Reload a module if its file has changed.
    
    Args:
        module_name: Full module name (e.g., 'lab_testing.server.tool_handlers')
    
    Returns:
        True if module was reloaded, False otherwise
    """
    if not _should_reload_module(module_name):
        return False
    
    try:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
            return True
    except Exception as e:
        # Log but don't fail - reload errors shouldn't crash the server
        print(f"Warning: Failed to reload {module_name}: {e}", file=sys.stderr)
    
    return False


def reload_lab_testing_modules():
    """Reload all lab_testing modules that have changed"""
    modules_to_check = [
        "lab_testing.server.tool_handlers",
        "lab_testing.server.tool_definitions",
        "lab_testing.tools.device_manager",
        "lab_testing.tools.network_mapper",
        "lab_testing.tools.ota_manager",
        "lab_testing.tools.vpn_manager",
        "lab_testing.tools.tasmota_control",
        "lab_testing.tools.power_monitor",
        "lab_testing.tools.batch_operations_async",
        "lab_testing.tools.device_verification",
        "lab_testing.resources.device_inventory",
        "lab_testing.resources.network_status",
        "lab_testing.resources.help",
        "lab_testing.resources.health",
        "lab_testing.config",
    ]
    
    reloaded = []
    for module_name in modules_to_check:
        if reload_if_changed(module_name):
            reloaded.append(module_name)
    
    return reloaded


def is_dev_mode() -> bool:
    """Check if development mode is enabled"""
    return os.getenv("MCP_DEV_MODE", "").lower() in ("1", "true", "yes")


def setup_auto_reload():
    """Set up auto-reload for development mode"""
    if not is_dev_mode():
        return
    
    # Initialize mtimes for all modules
    reload_lab_testing_modules()
    
    print("Development mode enabled: Auto-reload active", file=sys.stderr)








