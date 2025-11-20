# Foundries VPN Troubleshooting Guide

**Last Updated:** 2025-11-20  
**Purpose:** Document common issues, root causes, and fixes for Foundries VPN setup

## Critical Issues and Fixes

### Issue 1: Daemon Parsing Error - "Line unrecognized: `Address=10.42.42.1'"

**Symptoms:**
- Daemon logs show: `syncconf failed, using wg-quick: Line unrecognized: 'Address=10.42.42.1'`
- Service may fail to start or restart repeatedly
- WireGuard interface may not come up properly

**Root Cause:**
The `factory-wireguard-server` daemon was attempting to use `wg syncconf` to apply configuration changes without bringing the interface down. However, `wg syncconf` only supports pure WireGuard directives (like `PrivateKey`, `PublicKey`, `AllowedIPs`), not `wg-quick` extensions (like `Address`, `PostUp`, `PostDown`).

**Fix:**
Updated `apply_conf()` method in `factory-wireguard.py` to:
1. Check if interface exists using `ip link show`
2. Always use `wg-quick down` and `wg-quick up` for configs with `wg-quick` directives
3. Remove the `wg syncconf` attempt entirely

**Code Changes:**
```python
# OLD (broken):
result = subprocess.run(
    ["wg", "syncconf", intf_name, "/etc/wireguard/%s.conf" % intf_name],
    ...
)
if result.returncode != 0:
    # Fall back to wg-quick
    ...

# NEW (fixed):
interface_exists = False
try:
    result = subprocess.run(
        ["ip", "link", "show", intf_name],
        ...
    )
    interface_exists = result.returncode == 0
except Exception:
    pass

if interface_exists:
    subprocess.check_call(["wg-quick", "down", intf_name], timeout=10)
    subprocess.check_call(["wg-quick", "up", intf_name], timeout=10)
else:
    subprocess.check_call(["wg-quick", "up", intf_name], timeout=10)
```

**Prevention:**
- Always use `wg-quick` for configs containing `wg-quick` directives
- Never mix `wg syncconf` with `wg-quick` config files
- Test daemon startup after code changes

---

### Issue 2: Client Cannot Connect - "100% packet loss" When Pinging Server

**Symptoms:**
- Client VPN connection shows as "activated" in NetworkManager
- `ping 10.42.42.1` fails with 100% packet loss
- WireGuard handshake may or may not be established
- Server can ping client, but client cannot ping server

**Root Cause:**
The client peer was not configured on the WireGuard server. Client peers are **NOT** automatically managed by the `factory-wireguard-server` daemon (only device peers are). The client peer must be manually added to the server configuration.

**Diagnosis:**
```bash
# On server - check if client peer exists
sudo wg show factory | grep <CLIENT_PUBLIC_KEY>

# If no output, client peer is missing
# Check config file
sudo grep <CLIENT_PUBLIC_KEY> /etc/wireguard/factory.conf
```

**Fix:**

**Step 1: Add Client Peer to Runtime**
```bash
# On VPN server
sudo wg set factory peer <CLIENT_PUBLIC_KEY> allowed-ips 10.42.42.0/24

# Verify
sudo wg show factory | grep -A 3 <CLIENT_PUBLIC_KEY>
```

**Step 2: Add Client Peer to Config File**
```bash
# On VPN server
sudo cat >> /etc/wireguard/factory.conf << EOF

# Client peer (username)
[Peer]
PublicKey = <CLIENT_PUBLIC_KEY>
AllowedIPs = 10.42.42.0/24
EOF

# Save configuration
sudo wg-quick save factory
```

**Step 3: Verify Client Connection**
```bash
# On client machine
ping -c 3 10.42.42.1

# Should see successful pings
```

**Important Notes:**
- Client peers persist across daemon restarts once added to config file
- Use `AllowedIPs = 10.42.42.0/24` (subnet) not `/32` (single IP) for device-to-device communication
- Client peer registration requires server administrator access
- Contact: ajlennon@dynamicdevices.co.uk for client peer registration

**Prevention:**
- Document client peer registration as a critical step in setup documentation
- Create automated tooling for client peer registration (future enhancement)
- Add client peer to config file immediately after runtime addition

---

### Issue 3: Client Connection Not Working After Server Fix

**Symptoms:**
- Server is correctly configured with client peer
- Server shows active handshake with client
- Client still cannot ping server
- NetworkManager shows connection as "activated"

**Root Cause:**
NetworkManager connection may have been created before the server was properly configured, or the connection configuration may be stale. NetworkManager needs to reimport the connection from the config file to pick up changes.

**Fix:**

**Step 1: Delete Existing Connection**
```bash
# On client machine
nmcli connection delete foundries
```

**Step 2: Reimport Connection**
```bash
# Import from config file
nmcli connection import type wireguard file ~/.config/wireguard/foundries.conf

# Connect
nmcli connection up foundries

# Verify
ping -c 3 10.42.42.1
```

**Alternative: Restart Connection**
```bash
nmcli connection down foundries
sleep 2
nmcli connection up foundries
```

**Prevention:**
- Always reimport NetworkManager connection after server configuration changes
- Verify connectivity immediately after connection import
- Document NetworkManager reimport as part of troubleshooting steps

---

## Common Issues

### Issue 4: Device Peers Have `allowed ips: (none)` After Daemon Restart

**Symptoms:**
- `wg show factory` shows device peers with `allowed ips: (none)`
- Devices cannot communicate with each other or with client
- Daemon logs show no errors

**Root Cause:**
WireGuard clears `AllowedIPs` when peers reconnect with active endpoints. The daemon's `apply_conf()` function needs to handle this by removing peers, waiting, then reapplying config.

**Fix:**
Ensure daemon is running with `--allow-device-to-device` flag and that `apply_conf()` properly removes peers before applying config:

```bash
# Check daemon is running with correct flag
sudo systemctl status factory-vpn-<factory-name>.service | grep allow-device-to-device

# Restart daemon if needed
sudo systemctl restart factory-vpn-<factory-name>.service
```

**Prevention:**
- Always start daemon with `--allow-device-to-device` flag for development environments
- Monitor daemon logs for `AllowedIPs` clearing issues
- Use `wg show factory` regularly to verify peer configuration

---

### Issue 5: Client Peer AllowedIPs Reverts to `/32` After Daemon Restart

**Symptoms:**
- Client peer `AllowedIPs` changes from `10.42.42.0/24` to `10.42.42.10/32`
- Client can ping server but not devices
- Config file shows correct `AllowedIPs = 10.42.42.0/24`

**Root Cause:**
The daemon may be overwriting the client peer configuration, or `wg-quick save` is not preserving the client peer correctly.

**Fix:**
1. Verify client peer is in config file:
   ```bash
   sudo grep -A 3 <CLIENT_PUBLIC_KEY> /etc/wireguard/factory.conf
   ```

2. Ensure config file has correct `AllowedIPs`:
   ```bash
   sudo sed -i 's|AllowedIPs = 10.42.42.10/32|AllowedIPs = 10.42.42.0/24|' /etc/wireguard/factory.conf
   ```

3. Restart WireGuard interface:
   ```bash
   sudo wg-quick down factory
   sudo wg-quick up factory
   ```

4. Verify:
   ```bash
   sudo wg show factory | grep -A 3 <CLIENT_PUBLIC_KEY>
   ```

**Prevention:**
- Always update config file, not just runtime, when changing client peer `AllowedIPs`
- Use `wg-quick save factory` after making runtime changes
- Document that client peers are NOT managed by daemon (they persist manually)

---

### Issue 6: Missing `--allow-device-to-device` Argument Error

**Symptoms:**
- Daemon fails to start with: `error: unrecognized arguments: --allow-device-to-device`
- Service status shows: `Failed with result 'exit-code'`

**Root Cause:**
The `--allow-device-to-device` argument was not added to the daemon subparser in `factory-wireguard.py`.

**Fix:**
Add argument to daemon subparser:

```python
p = sub.add_parser("daemon", help="Keep wireguard server in sync with Factory devices")
p.set_defaults(func=daemon)
p.add_argument("--interval", "-i", type=int, default=300, ...)
p.add_argument(
    "--allow-device-to-device",
    action="store_true",
    help="Allow device-to-device communication by setting AllowedIPs to subnet (10.42.42.0/24) instead of individual device IPs",
)
```

**Prevention:**
- Always add new arguments to the correct subparser
- Test daemon startup after adding new arguments
- Verify argument parsing with `--help` flag

---

## Diagnostic Commands

### Server-Side Diagnostics

```bash
# Check daemon status
sudo systemctl status factory-vpn-<factory-name>.service

# Check WireGuard interface status
sudo wg show factory

# Check config file
sudo cat /etc/wireguard/factory.conf

# Check daemon logs
sudo journalctl -u factory-vpn-<factory-name>.service -n 50 --no-pager

# Check IP forwarding
sysctl net.ipv4.ip_forward

# Check firewall rules
sudo iptables -L -n | grep factory

# Check routes
ip route | grep 10.42.42
```

### Client-Side Diagnostics

```bash
# Check VPN connection status
nmcli connection show foundries

# Check WireGuard status (requires sudo)
sudo wg show foundries

# Check routes
ip route | grep 10.42.42

# Test connectivity
ping -c 3 10.42.42.1

# Check NetworkManager logs
journalctl -u NetworkManager -n 50 --no-pager | grep wireguard
```

---

## Prevention Checklist

**Before Starting Daemon:**
- [ ] Verify `--allow-device-to-device` flag is in daemon subparser
- [ ] Test daemon startup with `--help` flag
- [ ] Verify config file syntax is correct
- [ ] Ensure OAuth2 credentials are valid

**Before Client Connection:**
- [ ] Client peer is registered on server (runtime and config file)
- [ ] Client peer has correct `AllowedIPs = 10.42.42.0/24` (not `/32`)
- [ ] Client config file has correct private key and assigned IP
- [ ] Server endpoint is reachable

**After Server Changes:**
- [ ] Verify WireGuard interface is up: `wg show factory`
- [ ] Check all peers have correct `AllowedIPs`
- [ ] Test connectivity from server to client
- [ ] Test connectivity from client to server

**After Client Connection:**
- [ ] Reimport NetworkManager connection if server was changed
- [ ] Verify handshake is established: `wg show foundries`
- [ ] Test ping to server: `ping 10.42.42.1`
- [ ] Test ping to devices: `ping 10.42.42.4`

---

## Contact

For assistance with Foundries VPN troubleshooting:
- **Email:** ajlennon@dynamicdevices.co.uk (Alex J Lennon)
- **Purpose:** Server configuration, client peer registration, advanced troubleshooting

---

## Related Documentation

- `docs/FOUNDRIES_VPN_CLEAN_INSTALLATION.md` - Complete setup guide
- `docs/FOUNDRIES_VPN_CLIENT_SETUP.md` - Client setup details
- `lab_testing/resources/help.py` - MCP tool help documentation

