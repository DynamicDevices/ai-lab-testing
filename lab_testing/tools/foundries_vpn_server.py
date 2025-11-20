"""
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

from lab_testing.tools.foundries_vpn_helpers import (
    _check_fioctl_configured,
    _check_fioctl_installed,
    _get_fioctl_path,
)


def get_foundries_vpn_server_config(factory: Optional[str] = None) -> Dict[str, Any]:
    """
    Get Foundries VPN server configuration using fioctl API.

    Returns WireGuard server endpoint, address, and public key.

    Args:
        factory: Optional factory name (defaults to configured factory)

    Returns:
        Dictionary with VPN server configuration
    """
    try:
        # Check if fioctl is installed and configured
        fioctl_installed, fioctl_error = _check_fioctl_installed()
        if not fioctl_installed:
            return {
                "success": False,
                "error": fioctl_error,
                "suggestions": [
                    "Install fioctl CLI tool: https://github.com/foundriesio/fioctl",
                ],
            }

        fioctl_configured, config_error = _check_fioctl_configured()
        if not fioctl_configured:
            return {
                "success": False,
                "error": config_error,
                "suggestions": [
                    "Run 'fioctl login' to configure FoundriesFactory credentials",
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

        # Get WireGuard server config
        cmd = [fioctl_path, "config", "wireguard"]
        if factory:
            cmd.extend(["--factory", factory])

        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            return {
                "success": False,
                "error": f"Failed to get VPN server config: {error_msg}",
                "suggestions": [
                    "Check fioctl is configured correctly: 'fioctl factories list'",
                    "Ensure you have access to the factory",
                ],
            }

        # Parse output
        config = {}
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower().replace(" ", "_")
                value = value.strip()
                config[key] = value

        enabled = config.get("enabled", "false").lower() == "true"

        return {
            "success": True,
            "enabled": enabled,
            "endpoint": config.get("endpoint", ""),
            "address": config.get("address", ""),
            "public_key": config.get("public_key", ""),
            "factory": factory or "default",
            "message": (
                "VPN server config retrieved successfully" if enabled else "VPN server is disabled"
            ),
            "next_steps": (
                ["Enable VPN on devices: enable_foundries_vpn_device(device_name)"]
                if enabled
                else ["Enable VPN server in FoundriesFactory"]
            ),
        }

    except Exception as e:
        logger.error(f"Failed to get VPN server config: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to get VPN server config: {e!s}",
            "suggestions": [
                "Check if fioctl is installed: https://github.com/foundriesio/fioctl",
                "Check if fioctl is configured: Run 'fioctl login'",
            ],
        }


def enable_foundries_vpn_device(device_name: str, factory: Optional[str] = None) -> Dict[str, Any]:
    """
    Enable WireGuard VPN on a Foundries device.

    Uses fioctl to enable WireGuard configuration on a device.
    The device will connect to the Foundries VPN server after OTA update (up to 5 minutes).

    Args:
        device_name: Name of the device to enable VPN on
        factory: Optional factory name. If not provided, uses default factory from fioctl config.

    Returns:
        Dictionary with operation results
    """
    try:
        # Check if fioctl is installed and configured
        fioctl_installed, fioctl_error = _check_fioctl_installed()
        if not fioctl_installed:
            return {
                "success": False,
                "error": fioctl_error,
                "suggestions": [
                    "Install fioctl CLI tool: https://github.com/foundriesio/fioctl",
                ],
            }

        fioctl_configured, config_error = _check_fioctl_configured()
        if not fioctl_configured:
            return {
                "success": False,
                "error": config_error,
                "suggestions": [
                    "Run 'fioctl login' to configure FoundriesFactory credentials",
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

        # Build fioctl command
        cmd = [fioctl_path, "devices", "config", "wireguard", device_name, "enable"]
        if factory:
            cmd.extend(["--factory", factory])

        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            return {
                "success": True,
                "device_name": device_name,
                "factory": factory or "default",
                "message": f"WireGuard VPN enabled on device '{device_name}'. Configuration will be applied via OTA update (up to 5 minutes).",
                "next_steps": [
                    "Wait for OTA update to complete (up to 5 minutes)",
                    "Check device status: list_foundries_devices()",
                    "Connect to Foundries VPN: connect_foundries_vpn()",
                ],
            }

        error_msg = result.stderr.strip() if result.stderr else "Unknown error"
        return {
            "success": False,
            "error": f"Failed to enable WireGuard VPN on device '{device_name}': {error_msg}",
            "suggestions": [
                "Verify device name is correct: list_foundries_devices()",
                "Check device exists in factory",
                "Ensure you have permissions to configure devices",
            ],
        }

    except Exception as e:
        logger.error(f"Failed to enable Foundries VPN on device: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to enable Foundries VPN on device: {e!s}",
            "suggestions": [
                "Check if fioctl is installed: https://github.com/foundriesio/fioctl",
                "Check if fioctl is configured: Run 'fioctl login'",
                "Verify device name is correct: list_foundries_devices()",
                "Check device exists in factory",
            ],
        }


def disable_foundries_vpn_device(device_name: str, factory: Optional[str] = None) -> Dict[str, Any]:
    """
    Disable WireGuard VPN on a Foundries device.

    Uses fioctl to disable WireGuard configuration on a device.
    The device will disconnect from the Foundries VPN server after OTA update (up to 5 minutes).

    Args:
        device_name: Name of the device to disable VPN on
        factory: Optional factory name. If not provided, uses default factory from fioctl config.

    Returns:
        Dictionary with operation results
    """
    try:
        # Check if fioctl is installed and configured
        fioctl_installed, fioctl_error = _check_fioctl_installed()
        if not fioctl_installed:
            return {
                "success": False,
                "error": fioctl_error,
                "suggestions": [
                    "Install fioctl CLI tool: https://github.com/foundriesio/fioctl",
                ],
            }

        fioctl_configured, config_error = _check_fioctl_configured()
        if not fioctl_configured:
            return {
                "success": False,
                "error": config_error,
                "suggestions": [
                    "Run 'fioctl login' to configure FoundriesFactory credentials",
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

        # Build fioctl command
        cmd = [fioctl_path, "devices", "config", "wireguard", device_name, "disable"]
        if factory:
            cmd.extend(["--factory", factory])

        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            return {
                "success": True,
                "device_name": device_name,
                "factory": factory or "default",
                "message": f"WireGuard VPN disabled on device '{device_name}'. Configuration will be applied via OTA update (up to 5 minutes).",
                "next_steps": [
                    "Wait for OTA update to complete (up to 5 minutes)",
                    "Check device status: list_foundries_devices()",
                ],
            }

        error_msg = result.stderr.strip() if result.stderr else "Unknown error"
        return {
            "success": False,
            "error": f"Failed to disable WireGuard VPN on device '{device_name}': {error_msg}",
            "suggestions": [
                "Verify device name is correct: list_foundries_devices()",
                "Check device exists in factory",
                "Ensure you have permissions to configure devices",
            ],
        }

    except Exception as e:
        logger.error(f"Failed to disable Foundries VPN on device: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to disable Foundries VPN on device: {e!s}",
            "suggestions": [
                "Check if fioctl is installed: https://github.com/foundriesio/fioctl",
                "Check if fioctl is configured: Run 'fioctl login'",
                "Verify device name is correct: list_foundries_devices()",
                "Check device exists in factory",
            ],
        }


def enable_foundries_device_to_device(
    device_name: str,
    device_ip: Optional[str] = None,
    vpn_subnet: str = "10.42.42.0/24",
    server_host: Optional[str] = None,
    server_port: int = 5025,
    server_user: str = "root",
    server_password: Optional[str] = None,
    device_user: str = "fio",
    device_password: str = "fio",
) -> Dict[str, Any]:
    """
    Enable device-to-device communication for a Foundries device.

    This tool SSHes into the WireGuard server, then from there to the target device,
    and updates the device's NetworkManager WireGuard configuration to allow the full
    VPN subnet instead of just the server IP. This enables device-to-device communication
    for debugging/development purposes.

    By default, Foundries devices use restrictive AllowedIPs (server IP only) for security.
    This tool temporarily overrides that for development/debugging.

    Args:
        device_name: Name of the Foundries device (e.g., "imx8mm-jaguar-sentai-2d0e0a09dab86563")
        device_ip: VPN IP address of the device (e.g., "10.42.42.2"). If not provided,
                   will try to get from device list.
        vpn_subnet: VPN subnet to allow (default: "10.42.42.0/24")
        server_host: WireGuard server hostname/IP (default: from config or "144.76.167.54")
        server_port: SSH port on WireGuard server (default: 5025)
        server_user: SSH user for WireGuard server (default: "root")
        server_password: SSH password for WireGuard server (if not using SSH keys)
        device_user: SSH user on device (default: "fio")
        device_password: SSH password on device (default: "fio")

    Returns:
        Dictionary with operation results
    """
    try:
        steps_completed = []
        steps_failed = []

        # Get device IP if not provided
        if not device_ip:
            from lab_testing.tools.foundries_devices import list_foundries_devices

            devices = list_foundries_devices()
            if not devices.get("success"):
                return {
                    "success": False,
                    "error": "Failed to list devices to find device IP",
                    "details": devices,
                }

            device_found = False
            for device in devices.get("devices", []):
                if device.get("name") == device_name:
                    device_ip = device.get("vpn_ip")
                    device_found = True
                    break

            if not device_found:
                return {
                    "success": False,
                    "error": f"Device '{device_name}' not found in device list",
                    "suggestions": [
                        "Check device name spelling",
                        "Ensure device has VPN enabled",
                        "List devices: list_foundries_devices()",
                    ],
                }

        if not device_ip:
            return {
                "success": False,
                "error": "Device IP not found and not provided",
            }

        # Get server host from config if not provided
        if not server_host:
            config_path = get_foundries_vpn_config()
            if config_path and config_path.exists():
                # Try to read config file to get server endpoint
                try:
                    config_content = config_path.read_text()
                    for line in config_content.split("\n"):
                        if line.startswith("Endpoint =") or line.startswith("Endpoint="):
                            endpoint = line.split("=", 1)[1].strip()
                            # Extract host from endpoint (e.g., "144.76.167.54:5555" -> "144.76.167.54")
                            server_host = endpoint.split(":")[0] if ":" in endpoint else endpoint
                            break
                except Exception:
                    pass

            if not server_host:
                server_host = "144.76.167.54"  # Default

        steps_completed.append(f"Resolved device IP: {device_ip}, server: {server_host}")

        # Build SSH command to update device config
        # We SSH to the server, then from there SSH to the device using sshpass
        # Use | as sed delimiter to avoid issues with / in subnet (e.g., 10.42.42.0/24)

        # Build the command that will run on the device
        # Use double quotes for the inner command to allow variable expansion
        device_update_cmd = f'echo "{device_password}" | sudo -S sed -i "s|allowed-ips=10.42.42.1|allowed-ips={vpn_subnet}|" /etc/NetworkManager/system-connections/factory-vpn0.nmconnection && echo Config updated'
        device_reload_cmd = f'echo "{device_password}" | sudo -S nmcli connection reload factory-vpn0 && echo "{device_password}" | sudo -S nmcli connection down factory-vpn0 && sleep 1 && echo "{device_password}" | sudo -S nmcli connection up factory-vpn0 && sleep 2 && echo "{device_password}" | sudo -S wg show factory-vpn0 | grep allowed'

        # Combine device commands
        device_full_cmd = f"{device_update_cmd} && {device_reload_cmd}"

        # Build the command that runs on the server (SSH to device using sshpass)
        # Use single quotes around the device command to prevent shell expansion on server
        server_cmd = f"sshpass -p '{device_password}' ssh -o StrictHostKeyChecking=no {device_user}@{device_ip} '{device_full_cmd}'"

        # Step 3: Set server-side AllowedIPs
        # First, get device public key from server
        get_key_cmd = f"""wg show factory | grep -A 5 "{device_ip}" | grep "peer:" | awk '{{print $2}}' || wg show factory | grep -B 5 "{device_ip}" | grep "peer:" | awk '{{print $2}}'"""

        # Build full command to run on server
        if server_password:
            ssh_to_server = f"sshpass -p '{server_password}' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p {server_port} {server_user}@{server_host}"
        else:
            ssh_to_server = (
                f"ssh -o StrictHostKeyChecking=no -p {server_port} {server_user}@{server_host}"
            )

        # Execute update - use double quotes around server_cmd to allow variable expansion
        full_cmd = f'{ssh_to_server} "{server_cmd}"'

        logger.info(f"Enabling device-to-device for {device_name} ({device_ip})")
        result = subprocess.run(
            full_cmd,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Check if the command succeeded by looking for success indicators
        # The banner may cause non-zero exit codes, but if we see "Config updated" it worked
        output = result.stdout + result.stderr
        success_indicator = "Config updated" in output or "allowed" in output.lower()

        if result.returncode != 0 and not success_indicator:
            steps_failed.append("Failed to update device config")
            return {
                "success": False,
                "error": f"Failed to update device configuration: {result.stderr}",
                "steps_completed": steps_completed,
                "steps_failed": steps_failed,
                "suggestions": [
                    "⚠️ CRITICAL: Device may need device-to-device communication enabled",
                    "Check SSH access from VPN server to device (device may be unreachable)",
                    "Verify device IP is correct: list_foundries_devices()",
                    "Check device is online and VPN is enabled",
                    "If device is online but unreachable, device NetworkManager config may need update",
                    "See docs/FOUNDRIES_VPN_CLEAN_INSTALLATION.md Part 3.3 for manual steps",
                ],
            }

        # If we see success indicators, treat as success even if return code is non-zero
        if success_indicator:
            steps_completed.append("Updated device NetworkManager config")
            steps_completed.append("Reloaded NetworkManager connection")

        steps_completed.append("Updated device NetworkManager config")
        steps_completed.append("Reloaded NetworkManager connection")

        # Set server-side AllowedIPs
        # Get device public key
        key_result = subprocess.run(
            f"""{ssh_to_server} "{get_key_cmd}" """,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if key_result.returncode == 0 and key_result.stdout.strip():
            pubkey = key_result.stdout.strip()
            set_server_cmd = f"""wg set factory peer {pubkey} allowed-ips {vpn_subnet}"""

            server_result = subprocess.run(
                f"""{ssh_to_server} "{set_server_cmd}" """,
                shell=True,
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if server_result.returncode == 0:
                steps_completed.append(f"Set server-side AllowedIPs to {vpn_subnet}")
            else:
                steps_failed.append("Failed to set server-side AllowedIPs")
                logger.warning(f"Failed to set server-side AllowedIPs: {server_result.stderr}")

        return {
            "success": True,
            "device_name": device_name,
            "device_ip": device_ip,
            "vpn_subnet": vpn_subnet,
            "steps_completed": steps_completed,
            "steps_failed": steps_failed,
            "message": f"Device-to-device communication enabled for {device_name}",
            "note": "Device config updated. Server-side AllowedIPs may need to be set manually if daemon overwrites it.",
        }

    except Exception as e:
        logger.error(f"Failed to enable device-to-device: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Operation failed: {e!s}",
            "steps_completed": steps_completed if "steps_completed" in locals() else [],
            "steps_failed": steps_failed if "steps_failed" in locals() else [],
            "suggestions": [
                "Check device is online and accessible",
                "Verify SSH credentials",
                "Check WireGuard server is accessible",
            ],
        }
