# Setup

## Installation

**Requirements: Python 3.10+** (MCP SDK requires Python 3.10+)

```bash
# Install the MCP SDK (requires Python 3.10+)
python3.10 -m pip install git+https://github.com/modelcontextprotocol/python-sdk.git

# Install this package
python3.10 -m pip install -e ".[dev]"  # Optional: dev dependencies

# Optional: git hooks
pre-commit install
```

**Note:** If your default `python3` is 3.8 or 3.9, use `python3.10` explicitly for MCP SDK installation.

## Configuration

Uses existing lab testing framework:
- Device config: `{LAB_TESTING_ROOT}/config/lab_devices.json`
- VPN config: Auto-detected (see [VPN Setup Guide](VPN_SETUP.md))

### Environment Variables

- `LAB_TESTING_ROOT`: Path to lab testing framework (default: `/data_drive/esl/ai-lab-testing`)
- `VPN_CONFIG_PATH`: Path to WireGuard config file (optional, auto-detected if not set)
- `FOUNDRIES_VPN_CONFIG_PATH`: Path to Foundries VPN config file (optional, auto-detected if not set)
- `TARGET_NETWORK`: Target network for lab testing operations (default: `192.168.2.0/24`)
- `MCP_DEV_MODE`: Enable development mode with auto-reload (set to `1`, `true`, or `yes` to enable)

### Target Network Configuration

The target network determines which network is used for lab testing operations. It can be configured in three ways (priority order):

1. **Environment Variable**: Set `TARGET_NETWORK` environment variable
   ```bash
   export TARGET_NETWORK=192.168.2.0/24
   ```

2. **Config File**: Add to `lab_devices.json`:
   ```json
   {
     "lab_infrastructure": {
       "network_access": {
         "target_network": "192.168.2.0/24",
         "lab_networks": ["192.168.2.0/24"]
       }
     }
   }
   ```

3. **Default**: `192.168.2.0/24` (if not configured)

The `lab_networks` list can contain multiple networks for scanning, but `target_network` specifies the primary network for lab operations.

### VPN Configuration

The server automatically searches for WireGuard configs in:
1. `VPN_CONFIG_PATH` environment variable (if set)
2. `{LAB_TESTING_ROOT}/secrets/wg0.conf` (or `wireguard.conf`, `vpn.conf`)
3. `~/.config/wireguard/*.conf`
4. `/etc/wireguard/*.conf`

**No VPN?** See [VPN Setup Guide](VPN_SETUP.md) for setup instructions, or use the MCP tools:
- `vpn_setup_instructions` - Get setup help
- `create_vpn_config_template` - Create a config template
- `check_wireguard_installed` - Check if WireGuard is installed

**Foundries VPN?** See [Foundries VPN Setup Guide](FOUNDRIES_VPN_SETUP.md) for Foundries VPN setup. Foundries VPN configs are searched in:
1. `FOUNDRIES_VPN_CONFIG_PATH` environment variable (if set)
2. `{LAB_TESTING_ROOT}/secrets/foundries-vpn.conf` or `foundries.conf`
3. `~/.config/wireguard/foundries.conf`
4. `/etc/wireguard/foundries.conf`

## Cursor Integration

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "ai-lab-testing": {
      "command": "python3.10",
      "args": ["/absolute/path/to/lab_testing/server.py"],
      "env": {
        "LAB_TESTING_ROOT": "/data_drive/esl/ai-lab-testing",
        "MCP_DEV_MODE": "1"
      }
    }
  }
}
```

**Important:** Use `python3.10` (or `python3.11+`) since MCP SDK requires Python 3.10+.

Or use installed package: `"command": "python3.10", "args": ["-m", "lab_testing.server"]`

### Development Mode (Auto-Reload)

During development, you can enable auto-reload so that code changes are picked up automatically without restarting Cursor. This is especially useful when modifying tool handlers or network mapping code.

**To enable:** Add `"MCP_DEV_MODE": "1"` to the `env` section in your MCP configuration (as shown above).

**How it works:**
- The server checks for file changes before each tool call
- Modified Python modules are automatically reloaded using `importlib.reload()`
- No need to restart Cursor after making code changes
- Reloaded modules are logged for debugging

**Note:** Auto-reload only works for modules in the `lab_testing` package. Changes to `server.py` itself still require a restart.

Restart Cursor after initial setup.

### Tool Call Timeouts

**Note:** Some tools (like `create_network_map`) may take longer than 30 seconds if they perform network scans. Cursor has a default 30-second timeout for MCP tool calls.

**Solutions:**
1. **Use Quick Mode**: For `create_network_map`, set `quick_mode: true` to skip network scanning and only show configured devices (completes in <5 seconds).
2. **Optimized Scanning**: The network scanner has been optimized with faster ping timeouts (0.5s) and increased parallelism (100 workers) to reduce scan time.
3. **Client Timeout**: Currently, there's no way to configure the MCP client timeout in Cursor's `mcp.json`. The timeout is hardcoded in the Cursor client. If you need full network scans, consider running the tool directly via Python or use quick mode for faster results.

## Verification

```bash
python3 test_server.py
```

