# Key Learnings and Insights

This document captures important learnings from developing and troubleshooting the MCP Remote Testing server, particularly around VPN setup, device management, and troubleshooting.

## VPN Architecture

### Standard WireGuard VPN
- **Type:** Direct peer-to-peer connection to hardware lab network
- **Complexity:** Simple, reliable
- **Status:** ✅ Working well
- **Peer Management:** Manual peer configuration
- **Routing:** Uses NetworkManager routing to only route target networks, preserving internet connectivity

### Foundries VPN
- **Type:** Server-based architecture with centralized VPN server
- **Complexity:** More complex but enables automatic device discovery and management
- **Status:** ✅ Fully operational (server daemon running, devices connected)
- **Peer Management:** Automatic via server daemon that monitors FoundriesFactory API
- **Routing:** NetworkManager configured to only route VPN network (10.42.42.0/24), preserves internet

**Key Difference:** Standard VPN = manual peer config. Foundries VPN = automatic peer management via server daemon.

## Critical Routing Configuration Fix

### Problem Discovered
Without proper routing configuration, VPN becomes default route and breaks internet connectivity. All traffic routed through VPN, causing internet loss.

### Solution Implemented
NetworkManager routing configuration is essential. Foundries VPN connection explicitly:
1. Parses `AllowedIPs` from WireGuard config
2. Sets `ipv4.routes` to only route `AllowedIPs`
3. Sets `ipv4.never-default yes` to prevent VPN from becoming default route

This preserves internet connectivity while routing VPN network traffic correctly.

**Implementation:** `connect_foundries_vpn()` function in `lab_testing/tools/foundries_vpn.py`

**Testing:** Verified internet connectivity preserved when Foundries VPN connected. Only traffic to VPN network routed through VPN.

## Server Daemon Function

### What It Does
The `factory-wireguard-server` daemon on Proxmox server:
1. Monitors FoundriesFactory API for devices with `wireguard.enabled = true`
2. Automatically adds devices as WireGuard peers when VPN enabled
3. Removes peers when VPN disabled on devices
4. Updates `/etc/hosts` on server with device hostnames for easy access

### Status
✅ Daemon is now running and working correctly

### Requirements
- Valid OAuth2 credentials in `/root/fiocreds.json` on server
- Credentials may expire or become invalid if factory keys change
- Need periodic refresh via `fioctl login` (on machine with fioctl), convert to fiocreds.json format, update on server

### Location
Daemon script: `/root/factory-wireguard-server/factory-wireguard.py` on Proxmox server

## Client Tools

### Status
✅ All Foundries VPN client-side tools work correctly

### Connection Method
- NetworkManager preferred (no root required, better system integration)
- Falls back to wg-quick if NetworkManager not available (requires root)

### Config Management
Client config search order:
1. `FOUNDRIES_VPN_CONFIG_PATH` environment variable
2. `~/.config/wireguard/foundries.conf`
3. `{LAB_TESTING_ROOT}/secrets/foundries-vpn.conf`
4. `/etc/wireguard/foundries.conf`

Centralized config function ensures consistency across tools.

### Automation
- `setup_foundries_vpn()` provides automated end-to-end setup
- Checks prerequisites, validates/generates config, connects to VPN
- `auto_generate_config=True` generates template if config not found

## Device Management

### Discovery
Foundries devices discovered via FoundriesFactory API using `fioctl devices list`. Returns device name, target, status, apps, update status.

### VPN Enable/Disable
- Enable VPN on device via `enable_foundries_vpn_device(device_name)`
- Uses FoundriesFactory API
- Device connects after OTA update (up to 5 minutes)
- Server daemon automatically detects and adds device as peer

### Hostname Resolution
- Server daemon populates `/etc/hosts` on server with device hostnames
- Client may need local `/etc/hosts` entries or use IP addresses directly for SSH access

## Troubleshooting Insights

### Server Access
- tmate works for interactive sessions but doesn't support non-interactive SSH commands
- For automated access, need regular SSH or run commands interactively and share output

### Credential Refresh
- If factory keys change, server credentials need refresh
- Regenerate via `fioctl login` on machine with fioctl
- Convert to `fiocreds.json` format, update on server

### Hostname Resolution
- Device hostnames may not resolve locally
- Check server `/etc/hosts` (populated by daemon) or use VPN IP addresses directly
- Can add to local `/etc/hosts` for convenience

### ICMP Blocking
- Ping to VPN server may fail (ICMP blocked) but VPN routing still works
- Use SSH or other protocols to verify connectivity

## Best Practices

### VPN Choice
- Use standard WireGuard VPN for hardware lab access (simple, reliable)
- Use Foundries VPN for Foundries devices (automatic peer management, device discovery)

### Routing Configuration
- Always configure VPN routing to only route target networks
- Never allow VPN to become default route unless intentionally routing all traffic

### NetworkManager
- Prefer NetworkManager for VPN connections (no root required, better system integration, easier routing configuration)

### Peer Registration
- Foundries VPN requires manual client peer registration on server (one-time setup)
- Server daemon handles device peers automatically

## File Transfer Learnings

### Multiplexed SSH
- First transfer establishes connection (~1-2s overhead)
- Subsequent transfers reuse connection (near-zero overhead)
- 4.33x speedup for parallel transfers vs sequential (tested with 100+ files)

### Tool Selection
- Single file: `copy_file_to_device` (fastest for one file)
- Multiple files (10+): `copy_files_to_device_parallel` (fastest, 4.33x speedup)
- Large directory: `sync_directory_to_device` (requires rsync) or `copy_files_to_device_parallel` (fallback)

### Performance
- Compression enabled by default for faster transfers over slow links
- Large files (>50MB) may timeout on slow VPN links (60s timeout)
- Parallel transfers scale well (tested successfully with 100-200 files)

## Error Handling

### Helpful Error Messages
- Tools return structured responses with `success`, `error`, `message`, and `next_steps` fields
- Error messages include specific suggestions and related tools
- `next_steps` arrays guide users through workflows

### Prerequisite Checks
- Tools check prerequisites (fioctl installed, configured, WireGuard tools, etc.)
- Provide helpful installation/configuration instructions when prerequisites missing

### Troubleshooting Guidance
- Tools provide actionable troubleshooting steps
- Link to relevant documentation and workflows
- Suggest alternative approaches when primary method fails
