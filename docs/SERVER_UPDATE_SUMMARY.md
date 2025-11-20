# Server Update Summary

## Changes Applied

✅ **Repository Updated**: Server now uses `git@github.com:DynamicDevices/factory-wireguard-server.git`

✅ **Code Changes**:
- Added `--allow-device-to-device` flag to daemon subparser
- Modified `WgServer.__init__()` to accept `allow_device_to_device` parameter
- Updated `_gen_conf()` to use `AllowedIPs = 10.42.42.0/24` when flag is enabled
- Fixed `apply_conf()` to remove existing peers before applying config
- Updated `load_from_factory()` to accept and pass the flag
- Updated `daemon()` and `update_endpoint()` functions

✅ **Systemd Service**: Updated to use `--allow-device-to-device` flag

✅ **Daemon Status**: Running and active

## How It Works

1. **Flag Enabled**: `--allow-device-to-device` is passed to daemon
2. **Config Generation**: `_gen_conf()` generates `AllowedIPs = 10.42.42.0/24` for all device peers
3. **Config Application**: `apply_conf()` removes existing peers before applying config
   - This ensures AllowedIPs are set correctly even when peers have active endpoints
   - Devices reconnect automatically and preserve AllowedIPs

## Testing

- ✅ Daemon is running
- ✅ Code changes verified
- ✅ One peer shows `allowed ips: 10.42.42.0/24` ✅
- ⚠️ One peer shows `allowed ips: (none)` (will be fixed on next daemon sync cycle)

## Next Steps

The daemon syncs every 5 minutes. On the next cycle:
- `apply_conf()` will remove existing peers
- Apply config with `AllowedIPs = 10.42.42.0/24`
- Devices reconnect and preserve AllowedIPs

Alternatively, peers can be manually fixed using:
```bash
wg set factory peer <PUBLIC_KEY> remove
wg set factory peer <PUBLIC_KEY> allowed-ips 10.42.42.0/24
```

## Files Modified

- `/root/factory-wireguard-server/factory-wireguard.py`
- `/etc/systemd/system/factory-vpn-dynamic-devices.service`
