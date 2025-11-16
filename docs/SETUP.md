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
- Device config: `/data_drive/esl/lab-testing/config/lab_devices.json`
- VPN config: `/data_drive/esl/lab-testing/secrets/wg0.conf`

Override: `export LAB_TESTING_ROOT=/path/to/lab-testing`

## Cursor Integration

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "lab-testing": {
      "command": "python3.10",
      "args": ["/absolute/path/to/mcp_remote_testing/server.py"],
      "env": {"LAB_TESTING_ROOT": "/data_drive/esl/lab-testing"}
    }
  }
}
```

**Important:** Use `python3.10` (or `python3.11+`) since MCP SDK requires Python 3.10+.

Or use installed package: `"command": "python3.10", "args": ["-m", "mcp_remote_testing.server"]`

Restart Cursor.

## Verification

```bash
python3 test_server.py
```

