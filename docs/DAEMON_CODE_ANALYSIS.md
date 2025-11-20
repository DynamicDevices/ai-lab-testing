# Factory WireGuard Daemon Code Analysis

## Repository

Yes, this code is from: https://github.com/foundriesio/factory-wireguard-server

## Key Functions

### 1. `gen_conf()` - Line ~240-270
Generates WireGuard configuration file with:
- AllowedIPs = 10.42.42.0/24 (after our modification on line 257)

### 2. `apply_conf()` - Line ~269-310
Applies the generated configuration using `wg-quick up`.

**THE PROBLEM IS HERE:**
- Calls `wg-quick up factory` which applies config
- If peers already exist with endpoints, WireGuard clears AllowedIPs
- No code to remove peers before applying config

### 3. `daemon()` - Line ~493-530
Main loop that:
- Periodically checks for config changes
- Calls `apply_conf()` when changes detected
- Runs every 5 minutes (default)

## Root Cause

The `apply_conf()` function uses `wg-quick up` which:
1. Reads config file (has AllowedIPs = 10.42.42.0/24)
2. Uses `wg setconf` to apply peers
3. BUT: If peers already have endpoints, WireGuard clears AllowedIPs

## Solution

Modify `apply_conf()` to:
1. Remove existing device peers BEFORE calling `wg-quick up`
2. Then apply config (peers added without endpoints)
3. Devices reconnect and add endpoints, preserving AllowedIPs

## Code Location

File: `/root/factory-wireguard-server/factory-wireguard.py`
Function: `apply_conf()` around line 269-310
