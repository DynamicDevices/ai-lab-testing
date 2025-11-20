"""
Foundries.io VPN Management Tools for MCP Server

Provides tools for managing Foundries VPN connections and devices.
Foundries VPN uses WireGuard but with a server-based architecture where
devices connect to a centralized VPN server managed by FoundriesFactory.

This module re-exports functions from specialized sub-modules for backward compatibility.
The actual implementations are in:
- foundries_vpn_helpers: Helper functions
- foundries_vpn_core: Core connection/status functions
- foundries_vpn_server: Server operations
- foundries_vpn_client: Client configuration
- foundries_vpn_peer: Peer registration
- foundries_vpn_validation: Validation functions

Copyright (C) 2025 Dynamic Devices Ltd
License: GPL-3.0-or-later
"""

from typing import Any, Dict, Optional

from lab_testing.utils.foundries_vpn_cache import (
    cache_vpn_ip,
    get_all_cached_ips,
    get_vpn_ip,
    remove_vpn_ip,
)
from lab_testing.utils.logger import get_logger

# Import all functions from sub-modules for backward compatibility
from lab_testing.tools.foundries_vpn_client import (
    check_foundries_vpn_client_config,
    generate_foundries_vpn_client_config_template,
    setup_foundries_vpn,
)
from lab_testing.tools.foundries_vpn_core import (
    connect_foundries_vpn,
    foundries_vpn_status,
    verify_foundries_vpn_connection,
)
from lab_testing.tools.foundries_vpn_peer import (
    check_client_peer_registered,
    register_foundries_vpn_client,
)
from lab_testing.tools.foundries_vpn_server import (
    disable_foundries_vpn_device,
    enable_foundries_device_to_device,
    enable_foundries_vpn_device,
    get_foundries_vpn_server_config,
)
from lab_testing.tools.foundries_vpn_validation import (
    validate_foundries_device_connectivity,
)

logger = get_logger()


def manage_foundries_vpn_ip_cache(
    action: str = "get",
    device_name: Optional[str] = None,
    vpn_ip: Optional[str] = None,
    refresh_from_server: bool = False,
    server_host: Optional[str] = None,
    server_port: int = 5025,
    server_user: str = "root",
    server_password: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Manage Foundries VPN IP address cache.

    This tool allows you to query, update, and refresh the cache of Foundries device VPN IP addresses.
    The cache is populated from the WireGuard server's /etc/hosts file or fioctl.

    Args:
        action: Action to perform - "get" (get IP for device), "list" (list all cached IPs),
                "set" (manually set IP), "remove" (remove entry), "refresh" (refresh from server)
        device_name: Foundries device name (required for get/set/remove actions)
        vpn_ip: VPN IP address (required for set action)
        refresh_from_server: If True, refresh cache from WireGuard server /etc/hosts (for refresh action)
        server_host: WireGuard server hostname/IP (default: from config or "proxmox.dynamicdevices.co.uk")
        server_port: SSH port on WireGuard server (default: 5025)
        server_user: SSH user for WireGuard server (default: "root")
        server_password: SSH password for WireGuard server (if not using SSH keys)

    Returns:
        Dictionary with operation results
    """
    import subprocess

    from lab_testing.tools.foundries_vpn_helpers import (
        _check_fioctl_configured,
        _check_fioctl_installed,
        _get_fioctl_path,
    )

    try:
        if action == "get":
            if not device_name:
                return {
                    "success": False,
                    "error": "device_name is required for 'get' action",
                }

            cached_ip = get_vpn_ip(device_name)
            if cached_ip:
                return {
                    "success": True,
                    "device_name": device_name,
                    "vpn_ip": cached_ip,
                    "cached": True,
                }
            return {
                "success": False,
                "device_name": device_name,
                "error": "VPN IP not found in cache",
                "suggestions": [
                    "Refresh cache from server: manage_foundries_vpn_ip_cache(action='refresh')",
                    "Manually set IP: manage_foundries_vpn_ip_cache(action='set', device_name='...', vpn_ip='...')",
                    "List all cached IPs: manage_foundries_vpn_ip_cache(action='list')",
                ],
            }

        if action == "list":
            cached_ips = get_all_cached_ips()
            devices = []
            for dev_name, entry in cached_ips.items():
                devices.append(
                    {
                        "device_name": dev_name,
                        "vpn_ip": entry.get("vpn_ip"),
                        "source": entry.get("source", "unknown"),
                        "cached_at": entry.get("cached_at"),
                    }
                )

            return {
                "success": True,
                "count": len(devices),
                "devices": devices,
            }

        if action == "set":
            if not device_name or not vpn_ip:
                return {
                    "success": False,
                    "error": "device_name and vpn_ip are required for 'set' action",
                }

            cache_vpn_ip(device_name, vpn_ip, source="manual")
            return {
                "success": True,
                "device_name": device_name,
                "vpn_ip": vpn_ip,
                "message": f"Cached VPN IP for {device_name}: {vpn_ip}",
            }

        if action == "remove":
            if not device_name:
                return {
                    "success": False,
                    "error": "device_name is required for 'remove' action",
                }

            removed = remove_vpn_ip(device_name)
            if removed:
                return {
                    "success": True,
                    "device_name": device_name,
                    "message": f"Removed VPN IP cache entry for {device_name}",
                }
            return {
                "success": False,
                "device_name": device_name,
                "error": "Device not found in cache",
            }

        if action == "refresh":
            # Use fioctl to get VPN IPs from device configurations
            # This is more reliable than reading /etc/hosts from WireGuard server

            # Check if fioctl is installed and configured
            fioctl_installed, fioctl_error = _check_fioctl_installed()
            if not fioctl_installed:
                return {
                    "success": False,
                    "error": fioctl_error,
                    "suggestions": [
                        "Install fioctl CLI tool: https://github.com/foundriesio/fioctl",
                        "Or use refresh_from_server=true to refresh from WireGuard server /etc/hosts",
                    ],
                }

            fioctl_configured, config_error = _check_fioctl_configured()
            if not fioctl_configured:
                return {
                    "success": False,
                    "error": config_error,
                    "suggestions": [
                        "Run 'fioctl login' to configure FoundriesFactory credentials",
                        "Or use refresh_from_server=true to refresh from WireGuard server /etc/hosts",
                    ],
                }

            # Get fioctl path
            fioctl_path = _get_fioctl_path()
            if not fioctl_path:
                return {
                    "success": False,
                    "error": "fioctl not found",
                    "suggestions": [
                        "Install fioctl CLI tool: https://github.com/foundriesio/fioctl",
                    ],
                }

            # First, list all devices
            list_cmd = [fioctl_path, "devices", "list"]
            list_result = subprocess.run(
                list_cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if list_result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Failed to list devices: {list_result.stderr}",
                    "suggestions": [
                        "Check fioctl is configured correctly: 'fioctl factories list'",
                    ],
                }

            # Parse device names from fioctl output
            devices = []
            for line in list_result.stdout.strip().split("\n"):
                line = line.strip()
                if not line or line.startswith("NAME") or line.startswith("----"):
                    continue
                # Extract device name (first column)
                parts = [p.strip() for p in line.split() if p.strip()]
                if parts:
                    device_name_parsed = parts[0]
                    # Only process Foundries device names
                    if "imx8mm" in device_name_parsed or "jaguar" in device_name_parsed:
                        devices.append(device_name_parsed)

            # Get VPN IP for each device from fioctl config
            cached_count = 0
            errors = []

            for device_name_parsed in devices:
                try:
                    # Get device wireguard config
                    config_cmd = [fioctl_path, "devices", "config", device_name_parsed, "wireguard"]
                    config_result = subprocess.run(
                        config_cmd,
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                    if config_result.returncode == 0:
                        # Parse output for address= line
                        # Format: "address=10.42.42.4" or similar
                        for line in config_result.stdout.split("\n"):
                            line = line.strip()
                            if line.startswith("address="):
                                ip_addr = line.split("=", 1)[1].strip()
                                if ip_addr and ip_addr != "(none)":
                                    cache_vpn_ip(device_name_parsed, ip_addr, source="fioctl")
                                    cached_count += 1
                                    logger.debug(f"Cached VPN IP for {device_name_parsed}: {ip_addr}")
                                    break
                    else:
                        # Device might not have VPN enabled, skip silently
                        logger.debug(
                            f"Device {device_name_parsed} has no WireGuard config (may not be enabled)"
                        )
                except Exception as e:
                    errors.append(f"Failed to get VPN IP for {device_name_parsed}: {e!s}")

            return {
                "success": True,
                "cached_count": cached_count,
                "source": "fioctl",
                "devices_checked": len(devices),
                "message": f"Refreshed VPN IP cache from fioctl: {cached_count} devices cached",
                "errors": errors if errors else None,
            }

        return {
            "success": False,
            "error": f"Unknown action: {action}",
            "valid_actions": ["get", "list", "set", "remove", "refresh"],
        }

    except Exception as e:
        logger.error(f"Failed to manage VPN IP cache: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Operation failed: {e!s}",
            "suggestions": [
                "Check action parameter is valid",
                "Verify required parameters are provided",
            ],
        }
