# Foundries VPN Client Setup Guide

**Complete guide for connecting your local system to the Foundries WireGuard VPN server for remote device development.**

## Overview

Foundries VPN uses a **server-based WireGuard architecture** where:
- **VPN Server:** `proxmox.dynamicdevices.co.uk` (144.76.167.54:5555)
- **VPN Network:** `10.42.42.0/24` (server is `10.42.42.1`)
- **Your devices** connect to the VPN server
- **Your local machine** connects to the same VPN server
- **Result:** You can access devices remotely via the VPN network

## Prerequisites

1. **WireGuard tools installed** on your local system
2. **fioctl CLI tool** installed and configured (for getting VPN config)
3. **Access to FoundriesFactory** (to obtain client configuration)

## Step-by-Step Setup

### Step 1: Verify VPN Server Configuration

First, check that the VPN server is configured and enabled:

```bash
# Using MCP tool (if available)
get_foundries_vpn_server_config()

# Or using fioctl directly
fioctl config wireguard show
```

**Expected Output:**
```
Enabled: true
Endpoint: 144.76.167.54:5555
Address: 10.42.42.1
Public Key: 9mOJNp50tokYgKVHK5FQgwlFGM8asm11oHdoWlEvkxI=
```

### Step 2: Obtain Client Configuration File

You need a WireGuard client configuration file. This contains:
- Your private key (unique to you)
- Your assigned VPN IP address
- Server public key and endpoint
- Network routes

**Option A: FoundriesFactory Web Interface (Recommended)**

1. Log in to [FoundriesFactory](https://app.foundries.io)
2. Navigate to your factory (e.g., `dynamic-devices`)
3. Go to **Settings** → **Remote Access** or **VPN**
4. Download or generate your WireGuard client configuration file
5. Save it as `foundries.conf` or `foundries-vpn.conf`

**Option B: Contact VPN Administrator**

Contact your Foundries VPN server administrator to obtain:
- A WireGuard client configuration file, OR
- Your assigned VPN IP address and private key

**Option C: Generate Your Own Config (if you have server details)**

If you have the server information, you can create your own config:

```bash
# Generate your private/public key pair
wg genkey | tee /tmp/privatekey | wg pubkey > /tmp/publickey

# View your public key (share this with VPN admin to get assigned IP)
cat /tmp/publickey
```

Then create `~/.config/wireguard/foundries.conf`:

```ini
[Interface]
# Your private key (from wg genkey)
PrivateKey = YOUR_PRIVATE_KEY_HERE

# Your assigned VPN IP address (get from VPN admin)
Address = 10.42.42.X/24

# Optional: DNS servers
DNS = 8.8.8.8, 8.8.4.4

[Peer]
# Server's public key (from get_foundries_vpn_server_config)
PublicKey = 9mOJNp50tokYgKVHK5FQgwlFGM8asm11oHdoWlEvkxI=

# Server endpoint (proxmox.dynamicdevices.co.uk)
Endpoint = 144.76.167.54:5555

# Allowed IPs - routes to send through VPN
# Use specific subnets for lab network access only
AllowedIPs = 10.42.42.0/24, 192.168.2.0/24

# Keep connection alive
PersistentKeepalive = 25
```

**Important:** Replace:
- `YOUR_PRIVATE_KEY_HERE` with your generated private key
- `10.42.42.X/24` with your assigned VPN IP address (get from VPN admin)
- Adjust `AllowedIPs` to match your lab network subnets

### Step 3: Save Configuration File

Save the WireGuard config file in one of these locations (searched in order):

1. **Recommended:** `~/.config/wireguard/foundries.conf`
2. **Alternative:** `{LAB_TESTING_ROOT}/secrets/foundries-vpn.conf`
3. **Alternative:** `{LAB_TESTING_ROOT}/secrets/foundries.conf`
4. **System-wide:** `/etc/wireguard/foundries.conf` (requires root)

**Set Secure Permissions:**
```bash
chmod 600 ~/.config/wireguard/foundries.conf
```

**Or use environment variable:**
```bash
export FOUNDRIES_VPN_CONFIG_PATH=/path/to/your/foundries.conf
```

### Step 4: Connect to VPN

**Method 1: Using MCP Tools (Recommended)**

```python
# Check VPN status
foundries_vpn_status()

# Connect to VPN (auto-detects config)
connect_foundries_vpn()

# Or specify config path
connect_foundries_vpn(config_path="/path/to/foundries.conf")
```

**Method 2: Using NetworkManager (No Root Required)**

```bash
# Import config into NetworkManager
nmcli connection import type wireguard file ~/.config/wireguard/foundries.conf

# Connect
nmcli connection up foundries

# Check status
nmcli connection show foundries
```

**Method 3: Using wg-quick (Requires Root)**

```bash
# Connect
sudo wg-quick up ~/.config/wireguard/foundries.conf

# Check status
sudo wg show

# Disconnect
sudo wg-quick down foundries
```

### Step 5: Verify Connection

**Check VPN Status:**

```bash
# Using MCP tool
foundries_vpn_status()

# Or manually
wg show
nmcli connection show --active | grep wireguard
ip addr show wg0  # or your interface name
```

**Test Connectivity:**

```bash
# Ping VPN server
ping 10.42.42.1

# Check routing
ip route | grep 10.42.42

# Test device access (if devices are on VPN)
ping 192.168.2.18  # Example device IP
```

### Step 6: Access Devices for Remote Development

Once connected to the VPN, you can:

1. **List Foundries devices:**
   ```python
   list_foundries_devices()
   ```

2. **SSH to devices:**
   ```python
   ssh_to_device("device_id", "uptime")
   ```

3. **Test device connectivity:**
   ```python
   test_device("device_id")
   ```

4. **Copy files to devices:**
   ```python
   copy_file_to_device("device_id", "/local/path", "/remote/path")
   copy_files_to_device_parallel("device_id", [["/local/file1", "/remote/file1"], ...])
   ```

5. **Run remote commands:**
   ```python
   ssh_to_device("device_id", "ls -la /tmp")
   ```

## Complete Workflow Example

```python
# 1. Check VPN server status
get_foundries_vpn_server_config()
# Returns: endpoint, address, public_key

# 2. Connect to VPN
connect_foundries_vpn()
# Auto-detects config file and connects

# 3. List available devices
list_foundries_devices()
# Shows all Foundries devices

# 4. Test device connectivity
test_device("imx8mm-jaguar-sentai-2d0e0a09dab86563")

# 5. Set up SSH access
install_ssh_key("device_id")
enable_passwordless_sudo("device_id")

# 6. Deploy application
copy_files_to_device_parallel("device_id", [
    ["/local/app", "/usr/local/bin/app"],
    ["/local/config.json", "/etc/app/config.json"]
])

# 7. Run application
ssh_to_device("device_id", "systemctl start app")

# 8. When done, clean up
disable_passwordless_sudo("device_id")
# Optionally disconnect VPN
disconnect_vpn()
```

## Troubleshooting

### VPN Won't Connect

**Check:**
1. Config file exists and has correct permissions (`chmod 600`)
2. WireGuard tools installed: `which wg`
3. Server is accessible: `ping 144.76.167.54`
4. Port 5555 is not blocked by firewall
5. Config file format is correct (check for typos)

**Common Issues:**

- **"Permission denied"** → Use NetworkManager instead of wg-quick, or use sudo
- **"Connection timeout"** → Check firewall, verify server endpoint
- **"Invalid key"** → Regenerate keys and update config
- **"Address already in use"** → Another VPN connection active, disconnect first

### Can't Access Devices

**Check:**
1. VPN is connected: `wg show` or `foundries_vpn_status()`
2. Devices are on VPN: `list_foundries_devices()` shows devices
3. Devices have WireGuard enabled: `enable_foundries_vpn_device(device_name)`
4. Routing is correct: `ip route | grep 192.168.2`
5. Firewall allows traffic: Check iptables/firewalld rules

### Config File Not Found

**Solutions:**
1. Place config in one of the standard locations (see Step 3)
2. Set `FOUNDRIES_VPN_CONFIG_PATH` environment variable
3. Provide `config_path` parameter to `connect_foundries_vpn()`

## Architecture Diagram

```
┌─────────────────┐
│  Your Local     │
│  Machine        │
│  (VPN Client)   │
└────────┬────────┘
         │ WireGuard
         │ (10.42.42.X)
         │
         ▼
┌─────────────────────────┐
│  Foundries VPN Server   │
│  proxmox.dynamicdevices │
│  .co.uk:5555            │
│  (10.42.42.1)           │
└────────┬────────────────┘
         │ WireGuard
         │ (10.42.42.Y)
         │
    ┌────┴────┬──────────┬──────────┐
    │         │          │          │
    ▼         ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│Device 1│ │Device 2│ │Device 3│ │Device 4│
│192.168.│ │192.168.│ │192.168.│ │192.168.│
│  2.18  │ │  2.22  │ │  2.132 │ │  2.115 │
└────────┘ └────────┘ └────────┘ └────────┘
```

**Key Points:**
- All devices connect to the same VPN server
- Your local machine connects to the same server
- VPN server routes traffic between clients and devices
- Devices are accessible via their lab network IPs (192.168.2.X)

## Security Best Practices

1. **Keep private keys secure:**
   - Never commit private keys to git
   - Use `chmod 600` on config files
   - Store configs in `~/.config/wireguard/` (user-specific)

2. **Use specific AllowedIPs:**
   - Don't use `0.0.0.0/0` (routes all traffic through VPN)
   - Use specific subnets: `10.42.42.0/24, 192.168.2.0/24`
   - This prevents routing all internet traffic through VPN

3. **Disconnect when not needed:**
   - Use `disconnect_vpn()` when finished
   - Prevents accidental traffic routing

4. **Rotate keys periodically:**
   - Generate new keys and update config
   - Remove old keys from server

## Next Steps

Once VPN is connected:

1. ✅ **Enable VPN on devices:** `enable_foundries_vpn_device(device_name)`
2. ✅ **Set up SSH access:** `install_ssh_key(device_id)`
3. ✅ **Enable passwordless sudo:** `enable_passwordless_sudo(device_id)` (for testing)
4. ✅ **Deploy applications:** `copy_files_to_device_parallel(device_id, file_pairs)`
5. ✅ **Run tests:** `ssh_to_device(device_id, "your-test-command")`
6. ✅ **Clean up:** `disable_passwordless_sudo(device_id)` when done

## Additional Resources

- **Foundries VPN Documentation:** https://docs.foundries.io/latest/reference-manual/remote-access/wireguard.html
- **WireGuard Documentation:** https://www.wireguard.com/
- **fioctl Documentation:** https://docs.foundries.io/latest/reference-manual/fioctl/
- **MCP Remote Development Guide:** [docs/REMOTE_DEVELOPMENT_GUIDE.md](REMOTE_DEVELOPMENT_GUIDE.md)

