#!/usr/bin/env python3
"""
Script to refactor foundries_vpn.py into smaller modules.

This script extracts functions into logical modules while preserving
all imports and dependencies.
"""

import re
from pathlib import Path

# Function groupings
GROUPS = {
    "foundries_vpn_helpers": [
        "_check_fioctl_installed",
        "_get_fioctl_path",
        "_check_fioctl_configured",
    ],
    "foundries_vpn_core": [
        "foundries_vpn_status",
        "connect_foundries_vpn",
        "verify_foundries_vpn_connection",
    ],
    "foundries_vpn_server": [
        "get_foundries_vpn_server_config",
        "enable_foundries_vpn_device",
        "disable_foundries_vpn_device",
        "enable_foundries_device_to_device",
    ],
    "foundries_vpn_client": [
        "check_foundries_vpn_client_config",
        "generate_foundries_vpn_client_config_template",
        "setup_foundries_vpn",
    ],
    "foundries_vpn_peer": [
        "check_client_peer_registered",
        "register_foundries_vpn_client",
    ],
    "foundries_vpn_validation": [
        "validate_foundries_device_connectivity",
    ],
}

# Common header (imports)
COMMON_HEADER = '''"""
Foundries.io VPN Management Tools for MCP Server

Provides tools for managing Foundries VPN connections and devices.
Foundries VPN uses WireGuard but with a server-based architecture where
devices connect to a centralized VPN server managed by FoundriesFactory.

Copyright (C) 2025 Dynamic Devices Ltd
License: GPL-3.0-or-later
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from lab_testing.config import get_foundries_vpn_config
from lab_testing.utils.foundries_vpn_cache import (
    cache_vpn_ip,
    get_all_cached_ips,
    get_vpn_ip,
    remove_vpn_ip,
)
from lab_testing.utils.logger import get_logger

logger = get_logger()
'''

# Additional imports per module
MODULE_IMPORTS = {
    "foundries_vpn_helpers": """import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple
""",
    "foundries_vpn_core": """from lab_testing.tools.foundries_vpn_helpers import (
    _check_fioctl_configured,
    _check_fioctl_installed,
)
""",
    "foundries_vpn_server": """from lab_testing.tools.foundries_vpn_helpers import (
    _check_fioctl_configured,
    _check_fioctl_installed,
    _get_fioctl_path,
)
""",
    "foundries_vpn_client": """from lab_testing.tools.foundries_vpn_helpers import (
    _check_fioctl_configured,
    _check_fioctl_installed,
    _get_fioctl_path,
)
from lab_testing.tools.foundries_vpn_server import get_foundries_vpn_server_config
""",
    "foundries_vpn_peer": """from lab_testing.tools.foundries_vpn_helpers import (
    _check_fioctl_configured,
    _check_fioctl_installed,
    _get_fioctl_path,
)
from lab_testing.config import get_foundries_vpn_config
from lab_testing.tools.foundries_vpn_core import foundries_vpn_status
""",
    "foundries_vpn_validation": """import subprocess
from typing import Any, Dict, Optional

from lab_testing.tools.foundries_vpn_core import (
    connect_foundries_vpn,
    foundries_vpn_status,
    verify_foundries_vpn_connection,
)
from lab_testing.tools.foundries_vpn_server import get_foundries_vpn_server_config
from lab_testing.tools.foundries_devices import list_foundries_devices
from lab_testing.utils.logger import get_logger

logger = get_logger()
""",
}


def extract_function(content: str, func_name: str) -> str:
    """Extract a function from content."""
    # Find function start
    pattern = rf"^def {re.escape(func_name)}\("
    lines = content.split("\n")

    start_idx = None
    for i, line in enumerate(lines):
        if re.match(pattern, line):
            start_idx = i
            break

    if start_idx is None:
        return None

    # Find function end (next def or end of file)
    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        if re.match(r"^def ", lines[i]):
            end_idx = i
            break

    return "\n".join(lines[start_idx:end_idx])


def main():
    """Main refactoring function."""
    base_path = Path("lab_testing/tools")
    source_file = base_path / "foundries_vpn.py"

    with open(source_file) as f:
        content = f.read()

    # Extract functions
    functions = {}
    for func_name in sum(GROUPS.values(), []):
        func_code = extract_function(content, func_name)
        if func_code:
            functions[func_name] = func_code
        else:
            print(f"Warning: Function {func_name} not found")

    # Create modules
    for module_name, func_names in GROUPS.items():
        module_path = base_path / f"{module_name}.py"

        # Build module content
        module_content = []

        # Add header
        if module_name == "foundries_vpn_helpers":
            # Helpers has its own simpler header
            module_content.append(
                '''"""
Foundries VPN Helper Functions

Shared helper functions for Foundries VPN operations.

Copyright (C) 2025 Dynamic Devices Ltd
License: GPL-3.0-or-later
"""

import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple
'''
            )
        else:
            module_content.append(COMMON_HEADER)
            if module_name in MODULE_IMPORTS:
                module_content.append(MODULE_IMPORTS[module_name])

        module_content.append("")

        # Add functions
        for func_name in func_names:
            if func_name in functions:
                module_content.append(functions[func_name])
                module_content.append("")

        # Write module
        with open(module_path, "w") as f:
            f.write("\n".join(module_content))

        print(f"Created {module_path} with {len(func_names)} functions")

    print("\nRefactoring complete!")
    print("\nNext steps:")
    print("1. Update foundries_vpn.py to re-export all functions")
    print("2. Update imports in tool_handlers.py")
    print("3. Test that everything works")


if __name__ == "__main__":
    main()
