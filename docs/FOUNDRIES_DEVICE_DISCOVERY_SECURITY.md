# Foundries Device Discovery - Security Considerations

## Current Situation

Foundries devices are accessible via VPN but not automatically discoverable by the MCP server's device discovery mechanisms. This is actually a **security feature** rather than a limitation.

## Device Information

From server `/etc/hosts`:
- `10.42.42.2` -> `imx8mm-jaguar-sentai-2d0e0a09dab86563`
- `10.42.42.3` -> `imx8mm-jaguar-inst-5120a09dab86563`

## Security Considerations

### Why Devices Aren't Auto-Discovered

1. **Network Isolation**: Foundries VPN network (10.42.42.0/24) is separate from hardware lab network (192.168.2.0/24)
2. **Device Discovery Scope**: Current discovery scans hardware lab network, not Foundries VPN network
3. **Access Control**: Devices require explicit VPN connection and knowledge of IPs/hostnames

### Security Risks of Auto-Discovery

**Potential Risks:**
- Exposes device information to anyone with VPN access
- Makes devices easily discoverable and accessible
- Could enable unauthorized access if VPN credentials compromised
- Network scanning might trigger security alerts on devices

**Benefits of Current Approach:**
- Devices only accessible to those who know IPs/hostnames
- Explicit access control via VPN
- Reduced attack surface
- Better security posture

## Options for Device Discovery

### Option 1: Manual Device Config (Recommended for Security)
Add devices manually to `config/lab_devices.json`:
- Only adds devices you explicitly want to manage
- Full control over which devices are accessible
- No automatic network scanning
- **Best for**: Production environments, security-conscious setups

### Option 2: Selective VPN Network Scanning
Add Foundries VPN network to discovery scan when VPN connected:
- Scans 10.42.42.0/24 only when Foundries VPN active
- Requires VPN connection (access control)
- Could be limited to specific IP ranges
- **Best for**: Development environments, controlled access

### Option 3: Foundries API-Based Discovery
Use FoundriesFactory API to discover devices:
- Already implemented via `list_foundries_devices()`
- No network scanning required
- Uses FoundriesFactory authentication
- **Best for**: Foundries-specific device management

### Option 4: Hybrid Approach
- Use Foundries API for device listing (`list_foundries_devices()`)
- Manual config for devices you want to manage via MCP tools
- Network scanning only for hardware lab network
- **Best for**: Mixed environments

## Recommended Approach

**For Debugging/Development:**
1. Add devices manually to `config/lab_devices.json` with VPN IPs
2. Use Foundries API (`list_foundries_devices()`) for device status
3. Keep network scanning limited to hardware lab network
4. Document device IPs in local `/etc/hosts` for convenience

**For Production:**
1. Keep devices out of auto-discovery
2. Use Foundries API for device management
3. Require explicit device config for MCP tool access
4. Maintain strict access control

## Implementation

### Adding Devices Manually

Add to `config/lab_devices.json`:
```json
{
  "devices": {
    "imx8mm-jaguar-sentai": {
      "ip": "10.42.42.2",
      "device_type": "foundries_device",
      "friendly_name": "Jaguar Sentai Board",
      "ssh_user": "root",
      "ports": {"ssh": 22},
      "fio_factory": "default",
      "fio_device_name": "imx8mm-jaguar-sentai-2d0e0a09dab86563"
    },
    "imx8mm-jaguar-inst": {
      "ip": "10.42.42.3",
      "device_type": "foundries_device",
      "friendly_name": "Jaguar INST Board",
      "ssh_user": "root",
      "ports": {"ssh": 22},
      "fio_factory": "default",
      "fio_device_name": "imx8mm-jaguar-inst-5120a09dab86563"
    }
  }
}
```

### Adding to Local /etc/hosts

```bash
sudo bash -c 'cat >> /etc/hosts << EOF
# Foundries VPN Devices
10.42.42.2  imx8mm-jaguar-sentai-2d0e0a09dab86563
10.42.42.3  imx8mm-jaguar-inst-5120a09dab86563
EOF'
```

## Security Best Practices

1. **Access Control**: Only add devices you need to manage
2. **VPN Requirement**: Ensure Foundries VPN is required for access
3. **Credential Management**: Use SSH keys, not passwords
4. **Audit Trail**: Log device access and operations
5. **Network Isolation**: Keep Foundries VPN separate from hardware lab network
6. **Regular Review**: Periodically review device config and access

## Conclusion

The current approach (manual device config) is more secure than auto-discovery. For debugging, manually adding devices to config provides the right balance of accessibility and security.
