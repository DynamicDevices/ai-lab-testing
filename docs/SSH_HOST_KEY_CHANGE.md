# SSH Host Key Change - Troubleshooting Guide

## Problem

When connecting to devices via SSH, you may see:
```
WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!
Host key for 10.42.42.X has changed and you have requested strict checking.
```

## Why This Happens

SSH host keys can change when:
- Device firmware is updated/reinstalled
- Device is factory reset
- Device's SSH keys are regenerated
- Device is replaced with a different device at the same IP

SSH stores known host keys in `~/.ssh/known_hosts` to prevent man-in-the-middle attacks. When a key changes, SSH warns you.

## Solution

### Quick Fix (Remove Old Key)

From the gateway container or your local machine:

```bash
# Remove old key for specific IP
ssh-keygen -f ~/.ssh/known_hosts -R "10.42.42.3"

# Or remove old key for hostname
ssh-keygen -f ~/.ssh/known_hosts -R "imx8mm-jaguar-inst-5120a09dab86563"
```

Then connect again - SSH will prompt to accept the new key:
```bash
ssh fio@10.42.42.3
# Type "yes" when prompted to accept new key
```

### For Gateway Container

If you're on the gateway container (`root@wireguard`):

```bash
# Remove old key
ssh-keygen -f /root/.ssh/known_hosts -R "10.42.42.3"

# Connect again (will prompt for new key)
ssh fio@10.42.42.3
```

### Automated Fix (If Needed)

You can also remove the offending line directly:
```bash
# Remove line 32 (as shown in error message)
sed -i '32d' ~/.ssh/known_hosts
```

## Security Considerations

**When to be concerned:**
- If you're connecting to a device you've been using regularly and the key changes unexpectedly
- If you're on an untrusted network
- If multiple devices show key changes at once

**When it's normal:**
- After firmware updates
- After device reinstallation
- After factory reset
- When connecting to a device for the first time from a new location

## Best Practices

1. **Accept new keys after firmware updates** - Expected behavior
2. **Verify device identity** - Use `verify_device_identity()` tool if available
3. **Use SSH keys for authentication** - More secure than passwords
4. **Keep known_hosts clean** - Remove old entries for devices that have been replaced

## For Foundries Devices

Foundries devices may have their SSH keys regenerated during:
- OTA updates
- Factory reset
- Device reconfiguration

This is normal and expected. Simply remove the old key and accept the new one.
