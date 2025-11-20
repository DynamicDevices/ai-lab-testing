# WireGuard AllowedIPs Solution

## Problem

Device peers show `allowed ips: (none)` in WireGuard runtime, even though:
- Config file has `AllowedIPs = 10.42.42.0/24`
- Manual `wg set` commands are executed
- Daemon code generates correct AllowedIPs

## Root Cause

**WireGuard clears AllowedIPs when adding peers that already have endpoints configured.**

When a peer is added WITH an existing endpoint (from device-side connection),
WireGuard clears the AllowedIPs. This happens because WireGuard might be
using device-side AllowedIPs configuration instead of server-side.

## Solution

**Add peers WITHOUT endpoints first, then set AllowedIPs, then let devices connect.**

### Steps:

1. **Remove existing device peers:**
   ```bash
   wg set factory peer <PUBLIC_KEY> remove
   ```

2. **Add peers WITHOUT endpoints, WITH AllowedIPs:**
   ```bash
   wg set factory peer <PUBLIC_KEY> allowed-ips 10.42.42.0/24
   ```

3. **Wait for devices to connect** (they will add endpoints automatically)

4. **Verify AllowedIPs persist:**
   ```bash
   wg show factory
   ```

## Why This Works

- When peer is added without endpoint, WireGuard accepts AllowedIPs
- When device connects later (adding endpoint), AllowedIPs persist
- If peer already has endpoint when AllowedIPs are set, WireGuard clears them

## Implementation

Update the `factory-wireguard-server` daemon to:
1. Remove device peers before regenerating config
2. Add peers with AllowedIPs first
3. Let devices connect (endpoints added automatically)

Or modify the daemon's `apply_conf()` function to:
1. Check if peer has endpoint
2. If yes, remove peer, add back without endpoint, set AllowedIPs
3. Device will reconnect and add endpoint, preserving AllowedIPs

## Testing

After applying this fix:
- ✅ Device peers show `allowed ips: 10.42.42.0/24`
- ✅ Client can ping devices via VPN IPs
- ✅ Devices can communicate with each other
- ✅ AllowedIPs persist after device reconnections
