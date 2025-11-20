# Foundries VPN Bootstrap Guide

**Purpose:** Guide for clean installation and bootstrap scenarios

## Bootstrap Problem

To connect to Foundries VPN, you need your client peer registered on the server. But to register your client peer, you need server access. This creates a chicken-and-egg problem for clean installations.

## Solution: Two-Phase Bootstrap

### Phase 1: First Admin (One-Time Setup)

The **first admin** needs initial server access to register themselves. This is a one-time setup.

**Options for First Admin:**

1. **Direct Server Access** (if available):
   ```bash
   # If you have console/physical access to Proxmox server
   ssh root@<server-local-ip>
   ```

2. **Public IP Access** (one-time only):
   ```bash
   # One-time access via public IP
   ssh root@proxmox.dynamicdevices.co.uk -p 5025
   ```

3. **Another Admin** (if available):
   - If another admin is already connected, they can register you via Foundries VPN

**First Admin Registration Steps:**

```bash
# On server (via one of the above methods)
# Generate your WireGuard keys first (on your local machine)
# wg genkey | tee privatekey | wg pubkey > publickey

# On server, add to client peer config file
echo "YOUR_PUBLIC_KEY 10.42.42.10 admin" >> /etc/wireguard/factory-clients.conf

# Apply client peer
wg set factory peer YOUR_PUBLIC_KEY allowed-ips 10.42.42.0/24
wg-quick save factory

# Verify
wg show factory | grep YOUR_PUBLIC_KEY
```

**First Admin Connects:**

```bash
# On local machine
connect_foundries_vpn()

# Verify
ping 10.42.42.1
```

### Phase 2: Subsequent Engineers (Via Foundries VPN)

Once the first admin is connected, **all subsequent client registrations** can be done via Foundries VPN.

**Admin Registers New Engineer:**

```python
# Admin (connected to Foundries VPN) registers new engineer
register_foundries_vpn_client(
    client_public_key="NEW_ENGINEER_PUBLIC_KEY",
    assigned_ip="10.42.42.11"
)
```

**Engineer Connects:**

```bash
# Engineer connects to Foundries VPN
connect_foundries_vpn()

# Verify
ping 10.42.42.1
```

## Complete Workflow

### For First Admin (Clean Installation)

1. **Generate WireGuard Keys:**
   ```bash
   wg genkey | tee ~/foundries_private.key | wg pubkey > ~/foundries_public.key
   cat ~/foundries_public.key  # Share this with server admin or use for self-registration
   ```

2. **Get Initial Server Access:**
   - Use public IP: `ssh root@proxmox.dynamicdevices.co.uk -p 5025`
   - Or direct access if available

3. **Register Client Peer:**
   ```bash
   # On server
   echo "YOUR_PUBLIC_KEY 10.42.42.10 admin" >> /etc/wireguard/factory-clients.conf
   wg set factory peer YOUR_PUBLIC_KEY allowed-ips 10.42.42.0/24
   wg-quick save factory
   ```

4. **Create Client Config:**
   ```bash
   # On local machine
   setup_foundries_vpn(auto_generate_config=True)
   # Edit config file with your private key and assigned IP
   ```

5. **Connect:**
   ```bash
   connect_foundries_vpn()
   ```

6. **Verify:**
   ```bash
   ping 10.42.42.1
   check_client_peer_registered()
   ```

### For Subsequent Engineers

1. **Generate WireGuard Keys:**
   ```bash
   wg genkey | tee ~/foundries_private.key | wg pubkey > ~/foundries_public.key
   ```

2. **Share Public Key with Admin:**
   - Email: ajlennon@dynamicdevices.co.uk
   - Or admin uses `register_foundries_vpn_client()` tool

3. **Admin Registers You:**
   - Admin (connected to Foundries VPN) runs registration tool
   - Or admin manually adds to `/etc/wireguard/factory-clients.conf` on server

4. **Create Client Config:**
   ```bash
   setup_foundries_vpn(auto_generate_config=True)
   # Edit config file with your private key and assigned IP
   ```

5. **Connect:**
   ```bash
   connect_foundries_vpn()
   ```

6. **Verify:**
   ```bash
   ping 10.42.42.1
   check_client_peer_registered()
   ```

## Server Access After Connection

Once connected to Foundries VPN, you can access the server at `10.42.42.1`:

```bash
# SSH to server (if SSH is configured on VPN interface)
ssh root@10.42.42.1 -p 5025

# Or use MCP tools that connect via Foundries VPN
register_foundries_vpn_client(...)  # Connects via 10.42.42.1
check_client_peer_registered(...)   # Connects via 10.42.42.1
```

## Key Points

✅ **First admin** needs initial server access (one-time only)  
✅ **Subsequent engineers** can be registered via Foundries VPN by admin  
✅ **All operations** after first admin connects are via Foundries VPN  
✅ **No public IP** needed after initial bootstrap  
✅ **Field devices** accessible via Foundries VPN (not hardware lab VPN)  
✅ **Server management** via Foundries VPN (`10.42.42.1`)

## Troubleshooting

**Cannot connect to Foundries VPN:**
- Check client peer is registered: `check_client_peer_registered()`
- Verify config file has correct private key and assigned IP
- Check VPN status: `foundries_vpn_status()`

**Client peer not registered:**
- Contact VPN admin: ajlennon@dynamicdevices.co.uk
- Or admin can register via Foundries VPN: `register_foundries_vpn_client()`

**Server not accessible via Foundries VPN:**
- Verify VPN is connected: `foundries_vpn_status()`
- Ping server: `ping 10.42.42.1`
- Check SSH is configured on VPN interface (may need server configuration)

