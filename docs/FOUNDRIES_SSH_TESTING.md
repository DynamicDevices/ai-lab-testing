# Foundries Device SSH Testing Status

## Current Status

### ✅ What's Working
- Foundries VPN connected: 10.42.42.10/24
- VPN routing configured correctly
- Foundries devices visible via API: 4 devices (2 online)
- Online devices:
  - `imx8mm-jaguar-inst-5120a09dab86563` (Status: OK)
  - `imx8mm-jaguar-sentai-2d0e0a09dab86563` (Status: OK)

### ⚠️ What's Needed
- Device VPN IP addresses (need from server)
- Hostname resolution (need /etc/hosts entries or use IPs directly)
- Devices not in local device config (need to add or use IPs directly)

## To Get Device IPs

### Option 1: Check WireGuard Server
On the WireGuard server, run:
```bash
sudo wg show factory
```

This will show all device peers with their VPN IPs, for example:
```
peer: <device-public-key>
  allowed ips: 10.42.42.X/32
  endpoint: <device-endpoint>
```

### Option 2: Check Server /etc/hosts
The server daemon populates `/etc/hosts` with device hostnames:
```bash
cat /etc/hosts | grep jaguar
```

This will show entries like:
```
10.42.42.X  imx8mm-jaguar-inst-5120a09dab86563
```

## Testing SSH Access

Once we have device IPs, we can:

1. **Test SSH directly by IP:**
   ```bash
   ssh root@10.42.42.X
   ```

2. **Add to local /etc/hosts for hostname resolution:**
   ```bash
   sudo echo "10.42.42.X  imx8mm-jaguar-inst-5120a09dab86563" >> /etc/hosts
   ```

3. **Add devices to local device config** (if using MCP tools):
   Add entries to `config/lab_devices.json` with device IPs and Foundries device names.

## Next Steps

1. Get device VPN IPs from server (see above)
2. Test SSH connectivity to devices via VPN IPs
3. Add to /etc/hosts or device config for easier access
4. Verify SSH access works correctly
