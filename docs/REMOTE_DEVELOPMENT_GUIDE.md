# Remote Development Guide

**Purpose:** Complete guide for engineers doing remote embedded hardware development using this MCP server.

## Overview

This MCP server is designed to make remote hardware development as easy as possible. Whether you're working from home, a different office, or traveling, you should be able to:

- Discover and connect to lab devices effortlessly
- Set up secure access (SSH keys, passwordless sudo) with minimal friction
- Run commands and tests on remote boards without complex setup
- Build and deploy applications to remote devices
- Clean up securely when finished

The tools provide intelligent guidance, suggest next steps, and handle common workflows automatically.

---

## Complete Remote Development Workflow

### 1. Connect to VPN

**Goal:** Establish secure connection to the lab network.

```python
# Check VPN status
vpn_status()

# Connect if needed
connect_vpn()
```

**Best Practice:** Always check VPN status before attempting device access.

---

### 2. Discover Available Devices

**Goal:** Find and identify boards/devices you want to work with.

```python
# List all devices
list_devices()

# Filter by type (e.g., sentai_board, eink_board)
list_devices(device_type_filter="sentai_board")

# Filter by status (online, offline, discovered)
list_devices(status_filter="online")

# Search by IP or name
list_devices(search_query="192.168.2.18")

# Sort results
list_devices(sort_by="ip", sort_order="asc")
```

**Best Practice:** Use filters and search to quickly find your target device.

---

### 3. Test Device Connectivity

**Goal:** Verify the device is reachable before operations.

```python
# Test connectivity (ping + SSH check)
test_device(device_id="my-device")
```

**Best Practice:** Always test connectivity before running operations.

---

### 4. Set Up Secure Access

**Goal:** Enable passwordless SSH and sudo for convenient development.

#### Step 4a: Cache Credentials (if needed)

```python
# Cache SSH credentials (if password needed for initial setup)
cache_device_credentials(
    device_id="my-device",
    username="fio",
    password="your-password"
)
```

**When to use:** Only if you need to provide a password for SSH key installation.

#### Step 4b: Check SSH Key Status

```python
# Check if SSH key is already installed
check_ssh_key_status(device_id="my-device")
```

**What to look for:**
- `key_installed: true` → SSH key already working, skip to Step 4c
- `key_installed: false` → Need to install SSH key (Step 4c)

#### Step 4c: Install SSH Key

```python
# Install SSH public key for passwordless access
install_ssh_key(device_id="my-device")
```

**What happens:**
- Uses your default SSH key (`~/.ssh/id_rsa.pub` or `~/.ssh/id_ed25519.pub`)
- Installs it on the device's `~/.ssh/authorized_keys`
- Uses cached credentials if password needed

**Next Steps:** The tool will suggest testing SSH access.

#### Step 4d: Enable Passwordless Sudo (for testing convenience)

```python
# Enable passwordless sudo for testing/debugging
enable_passwordless_sudo(device_id="my-device")
```

**What happens:**
- Creates `/etc/sudoers.d/{username}` file
- Validates with `visudo` before applying
- Allows sudo commands without password

**Important:** Remember to disable when finished (see Cleanup section).

---

### 5. Verify Setup

**Goal:** Confirm everything is working.

```python
# Test SSH access
ssh_to_device(device_id="my-device", command="whoami")

# Test passwordless sudo
ssh_to_device(device_id="my-device", command="sudo whoami")
```

**Expected Results:**
- SSH command returns your username
- Sudo command returns `root` without password prompt

---

### 6. Run Development Tasks

**Goal:** Execute commands, copy files, build and test applications.

#### Run Commands

```python
# Execute any command
ssh_to_device(device_id="my-device", command="uptime")
ssh_to_device(device_id="my-device", command="ls -la")
ssh_to_device(device_id="my-device", command="cat /etc/os-release")
```

#### Check System Status

```python
# Get comprehensive system status
get_system_status(device_id="my-device")

# Get firmware version
get_firmware_version(device_id="my-device")
```

#### Deploy Containers (Foundries.io devices)

```python
# List existing containers
list_containers(device_id="my-device")

# Deploy new container
deploy_container(
    device_id="my-device",
    container_name="my-app",
    image="my-registry/my-app:latest"
)
```

#### Monitor Power Consumption

```python
# Start power monitoring
start_power_monitoring(
    device_id="my-device",
    test_name="my-test",
    duration=300
)

# Get power logs
get_power_logs(test_name="my-test")
```

---

### 7. Clean Up When Finished

**Goal:** Restore device security settings.

#### Step 7a: Disable Passwordless Sudo

```python
# Disable passwordless sudo (restore security)
disable_passwordless_sudo(device_id="my-device")
```

**Why:** Passwordless sudo is convenient for development but should be disabled when finished.

**Verification:**
```python
# Should fail (requires password)
ssh_to_device(device_id="my-device", command="sudo -n whoami")
```

#### Step 7b: (Optional) Remove SSH Key

**Note:** SSH keys are generally safe to leave installed. Only remove if:
- Device is being returned/reassigned
- Security policy requires removal
- You want to force password authentication

**Manual removal:** SSH to device and edit `~/.ssh/authorized_keys` on the device.

---

## Common Workflows

### Quick Device Check

```python
# 1. Check VPN
vpn_status()

# 2. List devices
list_devices()

# 3. Test device
test_device(device_id="my-device")
```

### Setting Up a New Device

```python
# 1. Connect VPN
connect_vpn()

# 2. Find device
list_devices(search_query="192.168.2.18")

# 3. Test connectivity
test_device(device_id="new-device")

# 4. Set up credentials
cache_device_credentials(device_id="new-device", username="fio", password="fio")
install_ssh_key(device_id="new-device")
enable_passwordless_sudo(device_id="new-device")

# 5. Verify
ssh_to_device(device_id="new-device", command="whoami")
ssh_to_device(device_id="new-device", command="sudo whoami")
```

### Daily Development Session

```python
# 1. Connect VPN
connect_vpn()

# 2. Find your device
list_devices(device_type_filter="sentai_board")

# 3. Quick connectivity check
test_device(device_id="my-device")

# 4. Run your commands
ssh_to_device(device_id="my-device", command="cd /app && make")
ssh_to_device(device_id="my-device", command="sudo systemctl restart my-service")

# 5. When done
disable_passwordless_sudo(device_id="my-device")
```

---

## Troubleshooting

### VPN Not Connecting

**Symptoms:** Cannot reach devices, `list_devices` shows no devices.

**Solutions:**
1. Check VPN config: `list_vpn_configs()` or `vpn_setup_instructions()`
2. Try NetworkManager method: `setup_networkmanager_vpn()`
3. Check VPN config path: Verify `VPN_CONFIG_PATH` environment variable

### Device Not Found

**Symptoms:** `device_id` not recognized, device not in list.

**Solutions:**
1. List all devices: `list_devices()` to see available options
2. Check spelling: Device IDs are case-sensitive
3. Use friendly name: Try the device's `friendly_name` instead
4. Force refresh: `list_devices(force_refresh=true)` to rescan
5. In DHCP environments: Use `verify_device_identity()` to ensure correct device

### SSH Fails

**Symptoms:** Cannot SSH to device, authentication errors.

**Solutions:**
1. Check SSH key status: `check_ssh_key_status(device_id)`
2. Install SSH key: `install_ssh_key(device_id)`
3. Cache credentials: `cache_device_credentials(device_id, username, password)`
4. Verify device online: `test_device(device_id)`
5. Check VPN: `vpn_status()`
6. Check SSH status in device list: `list_devices(ssh_status_filter="error")`

### Sudo Fails

**Symptoms:** Sudo commands require password or fail.

**Solutions:**
1. Check if passwordless sudo enabled: Try `ssh_to_device(device_id, "sudo -n whoami")`
2. Enable passwordless sudo: `enable_passwordless_sudo(device_id)`
3. Verify SSH key installed: `check_ssh_key_status(device_id)`
4. Check user has sudo permissions on device

---

## Best Practices

### Security

- ✅ **Use SSH keys** instead of passwords when possible
- ✅ **Enable passwordless sudo** only when needed for testing
- ✅ **Disable passwordless sudo** when finished
- ✅ **Keep credentials secure** - they're cached in `~/.cache/ai-lab-testing/credentials.json`

### Workflow

- ✅ **Always check VPN** before accessing devices
- ✅ **Test connectivity** before running operations
- ✅ **Use device filters** to quickly find targets
- ✅ **Follow the setup workflow** (VPN → Discover → Test → Setup → Use → Cleanup)

### Development

- ✅ **Use descriptive test names** for power monitoring
- ✅ **Verify operations** after setup (test SSH, test sudo)
- ✅ **Clean up when finished** (disable passwordless sudo)
- ✅ **Check device status** regularly (`get_system_status`)

---

## Getting Help

### Help Documentation

```python
# Get comprehensive help
help()  # or help(topic="all")

# Get help for specific topics
help(topic="workflows")
help(topic="troubleshooting")
help(topic="best_practices")
```

### Error Messages

All tools provide helpful error messages with:
- **Suggestions:** What to try next
- **Related Tools:** Tools that might help
- **Next Steps:** Clear action items

### Resources

- **Device Inventory:** `device://inventory` - All configured devices
- **Network Status:** `network://status` - VPN and network info
- **Health Status:** `health://status` - Server health and metrics

---

## Example: Complete Session

```python
# === SETUP PHASE ===

# 1. Connect VPN
vpn_status()  # Check status
connect_vpn()  # Connect if needed

# 2. Discover devices
devices = list_devices(device_type_filter="sentai_board")
# Choose device: "test-sentai-board"

# 3. Test connectivity
test_device(device_id="test-sentai-board")

# 4. Set up credentials
check_ssh_key_status(device_id="test-sentai-board")
# If not installed:
cache_device_credentials(device_id="test-sentai-board", username="fio", password="fio")
install_ssh_key(device_id="test-sentai-board")
enable_passwordless_sudo(device_id="test-sentai-board")

# 5. Verify setup
ssh_to_device(device_id="test-sentai-board", command="whoami")
ssh_to_device(device_id="test-sentai-board", command="sudo whoami")

# === DEVELOPMENT PHASE ===

# Run your development tasks
ssh_to_device(device_id="test-sentai-board", command="cd /app && make clean")
ssh_to_device(device_id="test-sentai-board", command="cd /app && make")
ssh_to_device(device_id="test-sentai-board", command="sudo systemctl restart my-app")
ssh_to_device(device_id="test-sentai-board", command="journalctl -u my-app -n 50")

# Check system status
get_system_status(device_id="test-sentai-board")

# === CLEANUP PHASE ===

# Disable passwordless sudo
disable_passwordless_sudo(device_id="test-sentai-board")

# Verify cleanup
ssh_to_device(device_id="test-sentai-board", command="sudo -n whoami")
# Should fail (requires password) ✓
```

---

**Remember:** The tools are designed to guide you. When in doubt, check the error messages and suggestions - they'll point you in the right direction!

