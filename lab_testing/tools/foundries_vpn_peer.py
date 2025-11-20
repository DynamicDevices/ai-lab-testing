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

from lab_testing.config import get_foundries_vpn_config
from lab_testing.tools.foundries_vpn_helpers import (
    _check_fioctl_configured,
    _check_fioctl_installed,
    _get_fioctl_path,
)


def check_client_peer_registered(
    client_public_key: Optional[str] = None,
    server_host: Optional[str] = None,
    server_port: int = 5025,
    server_user: str = "root",
    server_password: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Check if a client peer is registered on the Foundries WireGuard server.

    This tool checks if the client's public key is configured as a peer on the server.
    It can connect via Foundries VPN (if connected) or standard VPN (hardware lab).

    Args:
        client_public_key: Client's WireGuard public key. If not provided, will try to
                          derive from local config file.
        server_host: WireGuard server hostname/IP. If not provided, will try to get
                    from Foundries VPN config or use standard VPN IP.
        server_port: SSH port on WireGuard server (default: 5025)
        server_user: SSH user for WireGuard server (default: "root")
        server_password: SSH password for WireGuard server (if not using SSH keys)

    Returns:
        Dictionary with client peer registration status
    """
    try:
        # Get client public key if not provided
        if not client_public_key:
            config_path = get_foundries_vpn_config()
            if config_path and config_path.exists():
                try:
                    config_content = config_path.read_text()
                    for line in config_content.split("\n"):
                        if "PrivateKey" in line and "=" in line:
                            privkey = line.split("=", 1)[1].strip()
                            # Derive public key
                            result = subprocess.run(
                                ["wg", "pubkey"],
                                check=False,
                                input=privkey.encode(),
                                capture_output=True,
                                text=True,
                                timeout=5,
                            )
                            if result.returncode == 0:
                                client_public_key = result.stdout.strip()
                                break
                except Exception as e:
                    logger.warning(f"Failed to derive public key from config: {e}")

        if not client_public_key:
            return {
                "success": False,
                "error": "Client public key not provided and could not be derived from config",
                "suggestions": [
                    "Provide client_public_key parameter",
                    "Ensure Foundries VPN config file exists with PrivateKey",
                    "Generate keys: wg genkey | tee privatekey | wg pubkey > publickey",
                ],
            }

        # Determine server host
        foundries_vpn_connected = False
        if not server_host:
            # Check if Foundries VPN is connected (local import to avoid circular dependency)
            from lab_testing.tools.foundries_vpn_core import foundries_vpn_status

            status = foundries_vpn_status()
            if status.get("connected"):
                foundries_vpn_connected = True
                server_host = "10.42.42.1"  # Foundries VPN server IP
            else:
                # Not connected - cannot check without VPN
                return {
                    "success": False,
                    "error": "Foundries VPN not connected. Cannot check client peer registration without VPN connection.",
                    "suggestions": [
                        "Connect to Foundries VPN first: connect_foundries_vpn()",
                        "If not registered, contact VPN admin: ajlennon@dynamicdevices.co.uk",
                    ],
                }

        # Build SSH command
        if server_password:
            ssh_cmd = f"sshpass -p '{server_password}' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p {server_port} {server_user}@{server_host}"
        else:
            ssh_cmd = (
                f"ssh -o StrictHostKeyChecking=no -p {server_port} {server_user}@{server_host}"
            )

        # Check if peer exists in runtime
        check_runtime_cmd = f"{ssh_cmd} 'wg show factory | grep -A 3 \"{client_public_key}\"'"
        result = subprocess.run(
            check_runtime_cmd,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )

        runtime_registered = result.returncode == 0 and client_public_key in result.stdout

        # Check if peer exists in config file
        check_config_cmd = f'{ssh_cmd} \'grep -A 3 "{client_public_key}" /etc/wireguard/factory.conf || grep "{client_public_key}" /etc/wireguard/factory-clients.conf\''
        result_config = subprocess.run(
            check_config_cmd,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )

        config_registered = result.returncode == 0 and client_public_key in result_config.stdout

        # Parse assigned IP if registered
        assigned_ip = None
        allowed_ips = None
        if runtime_registered:
            # Extract IP from wg show output
            for line in result.stdout.split("\n"):
                if "allowed ips:" in line.lower():
                    allowed_ips = line.split(":")[1].strip() if ":" in line else None
                    # Extract IP from allowed_ips (e.g., "10.42.42.10/32" -> "10.42.42.10")
                    if allowed_ips and "/" in allowed_ips:
                        assigned_ip = allowed_ips.split("/")[0]
                    break

        return {
            "success": True,
            "client_public_key": client_public_key,
            "registered": runtime_registered or config_registered,
            "runtime_registered": runtime_registered,
            "config_registered": config_registered,
            "assigned_ip": assigned_ip,
            "allowed_ips": allowed_ips,
            "server_host": server_host,
            "connection_method": "Foundries VPN" if foundries_vpn_connected else "Not connected",
            "next_steps": (
                [
                    "Client peer is registered. You can connect to Foundries VPN.",
                    "If not connected, use: connect_foundries_vpn()",
                ]
                if (runtime_registered or config_registered)
                else [
                    "Client peer is NOT registered on server",
                    "Register using: register_foundries_vpn_client()",
                    "Or contact VPN admin: ajlennon@dynamicdevices.co.uk",
                ]
            ),
        }
    except Exception as e:
        logger.error(f"Failed to check client peer registration: {e}")
        return {
            "success": False,
            "error": f"Failed to check client peer registration: {e!s}",
            "suggestions": [
                "Check VPN connection (Foundries or standard)",
                "Verify server host and port are correct",
                "Check SSH access to server",
            ],
        }


def register_foundries_vpn_client(
    client_public_key: str,
    assigned_ip: str,
    server_host: Optional[str] = None,
    server_port: int = 5025,
    server_user: str = "root",
    server_password: Optional[str] = None,
    use_config_file: bool = True,
) -> Dict[str, Any]:
    """
    Register a client peer on the Foundries WireGuard server.

    This tool automates client peer registration. It connects to the server via
    Foundries VPN (10.42.42.1). Requires Foundries VPN to be connected first.

    **Bootstrap Scenario:** For clean installation, the first admin needs initial
    server access (public IP or direct access) to register themselves. After the
    first admin connects, all subsequent client registrations can be done via
    Foundries VPN by the admin.

    Args:
        client_public_key: Client's WireGuard public key to register
        assigned_ip: IP address to assign to client (e.g., "10.42.42.10")
        server_host: WireGuard server hostname/IP. If not provided, will try to get
                    from Foundries VPN config or use standard VPN IP.
        server_port: SSH port on WireGuard server (default: 5025)
        server_user: SSH user for WireGuard server (default: "root")
        server_password: SSH password for WireGuard server (if not using SSH keys)
        use_config_file: If True, use config file method (/etc/wireguard/factory-clients.conf).
                        If False, use legacy method (wg set + wg-quick save).

    Returns:
        Dictionary with registration results
    """
    try:
        steps_completed = []
        steps_failed = []

        # Determine server host
        foundries_vpn_connected = False
        if not server_host:
            # Check if Foundries VPN is connected (local import to avoid circular dependency)
            from lab_testing.tools.foundries_vpn_core import foundries_vpn_status

            status = foundries_vpn_status()
            if status.get("connected"):
                foundries_vpn_connected = True
                server_host = "10.42.42.1"  # Foundries VPN server IP
                steps_completed.append("Using Foundries VPN for server access: 10.42.42.1")
            else:
                # Not connected - need Foundries VPN for server access
                return {
                    "success": False,
                    "error": "Foundries VPN not connected. Cannot access server without VPN connection.",
                    "suggestions": [
                        "Connect to Foundries VPN first: connect_foundries_vpn()",
                        "If this is first-time setup, contact VPN admin: ajlennon@dynamicdevices.co.uk",
                        "Admin can register your client peer, then you can connect",
                    ],
                    "bootstrap_note": (
                        "For clean installation: First admin needs initial server access (public IP or direct access). "
                        "After first admin connects, all subsequent client registrations can be done via Foundries VPN."
                    ),
                }

        # Build SSH command
        if server_password:
            ssh_cmd = f"sshpass -p '{server_password}' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p {server_port} {server_user}@{server_host}"
        else:
            ssh_cmd = (
                f"ssh -o StrictHostKeyChecking=no -p {server_port} {server_user}@{server_host}"
            )

        # Check if peer already exists
        check_cmd = f"{ssh_cmd} 'wg show factory | grep \"{client_public_key}\"'"
        result = subprocess.run(
            check_cmd,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and client_public_key in result.stdout:
            return {
                "success": True,
                "message": "Client peer already registered",
                "client_public_key": client_public_key,
                "assigned_ip": assigned_ip,
                "steps_completed": ["Client peer already exists on server"],
            }

        if use_config_file:
            # Method 1: Use config file (Priority 2 - preferred)
            # Add to factory-clients.conf
            comment = f"# Client peer - {assigned_ip}"
            peer_line = f"{client_public_key} {assigned_ip} client"

            # Check if config file exists, create if not
            check_file_cmd = f"{ssh_cmd} 'test -f /etc/wireguard/factory-clients.conf && echo exists || echo notfound'"
            result = subprocess.run(
                check_file_cmd,
                shell=True,
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if "notfound" in result.stdout:
                # Create config file
                create_cmd = f"{ssh_cmd} 'echo \"# Foundries VPN Client Peers\" > /etc/wireguard/factory-clients.conf && chmod 600 /etc/wireguard/factory-clients.conf'"
                result = subprocess.run(
                    create_cmd,
                    shell=True,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    steps_completed.append("Created /etc/wireguard/factory-clients.conf")

            # Check if peer already in config file
            check_peer_cmd = (
                f"{ssh_cmd} 'grep \"{client_public_key}\" /etc/wireguard/factory-clients.conf'"
            )
            result = subprocess.run(
                check_peer_cmd,
                shell=True,
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0 and client_public_key in result.stdout:
                steps_completed.append("Client peer already in config file")
            else:
                # Add peer to config file
                add_peer_cmd = (
                    f"{ssh_cmd} 'echo \"{peer_line}\" >> /etc/wireguard/factory-clients.conf'"
                )
                result = subprocess.run(
                    add_peer_cmd,
                    shell=True,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    steps_completed.append(f"Added client peer to config file: {assigned_ip}")
                else:
                    steps_failed.append(f"Failed to add to config file: {result.stderr}")

            # Apply client peer (daemon will pick it up, or apply manually)
            apply_cmd = f"{ssh_cmd} 'wg set factory peer {client_public_key} allowed-ips {assigned_ip}/32 && wg-quick save factory'"
            result = subprocess.run(
                apply_cmd,
                shell=True,
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                steps_completed.append("Applied client peer to WireGuard interface")
            else:
                steps_failed.append(f"Failed to apply peer: {result.stderr}")

        else:
            # Method 2: Legacy method (direct wg set)
            allowed_ips = f"{assigned_ip}/32"
            register_cmd = f"{ssh_cmd} 'wg set factory peer {client_public_key} allowed-ips {allowed_ips} && wg-quick save factory'"
            result = subprocess.run(
                register_cmd,
                shell=True,
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                steps_completed.append(f"Registered client peer: {assigned_ip}")
            else:
                steps_failed.append(f"Failed to register peer: {result.stderr}")

        # Verify registration
        verify_result = check_client_peer_registered(
            client_public_key=client_public_key,
            server_host=server_host,
            server_port=server_port,
            server_user=server_user,
            server_password=server_password,
        )

        if verify_result.get("registered"):
            steps_completed.append("Verified client peer registration")
        else:
            steps_failed.append("Client peer registration verification failed")

        if steps_failed:
            return {
                "success": False,
                "error": "Some steps failed during client peer registration",
                "client_public_key": client_public_key,
                "assigned_ip": assigned_ip,
                "steps_completed": steps_completed,
                "steps_failed": steps_failed,
                "suggestions": [
                    "Check SSH access to server",
                    "Verify server host and port are correct",
                    "Check VPN connection (Foundries or standard)",
                    "Try manual registration: ssh to server and run wg set commands",
                ],
            }

        return {
            "success": True,
            "message": "Client peer registered successfully",
            "client_public_key": client_public_key,
            "assigned_ip": assigned_ip,
            "server_host": server_host,
            "connection_method": "Foundries VPN" if foundries_vpn_connected else "Not connected",
            "steps_completed": steps_completed,
            "next_steps": [
                "Client peer is now registered on server",
                "If using standard VPN, disconnect: disconnect_vpn()",
                "Connect to Foundries VPN: connect_foundries_vpn()",
                "Verify connection: ping 10.42.42.1",
            ],
        }

    except Exception as e:
        logger.error(f"Failed to register client peer: {e}")
        return {
            "success": False,
            "error": f"Failed to register client peer: {e!s}",
            "suggestions": [
                "Check VPN connection (Foundries or standard)",
                "Verify server host and port are correct",
                "Check SSH access to server",
                "Contact VPN admin: ajlennon@dynamicdevices.co.uk",
            ],
        }
