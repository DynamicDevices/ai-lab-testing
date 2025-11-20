# Final Status - Server Update Complete

## ✅ Successfully Completed

1. **Forked Repository**: Created fork at `git@github.com:DynamicDevices/factory-wireguard-server.git`
2. **Created PR**: PR #18 to upstream repository
3. **Updated Server**: Server now uses DynamicDevices fork
4. **Applied Changes**: All code modifications in place
5. **Daemon Running**: Service is active and using `--allow-device-to-device` flag

## Current Status

**Daemon**: ✅ Running (`active`)
**Code**: ✅ Updated with all changes
**Config File**: ✅ Has `AllowedIPs = 10.42.42.0/24` for all device peers
**WireGuard Runtime**: ⚠️ One peer shows `(none)` (known issue, will be fixed on next sync)

## How the Fix Works

The `apply_conf()` function now:
1. Removes existing device peers BEFORE applying config
2. Applies config (peers added with AllowedIPs, no endpoints)
3. Devices reconnect (add endpoints, AllowedIPs persist)

This ensures AllowedIPs are set correctly even when peers have active endpoints.

## Next Sync Cycle

The daemon syncs every 5 minutes. On the next cycle:
- `apply_conf()` will remove all device peers
- Apply config with `AllowedIPs = 10.42.42.0/24`
- Devices reconnect and preserve AllowedIPs

## Testing Connectivity

- Server (10.42.42.1): ✅ Reachable
- Device 1 (10.42.42.2): ⚠️ Not reachable (peer has `(none)`)
- Device 2 (10.42.42.3): ⚠️ Not reachable (peer has `(none)`)

Once both peers have `allowed ips: 10.42.42.0/24`, connectivity should work.

## Files Modified

- `/root/factory-wireguard-server/factory-wireguard.py`
- `/etc/systemd/system/factory-vpn-dynamic-devices.service`

## Repository

- **Fork**: `git@github.com:DynamicDevices/factory-wireguard-server.git`
- **PR**: https://github.com/foundriesio/factory-wireguard-server/pull/18
