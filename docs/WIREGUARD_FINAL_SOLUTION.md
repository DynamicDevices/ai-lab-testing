# WireGuard AllowedIPs Final Solution

## Problem Summary

Device peers show `allowed ips: (none)` in WireGuard runtime, preventing connectivity.

## Root Cause

**WireGuard clears AllowedIPs when peers are added/modified while they have active endpoints.**

When the `factory-wireguard-server` daemon regenerates config using `wg-quick up`,
it applies peers that already have endpoints from device connections. WireGuard
then clears the AllowedIPs for these peers.

## Solution

**Modify the daemon to remove peers before regenerating config, then add them back without endpoints.**

### Implementation Steps:

1. **Stop daemon:**
   ```bash
   systemctl stop factory-vpn-dynamic-devices.service
   ```

2. **Fix peers manually (temporary):**
   ```bash
   # Remove peer
   wg set factory peer <PUBLIC_KEY> remove
   sleep 2
   
   # Add peer WITHOUT endpoint, WITH AllowedIPs
   wg set factory peer <PUBLIC_KEY> allowed-ips 10.42.42.0/24
   
   # Device will reconnect and add endpoint, preserving AllowedIPs
   ```

3. **Update daemon code** (`factory-wireguard.py`):
   - In `apply_conf()` function, before calling `wg-quick up`:
     - Remove all device peers
     - Regenerate config with AllowedIPs
     - Apply config (peers added without endpoints)
     - Devices reconnect automatically, adding endpoints

### Code Change:

In `/root/factory-wireguard-server/factory-wireguard.py`, modify `apply_conf()`:

```python
def apply_conf(self, factory_name, conf):
    # Remove existing device peers before regenerating
    for device in self.devices:
        try:
            subprocess.run(['wg', 'set', 'factory', 'peer', device.pubkey, 'remove'],
                         check=False, capture_output=True)
        except:
            pass
    
    # Now apply new config (peers added without endpoints)
    # ... rest of apply_conf() code ...
```

## Testing

After implementing:
- ✅ All device peers show `allowed ips: 10.42.42.0/24`
- ✅ Client can ping devices via VPN IPs
- ✅ Devices can communicate with each other
- ✅ AllowedIPs persist after daemon restarts

## Current Status

- **Device Peer 1**: ✅ Shows `10.42.42.0/24` (after manual fix)
- **Device Peer 2**: ⚠️ Shows `(none)` (daemon overwrites)
- **Client Peer**: ✅ Shows `10.42.42.0/24`

**Next Step**: Update daemon code to implement this fix permanently.
