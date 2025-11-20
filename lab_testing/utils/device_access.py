"""
Unified Device Access Helper

Provides a unified interface for accessing both Foundries devices (via VPN IP)
and local config devices. Automatically detects device type and uses appropriate
access method.

Copyright (C) 2025 Dynamic Devices Ltd
License: GPL-3.0-or-later
"""

import subprocess
from typing import Any, Dict, Optional

from lab_testing.config import get_lab_devices_config
from lab_testing.tools.device_manager import load_device_config, resolve_device_identifier
from lab_testing.utils.credentials import get_ssh_command
from lab_testing.utils.foundries_vpn_cache import get_vpn_ip
from lab_testing.utils.logger import get_logger

logger = get_logger()


def get_unified_device_info(device_id_or_name: str) -> Dict[str, Any]:
    """
    Get device information for both Foundries and local devices.

    Checks:
    1. Foundries VPN IP cache (for Foundries devices)
    2. Local device config (for configured devices)

    Args:
        device_id_or_name: Device identifier or friendly name

    Returns:
        Dictionary with device info including:
        - device_id: Resolved device ID
        - ip: IP address (VPN IP for Foundries, config IP for local)
        - username: SSH username
        - ssh_port: SSH port
        - device_type: "foundries" or "local"
        - source: "vpn_cache" or "config"
    """
    # First check Foundries VPN IP cache
    vpn_ip = get_vpn_ip(device_id_or_name)
    if vpn_ip:
        logger.debug(f"Found Foundries device {device_id_or_name} in VPN cache: {vpn_ip}")
        return {
            "device_id": device_id_or_name,
            "ip": vpn_ip,
            "username": "fio",  # Default Foundries SSH user
            "ssh_port": 22,
            "device_type": "foundries",
            "source": "vpn_cache",
        }

    # Fall back to local device config
    try:
        device_id = resolve_device_identifier(device_id_or_name)
        if device_id:
            config = load_device_config()
            devices = config.get("devices", {})
            if device_id in devices:
                device = devices[device_id]
                ip = device.get("ip")
                if ip:
                    logger.debug(f"Found local device {device_id} in config: {ip}")
                    return {
                        "device_id": device_id,
                        "ip": ip,
                        "username": device.get("ssh_user", "root"),
                        "ssh_port": device.get("ports", {}).get("ssh", 22),
                        "device_type": "local",
                        "source": "config",
                    }
    except Exception as e:
        logger.debug(f"Error checking local config for {device_id_or_name}: {e}")

    # Not found in either source
    return {
        "error": f"Device '{device_id_or_name}' not found in VPN cache or local config",
    }


def ssh_to_unified_device(
    device_id_or_name: str, command: str, username: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute SSH command on device (Foundries or local).

    Automatically detects device type and uses appropriate access method.

    Args:
        device_id_or_name: Device identifier or friendly name
        command: Command to execute
        username: Optional SSH username (overrides default)

    Returns:
        Dictionary with command results (success, stdout, stderr)
    """
    device_info = get_unified_device_info(device_id_or_name)
    if "error" in device_info:
        return {"success": False, "error": device_info["error"]}

    ip = device_info["ip"]
    ssh_port = device_info["ssh_port"]
    default_username = device_info["username"]
    device_type = device_info["device_type"]

    # Use provided username or device default
    ssh_username = username if username else default_username

    logger.debug(
        f"Executing SSH command on {device_type} device {device_id_or_name} ({ip}): {command}"
    )

    # Build SSH command
    ssh_cmd = get_ssh_command(ip, ssh_username, command, device_id_or_name, use_password=False)

    # Add port if not default
    if ssh_port != 22:
        # Insert port option before username@ip
        username_ip = f"{ssh_username}@{ip}"
        if username_ip in ssh_cmd:
            port_idx = ssh_cmd.index(username_ip)
            ssh_cmd.insert(port_idx, "-p")
            ssh_cmd.insert(port_idx + 1, str(ssh_port))

    # Execute command
    try:
        result = subprocess.run(
            ssh_cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "device_id": device_info["device_id"],
            "device_type": device_type,
            "ip": ip,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "SSH command timed out after 60 seconds",
            "device_id": device_info["device_id"],
            "device_type": device_type,
            "ip": ip,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"SSH command failed: {e!s}",
            "device_id": device_info["device_id"],
            "device_type": device_type,
            "ip": ip,
        }
