# Simple WireGuard Configuration for Development

## Goal
Enable all devices and clients to communicate with each other on the VPN network.

## Simple Configuration

### All Peers: Use Full VPN Network Access

**For Development:** Set all peers to `allowed-ips: 10.42.42.0/24`

This allows:
- ✅ Client can reach all devices
- ✅ Devices can reach client
- ✅ Devices can reach each other
- ✅ Network scanning works
- ✅ Full development access

## One-Command Setup

Run this on the gateway container (`root@wireguard`):

```bash
# Add/update client peer
sudo wg set factory peer mzHaZPGowqqzAa5tVFQJs0zoWuDVLppt44HwgdcPXkg= allowed-ips 10.42.42.0/24

# Update device peers
sudo wg set factory peer 7RI5ZqxHy0MbtowYH1lcnBLoP7Zx+AtcPWq4kD2UPU0= allowed-ips 10.42.42.0/24
sudo wg set factory peer ueiKEbnBWnbkNePceOxbz6q9NnM8skS6dWZ7p1Y2Sh4= allowed-ips 10.42.42.0/24

# Enable IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward
echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
sysctl -p

# Allow forwarding between VPN peers (if firewall is blocking)
sudo iptables -A FORWARD -i factory -o factory -j ACCEPT 2>/dev/null || true

# Save configuration
sudo wg-quick save factory
```

## Verify

```bash
sudo wg show factory
```

Should show all peers with `allowed ips: 10.42.42.0/24`

## Test

From client:
```bash
ping 10.42.42.2
ping 10.42.42.3
ssh fio@10.42.42.2
nmap -sn 10.42.42.0/24
```

## That's It!

For development, this simple configuration enables full VPN network communication.
No complex routing rules, no restrictive allowed-ips - just full network access.

## For Production Later

When moving to production, you can restrict allowed-ips:
- Client: `allowed-ips: 10.42.42.10/32,10.42.42.2/32` (only specific devices)
- Devices: `allowed-ips: 10.42.42.2/32` (only own IP)

But for development, `10.42.42.0/24` is simplest and works best.
