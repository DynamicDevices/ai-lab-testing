#!/bin/bash
# Simple WireGuard Development Configuration (no sudo - running as root)
# Run on gateway container: root@wireguard

echo "=== Setting up WireGuard for Development ==="
echo ""

# Client peer
echo "Adding/updating client peer..."
wg set factory peer mzHaZPGowqqzAa5tVFQJs0zoWuDVLppt44HwgdcPXkg= allowed-ips 10.42.42.0/24

# Device peers
echo "Updating device peers..."
wg set factory peer 7RI5ZqxHy0MbtowYH1lcnBLoP7Zx+AtcPWq4kD2UPU0= allowed-ips 10.42.42.0/24
wg set factory peer ueiKEbnBWnbkNePceOxbz6q9NnM8skS6dWZ7p1Y2Sh4= allowed-ips 10.42.42.0/24

# IP forwarding
echo "Enabling IP forwarding..."
echo 1 > /proc/sys/net/ipv4/ip_forward
echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
sysctl -p >/dev/null 2>&1

# Firewall (allow forwarding between VPN peers)
echo "Configuring firewall..."
iptables -A FORWARD -i factory -o factory -j ACCEPT 2>/dev/null || true

# Save
echo "Saving configuration..."
wg-quick save factory

echo ""
echo "=== Verification ==="
wg show factory

echo ""
echo "✅ Done! All peers can now communicate."
echo ""
echo "Test from client:"
echo "  ping 10.42.42.2"
echo "  ssh fio@10.42.42.2"
echo "  nmap -sn 10.42.42.0/24"
