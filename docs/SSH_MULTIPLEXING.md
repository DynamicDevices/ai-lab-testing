# SSH Multiplexing Best Practice

## Overview

SSH multiplexing (ControlMaster) allows reusing a single SSH connection for multiple commands, significantly improving performance and reducing authentication overhead.

## Benefits

- ✅ **Faster**: Subsequent commands reuse existing connection (no handshake delay)
- ✅ **Efficient**: Single authentication for multiple commands
- ✅ **Reliable**: Connection persists for 5 minutes (300 seconds)
- ✅ **Automatic**: Falls back to new connection if master is unavailable

## Setup

### 1. Create Control Directory

```bash
mkdir -p ~/.ssh/controlmasters
chmod 700 ~/.ssh/controlmasters
```

### 2. Add to SSH Config

Add to `~/.ssh/config`:

```
Host wireguard-server
    HostName proxmox.dynamicdevices.co.uk
    Port 5025
    User root
    ControlMaster yes
    ControlPath ~/.ssh/controlmasters/%h-%p-%r
    ControlPersist 300
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
```

### 3. Use in Commands

**With SSH config:**
```bash
ssh wireguard-server "command"
```

**With command-line options:**
```bash
ssh -o ControlMaster=yes \
    -o ControlPath=~/.ssh/controlmasters/%h-%p-%r \
    -o ControlPersist=300 \
    -p 5025 root@proxmox.dynamicdevices.co.uk "command"
```

**With sshpass:**
```bash
# First connection (establishes master)
sshpass -p 'password' ssh -o ControlMaster=yes \
    -o ControlPath=~/.ssh/controlmasters/%h-%p-%r \
    -o ControlPersist=300 \
    -p 5025 root@host "command"

# Subsequent connections (reuse master)
ssh -o ControlPath=~/.ssh/controlmasters/%h-%p-%r \
    -p 5025 root@host "command"
```

## ControlMaster Options Explained

- **ControlMaster yes**: Enable connection sharing
- **ControlPath**: Path template for control socket
  - `%h`: Hostname
  - `%p`: Port
  - `%r`: Username
- **ControlPersist 300**: Keep master connection alive for 300 seconds (5 minutes)

## Best Practices

1. **Always use multiplexing** for repeated SSH connections to the same host
2. **Set ControlPersist** to reasonable value (300-600 seconds)
3. **Use unique ControlPath** per host/port/user combination
4. **Clean up old sockets** if needed: `rm ~/.ssh/controlmasters/*`

## Example: WireGuard Server

For the WireGuard server at `proxmox.dynamicdevices.co.uk:5025`:

```bash
# Establish master connection
sshpass -p 'decafbad00' ssh -o ControlMaster=yes \
    -o ControlPath=~/.ssh/controlmasters/%h-%p-%r \
    -o ControlPersist=300 \
    -o StrictHostKeyChecking=no \
    -p 5025 root@proxmox.dynamicdevices.co.uk "hostname"

# Reuse connection (no password needed)
ssh -o ControlPath=~/.ssh/controlmasters/%h-%p-%r \
    -p 5025 root@proxmox.dynamicdevices.co.uk "wg show factory"
```

## Troubleshooting

**Connection refused:**
- Master connection may have expired
- Re-establish master connection

**Permission denied:**
- Check ControlPath directory permissions
- Ensure `~/.ssh/controlmasters` exists and is writable

**Stale connections:**
```bash
# List active control sockets
ls -la ~/.ssh/controlmasters/

# Remove stale sockets
rm ~/.ssh/controlmasters/*
```
