# Getting a New Target Board Directly Accessible

Quick guide to enable direct access to a new Foundries device via VPN.

## Prerequisites

- Foundries device is online and VPN enabled in FoundriesFactory
- VPN server access (SSH to `144.76.167.54:5025`)
- Your client VPN connection is active

## Steps

### 1. Verify Device Status

Check device is online and VPN enabled:
```bash
fioctl devices show <device-name>
```

Look for:
- `status: OK`
- `wireguard-client` section with VPN IP (e.g., `address=10.42.42.X`)

### 2. Register Your Client Peer (If Not Already Done)

If you can't ping the VPN server (`10.42.42.1`), register your client:

```bash
# Get your public key
cat ~/.config/wireguard/foundries.conf | grep PrivateKey | awk '{print $3}' | wg pubkey

# Register on server (replace with your public key and assigned IP)
ssh root@144.76.167.54 -p 5025
wg set factory peer <your-public-key> allowed-ips 10.42.42.10/32
echo "<your-public-key> 10.42.42.10 your-name" >> /etc/wireguard/factory-clients.conf
```

### 3. Enable Device-to-Device Communication

**Server-side:**
```bash
# Get device public key
fioctl devices show <device-name> | grep -A 5 wireguard | grep pubkey

# Set AllowedIPs to subnet on server
ssh root@144.76.167.54 -p 5025
wg set factory peer <device-public-key> allowed-ips 10.42.42.0/24
wg-quick save factory
```

**Device-side (temporary - until PR is deployed):**
```bash
# SSH to device via server
ssh root@144.76.167.54 -p 5025
ssh fio@<device-vpn-ip>

# Update AllowedIPs on device
sudo wg set factory-vpn0 peer <server-public-key> allowed-ips 10.42.42.0/24
```

**Note:** Device-side change is temporary. Once PR #18 is deployed with `--allow-device-to-device` flag, this will be persistent.

### 4. Verify Connectivity

```bash
# Ping device
ping -c 3 <device-vpn-ip>

# SSH to device
ssh fio@<device-vpn-ip>
```

## Using MCP Tools

Alternatively, use the MCP tools:

```bash
# Enable device-to-device (handles both server and device side)
enable_foundries_device_to_device(device_name="<device-name>", device_ip="<vpn-ip>")

# Test connectivity
test_device(device_id="<device-name>")
```

## Troubleshooting

**Can't ping VPN server:**
- Client peer not registered → Register client peer (Step 2)

**Can ping server but not device:**
- Server-side AllowedIPs not set → Set server AllowedIPs to subnet (Step 3)

**Device can't send packets:**
- Device-side AllowedIPs still `/32` → Update device AllowedIPs (Step 3)

**After device reboot:**
- Device-side AllowedIPs resets → Re-run device-side update (temporary until PR deployed)

## Future (After PR #18 Deployment)

Once `--allow-device-to-device` flag is deployed:
- Server-side AllowedIPs will be set automatically
- Device-side AllowedIPs will persist across reboots
- Only client peer registration needed for new users

---

*This document was created with the assistance of Cursor.AI for user @ajlennon.*

