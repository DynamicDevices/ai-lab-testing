# Factory WireGuard Server - Source Code Analysis

## Repository
https://github.com/foundriesio/factory-wireguard-server

## Key Finding: How AllowedIPs Are Set

**Line 257 in factory-wireguard.py:**
```python
AllowedIPs = {ip}
```

Where `{ip}` is the device's IP address (e.g., `10.42.42.2`).

**This means:** Each device peer gets `AllowedIPs = 10.42.42.2` (which WireGuard interprets as `/32` - only that IP).

## How The Daemon Works

**Lines 493-510:**
```python
def daemon(args):
    # Creates server config
    wgserver = WgServer.load_from_factory(args.api, args.factory, pkey)
    cur_conf = ""
    while True:
        log.info("Looking for factory config changes")
        conf = wgserver.gen_conf(args.factory, args.no_sysctl)
        if cur_conf != conf:
            if cur_conf != "":
                log.info("Configuration changed, applying changes")
            wgserver.apply_conf(args.factory, conf, args.intf_name)
            cur_conf = conf
            update_dns(args.factory, args.intf_name)
        time.sleep(args.interval)
```

**Key Points:**
1. Daemon runs in a loop, checking for config changes
2. Regenerates config from FoundriesFactory API
3. Calls `apply_conf()` which uses `wg-quick down/up` to apply changes
4. **This overwrites any manual changes!**

## The Problem

1. **Daemon only manages Foundries devices** - It reads devices with VPN enabled from FoundriesFactory API
2. **Client peers are NOT managed by daemon** - They must be added manually
3. **Daemon regenerates config periodically** - Any manual changes get overwritten
4. **Devices get `/32` allowed-ips** - Only their own IP, preventing peer-to-peer communication

## Why Client Can't Reach Devices

1. Client peer is missing (not managed by daemon)
2. Device peers have `/32` allowed-ips (too restrictive)
3. Even if we fix manually, daemon will overwrite device peer configs

## Solutions

### Option 1: Modify Daemon Code (Best for Development)

Modify `factory-wireguard.py` line 257 to use full network:
```python
AllowedIPs = 10.42.42.0/24  # Instead of {ip}
```

Then restart daemon.

### Option 2: Add Client Peer to Config File (Persists)

Edit `/etc/wireguard/factory.conf` directly and add client peer:
```ini
[Peer]
# Client
PublicKey = mzHaZPGowqqzAa5tVFQJs0zoWuDVLppt44HwgdcPXkg=
AllowedIPs = 10.42.42.0/24
```

But daemon will regenerate config and may remove it!

### Option 3: Modify Config After Daemon Updates (Workaround)

1. Let daemon manage device peers
2. After daemon updates, manually fix allowed-ips:
   ```bash
   wg set factory peer <device-key> allowed-ips 10.42.42.0/24
   ```
3. Add client peer manually
4. Save config: `wg-quick save factory`

But daemon will overwrite on next sync!

### Option 4: Patch Daemon Code (Recommended)

Modify the daemon to:
1. Allow full network access for development
2. Or add client peer management
3. Or make allowed-ips configurable

## Recommended Fix for Development

**Modify `/root/factory-wireguard-server/factory-wireguard.py` line 257:**

Change:
```python
AllowedIPs = {ip}
```

To:
```python
AllowedIPs = 10.42.42.0/24
```

Then:
1. Restart daemon: `systemctl restart factory-vpn-<factory>.service`
2. Or restart manually: `pkill -f factory-wireguard.py` then restart daemon
3. Add client peer manually: `wg set factory peer <CLIENT_PUBLIC_KEY> allowed-ips 10.42.42.0/24`
4. Save: `wg-quick save factory`

**Finding the Client Public Key:**

The client public key is the WireGuard public key from the client's configuration file. It can be extracted using:

```bash
# From client's config file
cat ~/.config/wireguard/foundries.conf | grep "PrivateKey" | awk '{print $3}' | wg pubkey

# Or from private key file
cat /path/to/privatekey | wg pubkey
```

**What it looks like:**
- Base64-encoded string ending with `=`
- Example: `mzHaZPGowqqzAa5tVFQJs0zoWuDVLppt44HwgdcPXkg=`
- About 44 characters long

**Note:** The client peer is NOT managed by the daemon, so it must be added manually and will persist. Device peers will now be configured with full network access (`10.42.42.0/24`) by the daemon.

This way, daemon will generate configs with full network access, and client peer persists.
