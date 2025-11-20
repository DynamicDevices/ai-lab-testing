# Pull Request Plan

## Goal
Add configuration option to enable device-to-device communication via WireGuard VPN.

## Changes Needed

### 1. Add Command-Line Argument
Add `--allow-device-to-device` flag to enable device-to-device communication.

### 2. Modify `gen_conf()` Function
- If `--allow-device-to-device` is set, use `AllowedIPs = 10.42.42.0/24`
- Otherwise, use `AllowedIPs = {device.ip}/32` (default behavior)

### 3. Fix `apply_conf()` Function
- Remove existing device peers BEFORE calling `wg-quick up`
- This ensures AllowedIPs are set correctly even when peers have endpoints

### 4. Update Documentation
- Update README.md with new option
- Explain device-to-device communication feature

## Implementation Steps

1. Fork repository (if not already forked)
2. Create feature branch: `feature/device-to-device-communication`
3. Make code changes
4. Test changes
5. Update documentation
6. Create pull request

## Code Changes

### Argument Parser
```python
parser.add_argument(
    "--allow-device-to-device",
    action="store_true",
    help="Allow devices to communicate with each other via VPN (default: devices can only reach server)"
)
```

### gen_conf() Modification
```python
# In _gen_conf() method, around line 257:
if self.allow_device_to_device:
    allowed_ips = "10.42.42.0/24"
else:
    allowed_ips = f"{device.ip}/32"

peer = """# {name}
[Peer]
PublicKey = {key}
AllowedIPs = {allowed_ips}
""".format(
    name=device.name, key=device.pubkey, ip=device.ip, allowed_ips=allowed_ips
)
```

### apply_conf() Fix
```python
def apply_conf(self, factory: str, conf: str, intf_name: str):
    # Remove existing device peers before applying config
    # This ensures AllowedIPs are set correctly
    if self.allow_device_to_device:
        try:
            for device in FactoryDevice.iter_vpn_enabled(factory, self.api):
                try:
                    subprocess.run(
                        ["wg", "set", intf_name, "peer", device.pubkey, "remove"],
                        check=False,
                        capture_output=True,
                        timeout=5
                    )
                except Exception:
                    pass
        except Exception:
            pass
    
    # Apply config
    with open("/etc/wireguard/%s.conf" % intf_name, "w") as f:
        os.fchmod(f.fileno(), 0o700)
        f.write(conf)
    try:
        subprocess.check_call(["wg-quick", "down", intf_name])
    except subprocess.CalledProcessError:
        log.info("Unable to take VPN down. Assuming initial invocation")
    subprocess.check_call(["wg-quick", "up", intf_name])
```
