"""
Tool Definitions for MCP Server

Contains all Tool schema definitions for the MCP server.

Copyright (C) 2025 Dynamic Devices Ltd
License: GPL-3.0-or-later
"""

from typing import List

from mcp.types import Tool


def get_all_tools() -> List[Tool]:
    """Get all tool definitions for the MCP server"""
    return [
        Tool(
            name="list_devices",
            description=(
                "List all devices on the target network with their status, firmware, and relationships. "
                "Supports filtering by type, status, SSH status, power state, and search queries. "
                "Includes summary statistics. Supports sorting and limiting results."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "device_type_filter": {
                        "type": "string",
                        "description": "Filter by device type (e.g., 'tasmota_device', 'eink_board', 'test_equipment', 'sentai_board')",
                    },
                    "status_filter": {
                        "type": "string",
                        "description": "Filter by status (e.g., 'online', 'offline', 'discovered')",
                    },
                    "search_query": {
                        "type": "string",
                        "description": "Search by IP address, hostname, friendly name, or device ID (case-insensitive)",
                    },
                    "show_summary": {
                        "type": "boolean",
                        "description": "Include summary statistics (counts by type/status) in response (default: true)",
                        "default": True,
                    },
                    "force_refresh": {
                        "type": "boolean",
                        "description": "Bypass cache and rescan all devices (default: false)",
                        "default": False,
                    },
                    "ssh_status_filter": {
                        "type": "string",
                        "description": "Filter by SSH status (e.g., 'ok', 'error', 'refused', 'timeout', 'unknown')",
                    },
                    "power_state_filter": {
                        "type": "string",
                        "description": "Filter Tasmota devices by power state (e.g., 'on', 'off')",
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "Sort results by field: 'ip', 'friendly_name', 'status', 'last_seen' (default: type then friendly_name)",
                    },
                    "sort_order": {
                        "type": "string",
                        "description": "Sort order: 'asc' or 'desc' (default: 'asc')",
                        "enum": ["asc", "desc"],
                        "default": "asc",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of devices to return (default: no limit)",
                        "minimum": 1,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="test_device",
            description=(
                "Test connectivity to a specific lab device. "
                "Checks ping reachability and SSH availability. "
                "Supports both device_id (unique ID) and friendly_name. "
                "Best practice: Use this before running operations on devices. "
                "In DHCP environments, use 'verify_device_identity' to ensure correct device."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Device identifier (device_id or friendly_name). Use 'list_devices' to see available options.",
                    }
                },
                "required": ["device_id"],
            },
        ),
        Tool(
            name="ssh_to_device",
            description=(
                "Execute an SSH command on a lab device. "
                "Prefers SSH keys, falls back to password authentication if keys not available. "
                "Uses default credentials (fio/fio) if no SSH keys and no cached credentials. "
                "Supports both device_id and friendly_name. "
                "Best practice: Test device connectivity first with 'test_device'. "
                "In DHCP environments, verify device identity with 'verify_device_identity'. "
                "All commands are tracked for security and debugging."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Device identifier (device_id or friendly_name). Use 'list_devices' to see available options.",
                    },
                    "command": {
                        "type": "string",
                        "description": "Command to execute on the device (e.g., 'uptime', 'cat /etc/os-release')",
                    },
                    "username": {
                        "type": "string",
                        "description": "SSH username (optional, uses device default from config)",
                    },
                },
                "required": ["device_id", "command"],
            },
        ),
        Tool(
            name="vpn_status",
            description="Get current WireGuard VPN connection status",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="connect_vpn",
            description="Connect to the WireGuard VPN for lab network access",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="disconnect_vpn",
            description="Disconnect from the WireGuard VPN",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="vpn_setup_instructions",
            description="Get WireGuard VPN setup instructions and check current configuration",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="check_wireguard_installed",
            description="Check if WireGuard tools are installed on the system",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="list_vpn_configs",
            description="List existing WireGuard configuration files",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="create_vpn_config_template",
            description="Create a WireGuard configuration template file",
            inputSchema={
                "type": "object",
                "properties": {
                    "output_path": {
                        "type": "string",
                        "description": "Path where to save the template (optional, defaults to secrets directory)",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="setup_networkmanager_vpn",
            description="Import WireGuard config into NetworkManager (allows connecting without root)",
            inputSchema={
                "type": "object",
                "properties": {
                    "config_path": {
                        "type": "string",
                        "description": "Path to WireGuard .conf file (optional, uses detected config if not specified)",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="vpn_statistics",
            description="Get detailed WireGuard VPN statistics (transfer data, handshakes, latency)",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        # Foundries VPN Tools (server-based WireGuard VPN)
        Tool(
            name="foundries_vpn_status",
            description=(
                "Get Foundries VPN connection status. "
                "Foundries VPN uses WireGuard but with a server-based architecture where devices connect "
                "to a centralized VPN server managed by FoundriesFactory. "
                "Requires fioctl CLI tool to be installed and configured."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="connect_foundries_vpn",
            description=(
                "Connect to Foundries VPN server. "
                "Requires a WireGuard configuration file obtained from FoundriesFactory. "
                "The config can be obtained via FoundriesFactory web interface or API. "
                "Searches for config in standard locations if not provided."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "config_path": {
                        "type": "string",
                        "description": "Optional path to WireGuard config file for Foundries VPN. If not provided, searches for Foundries VPN config in standard locations.",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="get_foundries_vpn_server_config",
            description=(
                "Get Foundries VPN server configuration using fioctl API. "
                "Returns WireGuard server endpoint, address, and public key. "
                "This is the server that devices connect to (e.g., proxmox.dynamicdevices.co.uk). "
                "Requires fioctl CLI tool to be installed and configured."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "factory": {
                        "type": "string",
                        "description": "Optional factory name. If not provided, uses default factory from fioctl config.",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="list_foundries_devices",
            description=(
                "List devices accessible via Foundries VPN. "
                "Uses fioctl to list devices in the FoundriesFactory that have WireGuard enabled. "
                "Requires fioctl CLI tool to be installed and configured."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "factory": {
                        "type": "string",
                        "description": "Optional factory name. If not provided, uses default factory from fioctl config.",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="enable_foundries_vpn_device",
            description=(
                "Enable WireGuard VPN on a Foundries device. "
                "Uses fioctl to enable WireGuard configuration on a device. "
                "The device will connect to the Foundries VPN server after OTA update (up to 5 minutes). "
                "Requires fioctl CLI tool to be installed and configured."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "device_name": {
                        "type": "string",
                        "description": "Name of the device to enable VPN on",
                    },
                    "factory": {
                        "type": "string",
                        "description": "Optional factory name. If not provided, uses default factory from fioctl config.",
                    },
                },
                "required": ["device_name"],
            },
        ),
        Tool(
            name="disable_foundries_vpn_device",
            description=(
                "Disable WireGuard VPN on a Foundries device. "
                "Uses fioctl to disable WireGuard configuration on a device. "
                "The device will disconnect from the Foundries VPN server after OTA update (up to 5 minutes). "
                "Requires fioctl CLI tool to be installed and configured."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "device_name": {
                        "type": "string",
                        "description": "Name of the device to disable VPN on",
                    },
                    "factory": {
                        "type": "string",
                        "description": "Optional factory name. If not provided, uses default factory from fioctl config.",
                    },
                },
                "required": ["device_name"],
            },
        ),
        Tool(
            name="enable_foundries_device_to_device",
            description=(
                "Enable device-to-device communication for a Foundries device via VPN. "
                "SSHes into the WireGuard server, then from there to the target device, "
                "and updates the device's NetworkManager WireGuard configuration to allow "
                "the full VPN subnet instead of just the server IP. "
                "This enables device-to-device communication for debugging/development purposes. "
                "By default, Foundries devices use restrictive AllowedIPs (server IP only) for security. "
                "This tool temporarily overrides that for development/debugging."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "device_name": {
                        "type": "string",
                        "description": "Name of the Foundries device (e.g., 'imx8mm-jaguar-sentai-2d0e0a09dab86563')",
                    },
                    "device_ip": {
                        "type": "string",
                        "description": "VPN IP address of the device (e.g., '10.42.42.2'). If not provided, will try to get from device list.",
                    },
                    "vpn_subnet": {
                        "type": "string",
                        "description": "VPN subnet to allow (default: '10.42.42.0/24')",
                        "default": "10.42.42.0/24",
                    },
                    "server_host": {
                        "type": "string",
                        "description": "WireGuard server hostname/IP (default: from config or '144.76.167.54')",
                    },
                    "server_port": {
                        "type": "integer",
                        "description": "SSH port on WireGuard server (default: 5025)",
                        "default": 5025,
                    },
                    "server_user": {
                        "type": "string",
                        "description": "SSH user for WireGuard server (default: 'root')",
                        "default": "root",
                    },
                    "server_password": {
                        "type": "string",
                        "description": "SSH password for WireGuard server (if not using SSH keys)",
                    },
                    "device_user": {
                        "type": "string",
                        "description": "SSH user on device (default: 'fio')",
                        "default": "fio",
                    },
                    "device_password": {
                        "type": "string",
                        "description": "SSH password on device (default: 'fio')",
                        "default": "fio",
                    },
                },
                "required": ["device_name"],
            },
        ),
        Tool(
            name="check_client_peer_registered",
            description=(
                "Check if a client peer is registered on the Foundries WireGuard server. "
                "Connects via Foundries VPN (if connected) or standard VPN (hardware lab) for bootstrap access. "
                "Can derive client public key from local config file if not provided. "
                "Useful for troubleshooting VPN connection issues."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "client_public_key": {
                        "type": "string",
                        "description": "Client's WireGuard public key. If not provided, will try to derive from local config file.",
                    },
                    "server_host": {
                        "type": "string",
                        "description": "WireGuard server hostname/IP. If not provided, will try Foundries VPN (10.42.42.1) or standard VPN (10.21.21.101).",
                    },
                    "server_port": {
                        "type": "integer",
                        "description": "SSH port on WireGuard server (default: 5025)",
                        "default": 5025,
                    },
                    "server_user": {
                        "type": "string",
                        "description": "SSH user for WireGuard server (default: 'root')",
                        "default": "root",
                    },
                    "server_password": {
                        "type": "string",
                        "description": "SSH password for WireGuard server (if not using SSH keys)",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="register_foundries_vpn_client",
            description=(
                "Register a client peer on the Foundries WireGuard server. "
                "Automates client peer registration by connecting to server via Foundries VPN (if connected) "
                "or standard VPN (hardware lab) for bootstrap access. "
                "Supports both config file method (factory-clients.conf) and legacy method (wg set). "
                "Use this tool to register your client before connecting to Foundries VPN."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "client_public_key": {
                        "type": "string",
                        "description": "Client's WireGuard public key to register",
                    },
                    "assigned_ip": {
                        "type": "string",
                        "description": "IP address to assign to client (e.g., '10.42.42.10')",
                    },
                    "server_host": {
                        "type": "string",
                        "description": "WireGuard server hostname/IP. If not provided, will try Foundries VPN (10.42.42.1) or standard VPN (10.21.21.101).",
                    },
                    "server_port": {
                        "type": "integer",
                        "description": "SSH port on WireGuard server (default: 5025)",
                        "default": 5025,
                    },
                    "server_user": {
                        "type": "string",
                        "description": "SSH user for WireGuard server (default: 'root')",
                        "default": "root",
                    },
                    "server_password": {
                        "type": "string",
                        "description": "SSH password for WireGuard server (if not using SSH keys)",
                    },
                    "use_config_file": {
                        "type": "boolean",
                        "description": "If True, use config file method (/etc/wireguard/factory-clients.conf). If False, use legacy method (wg set + wg-quick save).",
                        "default": True,
                    },
                },
                "required": ["client_public_key", "assigned_ip"],
            },
        ),
        Tool(
            name="manage_foundries_vpn_ip_cache",
            description=(
                "Manage Foundries VPN IP address cache. "
                "Query, update, and refresh the cache of Foundries device VPN IP addresses. "
                "The cache is populated from the WireGuard server's /etc/hosts file or manually. "
                "Useful for quickly looking up device VPN IPs without querying the server each time."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["get", "list", "set", "remove", "refresh"],
                        "description": "Action to perform: 'get' (get IP for device), 'list' (list all cached IPs), 'set' (manually set IP), 'remove' (remove entry), 'refresh' (refresh from server)",
                        "default": "get",
                    },
                    "device_name": {
                        "type": "string",
                        "description": "Foundries device name (required for get/set/remove actions, e.g., 'imx8mm-jaguar-inst-2240a09dab86563')",
                    },
                    "vpn_ip": {
                        "type": "string",
                        "description": "VPN IP address (required for 'set' action, e.g., '10.42.42.2')",
                    },
                    "refresh_from_server": {
                        "type": "boolean",
                        "description": "If True, refresh cache from WireGuard server /etc/hosts (for 'refresh' action)",
                        "default": False,
                    },
                    "server_host": {
                        "type": "string",
                        "description": "WireGuard server hostname/IP (default: from config or 'proxmox.dynamicdevices.co.uk')",
                    },
                    "server_port": {
                        "type": "integer",
                        "description": "SSH port on WireGuard server (default: 5025)",
                        "default": 5025,
                    },
                    "server_user": {
                        "type": "string",
                        "description": "SSH user for WireGuard server (default: 'root')",
                        "default": "root",
                    },
                    "server_password": {
                        "type": "string",
                        "description": "SSH password for WireGuard server (if not using SSH keys)",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="check_foundries_vpn_client_config",
            description=(
                "Check if Foundries VPN client configuration file exists and is valid. "
                "Validates the WireGuard config file format and checks for required fields. "
                "Searches standard locations if config_path not provided."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "config_path": {
                        "type": "string",
                        "description": "Optional path to config file. If not provided, searches standard locations.",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="generate_foundries_vpn_client_config_template",
            description=(
                "Generate a Foundries VPN client configuration template with server details. "
                "Gets server configuration from FoundriesFactory and creates a template config file "
                "that the user can fill in with their private key and assigned IP address. "
                "Requires fioctl CLI tool to be installed and configured."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "output_path": {
                        "type": "string",
                        "description": "Optional path to save config file. If not provided, uses standard location (~/.config/wireguard/foundries.conf).",
                    },
                    "factory": {
                        "type": "string",
                        "description": "Optional factory name. If not provided, uses default factory from fioctl config.",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="setup_foundries_vpn",
            description=(
                "Automated end-to-end Foundries VPN setup. "
                "Checks prerequisites, validates or generates client config, and connects to VPN. "
                "This is a convenience function that automates the entire setup process. "
                "Requires fioctl CLI tool and WireGuard tools to be installed."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "config_path": {
                        "type": "string",
                        "description": "Optional path to client config file. If not provided, searches standard locations.",
                    },
                    "factory": {
                        "type": "string",
                        "description": "Optional factory name. If not provided, uses default factory from fioctl config.",
                    },
                    "auto_generate_config": {
                        "type": "boolean",
                        "description": "If True and config not found, generates template config (requires manual editing). Default: False",
                        "default": False,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="verify_foundries_vpn_connection",
            description=(
                "Verify that Foundries VPN connection is working. "
                "Tests connectivity to VPN server and checks routing. "
                "Use this after connecting to ensure VPN is functioning correctly."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="validate_foundries_device_connectivity",
            description=(
                "Comprehensive step-by-step validation of Foundries VPN and device connectivity. "
                "Performs validation in sequence: "
                "1. Check connection to Foundries VPN server (ping test) "
                "2. List relevant Foundries devices "
                "3. Check devices are online and VPN is enabled "
                "4. Test ping and SSH connectivity to devices. "
                "Provides clear, sequential validation results to help diagnose connectivity issues. "
                "If device_name is provided, validates only that device. Otherwise validates all VPN-enabled devices."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "device_name": {
                        "type": "string",
                        "description": "Optional specific device name to validate (e.g., 'imx8mm-jaguar-inst-2240a09dab86563'). If not provided, validates all Foundries devices with VPN enabled.",
                    },
                    "factory": {
                        "type": "string",
                        "description": "Optional factory name. If not provided, uses default factory from fioctl config.",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="create_network_map",
            description="Create a visual map of running systems on the target network showing what's up and what isn't. Supports multiple layouts, export formats, device grouping, historical tracking, and performance metrics visualization.",
            inputSchema={
                "type": "object",
                "properties": {
                    "networks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Network CIDRs to scan (e.g., ['192.168.1.0/24']). If not provided, uses networks from config",
                    },
                    "scan_networks": {
                        "type": "boolean",
                        "description": "If true, actively scan networks for hosts (default: true)",
                        "default": True,
                    },
                    "test_configured_devices": {
                        "type": "boolean",
                        "description": "If true, test all configured devices (default: true)",
                        "default": True,
                    },
                    "max_hosts_per_network": {
                        "type": "integer",
                        "description": "Maximum hosts to scan per network (default: 254)",
                        "default": 254,
                    },
                    "quick_mode": {
                        "type": "boolean",
                        "description": "If true, skip network scanning and only show configured devices (faster, <5s). Use this if tool calls timeout (default: false)",
                        "default": False,
                    },
                    "layout": {
                        "type": "string",
                        "enum": ["lr", "tb", "radial", "hierarchical", "grid"],
                        "description": "Layout style: 'lr' (left-right, default), 'tb' (top-bottom), 'radial' (circular), 'hierarchical' (tree), 'grid' (grid layout)",
                        "default": "lr",
                    },
                    "group_by": {
                        "type": "string",
                        "enum": ["type", "status", "location", "power_circuit", "none"],
                        "description": "Group devices by: 'type' (device type), 'status' (online/offline), 'location' (physical location from config), 'power_circuit' (power switch), 'none' (no grouping)",
                        "default": "type",
                    },
                    "show_details": {
                        "type": "boolean",
                        "description": "If true, show detailed device information in node labels (firmware, MAC, last seen, etc.)",
                        "default": False,
                    },
                    "show_metrics": {
                        "type": "boolean",
                        "description": "If true, color-code devices by latency and show performance metrics",
                        "default": True,
                    },
                    "show_alerts": {
                        "type": "boolean",
                        "description": "If true, highlight devices with errors, warnings, or issues",
                        "default": True,
                    },
                    "show_history": {
                        "type": "boolean",
                        "description": "If true, show historical status changes and uptime indicators",
                        "default": False,
                    },
                    "export_format": {
                        "type": "string",
                        "enum": ["mermaid", "png", "svg", "pdf", "html", "json", "csv"],
                        "description": "Export format: 'mermaid' (Mermaid diagram, default), 'png' (PNG image), 'svg' (SVG image), 'pdf' (PDF document), 'html' (HTML report), 'json' (JSON data), 'csv' (CSV device list)",
                        "default": "mermaid",
                    },
                    "export_path": {
                        "type": "string",
                        "description": "Optional path to save exported file. If not provided, returns data inline.",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="verify_device_identity",
            description="Verify that a device at a given IP matches expected identity by checking hostname/unique ID (important for DHCP)",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Device identifier (device_id or friendly_name)",
                    },
                    "ip": {
                        "type": "string",
                        "description": "IP address to verify (optional, uses configured IP if not provided)",
                    },
                },
                "required": ["device_id"],
            },
        ),
        Tool(
            name="verify_device_by_ip",
            description="Identify which device (if any) is at a given IP address by checking hostname/unique ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "ip": {"type": "string", "description": "IP address to check"},
                    "username": {
                        "type": "string",
                        "description": "SSH username (default: root)",
                        "default": "root",
                    },
                    "ssh_port": {
                        "type": "integer",
                        "description": "SSH port (default: 22)",
                        "default": 22,
                    },
                },
                "required": ["ip"],
            },
        ),
        Tool(
            name="update_device_ip",
            description="Verify device identity and update IP address in config if device is verified and IP has changed (for DHCP environments)",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Device identifier (device_id or friendly_name)",
                    },
                    "new_ip": {
                        "type": "string",
                        "description": "New IP address to verify and potentially update",
                    },
                },
                "required": ["device_id", "new_ip"],
            },
        ),
        Tool(
            name="start_power_monitoring",
            description="Start a power monitoring session. Supports both DMM (Digital Multimeter) and Tasmota devices for power measurement",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Device identifier - DMM (test_equipment) or Tasmota device (tasmota_device) with energy monitoring (optional)",
                    },
                    "test_name": {
                        "type": "string",
                        "description": "Name for this test session (optional)",
                    },
                    "duration": {
                        "type": "integer",
                        "description": "Monitoring duration in seconds (optional)",
                    },
                    "monitor_type": {
                        "type": "string",
                        "enum": ["dmm", "tasmota"],
                        "description": "Type of monitor to use - 'dmm' (default) or 'tasmota'. Auto-detected from device type if not specified",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_power_logs",
            description="Get recent power monitoring log files",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_name": {
                        "type": "string",
                        "description": "Filter by test name (optional)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of log files to return",
                        "default": 10,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="tasmota_control",
            description="Control a Tasmota device (power switch, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {"type": "string", "description": "Tasmota device identifier"},
                    "action": {
                        "type": "string",
                        "enum": ["on", "off", "toggle", "status", "energy"],
                        "description": "Action to perform",
                    },
                },
                "required": ["device_id", "action"],
            },
        ),
        Tool(
            name="list_tasmota_devices",
            description="List all configured Tasmota devices and the devices they control",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="list_test_equipment",
            description="List all test equipment devices (DMM, oscilloscopes, etc.) found on the network. Includes both configured devices and auto-discovered devices.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="query_test_equipment",
            description="Send a SCPI command to test equipment (DMM, etc.) and get the response. Common commands: *IDN? (identify), MEAS:VOLT:DC? (measure DC voltage), MEAS:CURR:DC? (measure DC current)",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id_or_ip": {
                        "type": "string",
                        "description": "Device ID from config or IP address of the test equipment",
                    },
                    "scpi_command": {
                        "type": "string",
                        "description": "SCPI command to send (e.g., '*IDN?', 'MEAS:VOLT:DC?')",
                    },
                },
                "required": ["device_id_or_ip", "scpi_command"],
            },
        ),
        Tool(
            name="power_cycle_device",
            description="Power cycle a device by controlling its Tasmota power switch (turns off, waits, then turns on)",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Device identifier (device_id or friendly_name) to power cycle",
                    },
                    "off_duration": {
                        "type": "integer",
                        "description": "Duration in seconds to keep power off (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["device_id"],
            },
        ),
        Tool(
            name="help",
            description="Get help and usage documentation for the MCP server",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Specific topic (tools, resources, workflows, troubleshooting) or 'all' for complete help",
                        "enum": [
                            "all",
                            "tools",
                            "resources",
                            "workflows",
                            "troubleshooting",
                            "examples",
                        ],
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="check_ota_status",
            description="Check Foundries.io OTA update status for a device",
            inputSchema={
                "type": "object",
                "properties": {"device_id": {"type": "string", "description": "Device identifier"}},
                "required": ["device_id"],
            },
        ),
        Tool(
            name="trigger_ota_update",
            description="Trigger Foundries.io OTA update for a device",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {"type": "string", "description": "Device identifier"},
                    "target": {
                        "type": "string",
                        "description": "Target to update to (optional, uses device default)",
                    },
                },
                "required": ["device_id"],
            },
        ),
        Tool(
            name="list_containers",
            description="List Docker containers on a device",
            inputSchema={
                "type": "object",
                "properties": {"device_id": {"type": "string", "description": "Device identifier"}},
                "required": ["device_id"],
            },
        ),
        Tool(
            name="deploy_container",
            description="Deploy/update a container on a device",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {"type": "string", "description": "Device identifier"},
                    "container_name": {"type": "string", "description": "Container name"},
                    "image": {"type": "string", "description": "Container image to deploy"},
                },
                "required": ["device_id", "container_name", "image"],
            },
        ),
        Tool(
            name="get_system_status",
            description="Get comprehensive system status (uptime, load, memory, disk, kernel)",
            inputSchema={
                "type": "object",
                "properties": {"device_id": {"type": "string", "description": "Device identifier"}},
                "required": ["device_id"],
            },
        ),
        Tool(
            name="get_firmware_version",
            description="Get firmware/OS version information from /etc/os-release",
            inputSchema={
                "type": "object",
                "properties": {"device_id": {"type": "string", "description": "Device identifier"}},
                "required": ["device_id"],
            },
        ),
        Tool(
            name="batch_operation",
            description="Execute operation on multiple devices in parallel (for racks/regression testing)",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of device identifiers",
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["test", "ssh", "ota_check", "system_status", "list_containers"],
                        "description": "Operation to perform",
                    },
                    "max_concurrent": {
                        "type": "integer",
                        "description": "Maximum concurrent operations (default: 5)",
                        "default": 5,
                    },
                    "command": {
                        "type": "string",
                        "description": "Command for SSH operation (required if operation=ssh)",
                    },
                    "username": {"type": "string", "description": "SSH username (optional)"},
                },
                "required": ["device_ids", "operation"],
            },
        ),
        Tool(
            name="regression_test",
            description="Run regression test sequence on multiple devices in parallel",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_group": {
                        "type": "string",
                        "description": "Device group/tag to test (optional)",
                    },
                    "device_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific device IDs to test (optional)",
                    },
                    "test_sequence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of test operations (default: test, system_status, ota_check)",
                    },
                    "max_concurrent": {
                        "type": "integer",
                        "description": "Maximum concurrent operations per test (default: 5)",
                        "default": 5,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_device_groups",
            description="Get devices organized by groups/tags (for rack management)",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="analyze_power_logs",
            description="Analyze power logs for low power characteristics and suspend/resume detection",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_name": {
                        "type": "string",
                        "description": "Filter by test name (optional)",
                    },
                    "device_id": {"type": "string", "description": "Filter by device (optional)"},
                    "threshold_mw": {
                        "type": "number",
                        "description": "Power threshold in mW for low power detection (optional)",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="monitor_low_power",
            description="Monitor device for low power consumption",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {"type": "string", "description": "Device identifier"},
                    "duration": {
                        "type": "integer",
                        "description": "Monitoring duration in seconds",
                        "default": 300,
                    },
                    "threshold_mw": {
                        "type": "number",
                        "description": "Low power threshold in mW",
                        "default": 100.0,
                    },
                    "sample_rate": {
                        "type": "number",
                        "description": "Sampling rate in Hz",
                        "default": 1.0,
                    },
                },
                "required": ["device_id"],
            },
        ),
        Tool(
            name="compare_power_profiles",
            description="Compare power consumption across multiple test runs",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of test names to compare",
                    },
                    "device_id": {"type": "string", "description": "Optional device filter"},
                },
                "required": ["test_names"],
            },
        ),
        Tool(
            name="update_device_friendly_name",
            description="Update the friendly name for a discovered device in the cache. This allows you to use a custom name when referencing devices.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ip": {
                        "type": "string",
                        "description": "IP address of the device",
                    },
                    "friendly_name": {
                        "type": "string",
                        "description": "New friendly name to set for the device",
                    },
                },
                "required": ["ip", "friendly_name"],
            },
        ),
        Tool(
            name="cache_device_credentials",
            description="Cache SSH credentials (username/password) for a device. Credentials are stored securely in ~/.cache/ai-lab-testing/credentials.json. Prefer SSH keys over passwords when possible.",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Device identifier (device_id or friendly_name). Use 'list_devices' to see available options.",
                    },
                    "username": {
                        "type": "string",
                        "description": "SSH username",
                    },
                    "password": {
                        "type": "string",
                        "description": "SSH password (optional, prefer SSH keys)",
                    },
                    "credential_type": {
                        "type": "string",
                        "enum": ["ssh", "sudo"],
                        "default": "ssh",
                        "description": "Type of credential to cache",
                    },
                },
                "required": ["device_id", "username"],
            },
        ),
        Tool(
            name="check_ssh_key_status",
            description="Check if SSH key authentication is working for a device. Returns status of key installation and whether default SSH keys exist.",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Device identifier (device_id or friendly_name). Use 'list_devices' to see available options.",
                    },
                    "username": {
                        "type": "string",
                        "description": "SSH username (optional, uses device default from config)",
                    },
                },
                "required": ["device_id"],
            },
        ),
        Tool(
            name="install_ssh_key",
            description="Install SSH public key on target device for passwordless access. Uses default SSH key from ~/.ssh/id_rsa.pub or ~/.ssh/id_ed25519.pub. Requires password for initial access if key not already installed. Will use cached/default credentials if password not provided.",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Device identifier (device_id or friendly_name). Use 'list_devices' to see available options.",
                    },
                    "username": {
                        "type": "string",
                        "description": "SSH username (optional, uses device default from config)",
                    },
                    "password": {
                        "type": "string",
                        "description": "Password for initial access (if key not installed, uses cached/default if available)",
                    },
                },
                "required": ["device_id"],
            },
        ),
        Tool(
            name="enable_passwordless_sudo",
            description="Enable passwordless sudo on a device for testing/debugging. Creates a sudoers.d file that allows the SSH user to use sudo without a password. Validates the sudoers file with visudo before applying. Use disable_passwordless_sudo to revert changes when testing is finished.",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Device identifier (device_id or friendly_name). Use 'list_devices' to see available options.",
                    },
                    "username": {
                        "type": "string",
                        "description": "SSH username (optional, uses device default from config)",
                    },
                    "password": {
                        "type": "string",
                        "description": "Password for sudo access (if needed, uses cached/default if available)",
                    },
                },
                "required": ["device_id"],
            },
        ),
        Tool(
            name="disable_passwordless_sudo",
            description="Disable passwordless sudo on a device (revert changes). Removes the sudoers.d file that was created by enable_passwordless_sudo. Use this when testing is finished to restore normal sudo behavior.",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Device identifier (device_id or friendly_name). Use 'list_devices' to see available options.",
                    },
                    "username": {
                        "type": "string",
                        "description": "SSH username (optional, uses device default from config)",
                    },
                    "password": {
                        "type": "string",
                        "description": "Password for sudo access (if needed, uses cached/default if available)",
                    },
                },
                "required": ["device_id"],
            },
        ),
        Tool(
            name="copy_file_to_device",
            description="Copy a file from local machine to remote device. Optimized for speed using multiplexed SSH connections (ControlMaster). Supports compression for faster transfers over slow links. Best practice: Use sync_directory_to_device for multiple files or directories.",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Device identifier (device_id or friendly_name). Use 'list_devices' to see available options.",
                    },
                    "local_path": {
                        "type": "string",
                        "description": "Local file path to copy",
                    },
                    "remote_path": {
                        "type": "string",
                        "description": "Remote destination path on device",
                    },
                    "username": {
                        "type": "string",
                        "description": "SSH username (optional, uses device default from config)",
                    },
                    "preserve_permissions": {
                        "type": "boolean",
                        "description": "Preserve file permissions and timestamps (default: true)",
                        "default": True,
                    },
                },
                "required": ["device_id", "local_path", "remote_path"],
            },
        ),
        Tool(
            name="copy_file_from_device",
            description="Copy a file from remote device to local machine. Optimized for speed using multiplexed SSH connections (ControlMaster). Supports compression for faster transfers over slow links.",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Device identifier (device_id or friendly_name). Use 'list_devices' to see available options.",
                    },
                    "remote_path": {
                        "type": "string",
                        "description": "Remote file path on device",
                    },
                    "local_path": {
                        "type": "string",
                        "description": "Local destination path",
                    },
                    "username": {
                        "type": "string",
                        "description": "SSH username (optional, uses device default from config)",
                    },
                    "preserve_permissions": {
                        "type": "boolean",
                        "description": "Preserve file permissions and timestamps (default: true)",
                        "default": True,
                    },
                },
                "required": ["device_id", "remote_path", "local_path"],
            },
        ),
        Tool(
            name="sync_directory_to_device",
            description="Sync a local directory to remote device using rsync. Much faster than copying individual files. Optimized for speed using multiplexed SSH connections. Supports exclude patterns and delete option. Best practice: Use this for deploying applications or syncing project directories.",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Device identifier (device_id or friendly_name). Use 'list_devices' to see available options.",
                    },
                    "local_dir": {
                        "type": "string",
                        "description": "Local directory to sync",
                    },
                    "remote_dir": {
                        "type": "string",
                        "description": "Remote destination directory on device",
                    },
                    "username": {
                        "type": "string",
                        "description": "SSH username (optional, uses device default from config)",
                    },
                    "exclude": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of patterns to exclude (e.g., ['*.pyc', '__pycache__', '.git'])",
                    },
                    "delete": {
                        "type": "boolean",
                        "description": "Delete files on remote that don't exist locally (default: false)",
                        "default": False,
                    },
                },
                "required": ["device_id", "local_dir", "remote_dir"],
            },
        ),
        Tool(
            name="copy_files_to_device_parallel",
            description="Copy multiple files to remote device in parallel using multiplexed SSH connections. Much faster than copying files sequentially - all transfers share the same SSH connection. Best practice: Use this when copying multiple files at once (e.g., deploying an application with multiple binaries/configs).",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Device identifier (device_id or friendly_name). Use 'list_devices' to see available options.",
                    },
                    "file_pairs": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 2,
                            "maxItems": 2,
                        },
                        "description": "List of [local_path, remote_path] pairs to copy",
                    },
                    "username": {
                        "type": "string",
                        "description": "SSH username (optional, uses device default from config)",
                    },
                    "preserve_permissions": {
                        "type": "boolean",
                        "description": "Preserve file permissions and timestamps (default: true)",
                        "default": True,
                    },
                    "max_workers": {
                        "type": "integer",
                        "description": "Maximum number of parallel transfers (default: 5)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
                "required": ["device_id", "file_pairs"],
            },
        ),
    ]
