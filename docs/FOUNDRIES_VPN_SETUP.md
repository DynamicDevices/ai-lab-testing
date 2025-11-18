# Foundries VPN Setup Guide

This guide helps you set up Foundries VPN for use with the MCP Remote Testing server.

## Overview

Foundries VPN uses WireGuard but with a **server-based architecture** where devices connect to a centralized VPN server managed by FoundriesFactory. This is different from standard WireGuard (peer-to-peer).

**Key Differences:**
- **Standard WireGuard**: Direct peer-to-peer connections
- **Foundries VPN**: Server-based (devices → VPN Server → Client)

## Prerequisites

### 1. Install fioctl CLI Tool

**fioctl** is the Foundries.io command-line tool for managing FoundriesFactory.

**Installation:**

**Linux (using Go):**
```bash
# Install Go if not already installed
sudo apt install golang-go  # Debian/Ubuntu
# or
sudo yum install golang  # RHEL/CentOS

# Install fioctl
go install github.com/foundriesio/fioctl@latest

# Add Go bin to PATH (if not already)
export PATH=$PATH:$(go env GOPATH)/bin
echo 'export PATH=$PATH:$(go env GOPATH)/bin' >> ~/.bashrc
```

**Linux (using pre-built binary):**
```bash
# Download latest release from GitHub
wget https://github.com/foundriesio/fioctl/releases/latest/download/fioctl-linux-amd64
chmod +x fioctl-linux-amd64
sudo mv fioctl-linux-amd64 /usr/local/bin/fioctl
```

**macOS:**
```bash
brew install fioctl
```

**Windows:**
Download from: https://github.com/foundriesio/fioctl/releases

**Verify Installation:**
```bash
fioctl --version
```

### 2. Configure fioctl with FoundriesFactory Credentials

After installing fioctl, configure it with your FoundriesFactory credentials:

```bash
fioctl login
```

This will:
1. Open a browser for OAuth2 authentication
2. Store credentials securely
3. Configure default factory (if you have access to multiple factories)

**Verify Configuration:**
```bash
fioctl factories list
```

If configured correctly, this will list your accessible factories.

### 3. Install WireGuard Tools

Foundries VPN still uses WireGuard, so you need WireGuard tools installed:

**Debian/Ubuntu:**
```bash
sudo apt update
sudo apt install wireguard-tools
```

**RHEL/CentOS:**
```bash
sudo yum install wireguard-tools
```

**Arch Linux:**
```bash
sudo pacman -S wireguard-tools
```

**macOS:**
```bash
brew install wireguard-tools
```

## Foundries VPN Setup

### Step 1: Enable WireGuard on Devices

Use fioctl to enable WireGuard VPN on your Foundries devices:

```bash
fioctl devices config wireguard <device-name> enable
```

**Example:**
```bash
fioctl devices config wireguard my-device-01 enable
```

**Note:** Configuration changes are applied via OTA update, which may take up to 5 minutes.

### Step 2: Obtain VPN Configuration

Get the WireGuard configuration file from FoundriesFactory:

**Option A: FoundriesFactory Web Interface**
1. Log in to FoundriesFactory
2. Navigate to Remote Access / VPN section
3. Download WireGuard configuration file

**Option B: FoundriesFactory API**
Use the FoundriesFactory API to retrieve VPN configuration.

**Option C: VPN Server Admin**
Contact your Foundries VPN server administrator for the configuration file.

### Step 3: Save VPN Configuration

The MCP server automatically searches for Foundries VPN config files in this order:

1. **Environment Variable:** `FOUNDRIES_VPN_CONFIG_PATH` (if set)
2. **Secrets Directory:** `{LAB_TESTING_ROOT}/secrets/foundries-vpn.conf` or `foundries.conf`
3. **User Config:** `~/.config/wireguard/foundries.conf`
4. **System Config:** `/etc/wireguard/foundries.conf`

**Recommended Locations:**
- `~/.config/wireguard/foundries.conf` (user-specific)
- `{LAB_TESTING_ROOT}/secrets/foundries-vpn.conf` (project-specific)

**Set Secure Permissions:**
```bash
chmod 600 ~/.config/wireguard/foundries.conf
```

**Using Environment Variable:**
```bash
export FOUNDRIES_VPN_CONFIG_PATH=/path/to/your/foundries.conf
```

Or in Cursor MCP config:
```json
{
  "mcpServers": {
    "ai-lab-testing": {
      "command": "python3.10",
      "args": ["/path/to/lab_testing/server.py"],
      "env": {
        "LAB_TESTING_ROOT": "/path/to/ai-lab-testing",
        "FOUNDRIES_VPN_CONFIG_PATH": "/path/to/foundries.conf"
      }
    }
  }
}
```

### Step 4: Connect to Foundries VPN

**Using MCP Tools (Recommended):**
```python
# Check VPN status
foundries_vpn_status()

# Connect to VPN (auto-detects config)
connect_foundries_vpn()

# Or specify config path
connect_foundries_vpn(config_path="/path/to/foundries.conf")
```

**Using NetworkManager (No Root Required):**
```bash
# Import config
nmcli connection import type wireguard file ~/.config/wireguard/foundries.conf

# Connect
nmcli connection up foundries
```

**Using wg-quick (Requires Root):**
```bash
sudo wg-quick up ~/.config/wireguard/foundries.conf
```

### Step 5: Verify Connection

**Check VPN Status:**
```bash
# Using MCP tool
foundries_vpn_status()

# Or manually
wg show
nmcli connection show --active | grep wireguard
```

**List Foundries Devices:**
```python
# Using MCP tool
list_foundries_devices()
```

**Access Devices:**
Once connected, devices should be accessible via the Foundries VPN server:
```bash
ssh <device-name>
```

## Using MCP Tools

The MCP server provides tools to manage Foundries VPN:

### 1. Check VPN Status
```python
foundries_vpn_status()
```
- Checks if fioctl is installed and configured
- Checks WireGuard connection status
- Provides helpful suggestions if prerequisites are missing

### 2. List Foundries Devices
```python
list_foundries_devices()
# Or with specific factory
list_foundries_devices(factory="my-factory")
```
- Lists devices in FoundriesFactory
- Shows devices with WireGuard enabled

### 3. Enable VPN on Device
```python
enable_foundries_vpn_device(device_name="my-device")
# Or with specific factory
enable_foundries_vpn_device(device_name="my-device", factory="my-factory")
```
- Enables WireGuard VPN on a device
- Configuration applied via OTA update (up to 5 minutes)

### 4. Disable VPN on Device
```python
disable_foundries_vpn_device(device_name="my-device")
```
- Disables WireGuard VPN on a device
- Configuration applied via OTA update (up to 5 minutes)

### 5. Connect to VPN
```python
connect_foundries_vpn()
# Or with specific config path
connect_foundries_vpn(config_path="/path/to/foundries.conf")
```
- Connects to Foundries VPN server
- Auto-detects config file if not specified

## Troubleshooting

### fioctl Not Found

**Error:** `fioctl not found in PATH`

**Solution:**
1. Install fioctl (see Installation section above)
2. Verify installation: `fioctl --version`
3. Ensure fioctl is in your PATH

### fioctl Not Configured

**Error:** `fioctl not configured. Run 'fioctl login'`

**Solution:**
1. Run `fioctl login` to configure credentials
2. Verify: `fioctl factories list`
3. Ensure you have access to FoundriesFactory

### VPN Config Not Found

**Error:** `Foundries VPN configuration file not found`

**Solution:**
1. Obtain WireGuard config from FoundriesFactory
2. Save config to one of these locations (searched in order):
   - Set `FOUNDRIES_VPN_CONFIG_PATH` environment variable
   - `{LAB_TESTING_ROOT}/secrets/foundries-vpn.conf` or `foundries.conf`
   - `~/.config/wireguard/foundries.conf`
   - `/etc/wireguard/foundries.conf`
3. Or provide `config_path` parameter to `connect_foundries_vpn()`
4. Verify config file exists and has correct permissions (`chmod 600`)

### Device Not Found

**Error:** `Failed to enable WireGuard VPN on device 'device-name'`

**Solution:**
1. Verify device name: `list_foundries_devices()`
2. Check device exists in factory
3. Ensure you have permissions to configure devices

### VPN Connection Fails

**Error:** `Failed to connect to Foundries VPN`

**Solution:**
1. Check VPN config file is valid
2. Verify VPN server is accessible
3. Check WireGuard tools are installed
4. Try NetworkManager method if wg-quick fails

## Differences from Standard WireGuard

| Aspect | Standard WireGuard | Foundries VPN |
|--------|-------------------|--------------|
| **Architecture** | Peer-to-peer | Server-based |
| **Configuration** | Manual config files | Managed via FoundriesFactory |
| **Device Management** | Manual peer management | Automated via `fioctl` |
| **Connection Model** | Direct device-to-device | Device → VPN Server → Client |

## Best Practices

1. **Use fioctl for Device Management**
   - Enable/disable VPN on devices via `fioctl devices config wireguard`
   - List devices via `fioctl devices list`

2. **Use MCP Tools for VPN Connection**
   - Check status before connecting
   - Auto-detect config files
   - Get helpful error messages and suggestions

3. **Wait for OTA Updates**
   - Device VPN configuration changes take up to 5 minutes
   - Check device status after enabling VPN

4. **Secure Configuration Files**
   - Set permissions: `chmod 600` on VPN config files
   - Store configs in secure locations

5. **Use NetworkManager When Possible**
   - Allows connecting without root privileges
   - Better integration with system networking

## Additional Resources

- **fioctl Documentation:** https://docs.foundries.io/latest/reference-manual/fioctl/
- **Foundries VPN Documentation:** https://docs.foundries.io/latest/reference-manual/remote-access/wireguard.html
- **fioctl GitHub:** https://github.com/foundriesio/fioctl
- **Foundries VPN Server:** https://github.com/foundriesio/factory-wireguard-server

## Summary

Foundries VPN setup requires:
1. ✅ Install `fioctl` CLI tool
2. ✅ Configure `fioctl` with `fioctl login`
3. ✅ Install WireGuard tools
4. ✅ Enable VPN on devices via `fioctl`
5. ✅ Obtain VPN config from FoundriesFactory
6. ✅ Connect using MCP tools or manual methods

The MCP server provides tools to simplify this process and guide you through each step.

