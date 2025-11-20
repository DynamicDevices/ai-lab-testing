# Server Access Alternatives to tmate

## Problem
tmate requires an interactive terminal session, blocking non-interactive SSH commands.

## Solutions

### Option 1: Regular SSH Access
If you have SSH keys set up to the WireGuard server:
```bash
ssh root@proxmox.dynamicdevices.co.uk
# Or whatever your SSH access is
```

Then I can potentially use SSH tools if configured in the environment.

### Option 2: Diagnostic Script + File Share (RECOMMENDED)
Create a script that outputs diagnostic info to a file:

**On the server:**
```bash
cat > /tmp/diagnose.sh << 'SCRIPT'
#!/bin/bash
{
  echo "=== WireGuard Diagnostic Output ==="
  echo "Generated: $(date)"
  echo ""
  echo "=== 1. Config File ==="
  cat /etc/wireguard/factory.conf
  echo ""
  echo "=== 2. WireGuard Status ==="
  wg show factory
  echo ""
  echo "=== 3. Daemon Status ==="
  systemctl status factory-vpn-dynamic-devices.service --no-pager -l
  echo ""
  echo "=== 4. Recent Daemon Logs ==="
  journalctl -u factory-vpn-dynamic-devices.service -n 50 --no-pager
  echo ""
  echo "=== 5. Daemon Process ==="
  ps aux | grep factory-wireguard | grep -v grep
  echo ""
  echo "=== 6. IP Forwarding ==="
  cat /proc/sys/net/ipv4/ip_forward
  echo ""
  echo "=== 7. Firewall Rules ==="
  iptables -L FORWARD -n -v
} > /tmp/diagnostic_output.txt 2>&1

cat /tmp/diagnostic_output.txt
SCRIPT

chmod +x /tmp/diagnose.sh
/tmp/diagnose.sh
```

Then share the contents of `/tmp/diagnostic_output.txt`.

### Option 3: Simple HTTP Server
If Python is available on the server:

**On the server:**
```bash
# Create diagnostic file
/tmp/diagnose.sh > /tmp/diagnostic_output.txt

# Serve it via HTTP
cd /tmp
python3 -m http.server 8000
```

Then access `http://proxmox.dynamicdevices.co.uk:8000/diagnostic_output.txt` (if firewall allows).

### Option 4: gotty (Terminal Sharing)
Install gotty for browser-based terminal access:

**On the server:**
```bash
wget https://github.com/sorenduan/gotty/releases/download/v1.5.0/gotty_v1.5.0_linux_amd64.tar.gz
tar -xzf gotty_v1.5.0_linux_amd64.tar.gz
./gotty -w -p 8000 bash
```

Then access via browser at `http://proxmox.dynamicdevices.co.uk:8000` (if firewall allows).

### Option 5: netcat Reverse Shell
More complex, requires coordination and firewall access.

## Recommended Approach

**Use Option 2 (Diagnostic Script)** - it's:
- ✅ No additional tools needed
- ✅ Works immediately
- ✅ Provides all needed information
- ✅ Easy to share output

Just run the script and share the output!
