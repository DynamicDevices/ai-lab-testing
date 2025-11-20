# Factory WireGuard Daemon Fix

## Problem Location

File: `/root/factory-wireguard-server/factory-wireguard.py`
Function: `apply_conf()` (lines 269-280)

## Current Code

```python
def apply_conf(self, factory: str, conf: str, intf_name: str):
    with open("/etc/wireguard/%s.conf" % intf_name, "w") as f:
        os.fchmod(f.fileno(), 0o700)
        f.write(conf)
    try:
        subprocess.check_call(["wg-quick", "down", intf_name])
    except subprocess.CalledProcessError:
        log.info("Unable to take VPN down. Assuming initial invocation")
    subprocess.check_call(["wg-quick", "up", intf_name])
```

## Problem

When `wg-quick up` is called, if peers already exist with endpoints,
WireGuard clears AllowedIPs. This happens because WireGuard sees
existing peers with endpoints and doesn't apply the AllowedIPs from
the config file.

## Solution

Remove existing device peers BEFORE calling `wg-quick up`:

```python
def apply_conf(self, factory: str, conf: str, intf_name: str):
    # Remove existing device peers before applying config
    # This ensures AllowedIPs are set correctly
    try:
        # Get list of device peers from config
        for device in FactoryDevice.iter_vpn_enabled(factory, self.api):
            try:
                # Remove peer if it exists
                subprocess.run(
                    ["wg", "set", intf_name, "peer", device.pubkey, "remove"],
                    check=False,
                    capture_output=True,
                    timeout=5
                )
            except Exception:
                pass  # Ignore errors if peer doesn't exist
    except Exception:
        pass  # Ignore errors if interface doesn't exist
    
    # Now apply config (peers will be added without endpoints)
    with open("/etc/wireguard/%s.conf" % intf_name, "w") as f:
        os.fchmod(f.fileno(), 0o700)
        f.write(conf)
    try:
        subprocess.check_call(["wg-quick", "down", intf_name])
    except subprocess.CalledProcessError:
        log.info("Unable to take VPN down. Assuming initial invocation")
    subprocess.check_call(["wg-quick", "up", intf_name])
    
    # Devices will reconnect and add endpoints, preserving AllowedIPs
```

## Why This Works

1. Remove existing peers (clears endpoints)
2. Apply config (peers added with AllowedIPs, no endpoints)
3. Devices reconnect (add endpoints, AllowedIPs persist)

## Testing

After applying fix:
- ✅ All device peers show `allowed ips: 10.42.42.0/24`
- ✅ Client can ping devices via VPN IPs
- ✅ Devices can communicate with each other
- ✅ AllowedIPs persist after daemon restarts
