# Foundries VPN Clean Installation Guide

**Date:** 2025-01-XX  
**Purpose:** Complete setup guide for a clean Foundries VPN installation with device-to-device communication enabled

## Quick Setup Checklist

**⚠️ CRITICAL STEPS FOR DEVICE-TO-DEVICE COMMUNICATION:**

1. ✅ **Server Setup:**
   - Install dependencies (wireguard, python3, sshpass)
   - Clone `factory-wireguard-server` repository (use fork with `--allow-device-to-device` support)
   - Generate WireGuard server keys
   - Configure OAuth2 credentials (`fiocreds.json`)
   - Enable VPN server in FoundriesFactory
   - **CRITICAL:** Start daemon with `--allow-device-to-device` flag
   - Configure IP forwarding and firewall

2. ✅ **Client Setup:**
   - Install `fioctl` and WireGuard tools
   - Configure `fioctl` (`fioctl login`)
   - Generate WireGuard client keys
   - Register client peer on server
   - Create client WireGuard config
   - Connect to VPN

3. ✅ **Device Setup:**
   - Enable VPN on device (`fioctl devices config wireguard <device> enable`)
   - Wait for OTA update (up to 5 minutes)
   - **CRITICAL:** Update device NetworkManager config (`allowed-ips=10.42.42.0/24`)
   - Reload NetworkManager connection

4. ✅ **Verification:**
   - Test VPN connectivity (ping server, ping devices)
   - Test device-to-device communication (ping between devices)
   - Verify server status

**⚠️ REMEMBER:** Device-to-device communication requires **BOTH**:
- Server-side: Daemon running with `--allow-device-to-device` flag
- Device-side: NetworkManager config updated to `allowed-ips=10.42.42.0/24`

## Overview

This guide documents the **critical learning** from successfully connecting to Foundries devices via VPN for the first time. It provides step-by-step instructions for setting up Foundries VPN on a clean installation, including enabling device-to-device communication.

## Critical Learning: Device-to-Device Communication

**Key Discovery:** Foundries devices, by default, configure WireGuard with restrictive `allowed-ips=10.42.42.1/32` (server IP only) in their NetworkManager configuration. This restrictive setting **syncs back to the server** when devices reconnect, overriding any server-side `AllowedIPs` settings.

**Impact:** Without proper configuration, devices can only communicate with the VPN server, not with each other or with client machines.

**Solution:** Both server-side and device-side configurations must be updated to enable device-to-device communication.

## Complete Setup Process

### Part 1: Server-Side Setup

#### 1.1 Install Dependencies

On the VPN server (Proxmox container or VM):

```bash
sudo apt update
sudo apt install git wireguard wireguard-tools python3 python3-requests iptables sshpass
```

**Note:** `sshpass` is required for the automated device-to-device setup tool.

#### 1.2 Clone VPN Server Repository

```bash
cd /root
git clone https://github.com/foundriesio/factory-wireguard-server.git
cd factory-wireguard-server
```

**For Development:** If you need device-to-device communication, use the fork with `--allow-device-to-device` support:

```bash
cd /root
git clone git@github.com:DynamicDevices/factory-wireguard-server.git
cd factory-wireguard-server
```

#### 1.3 Generate WireGuard Server Keys

```bash
# Generate private key
wg genkey | tee /root/wgpriv.key | wg pubkey > /root/wgpub.key

# Set secure permissions
chmod 600 /root/wgpriv.key
chmod 644 /root/wgpub.key
```

#### 1.4 Configure FoundriesFactory OAuth2 Credentials

**Option A: Using fioctl (Recommended)**

On a machine with `fioctl` installed:

```bash
# Login to FoundriesFactory
fioctl login

# Extract credentials
cat ~/.config/fioctl/credentials.json
```

**Option B: Manual OAuth2 Setup**

1. Go to FoundriesFactory web interface
2. Navigate to Settings → API Tokens
3. Create a new token with appropriate permissions
4. Convert to `fiocreds.json` format:

```json
{
  "access_token": "YOUR_ACCESS_TOKEN",
  "refresh_token": "YOUR_REFRESH_TOKEN",
  "expires_at": TIMESTAMP
}
```

Save to `/root/fiocreds.json` on the server:

```bash
chmod 600 /root/fiocreds.json
```

#### 1.5 Enable VPN Server in FoundriesFactory

```bash
cd /root/factory-wireguard-server

# Get server endpoint (replace with your server's public IP/hostname)
SERVER_ENDPOINT="proxmox.dynamicdevices.co.uk:5555"
SERVER_ADDRESS="10.42.42.1"

# Enable VPN server in factory
sudo ./factory-wireguard.py \
  --oauthcreds /root/fiocreds.json \
  --factory <your-factory-name> \
  --privatekey /root/wgpriv.key \
  enable \
  --endpoint $SERVER_ENDPOINT \
  --address $SERVER_ADDRESS
```

#### 1.6 Start VPN Server Daemon with Device-to-Device Support

**CRITICAL:** For development environments, start the daemon with `--allow-device-to-device` flag:

```bash
# Create systemd service file
sudo tee /etc/systemd/system/factory-vpn-<factory-name>.service << EOF
[Unit]
Description=Foundries WireGuard VPN Server Daemon
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /root/factory-wireguard-server/factory-wireguard.py \
  --oauthcreds /root/fiocreds.json \
  --factory <your-factory-name> \
  --privatekey /root/wgpriv.key \
  daemon \
  --allow-device-to-device \
  --interval 300
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl enable factory-vpn-<factory-name>.service
sudo systemctl start factory-vpn-<factory-name>.service

# Check status
sudo systemctl status factory-vpn-<factory-name>.service
```

**Key Configuration:**
- `--allow-device-to-device`: Enables device-to-device communication by setting `AllowedIPs = 10.42.42.0/24` for device peers
- `--interval 300`: How often to sync device settings (default: 300 seconds)

**Without `--allow-device-to-device`:** Devices will have restrictive `AllowedIPs = {device_ip}/32`, preventing device-to-device communication.

#### 1.7 Configure IP Forwarding and Firewall

```bash
# Enable IP forwarding
echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Configure firewall rules (for development - allows all VPN traffic)
sudo iptables -A FORWARD -i factory -j ACCEPT
sudo iptables -A FORWARD -o factory -j ACCEPT
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

# Save iptables rules (if using iptables-persistent)
sudo apt install iptables-persistent
sudo netfilter-persistent save
```

### Part 2: Client-Side Setup

#### 2.1 Install Prerequisites

**Install fioctl:**

```bash
# Using Go
go install github.com/foundriesio/fioctl@latest
export PATH=$PATH:$(go env GOPATH)/bin

# Or download pre-built binary
wget https://github.com/foundriesio/fioctl/releases/latest/download/fioctl-linux-amd64
chmod +x fioctl-linux-amd64
sudo mv fioctl-linux-amd64 /usr/local/bin/fioctl
```

**Install WireGuard:**

```bash
sudo apt install wireguard-tools network-manager network-manager-wireguard
```

#### 2.2 Configure fioctl

```bash
fioctl login
```

This will:
1. Open a browser for OAuth2 authentication
2. Store credentials securely
3. Configure default factory

**Verify:**

```bash
fioctl factories list
```

#### 2.3 Generate Client WireGuard Keys

```bash
# Generate key pair
wg genkey | tee ~/foundries_private.key | wg pubkey > ~/foundries_public.key

# View your public key (share this with VPN admin)
cat ~/foundries_public.key
```

**Example output:**
```
mzHaZPGowqqzAa5tVFQJs0zoWuDVLppt44HwgdcPXkg=
```

#### 2.4 Register Client Peer on Server

**CRITICAL STEP:** Your client must be added as a peer on the WireGuard server before connecting.

**Bootstrap Workflow (Clean Installation):**

**Important:** For clean installation, the **first admin** needs initial server access to register themselves. This can be:
- Direct server access (if you have physical/console access)
- Public IP access (one-time, for initial setup)
- Or another admin who is already connected can register you

**After First Admin Connects:** All subsequent client registrations can be done via Foundries VPN by the admin.

**Step 1: First Admin - Initial Registration**

If you're the first admin setting up the VPN:

```bash
# Option A: Direct server access (if available)
ssh root@<server-ip> -p 5025

# Option B: Public IP access (one-time only)
ssh root@proxmox.dynamicdevices.co.uk -p 5025

# On server, register yourself:
echo "YOUR_PUBLIC_KEY 10.42.42.10 admin" >> /etc/wireguard/factory-clients.conf
wg set factory peer YOUR_PUBLIC_KEY allowed-ips 10.42.42.0/24
wg-quick save factory
```

**Step 2: Connect to Foundries VPN**

After registration, connect:

```bash
connect_foundries_vpn()
```

**Step 3: Register Additional Clients (via Foundries VPN)**

Once connected, admin can register other engineers via Foundries VPN:

**Option A: Using MCP Tool (Recommended)**
```python
# Generate keys first if needed
# wg genkey | tee privatekey | wg pubkey > publickey

# Register client peer (connects via standard VPN if Foundries VPN not available)
register_foundries_vpn_client(
    client_public_key="mzHaZPGowqqzAa5tVFQJs0zoWuDVLppt44HwgdcPXkg=",
    assigned_ip="10.42.42.10"
)
```

**Option B: Manual Registration**
```bash
# On Proxmox server (accessed via standard VPN)
# Add to client peer config file (new method - Priority 2)
echo "mzHaZPGowqqzAa5tVFQJs0zoWuDVLppt44HwgdcPXkg= 10.42.42.10 ajlennon" >> /etc/wireguard/factory-clients.conf

# Apply client peers
wg-quick down factory && wg-quick up factory

# Or legacy method (still works):
wg set factory peer <CLIENT_PUBLIC_KEY> allowed-ips 10.42.42.0/24
wg-quick save factory
```

**All Future Access:** Via Foundries VPN only (`10.42.42.1`), no public IP needed!

**Note:** Once connected to Foundries VPN, you can:
- Access server: `ssh root@10.42.42.1 -p 5025` (if SSH is configured on VPN interface)
- Register new clients: Use `register_foundries_vpn_client()` tool
- Manage devices: All device operations via Foundries VPN

**Alternative: Contact VPN Administrator**
- Email: ajlennon@dynamicdevices.co.uk (Alex J Lennon)
- Provide your WireGuard public key
- Request an assigned IP address (e.g., `10.42.42.10`)

**Note:** With Priority 2 implementation, client peers are managed via `/etc/wireguard/factory-clients.conf` config file and persist across daemon restarts.

#### 2.5 Create Client WireGuard Configuration

**Get server configuration:**

```bash
# Using MCP tool (if available)
get_foundries_vpn_server_config()

# Or manually via fioctl
fioctl devices config wireguard show
```

**Create client config file:**

```bash
mkdir -p ~/.config/wireguard
cat > ~/.config/wireguard/foundries.conf << EOF
[Interface]
# Your private key (from step 2.3)
PrivateKey = YOUR_PRIVATE_KEY_HERE

# Your assigned IP address (from VPN admin)
Address = 10.42.42.10/32

[Peer]
# Server's public key (from get_foundries_vpn_server_config)
PublicKey = SERVER_PUBLIC_KEY_HERE

# Server endpoint
Endpoint = proxmox.dynamicdevices.co.uk:5555

# Allowed IPs (VPN network)
AllowedIPs = 10.42.42.0/24

# Keep connection alive
PersistentKeepalive = 25
EOF

chmod 600 ~/.config/wireguard/foundries.conf
```

**Replace:**
- `YOUR_PRIVATE_KEY_HERE` with your private key from `~/foundries_private.key`
- `SERVER_PUBLIC_KEY_HERE` with server's public key
- `10.42.42.10` with your assigned IP address

#### 2.6 Connect to VPN

**Using NetworkManager (Recommended):**

```bash
# Import config
nmcli connection import type wireguard file ~/.config/wireguard/foundries.conf

# Connect
nmcli connection up foundries

# Verify
nmcli connection show --active | grep wireguard
```

**Using wg-quick (Alternative):**

```bash
sudo wg-quick up ~/.config/wireguard/foundries.conf

# Verify
sudo wg show
```

**Using MCP Tools:**

```python
# Check status
foundries_vpn_status()

# Connect
connect_foundries_vpn()

# Verify
verify_foundries_vpn_connection()
```

### Part 3: Device Setup

#### 3.1 Enable VPN on Device

**Using fioctl:**

```bash
fioctl devices config wireguard <device-name> enable
```

**Using MCP Tools:**

```python
enable_foundries_vpn_device(device_name="imx8mm-jaguar-inst-2240a09dab86563")
```

**Wait for OTA Update:**
- Configuration changes are applied via OTA update
- May take up to 5 minutes
- Device will automatically connect to VPN server after update

#### 3.2 Verify Device Connection

**Check device is connected:**

```bash
# On VPN server
sudo wg show factory | grep -A 2 <device-pubkey>
```

**List devices:**

```python
# Using MCP tool
list_foundries_devices()
```

#### 3.3 Enable Device-to-Device Communication

**⚠️ CRITICAL STEP - REQUIRED FOR DEVICE-TO-DEVICE COMMUNICATION ⚠️**

**CRITICAL:** By default, Foundries devices configure WireGuard with restrictive `allowed-ips=10.42.42.1/32` (server IP only) in their NetworkManager configuration. This restrictive setting **MUST be updated on the device** to enable device-to-device communication. **This step is mandatory** - server-side configuration alone is not sufficient.

**Why This Step Is Critical:**
- Foundries devices receive their WireGuard configuration via OTA updates when VPN is enabled
- The default configuration restricts `allowed-ips` to the server IP only (`10.42.42.1/32`)
- This restrictive setting prevents devices from communicating with each other or client machines
- **Even if the server is configured with `--allow-device-to-device`, the device-side NetworkManager config must be updated manually**
- Without this step, device-to-device communication will not work

**Question for Foundries Team:** Is this default restrictive configuration (`allowed-ips=10.42.42.1/32`) sent by Foundries when VPN is enabled on a device? Is there a way to configure this via `fioctl` or OTA updates instead of requiring manual NetworkManager config changes?

**Automated Method (Using MCP Tool):**

```python
enable_foundries_device_to_device(
    device_name="imx8mm-jaguar-inst-2240a09dab86563",
    device_user="fio",
    device_password="fio"
)
```

**Manual Method:**

**Step 1: SSH to WireGuard Server**

```bash
ssh root@proxmox.dynamicdevices.co.uk -p 5025
```

**Step 2: SSH to Device from Server**

```bash
# Get device VPN IP from list_foundries_devices()
ssh fio@10.42.42.4
# Password: fio
```

**Step 3: Update Device NetworkManager Config**

```bash
# Edit NetworkManager config
sudo sed -i 's/allowed-ips=10.42.42.1/allowed-ips=10.42.42.0\/24/' \
  /etc/NetworkManager/system-connections/factory-vpn0.nmconnection

# Reload NetworkManager
sudo nmcli connection reload factory-vpn0
sudo nmcli connection down factory-vpn0
sleep 1
sudo nmcli connection up factory-vpn0

# Verify
sudo wg show factory-vpn0 | grep "allowed ips"
```

**Expected output:**
```
allowed ips: 10.42.42.0/24
```

**Step 4: Verify Server-Side AllowedIPs**

On the VPN server:

```bash
# Check device peer has correct AllowedIPs
sudo wg show factory | grep -A 2 <device-pubkey>
```

Should show:
```
allowed ips: 10.42.42.0/24
```

**Note:** If server daemon is running with `--allow-device-to-device`, it should automatically set this. However, if device reconnects with endpoint, WireGuard may clear `AllowedIPs`. The daemon's `apply_conf()` function handles this by removing peers, waiting, then reapplying config.

### Part 4: Verification and Testing

#### 4.1 Test VPN Connectivity

**From client machine:**

```bash
# Ping VPN server
ping -c 3 10.42.42.1

# Ping device
ping -c 3 10.42.42.4

# SSH to device
ssh fio@10.42.42.4
```

#### 4.2 Test Device-to-Device Communication

**From one device:**

```bash
# SSH to another device
ssh fio@10.42.42.2
```

#### 4.3 Verify Server Status

**On VPN server:**

```bash
# Check WireGuard status
sudo wg show factory

# Check daemon status
sudo systemctl status factory-vpn-<factory-name>.service

# Check daemon logs
sudo journalctl -u factory-vpn-<factory-name>.service -f
```

**Expected output:**

```
interface: factory
  public key: ...
  listening port: 5555

peer: <client-pubkey>
  endpoint: ...
  allowed ips: 10.42.42.0/24
  latest handshake: ...

peer: <device1-pubkey>
  endpoint: ...
  allowed ips: 10.42.42.0/24
  latest handshake: ...

peer: <device2-pubkey>
  endpoint: ...
  allowed ips: 10.42.42.0/24
  latest handshake: ...
```

## Troubleshooting

**For detailed troubleshooting guide, see:** `docs/FOUNDRIES_VPN_TROUBLESHOOTING.md`

### Common Issues

#### Daemon Parsing Error

**Symptom:** `syncconf failed, using wg-quick: Line unrecognized: 'Address=10.42.42.1'`

**Fix:** The daemon code has been updated to always use `wg-quick` instead of `wg syncconf`. Ensure you're using the latest `factory-wireguard.py` code.

#### Client Cannot Connect

**Symptom:** Client shows "activated" but cannot ping server (`10.42.42.1`)

**Common Causes:**
1. **Client peer not registered on server** (most common)
   - Check: `sudo wg show factory | grep <client-pubkey>`
   - Fix: Add client peer to server (see "Client Peer Registration" section above)
   
2. **Client peer `AllowedIPs` is `/32` instead of `/24`**
   - Check: `sudo wg show factory | grep -A 3 <client-pubkey>`
   - Fix: Update to `10.42.42.0/24` in both runtime and config file

3. **NetworkManager connection needs reimport**
   - Fix: `nmcli connection delete foundries && nmcli connection import type wireguard file ~/.config/wireguard/foundries.conf`

#### Device Not Connecting

1. **Check device VPN is enabled:**
   ```bash
   fioctl devices config wireguard <device-name> show
   ```

2. **Wait for OTA update** (up to 5 minutes)

3. **Check device logs:**
   ```bash
   ssh fio@<device-ip>
   sudo journalctl -u NetworkManager -f
   ```

#### Device-to-Device Not Working

1. **Check device NetworkManager config:**
   ```bash
   ssh fio@<device-ip>
   sudo cat /etc/NetworkManager/system-connections/factory-vpn0.nmconnection | grep allowed-ips
   ```
   Should show: `allowed-ips=10.42.42.0/24`

2. **Check server-side AllowedIPs:**
   ```bash
   sudo wg show factory | grep -A 2 <device-pubkey>
   ```
   Should show: `allowed ips: 10.42.42.0/24`

3. **Check server daemon is running with `--allow-device-to-device`:**
   ```bash
   sudo systemctl status factory-vpn-<factory-name>.service
   sudo cat /etc/systemd/system/factory-vpn-<factory-name>.service | grep allow-device-to-device
   ```

4. **Restart device WireGuard connection:**
   ```bash
   ssh fio@<device-ip>
   sudo nmcli connection down factory-vpn0
   sleep 2
   sudo nmcli connection up factory-vpn0
   ```

### Diagnostic Commands

**Server-side:**
```bash
# Check daemon status
sudo systemctl status factory-vpn-<factory-name>.service

# Check WireGuard peers
sudo wg show factory

# Check config file
sudo cat /etc/wireguard/factory.conf

# Check daemon logs
sudo journalctl -u factory-vpn-<factory-name>.service -n 50 --no-pager
```

**Client-side:**
```bash
# Check VPN connection
nmcli connection show foundries

# Test connectivity
ping -c 3 10.42.42.1

# Check routes
ip route | grep 10.42.42
```

## Summary

**Critical Steps for Clean Installation:**

1. ✅ **Server Setup:**
   - Install dependencies (including `sshpass`)
   - Clone `factory-wireguard-server` repository
   - Generate WireGuard keys
   - Configure OAuth2 credentials
   - Enable VPN server in FoundriesFactory
   - **Start daemon with `--allow-device-to-device` flag**

2. ✅ **Client Setup:**
   - Install `fioctl` and WireGuard tools
   - Configure `fioctl` with `fioctl login`
   - Generate WireGuard key pair
   - **Register client peer on server (requires admin)**
   - Create client WireGuard config
   - Connect to VPN

3. ✅ **Device Setup:**
   - Enable VPN on device via `fioctl`
   - Wait for OTA update (up to 5 minutes)
   - **Enable device-to-device communication** (update NetworkManager config)

4. ✅ **Verification:**
   - Test VPN connectivity
   - Test device-to-device communication
   - Verify server status

**Key Learning:** Device-to-device communication requires **both** server-side (`--allow-device-to-device` daemon flag) and device-side (NetworkManager config update) configuration changes.

## Contact

For assistance with Foundries VPN setup:
- **Email:** ajlennon@dynamicdevices.co.uk (Alex J Lennon)
- **Purpose:** Client peer registration, server configuration, troubleshooting

