# Foundries VPN Server - Current Status

## Problem
The `factory-wireguard-server` daemon on the Proxmox WireGuard server is not running, preventing automatic peer addition for Foundries devices.

## Current Status Summary

### ✅ What's Working
- **Standard WireGuard VPN**: Working well for hardware lab access
- **Foundries VPN Client**: Client-side setup and connection tools work correctly
- **NetworkManager Routing**: Correctly configured to only route VPN network, preserving internet connectivity
- **VPN Status & Connection Tools**: All client-side tools function properly
- **Device Management**: Enable/disable VPN on devices via FoundriesFactory API works
- **WireGuard Server**: Server is running on Proxmox (`proxmox.dynamicdevices.co.uk`)
- **Server-Side Daemon**: ✅ `factory-wireguard-server` daemon is now running
- **Automatic Peer Addition**: ✅ Devices with VPN enabled are being added as peers automatically
- **Device Connectivity**: ✅ Devices are connected to VPN server

### ⚠️ What Needs Verification
- **Hosts File**: Verify `/etc/hosts` on server is populated with device hostnames
- **Device Access**: Test SSH access to devices via VPN IPs or hostnames

## What We Know
- WireGuard server is running on Proxmox (`proxmox.dynamicdevices.co.uk`)
- Server interface: `factory` (port 5555)
- Client peer is working (10.42.42.10/32)
- `factory-wireguard-server` daemon is now running ✅
- Devices are connected to VPN server ✅
- Foundries VPN client connected successfully (10.42.42.10/24)
- 4 Foundries devices visible via API (2 online, 2 offline)

## Key Learnings

### VPN Architecture Differences

**Standard WireGuard VPN:**
- Direct peer-to-peer connection to hardware lab network
- Simple, reliable, works well
- Manual peer configuration
- Uses NetworkManager routing to only route target networks, preserving internet connectivity

**Foundries VPN:**
- Server-based architecture with centralized VPN server on Proxmox
- Client connects to server, server daemon manages device peers automatically
- More complex but enables automatic device discovery and management
- Server daemon (`factory-wireguard-server`) monitors FoundriesFactory API
- Automatically adds/removes devices as WireGuard peers based on VPN enable/disable
- Populates `/etc/hosts` on server with device hostnames

**Key Difference:** Standard VPN = manual peer config. Foundries VPN = automatic peer management via server daemon.

### Routing Configuration (CRITICAL FIX)

**Problem Discovered:**
- Without proper routing configuration, VPN becomes default route and breaks internet connectivity
- All traffic routed through VPN, causing internet loss

**Solution Implemented:**
- NetworkManager routing configuration is essential
- Foundries VPN connection explicitly:
  1. Parses `AllowedIPs` from WireGuard config
  2. Sets `ipv4.routes` to only route `AllowedIPs`
  3. Sets `ipv4.never-default yes` to prevent VPN from becoming default route
- This preserves internet connectivity while routing VPN network traffic correctly
- Implemented in `connect_foundries_vpn()` function using `nmcli connection modify`

**Testing:** Verified internet connectivity preserved when Foundries VPN connected. Only traffic to VPN network (10.42.42.0/24) routed through VPN.

### Server Daemon Function

**What It Does:**
- Monitors FoundriesFactory API for devices with `wireguard.enabled = true`
- Automatically adds devices as WireGuard peers when VPN enabled
- Removes peers when VPN disabled on devices
- Updates `/etc/hosts` on server with device hostnames for easy access

**Status:** ✅ Daemon is now running and working correctly

**Requirements:**
- Valid OAuth2 credentials in `/root/fiocreds.json` on server
- Credentials may expire or become invalid if factory keys change
- Need periodic refresh via `fioctl login` (on machine with fioctl), convert to fiocreds.json format, update on server

**Location:** Daemon script: `/root/factory-wireguard-server/factory-wireguard.py` on Proxmox server

### Client Tools

**Status:** ✅ All Foundries VPN client-side tools work correctly

**Connection Method:**
- NetworkManager preferred (no root required, better system integration)
- Falls back to wg-quick if NetworkManager not available (requires root)

**Config Management:**
- Client config search order:
  1. `FOUNDRIES_VPN_CONFIG_PATH` environment variable
  2. `~/.config/wireguard/foundries.conf`
  3. `{LAB_TESTING_ROOT}/secrets/foundries-vpn.conf`
  4. `/etc/wireguard/foundries.conf`
- Centralized config function ensures consistency across tools

**Automation:**
- `setup_foundries_vpn()` provides automated end-to-end setup
- Checks prerequisites, validates/generates config, connects to VPN
- `auto_generate_config=True` generates template if config not found

### Device Management

**Discovery:**
- Foundries devices discovered via FoundriesFactory API using `fioctl devices list`
- Returns device name, target, status, apps, update status

**VPN Enable/Disable:**
- Enable VPN on device via `enable_foundries_vpn_device(device_name)`
- Uses FoundriesFactory API
- Device connects after OTA update (up to 5 minutes)
- Server daemon automatically detects and adds device as peer

**Hostname Resolution:**
- Server daemon populates `/etc/hosts` on server with device hostnames
- Client may need local `/etc/hosts` entries or use IP addresses directly for SSH access

### Troubleshooting Insights

**Server Access:**
- tmate works for interactive sessions but doesn't support non-interactive SSH commands
- For automated access, need regular SSH or run commands interactively and share output

**Credential Refresh:**
- If factory keys change, server credentials need refresh
- Regenerate via `fioctl login` on machine with fioctl
- Convert to `fiocreds.json` format, update on server

**Hostname Resolution:**
- Device hostnames may not resolve locally
- Check server `/etc/hosts` (populated by daemon) or use VPN IP addresses directly
- Can add to local `/etc/hosts` for convenience

**ICMP Blocking:**
- Ping to VPN server may fail (ICMP blocked) but VPN routing still works
- Use SSH or other protocols to verify connectivity

### Best Practices Learned

**VPN Choice:**
- Use standard WireGuard VPN for hardware lab access (simple, reliable)
- Use Foundries VPN for Foundries devices (automatic peer management, device discovery)

**Routing Configuration:**
- Always configure VPN routing to only route target networks
- Never allow VPN to become default route unless intentionally routing all traffic

**NetworkManager:**
- Prefer NetworkManager for VPN connections (no root required, better system integration, easier routing configuration)

**Peer Registration:**
- Foundries VPN requires manual client peer registration on server (one-time setup)
- Server daemon handles device peers automatically

## What We Tried
1. Attempted to access server via tmate - tmate works but doesn't support non-interactive commands
2. Diagnosed daemon issues directly on server
3. Server daemon is now running and devices are connected ✅

## Current Verification (2025-01-XX)
- ✅ Foundries VPN client connected: 10.42.42.10/24
- ✅ NetworkManager connection active: `foundries` interface
- ✅ Foundries devices visible: 4 devices listed via API
- ✅ Online devices: 2 devices showing "OK" status
- ⚠️  Hostname resolution: Device hostnames not resolvable locally (may need /etc/hosts on client or DNS)
- ⚠️  Server ping: ICMP to server (10.42.42.1) blocked (may be expected)

## Why This Matters

The client-side tools work correctly, but without the server-side daemon:
- Devices with VPN enabled won't automatically appear as peers
- Manual peer addition required for each device
- `/etc/hosts` won't be populated, requiring IP addresses instead of hostnames
- No automatic updates when devices enable/disable VPN

## Next Steps (Verification)
1. **Verify device access** - Test SSH to devices:
   - Check WireGuard peers on server: `sudo wg show factory` (should show device peers)
   - Test SSH to online devices via VPN IPs
   - Verify hostname resolution (check server `/etc/hosts`)

2. **Test device connectivity**:
   - Try SSH to devices using their Foundries device names
   - If hostnames don't resolve, check server `/etc/hosts` or use IP addresses
   - Verify devices are reachable via VPN network (10.42.42.0/24)

3. **Document device IPs**:
   - Get device VPN IPs from server WireGuard config
   - Add to local `/etc/hosts` if needed for easier access
   - Or use IP addresses directly for SSH access

## Key Files on Server
- `/root/fiocreds.json` - OAuth2 credentials for FoundriesFactory API
- `/root/factory-wireguard-server/` - Daemon repository
- `/root/wgpriv.key` - WireGuard server private key
- `/etc/wireguard/factory.conf` - WireGuard server config

## Contact
For WireGuard server admin assistance: ajlennon@dynamicdevices.co.uk
