# WireGuard Connectivity Investigation Guide

## Problem
Client (10.42.42.10) cannot reach devices (10.42.42.2, 10.42.42.3) directly.
Devices ARE reachable from gateway container (10.42.42.1).

## Investigation Steps

### Step 1: Check WireGuard Server Configuration

On WireGuard server (`root@wireguard`):

```bash
# Check all peers and their allowed IPs
sudo wg show factory

# Expected output should show:
# - Client peer (10.42.42.10) with allowed-ips
# - Device peers (10.42.42.2, 10.42.42.3) with allowed-ips
# - Check if client's allowed-ips includes device network
```

**Key Check:** Does client peer have `allowed-ips` that include device IPs?
- If client has `allowed-ips: 10.42.42.10/32` only → Problem!
- Should have `allowed-ips: 10.42.42.0/24` or at least device IPs

### Step 2: Check IP Forwarding on Server

```bash
# Check if IP forwarding is enabled
cat /proc/sys/net/ipv4/ip_forward

# Should be: 1
# If 0, enable it:
echo 1 > /proc/sys/net/ipv4/ip_forward
# Make permanent:
echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
sysctl -p
```

### Step 3: Check Firewall Rules

```bash
# Check iptables rules
sudo iptables -L -n -v
sudo iptables -t nat -L -n -v

# Check FORWARD chain (critical for routing between peers)
sudo iptables -L FORWARD -n -v

# Check if there are rules blocking client-to-device traffic
# Look for rules that might drop packets between 10.42.42.10 and 10.42.42.2/3
```

**Common Issues:**
- FORWARD chain default policy is DROP
- Missing rules to allow VPN network traffic
- NAT rules interfering

### Step 4: Check WireGuard Peer Connectivity

On client machine:

```bash
# Check WireGuard status
sudo wg show foundries

# Should show:
# - Server peer with endpoint
# - Latest handshake time
# - Transfer stats
```

On server:

```bash
# Check if client peer is connected
sudo wg show factory | grep -A 5 "10.42.42.10"

# Check handshake times - should be recent (< 2 minutes)
```

### Step 5: Test Routing

On client:

```bash
# Check routes
ip route | grep 10.42.42

# Should show route to 10.42.42.0/24 via foundries interface

# Test traceroute
traceroute -n 10.42.42.2
# Should show path through VPN

# Test with tcpdump (if available)
sudo tcpdump -i foundries -n host 10.42.42.2
# In another terminal: ping 10.42.42.2
# Check if packets are sent but not received
```

### Step 6: Check WireGuard AllowedIPs Configuration

**Critical:** WireGuard peers can only communicate if their `allowed-ips` overlap.

**On Server - Check Client Peer:**
```bash
sudo wg show factory | grep -A 3 "mzHaZPGowqqzAa5tVFQJs0zoWuDVLppt44HwgdcPXkg="
# (Your client's public key)

# Check allowed-ips - should include device network:
# allowed ips: 10.42.42.10/32  # Current (too restrictive!)
# Should be: 10.42.42.0/24 or 10.42.42.10/32,10.42.42.0/24
```

**On Server - Check Device Peers:**
```bash
sudo wg show factory | grep -A 3 "10.42.42.2"
sudo wg show factory | grep -A 3 "10.42.42.3"

# Check allowed-ips - should allow communication with client
```

### Step 7: Fix WireGuard AllowedIPs (Most Likely Fix)

If client peer has restrictive `allowed-ips`, update it:

```bash
# On server, update client peer to allow full VPN network access
sudo wg set factory peer mzHaZPGowqqzAa5tVFQJs0zoWuDVLppt44HwgdcPXkg= allowed-ips 10.42.42.0/24

# Or more restrictive but still allows device access:
sudo wg set factory peer mzHaZPGowqqzAa5tVFQJs0zoWuDVLppt44HwgdcPXkg= allowed-ips 10.42.42.10/32,10.42.42.0/24

# Save configuration
sudo wg-quick save factory
```

### Step 8: Fix Firewall Rules (If Needed)

If firewall is blocking, add rules:

```bash
# Allow forwarding between VPN peers
sudo iptables -A FORWARD -i factory -o factory -j ACCEPT
sudo iptables -A FORWARD -i factory -j ACCEPT
sudo iptables -A FORWARD -o factory -j ACCEPT

# Save rules (method depends on system)
# For Debian/Ubuntu:
sudo iptables-save > /etc/iptables/rules.v4
# Or use netfilter-persistent
```

## Expected Configuration

### WireGuard Server Peer Configuration

**Client Peer:**
```
peer: <client-public-key>
  allowed ips: 10.42.42.0/24  # Allows access to entire VPN network
  # OR more restrictive:
  # allowed ips: 10.42.42.10/32,10.42.42.0/24
```

**Device Peers:**
```
peer: <device1-public-key>
  allowed ips: 10.42.42.2/32

peer: <device2-public-key>
  allowed ips: 10.42.42.3/32
```

### Routing

- Server: IP forwarding enabled (`net.ipv4.ip_forward=1`)
- Server: Firewall allows FORWARD between VPN peers
- Client: Route to 10.42.42.0/24 via foundries interface
- Devices: Route to 10.42.42.0/24 via WireGuard interface

## Testing After Fix

```bash
# From client:
ping 10.42.42.2
ping 10.42.42.3
ssh fio@10.42.42.2
ssh fio@10.42.42.3

# Scan VPN network:
nmap -sn 10.42.42.0/24
```

## Security Considerations

**For Development:**
- Allow full VPN network access: `allowed-ips: 10.42.42.0/24`
- Enable IP forwarding
- Allow FORWARD between VPN peers

**For Production:**
- More restrictive: Only allow specific device IPs
- Use firewall rules to limit access
- Monitor traffic

## Next Steps

1. Run investigation steps above
2. Identify the specific issue (likely allowed-ips or firewall)
3. Apply fix
4. Test connectivity
5. Document final configuration
