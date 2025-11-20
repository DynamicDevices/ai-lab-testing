# WireGuard Connectivity Fix Steps

## Current Configuration Analysis

From `wg show factory`:
- Device 1: `allowed-ips: 10.42.42.2/32` (too restrictive)
- Device 2: `allowed-ips: 10.42.42.3/32` (too restrictive)
- Client peer: Not visible in output (may be missing or not configured)

## Problem

WireGuard peers can only communicate if their `allowed-ips` overlap. Current configuration:
- Devices: `/32` (only their own IP)
- Client: Likely `/32` (only own IP)
- Result: No overlap → No communication

## Solution

### Step 1: Check if Client Peer Exists

```bash
# Check all peers
sudo wg show factory all

# Or check config file
cat /etc/wireguard/factory.conf | grep -A 5 "mzHaZPGowqqzAa5tVFQJs0zoWuDVLppt44HwgdcPXkg="
```

### Step 2: Add/Update Client Peer (If Missing)

If client peer doesn't exist, add it:

```bash
# Add client peer with VPN network access
sudo wg set factory peer mzHaZPGowqqzAa5tVFQJs0zoWuDVLppt44HwgdcPXkg= allowed-ips 10.42.42.0/24

# Or if peer doesn't exist at all, add it:
sudo wg set factory peer mzHaZPGowqqzAa5tVFQJs0zoWuDVLppt44HwgdcPXkg= allowed-ips 10.42.42.0/24 endpoint <client-endpoint>
```

### Step 3: Update Device Peers (For Development)

For development, allow devices to communicate with entire VPN network:

```bash
# Update Device 1
sudo wg set factory peer 7RI5ZqxHy0MbtowYH1lcnBLoP7Zx+AtcPWq4kD2UPU0= allowed-ips 10.42.42.0/24

# Update Device 2
sudo wg set factory peer ueiKEbnBWnbkNePceOxbz6q9NnM8skS6dWZ7p1Y2Sh4= allowed-ips 10.42.42.0/24
```

**Note:** For production, use more restrictive allowed-ips (only specific IPs needed).

### Step 4: Enable IP Forwarding

```bash
# Check current setting
cat /proc/sys/net/ipv4/ip_forward
# Should be: 1

# If 0, enable it:
echo 1 > /proc/sys/net/ipv4/ip_forward

# Make permanent:
echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
sysctl -p
```

### Step 5: Configure Firewall

```bash
# Check current FORWARD rules
sudo iptables -L FORWARD -n -v

# If FORWARD chain is blocking, add rules:
sudo iptables -A FORWARD -i factory -o factory -j ACCEPT
sudo iptables -A FORWARD -i factory -j ACCEPT
sudo iptables -A FORWARD -o factory -j ACCEPT

# Save rules (Debian/Ubuntu):
sudo iptables-save > /etc/iptables/rules.v4
# Or use netfilter-persistent:
sudo netfilter-persistent save
```

### Step 6: Save WireGuard Configuration

```bash
# Save current WireGuard config
sudo wg-quick save factory

# Verify saved config
cat /etc/wireguard/factory.conf
```

### Step 7: Test Connectivity

From client machine:
```bash
# Test ping
ping -c 3 10.42.42.2
ping -c 3 10.42.42.3

# Test SSH
ssh fio@10.42.42.2
ssh fio@10.42.42.3

# Scan network
nmap -sn 10.42.42.0/24
```

## Expected Final Configuration

**Client Peer:**
```
peer: mzHaZPGowqqzAa5tVFQJs0zoWuDVLppt44HwgdcPXkg=
  allowed ips: 10.42.42.0/24  # Full VPN network access
```

**Device Peers:**
```
peer: 7RI5ZqxHy0MbtowYH1lcnBLoP7Zx+AtcPWq4kD2UPU0=
  allowed ips: 10.42.42.0/24  # Full VPN network access

peer: ueiKEbnBWnbkNePceOxbz6q9NnM8skS6dWZ7p1Y2Sh4=
  allowed ips: 10.42.42.0/24  # Full VPN network access
```

## Security Considerations

**For Development:**
- `allowed-ips: 10.42.42.0/24` - Allows full VPN network access
- Enables scanning and direct device access
- Good for debugging and development

**For Production:**
- More restrictive: Only allow specific IPs needed
- Example: `allowed-ips: 10.42.42.10/32,10.42.42.2/32` (client can only reach device 2)
- Use firewall rules for additional access control

## Troubleshooting

If still not working after fixes:

1. **Check WireGuard logs:**
   ```bash
   sudo dmesg | grep wireguard
   sudo journalctl -u wg-quick@factory
   ```

2. **Verify routing:**
   ```bash
   ip route show
   ip route get 10.42.42.2
   ```

3. **Test packet capture:**
   ```bash
   sudo tcpdump -i factory -n host 10.42.42.2
   # In another terminal: ping 10.42.42.2
   ```

4. **Check peer handshakes:**
   ```bash
   sudo wg show factory
   # Check "latest handshake" times - should be recent
   ```
