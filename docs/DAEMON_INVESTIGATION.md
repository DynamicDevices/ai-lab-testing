# Daemon Overwriting Settings - Investigation

## Problem
The `factory-vpn-dynamic-devices.service` daemon keeps overwriting WireGuard peer `allowed-ips` settings, setting them to `(none)` instead of `10.42.42.0/24`.

## Root Cause Analysis

### How the Daemon Works

From source code analysis (`factory-wireguard.py`):

1. **Daemon Loop (lines 493-510):**
   - Runs in infinite loop
   - Calls `wgserver.gen_conf()` to generate config from FoundriesFactory API
   - Compares with current config
   - If different, calls `wgserver.apply_conf()` which uses `wg-quick down/up`
   - This overwrites any manual changes!

2. **Config Generation (line 257):**
   ```python
   AllowedIPs = {ip}
   ```
   - Where `{ip}` is device's IP (e.g., `10.42.42.2`)
   - WireGuard interprets this as `/32` (only that IP)
   - But if daemon code modification was applied, should be `10.42.42.0/24`

3. **apply_conf() Function (lines 269-277):**
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
   - Writes new config to `/etc/wireguard/factory.conf`
   - Uses `wg-quick down/up` which reads from config file
   - **This overwrites runtime changes made with `wg set`**

## Why Peers Show `(none)`

Possible reasons:

1. **Daemon code modification not applied:**
   - Line 257 still shows `AllowedIPs = {ip}`
   - When daemon generates config, it sets `AllowedIPs = 10.42.42.2` (device IP)
   - WireGuard might interpret this as invalid or `(none)` if format is wrong

2. **FoundriesFactory API doesn't return AllowedIPs:**
   - The daemon reads device info from FoundriesFactory API
   - API might not include `AllowedIPs` field
   - Daemon generates config without AllowedIPs

3. **Config file format issue:**
   - If `AllowedIPs = 10.42.42.2` (without `/32`), WireGuard might reject it
   - Or if missing entirely, shows as `(none)`

## Investigation Steps

1. **Check daemon code modification:**
   ```bash
   cat /root/factory-wireguard-server/factory-wireguard.py | grep -A 5 "AllowedIPs"
   ```
   Should show: `AllowedIPs = 10.42.42.0/24`

2. **Check daemon logs:**
   ```bash
   journalctl -u factory-vpn-dynamic-devices.service -n 50
   ```
   Look for "Configuration changed" messages

3. **Check generated config:**
   ```bash
   cat /etc/wireguard/factory.conf
   ```
   See what AllowedIPs values the daemon is generating

4. **Check daemon process:**
   ```bash
   ps aux | grep factory-wireguard
   ```
   Verify daemon is running and which script it's using

## Solutions

### Solution 1: Fix Daemon Code (Permanent Fix)

Modify `/root/factory-wireguard-server/factory-wireguard.py` line 257:

Change:
```python
AllowedIPs = {ip}
```

To:
```python
AllowedIPs = 10.42.42.0/24
```

Then restart daemon:
```bash
systemctl restart factory-vpn-dynamic-devices.service
```

### Solution 2: Stop Daemon, Edit Config, Don't Restart Daemon

1. Stop daemon permanently (for development):
   ```bash
   systemctl stop factory-vpn-dynamic-devices.service
   systemctl disable factory-vpn-dynamic-devices.service
   ```

2. Edit config file:
   ```bash
   nano /etc/wireguard/factory.conf
   ```
   Add `AllowedIPs = 10.42.42.0/24` to all `[Peer]` sections

3. Apply config:
   ```bash
   wg-quick down factory
   wg-quick up factory
   ```

4. Save:
   ```bash
   wg-quick save factory
   ```

5. Don't restart daemon (or it will overwrite again)

### Solution 3: Modify Daemon to Preserve Manual Peers

This would require code changes to:
- Read existing config file
- Preserve peers not in FoundriesFactory API (like client peer)
- Only update device peers from API

This is more complex but would be the proper solution.

## Recommended Approach

For development:
1. **Stop daemon permanently** (or disable auto-start)
2. **Edit config file manually** with all peers having `AllowedIPs = 10.42.42.0/24`
3. **Apply config** with `wg-quick`
4. **Don't restart daemon** until you need it

For production:
1. **Fix daemon code** to use `10.42.42.0/24` instead of `{ip}`
2. **Restart daemon** so it generates correct configs
3. **Add client peer manually** (daemon doesn't manage it)
