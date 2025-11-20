#!/bin/bash
# VPN Connectivity Test Script

echo "=== Foundries VPN Connectivity Test ==="
echo ""

# Check VPN is connected
if ip addr show foundries >/dev/null 2>&1; then
    VPN_IP=$(ip addr show foundries | grep "inet " | awk '{print $2}' | cut -d/ -f1)
    echo "✅ VPN Connected: $VPN_IP"
else
    echo "❌ VPN Not Connected"
    exit 1
fi

echo ""
echo "=== Testing Known Devices ==="
echo ""

# Test each known device
devices=(
    "10.42.42.1:Server/Gateway"
    "10.42.42.2:Device-1-Sentai"
    "10.42.42.3:Device-2-INST"
)

for device in "${devices[@]}"; do
    IFS=':' read -r ip name <<< "$device"
    echo "Testing $name ($ip):"
    
    # Ping test
    if timeout 2 ping -c 1 -W 1 "$ip" >/dev/null 2>&1; then
        echo "  Ping: ✅ UP"
    else
        echo "  Ping: ❌ DOWN"
    fi
    
    # SSH port test
    if timeout 2 bash -c "echo > /dev/tcp/$ip/22" 2>/dev/null; then
        echo "  SSH: ✅ Port 22 open"
        
        # Try SSH connection
        if timeout 3 ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no -o BatchMode=yes fio@"$ip" "hostname" 2>/dev/null; then
            echo "  SSH Auth: ✅ Connected"
        else
            echo "  SSH Auth: ⚠️  Port open but auth failed/timeout"
        fi
    else
        echo "  SSH: ❌ Port 22 closed/timeout"
    fi
    echo ""
done

echo "=== Network Scan ==="
echo "Scanning 10.42.42.0/24 for active hosts..."
nmap -sn 10.42.42.0/24 2>&1 | grep -E "Nmap scan|10\.42\.42\.[0-9]+" | head -15
