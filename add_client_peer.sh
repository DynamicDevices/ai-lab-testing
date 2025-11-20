#!/bin/bash
# Script to add client peer to WireGuard server

CLIENT_PUBLIC_KEY="mzHaZPGowqqzAa5tVFQJs0zoWuDVLppt44HwgdcPXkg="
CLIENT_IP="10.42.42.10"
VPN_NETWORK="10.42.42.0/24"

echo "=== Adding Client Peer to WireGuard ==="
echo ""

# Check if peer already exists
if sudo wg show factory | grep -q "$CLIENT_PUBLIC_KEY"; then
    echo "⚠️  Client peer already exists, updating allowed-ips..."
    sudo wg set factory peer "$CLIENT_PUBLIC_KEY" allowed-ips "$VPN_NETWORK"
else
    echo "➕ Adding new client peer..."
    sudo wg set factory peer "$CLIENT_PUBLIC_KEY" allowed-ips "$VPN_NETWORK"
fi

echo ""
echo "=== Updating Device Peers for Development ==="
echo ""

# Update device peers to allow VPN network access
sudo wg set factory peer 7RI5ZqxHy0MbtowYH1lcnBLoP7Zx+AtcPWq4kD2UPU0= allowed-ips "$VPN_NETWORK"
sudo wg set factory peer ueiKEbnBWnbkNePceOxbz6q9NnM8skS6dWZ7p1Y2Sh4= allowed-ips "$VPN_NETWORK"

echo ""
echo "=== Enabling IP Forwarding ==="
echo 1 > /proc/sys/net/ipv4/ip_forward
echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
sysctl -p

echo ""
echo "=== Checking Firewall ==="
sudo iptables -L FORWARD -n -v | head -5

echo ""
echo "=== Saving Configuration ==="
sudo wg-quick save factory

echo ""
echo "=== Verification ==="
sudo wg show factory

echo ""
echo "✅ Done! Client peer should now be configured."
echo "Test from client: ping 10.42.42.2"
