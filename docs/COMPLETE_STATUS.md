# Complete Status - Server Update

## ✅ Successfully Completed

1. **Repository**: Server uses `git@github.com:DynamicDevices/factory-wireguard-server.git`
2. **PR Created**: PR #18 to upstream repository
3. **Code Changes**: All modifications applied
4. **Daemon**: Running with `--allow-device-to-device` flag
5. **Fix**: `apply_conf()` removes peers before applying config
6. **Enhancement**: Daemon always applies config when `allow_device_to_device` is enabled

## Current Status

**Daemon**: ✅ Running (`active`)
**Code**: ✅ All changes applied
**Config File**: ✅ Has `AllowedIPs = 10.42.42.0/24` for all device peers
**WireGuard Runtime**: 
- Peer 1: `allowed ips: (none)` ⚠️
- Peer 2: `allowed ips: 10.42.42.0/24` ✅
- Client: `allowed ips: 10.42.42.0/24` ✅

## How It Works Now

1. **Daemon Logic**: Always applies config when `allow_device_to_device` is enabled
   - This ensures `apply_conf()` runs on every sync cycle
   - Not just when config string changes

2. **apply_conf() Fix**: Removes peers before applying config
   - Clears endpoints
   - Applies config with AllowedIPs
   - Devices reconnect and preserve AllowedIPs

## Next Steps

The daemon syncs every 5 minutes. On the next cycle:
- `apply_conf()` will remove all device peers
- Apply config with `AllowedIPs = 10.42.42.0/24`
- Devices reconnect and preserve AllowedIPs

This should fix the remaining peer with `(none)`.

## Testing

Once both device peers show `allowed ips: 10.42.42.0/24`:
- Devices should be able to communicate with each other
- Client should be able to reach devices
- Full device-to-device communication enabled

## Files Modified

- `/root/factory-wireguard-server/factory-wireguard.py`
  - Added `--allow-device-to-device` flag
  - Modified `apply_conf()` to remove peers before applying
  - Updated daemon to always apply when flag is enabled
- `/etc/systemd/system/factory-vpn-dynamic-devices.service`
  - Added `--allow-device-to-device` flag to ExecStart
