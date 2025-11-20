# WireGuard AllowedIPs Issue - Investigation Results

## Problem

Device peers show `allowed ips: (none)` in WireGuard runtime, even though:
- Config file has `AllowedIPs = 10.42.42.0/24`
- Daemon code generates `AllowedIPs = 10.42.42.0/24`
- Manual `wg set` commands are executed

## Key Findings

1. **Config file is correct** - Has `AllowedIPs = 10.42.42.0/24` for device peers
2. **Daemon code is correct** - Generates `AllowedIPs = 10.42.42.0/24`
3. **Manual `wg set` works inconsistently** - Sometimes sets, sometimes doesn't
4. **Client peer works fine** - Shows `10.42.42.0/24` correctly
5. **Device peers are inconsistent** - One shows `(none)`, one shows `10.42.42.0/24`

## Observations

- When `wg set` is used, AllowedIPs sometimes don't persist
- `wg-quick save` saves what WireGuard runtime has, not what's in config file
- Device peers have endpoints configured (from device side)
- Client peer has endpoint but AllowedIPs works

## Possible Causes

1. **WireGuard behavior**: AllowedIPs might be managed by device-side config
2. **Endpoint conflict**: Peers with endpoints might have AllowedIPs cleared
3. **Timing issue**: AllowedIPs might be cleared after handshake
4. **WireGuard version bug**: v1.0.20210914 might have an issue

## Next Steps

1. Check device-side WireGuard configuration
2. Verify if devices have correct AllowedIPs configured
3. Test if removing endpoints helps
4. Check WireGuard documentation for AllowedIPs behavior with endpoints

## Current Status

- Server: 10.42.42.1 - ✅ Reachable
- Device 1: 10.42.42.2 - ❌ Not reachable (peer shows `(none)`)
- Device 2: 10.42.42.3 - ⚠️ Sometimes shows `10.42.42.0/24`, sometimes `(none)`
- Client: 10.42.42.10 - ✅ Shows `10.42.42.0/24` correctly
