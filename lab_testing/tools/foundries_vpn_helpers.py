"""
Foundries VPN Helper Functions

Shared helper functions for Foundries VPN operations.

Copyright (C) 2025 Dynamic Devices Ltd
License: GPL-3.0-or-later
"""

import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple


def _check_fioctl_installed() -> tuple:
    """
    Check if fioctl CLI tool is installed.

    Checks both PATH and common installation locations.

    Returns:
        Tuple of (is_installed, error_message)
    """
    fioctl_path = _get_fioctl_path()
    if not fioctl_path:
        return (
            False,
            "fioctl not found in PATH or common locations. Install fioctl CLI tool: https://github.com/foundriesio/fioctl",
        )

    # Verify fioctl works by checking version (fioctl uses 'version' subcommand, not '--version')
    try:
        result = subprocess.run(
            [fioctl_path, "version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True, None
    except Exception as e:
        return False, f"fioctl found but failed to execute: {e!s}"

    return False, "fioctl found but version check failed"


def _get_fioctl_path() -> Optional[str]:
    """
    Get the path to fioctl executable.

    Returns:
        Path to fioctl, or None if not found
    """
    import shutil

    # Check PATH first
    fioctl_path = shutil.which("fioctl")
    if fioctl_path:
        return fioctl_path

    # Check common installation locations
    common_paths = [
        "/usr/local/bin/fioctl",
        "/usr/bin/fioctl",
        Path.home() / ".local/bin/fioctl",
    ]

    for path in common_paths:
        path_str = str(path) if isinstance(path, Path) else path
        if Path(path_str).exists():
            return path_str

    return None


def _check_fioctl_configured() -> tuple:
    """
    Check if fioctl is configured with Factory credentials.

    Returns:
        Tuple of (is_configured, error_message)
    """
    fioctl_path = _get_fioctl_path()
    if not fioctl_path:
        return False, "fioctl not found"

    try:
        result = subprocess.run(
            [fioctl_path, "factories", "list"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True, None
        return False, "fioctl not configured. Run 'fioctl login' to configure credentials"
    except Exception as e:
        return False, f"Failed to check fioctl configuration: {e!s}"
