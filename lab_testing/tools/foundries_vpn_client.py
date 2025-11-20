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


def check_foundries_vpn_client_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Check if Foundries VPN client configuration file exists and is valid.

    Validates the WireGuard config file format and checks for required fields.

    Args:
        config_path: Optional path to config file. If not provided, searches standard locations.

    Returns:
        Dictionary with validation results
    """
    try:
        # Find config file
        if config_path:
            vpn_config = Path(config_path)
        else:
            vpn_config = get_foundries_vpn_config()

        if not vpn_config or not vpn_config.exists():
            return {
                "success": False,
                "error": "Foundries VPN client configuration file not found",
                "config_path": str(vpn_config) if vpn_config else None,
                "suggestions": [
                    "Obtain WireGuard config from FoundriesFactory web interface",
                    "Generate config template: generate_foundries_vpn_client_config_template()",
                    "Place config file in one of these locations:",
                    "  - ~/.config/wireguard/foundries.conf",
                    "  - {LAB_TESTING_ROOT}/secrets/foundries-vpn.conf",
                    "Or set FOUNDRIES_VPN_CONFIG_PATH environment variable",
                ],
            }

        # Read and validate config file
        try:
            config_content = vpn_config.read_text()
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read config file: {e!s}",
                "config_path": str(vpn_config),
                "suggestions": [
                    "Check file permissions",
                    "Ensure file is readable",
                ],
            }

        # Validate WireGuard config format
        required_sections = ["[Interface]", "[Peer]"]
        required_interface_keys = ["PrivateKey"]
        required_peer_keys = ["PublicKey", "Endpoint"]

        has_interface = False
        has_peer = False
        interface_keys = set()
        peer_keys = set()

        current_section = None
        for line in config_content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("[") and line.endswith("]"):
                current_section = line
                if current_section == "[Interface]":
                    has_interface = True
                elif current_section == "[Peer]":
                    has_peer = True
            elif "=" in line and current_section:
                key = line.split("=")[0].strip()
                if current_section == "[Interface]":
                    interface_keys.add(key)
                elif current_section == "[Peer]":
                    peer_keys.add(key)

        # Check for required sections and keys
        errors = []
        if not has_interface:
            errors.append("Missing [Interface] section")
        if not has_peer:
            errors.append("Missing [Peer] section")
        if "PrivateKey" not in interface_keys:
            errors.append("Missing PrivateKey in [Interface] section")
        if "PublicKey" not in peer_keys:
            errors.append("Missing PublicKey in [Peer] section")
        if "Endpoint" not in peer_keys:
            errors.append("Missing Endpoint in [Peer] section")

        if errors:
            return {
                "success": False,
                "error": "Invalid WireGuard config format",
                "config_path": str(vpn_config),
                "errors": errors,
                "suggestions": [
                    "Check config file format matches WireGuard specification",
                    "Generate new config template: generate_foundries_vpn_client_config_template()",
                    "See WireGuard documentation: https://www.wireguard.com/",
                ],
            }

        # Check if PrivateKey looks valid (base64, 32 bytes = 44 chars)
        private_key_line = None
        for line in config_content.split("\n"):
            if line.strip().startswith("PrivateKey"):
                private_key_line = line.split("=")[1].strip()
                break

        if private_key_line and len(private_key_line) < 40:
            return {
                "success": False,
                "error": "PrivateKey appears invalid (too short)",
                "config_path": str(vpn_config),
                "suggestions": [
                    "Generate new private key: wg genkey",
                    "Regenerate config file",
                ],
            }

        return {
            "success": True,
            "config_path": str(vpn_config),
            "valid": True,
            "has_interface": True,
            "has_peer": True,
            "message": "Foundries VPN client configuration is valid",
            "next_steps": [
                "Connect to VPN: connect_foundries_vpn()",
                "Or use automated setup: setup_foundries_vpn()",
            ],
        }

    except Exception as e:
        logger.error(f"Failed to check Foundries VPN client config: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to check config: {e!s}",
            "suggestions": [
                "Check config file path",
                "Verify file permissions",
            ],
        }



def generate_foundries_vpn_client_config_template(
    output_path: Optional[str] = None, factory: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a Foundries VPN client configuration template with server details.

    Gets server configuration from FoundriesFactory and creates a template config file
    that the user can fill in with their private key and assigned IP address.

    Args:
        output_path: Optional path to save config file. If not provided, uses standard location.
        factory: Optional factory name. If not provided, uses default factory.

    Returns:
        Dictionary with generation results
    """
    try:
        # Check prerequisites
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

        # Get server configuration
        server_config = get_foundries_vpn_server_config(factory)
        if not server_config.get("success"):
            return {
                "success": False,
                "error": "Failed to get VPN server configuration",
                "details": server_config,
                "suggestions": [
                    "Check fioctl is configured correctly",
                    "Verify VPN server is enabled in FoundriesFactory",
                ],
            }

        if not server_config.get("enabled"):
            return {
                "success": False,
                "error": "VPN server is not enabled in FoundriesFactory",
                "suggestions": [
                    "Enable VPN server in FoundriesFactory",
                    "Contact Factory administrator",
                ],
            }

        # Determine output path
        if output_path:
            config_file = Path(output_path)
        else:
            # Use standard location
            config_file = Path.home() / ".config" / "wireguard" / "foundries.conf"
            config_file.parent.mkdir(parents=True, exist_ok=True)

        # Check if file already exists
        if config_file.exists():
            return {
                "success": False,
                "error": f"Config file already exists: {config_file}",
                "config_path": str(config_file),
                "suggestions": [
                    "Delete existing file or use different output_path",
                    "Check existing config: check_foundries_vpn_client_config()",
                ],
            }

        # Generate template
        server_address_base = server_config.get("address", "10.42.42.1").rsplit(".", 1)[0]
        template = f"""# Foundries VPN WireGuard Client Configuration
# Generated automatically - Fill in YOUR_PRIVATE_KEY_HERE and YOUR_VPN_IP_HERE

[Interface]
# Your private key (generate with: wg genkey | tee privatekey | wg pubkey > publickey)
# Share your public key with VPN administrator to get assigned IP address
PrivateKey = YOUR_PRIVATE_KEY_HERE

# Your assigned VPN IP address (get from VPN administrator)
# VPN network: {server_address_base}.X/24
Address = YOUR_VPN_IP_HERE

# Optional: DNS servers to use when connected
# DNS = 8.8.8.8, 8.8.4.4

[Peer]
# Server's public key (from FoundriesFactory)
PublicKey = {server_config.get('public_key', '')}

# Server endpoint
Endpoint = {server_config.get('endpoint', '')}

# Allowed IPs - routes to send through VPN
# Use specific subnets for lab network access only
AllowedIPs = {server_address_base}.0/24, 192.168.2.0/24

# Keep connection alive
PersistentKeepalive = 25
"""

        # Write template
        try:
            config_file.write_text(template)
            config_file.chmod(0o600)  # Secure permissions
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to write config file: {e!s}",
                "config_path": str(config_file),
            }

        return {
            "success": True,
            "config_path": str(config_file),
            "server_endpoint": server_config.get("endpoint"),
            "server_address": server_config.get("address"),
            "server_public_key": server_config.get("public_key"),
            "message": f"Config template generated at {config_file}",
            "next_steps": [
                "1. Generate your private key: wg genkey | tee privatekey | wg pubkey > publickey",
                "2. Share your public key with VPN administrator to get assigned IP address",
                "3. Edit config file and replace YOUR_PRIVATE_KEY_HERE and YOUR_VPN_IP_HERE",
                "4. Check config: check_foundries_vpn_client_config()",
                "5. Connect: connect_foundries_vpn() or setup_foundries_vpn()",
            ],
        }

    except Exception as e:
        logger.error(f"Failed to generate VPN client config template: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to generate template: {e!s}",
            "suggestions": [
                "Check fioctl is installed and configured",
                "Verify VPN server is enabled",
            ],
        }



def setup_foundries_vpn(
    config_path: Optional[str] = None,
    factory: Optional[str] = None,
    auto_generate_config: bool = False,
) -> Dict[str, Any]:
    """
    Automated end-to-end Foundries VPN setup.

    Checks prerequisites, validates or generates client config, and connects to VPN.
    This is a convenience function that automates the entire setup process.

    Args:
        config_path: Optional path to client config file. If not provided, searches standard locations.
        factory: Optional factory name. If not provided, uses default factory.
        auto_generate_config: If True and config not found, generates template config (requires manual editing).

    Returns:
        Dictionary with setup results
    """
    try:
        steps_completed = []
        steps_failed = []

        # Step 1: Check fioctl installation
        fioctl_installed, fioctl_error = _check_fioctl_installed()
        if not fioctl_installed:
            return {
                "success": False,
                "error": fioctl_error,
                "steps_completed": steps_completed,
                "steps_failed": ["Check fioctl installation"],
                "suggestions": [
                    "Install fioctl CLI tool: https://github.com/foundriesio/fioctl",
                ],
            }
        steps_completed.append("fioctl installed")

        # Step 2: Check fioctl configuration
        fioctl_configured, config_error = _check_fioctl_configured()
        if not fioctl_configured:
            return {
                "success": False,
                "error": config_error,
                "steps_completed": steps_completed,
                "steps_failed": ["Check fioctl configuration"],
                "suggestions": [
                    "Run 'fioctl login' to configure FoundriesFactory credentials",
                ],
            }
        steps_completed.append("fioctl configured")

        # Step 3: Check WireGuard tools
        wg_check = subprocess.run(
            ["which", "wg"], check=False, capture_output=True, text=True, timeout=5
        )
        if wg_check.returncode != 0:
            return {
                "success": False,
                "error": "WireGuard tools not installed",
                "steps_completed": steps_completed,
                "steps_failed": ["Check WireGuard tools"],
                "suggestions": [
                    "Install WireGuard tools: sudo apt install wireguard-tools",
                    "Or: sudo yum install wireguard-tools",
                ],
            }
        steps_completed.append("WireGuard tools installed")

        # Step 4: Get server configuration
        server_config = get_foundries_vpn_server_config(factory)
        if not server_config.get("success"):
            return {
                "success": False,
                "error": "Failed to get VPN server configuration",
                "steps_completed": steps_completed,
                "steps_failed": ["Get server configuration"],
                "details": server_config,
            }
        steps_completed.append("Server configuration retrieved")

        if not server_config.get("enabled"):
            return {
                "success": False,
                "error": "VPN server is not enabled in FoundriesFactory",
                "steps_completed": steps_completed,
                "steps_failed": ["VPN server enabled"],
                "suggestions": [
                    "Enable VPN server in FoundriesFactory",
                    "Contact Factory administrator",
                ],
            }
        steps_completed.append("VPN server enabled")

        # Step 5: Check or generate client config
        client_config_check = check_foundries_vpn_client_config(config_path)
        if not client_config_check.get("success"):
            if auto_generate_config:
                # Generate template config
                template_result = generate_foundries_vpn_client_config_template(
                    config_path, factory
                )
                if template_result.get("success"):
                    steps_completed.append("Config template generated")
                    return {
                        "success": False,
                        "error": "Client config template generated but requires manual editing",
                        "steps_completed": steps_completed,
                        "config_path": template_result.get("config_path"),
                        "next_steps": template_result.get("next_steps", []),
                        "message": "Template generated. Edit config file with your private key and assigned IP, then run setup_foundries_vpn() again.",
                    }
                steps_failed.append("Generate config template")
                return {
                    "success": False,
                    "error": "Failed to generate config template",
                    "steps_completed": steps_completed,
                    "steps_failed": steps_failed,
                    "details": template_result,
                }
            steps_failed.append("Client config found")
            return {
                "success": False,
                "error": "Client configuration not found",
                "steps_completed": steps_completed,
                "steps_failed": steps_failed,
                "details": client_config_check,
                "suggestions": [
                    "Obtain config from FoundriesFactory web interface",
                    "Or run: generate_foundries_vpn_client_config_template()",
                    "Or use auto_generate_config=True to generate template",
                ],
            }
        steps_completed.append("Client config found and valid")

        # Step 6: Connect to VPN
        connect_result = connect_foundries_vpn(config_path)
        if connect_result.get("success"):
            steps_completed.append("VPN connected")
            return {
                "success": True,
                "steps_completed": steps_completed,
                "connection_method": connect_result.get("method"),
                "message": "Foundries VPN setup completed successfully",
                "next_steps": [
                    "List devices: list_foundries_devices()",
                    "Test device connectivity: test_device(device_id)",
                ],
            }
        steps_failed.append("Connect to VPN")
        return {
            "success": False,
            "error": "Failed to connect to VPN",
            "steps_completed": steps_completed,
            "steps_failed": steps_failed,
            "details": connect_result,
        }

    except Exception as e:
        logger.error(f"Failed to setup Foundries VPN: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Setup failed: {e!s}",
            "steps_completed": steps_completed if "steps_completed" in locals() else [],
            "steps_failed": steps_failed if "steps_failed" in locals() else [],
            "suggestions": [
                "Check prerequisites manually",
                "Review error details",
            ],
        }


