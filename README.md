# Lab Testing MCP Server

MCP server exposing remote embedded hardware testing capabilities to AI assistants.

**Version**: 0.1.0

## Quick Start

**Requirements: Python 3.10+** (MCP SDK requires Python 3.10+)

```bash
# Install the MCP SDK (requires Python 3.10+)
python3.10 -m pip install git+https://github.com/modelcontextprotocol/python-sdk.git

# Install this package
python3.10 -m pip install -e ".[dev]"

# Verify installation
python3.10 mcp_remote_testing/test_server.py
```

## Configuration

Add to Cursor MCP config (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "lab-testing": {
      "command": "python3.10",
      "args": ["/home/ajlennon/data_drive/esl/mcp-remote-testing/mcp_remote_testing/server.py"],
      "env": {"LAB_TESTING_ROOT": "/data_drive/esl/lab-testing"}
    }
  }
}
```

**Important:** Use `python3.10` (or `python3.11+`) since MCP SDK requires Python 3.10+.

See [docs/SETUP.md](docs/SETUP.md) for detailed setup instructions or `mcp.json.example` for a template.

## Architecture

```mermaid
graph TB
    subgraph "AI Assistant"
        AI[Claude/Cursor]
    end
    subgraph "MCP Server"
        MCP[server.py]
        TOOLS[Tools]
        RES[Resources]
    end
    subgraph "Lab Framework"
        CFG[Config]
        DEV[Device Manager]
        VPN[VPN Manager]
        PWR[Power Monitor]
    end
    subgraph "Hardware"
        BOARD[iMX Boards]
        DMM[DMM]
        TASMOTA[Tasmota]
    end
    AI -->|MCP| MCP
    MCP --> TOOLS
    TOOLS --> DEV
    TOOLS --> VPN
    TOOLS --> PWR
    DEV --> BOARD
    PWR --> DMM
```

Data flow: AI → MCP Server → Tools → Lab Framework → Hardware

## Tools

- **Device**: `list_devices`, `test_device`, `ssh_to_device`
- **VPN**: `vpn_status`, `connect_vpn`, `disconnect_vpn`
- **Power**: `start_power_monitoring`, `get_power_logs`, `analyze_power_logs`, `monitor_low_power`, `compare_power_profiles`
- **Tasmota**: `tasmota_control`, `list_tasmota_devices`
- **OTA/Containers**: `check_ota_status`, `trigger_ota_update`, `list_containers`, `deploy_container`, `get_system_status`, `get_firmware_version`, `get_foundries_registration_status`, `get_secure_boot_status`, `get_device_identity`
- **Process Management**: `kill_stale_processes` - Kill duplicate processes that might interfere
- **Remote Access**: `create_ssh_tunnel`, `list_ssh_tunnels`, `close_ssh_tunnel`, `access_serial_port`, `list_serial_devices` - SSH tunnels and serial port access
- **Change Tracking**: `get_change_history`, `revert_changes` - Track and revert changes for security/debugging
- **Batch/Regression**: `batch_operation`, `regression_test`, `get_device_groups`
- **Help**: `help` - Get usage documentation and examples

## Resources

- `device://inventory` - Device inventory
- `network://status` - Network/VPN status
- `config://lab_devices` - Raw config
- `help://usage` - Help documentation and usage examples
- `health://status` - Server health, metrics, and SSH pool status

## Development

```bash
# Use Python 3.10+ for development
python3.10 -m pip install -e ".[dev]"
pre-commit install
black . && ruff check . --fix
```

**Adding tools**: Create function in `tools/`, register in `server.py` (`handle_list_tools`, `handle_call_tool`).

**Versioning**: Semantic versioning (MAJOR.MINOR.PATCH). Update `version.py`, see [CHANGELOG.md](CHANGELOG.md).

## Documentation

- [API Reference](docs/API.md) - Tool and resource API
- [Setup Guide](docs/SETUP.md) - Installation and configuration
- [Architecture Diagram](docs/architecture.mmd) - Full system diagram

## License

GPL-3.0-or-later - Copyright (C) 2025 Dynamic Devices Ltd

See [LICENSE](LICENSE) for full license text.

## Maintainer

Alex J Lennon <ajlennon@dynamicdevices.co.uk>
