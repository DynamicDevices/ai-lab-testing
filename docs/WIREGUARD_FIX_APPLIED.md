# WireGuard AllowedIPs Fix Applied

## Problem
WireGuard was clearing AllowedIPs when peers reconnected with endpoints, preventing device-to-device communication.

## Solution Applied

### 1. Updated `apply_conf()` Function
- Added 3-second sleep after removing peers to prevent immediate reconnection
- Uses `wg syncconf` first (preserves interface state better)
- Falls back to `wg-quick up/down` if syncconf fails
- Removes all device peers before applying config when `allow_device_to_device` is enabled

### 2. Manual Fix Applied
- Removed all peers
- Applied config fresh
- Added client peer with AllowedIPs = 10.42.42.0/24
- Fixed device peers AllowedIPs
- Saved config to persist changes

### 3. Daemon Restarted
- Daemon restarted with updated code
- Should now properly handle peer reconnections

## Testing
- Server (10.42.42.1): Testing...
- Device 1 (10.42.42.2): Testing...
- Device 2 (10.42.42.3): Testing...

## Next Steps
Monitor daemon logs to ensure AllowedIPs persist through sync cycles.
