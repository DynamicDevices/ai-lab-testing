# Foundries.io VPN Research

**Date:** 2025-11-18  
**Purpose:** Research Foundries.io VPN capabilities and integration approach

## Overview

Foundries.io provides a WireGuard-based VPN solution for secure remote access to devices. Unlike standard WireGuard (peer-to-peer), Foundries uses a **server-based architecture** where devices connect to a centralized VPN server managed by FoundriesFactory.

## Key Differences from Standard WireGuard

| Aspect | Standard WireGuard | Foundries VPN |
|--------|-------------------|--------------|
| **Architecture** | Peer-to-peer | Server-based (centralized) |
| **Configuration** | Manual config files | Managed via FoundriesFactory |
| **Device Management** | Manual peer management | Automated via `fioctl` |
| **Server Location** | User-managed | Foundries-managed or self-hosted |
| **Connection Model** | Direct device-to-device | Device → VPN Server → Client |

## Architecture

```
┌─────────────┐         ┌──────────────────┐         ┌─────────────┐
│   Client    │────────▶│  VPN Server      │────────▶│   Device    │
│  (Engineer) │         │  (Foundries)     │         │  (Board)    │
└─────────────┘         └──────────────────┘         └─────────────┘
                              │
                              │ Manages connections
                              │ Updates /etc/hosts
                              │
                        ┌─────┴─────┐
                        │ fioctl   │
                        │ Commands │
                        └──────────┘
```

## Components

### 1. VPN Server (`factory-wireguard-server`)

- **Location:** GitHub repository: `foundriesio/factory-wireguard-server`
- **Purpose:** Centralized VPN server that manages device connections
- **Features:**
  - Monitors connected devices
  - Updates `/etc/hosts` for easy device access
  - Integrates with FoundriesFactory OAuth2
  - Manages WireGuard peer configurations

### 2. Device Configuration

Devices are configured via `fioctl` commands:

```bash
# Enable WireGuard on a device
fioctl devices config wireguard <device> enable

# Disable WireGuard on a device
fioctl devices config wireguard <device> disable
```

### 3. Client Connection

Clients connect through the VPN server to access devices:

```bash
# SSH to device through VPN server
ssh <device>
```

## Setup Process

### Server Setup (Foundries-Managed or Self-Hosted)

1. **Install Dependencies:**
   ```bash
   sudo apt install git wireguard wireguard-tools python3 python3-requests iptables
   ```

2. **Clone VPN Server Repository:**
   ```bash
   git clone https://github.com/foundriesio/factory-wireguard-server/
   cd factory-wireguard-server
   ```

3. **Configure Factory:**
   ```bash
   sudo ./factory-wireguard.py \
     --oauthcreds /root/fiocreds.json \
     --factory <factory> \
     --privatekey /root/wgpriv.key \
     enable
   ```

4. **Run Daemon:**
   ```bash
   sudo ./factory-wireguard.py \
     --oauthcreds /root/fiocreds.json \
     --factory <factory> \
     --privatekey /root/wgpriv.key \
     daemon
   ```

### Device Setup

1. **Enable WireGuard on Device:**
   ```bash
   fioctl devices config wireguard <device> enable
   ```

2. **Wait for Configuration** (up to 5 minutes for OTA update)

3. **Device Connects to VPN Server**

### Client Setup

1. **Obtain VPN Configuration** from FoundriesFactory
2. **Import WireGuard Config** (standard WireGuard client)
3. **Connect to VPN Server**
4. **Access Devices** via SSH through VPN server

## Key Features

### Security
- **Encryption:** WireGuard protocol ensures secure, encrypted communication
- **Centralized Management:** All connections managed through VPN server
- **OAuth2 Integration:** Uses FoundriesFactory OAuth2 for authentication

### Performance
- **High Speed:** WireGuard's efficient protocol
- **Low Overhead:** Minimal performance impact
- **Scalable:** Server-based architecture supports many devices

### Management
- **Automated:** Device configuration via `fioctl` commands
- **Dynamic:** Server updates `/etc/hosts` automatically
- **Flexible:** Can be self-hosted or Foundries-managed

## Integration with MCP Server

### Current State

The MCP server currently supports **standard WireGuard VPN**:
- Direct peer-to-peer connections
- Manual configuration files
- Standard WireGuard tools (`wg`, `wg-quick`)

### Foundries VPN Integration Requirements

To support Foundries VPN, we would need:

1. **fioctl Integration:**
   - `fioctl devices config wireguard <device> enable/disable`
   - `fioctl devices list` (to discover devices)
   - `fioctl devices config wireguard <device> show` (to get device VPN status)

2. **VPN Server Connection:**
   - Connect to Foundries VPN server (not direct device connection)
   - Handle VPN server authentication (OAuth2)
   - Manage WireGuard config from FoundriesFactory

3. **Device Discovery:**
   - Discover devices via FoundriesFactory API
   - List devices connected to VPN server
   - Access devices through VPN server (not direct IP)

4. **New Tools Needed:**
   - `foundries_vpn_status` - Check Foundries VPN connection status
   - `connect_foundries_vpn` - Connect to Foundries VPN server
   - `list_foundries_devices` - List devices accessible via Foundries VPN
   - `enable_foundries_vpn_device` - Enable VPN on a device via fioctl
   - `disable_foundries_vpn_device` - Disable VPN on a device via fioctl

## Implementation Considerations

### Advantages
- ✅ **Centralized Management:** All devices managed through one VPN server
- ✅ **Automated Configuration:** Devices configured via `fioctl` commands
- ✅ **Scalability:** Server-based architecture supports many devices
- ✅ **Security:** OAuth2 authentication and WireGuard encryption
- ✅ **Integration:** Works seamlessly with FoundriesFactory

### Challenges
- ⚠️ **Dependency on fioctl:** Requires `fioctl` CLI tool installed and configured
- ⚠️ **VPN Server Required:** Need access to Foundries VPN server
- ⚠️ **Different Architecture:** Different from standard WireGuard (peer-to-peer)
- ⚠️ **OTA Dependency:** Device configuration changes require OTA update (up to 5 minutes)
- ⚠️ **OAuth2 Credentials:** Need FoundriesFactory OAuth2 credentials

### Compatibility

**Can Coexist with Standard WireGuard:**
- Standard WireGuard: Direct peer-to-peer connections
- Foundries VPN: Server-based connections
- Both can be used simultaneously (different interfaces/configs)

## Documentation References

- **Foundries Remote Access Documentation:**
  - https://beta-docs.foundries.io/latest/reference-manual/remote-access/remote-access.html
  - https://docs.foundries.io/latest/reference-manual/remote-access/wireguard.html

- **VPN Server Repository:**
  - https://github.com/foundriesio/factory-wireguard-server

## Next Steps

1. **Evaluate Requirements:**
   - Determine if Foundries VPN is needed for current use cases
   - Assess whether standard WireGuard is sufficient
   - Consider if both VPN types need to be supported

2. **If Implementing Foundries VPN:**
   - Install and configure `fioctl` CLI tool
   - Set up FoundriesFactory OAuth2 credentials
   - Implement Foundries VPN tools (status, connect, device management)
   - Test with Foundries devices
   - Document Foundries VPN setup process

3. **Integration Approach:**
   - Add Foundries VPN as separate tool category
   - Keep standard WireGuard tools for direct connections
   - Provide clear documentation on when to use which VPN type
   - Update help system with Foundries VPN guidance

## Conclusion

Foundries VPN uses WireGuard but with a **server-based architecture** rather than peer-to-peer. It requires:
- VPN server (Foundries-managed or self-hosted)
- `fioctl` CLI tool for device management
- FoundriesFactory OAuth2 credentials
- Different connection model (through VPN server, not direct)

**Recommendation:** Implement Foundries VPN support as a separate tool category, keeping standard WireGuard for direct peer-to-peer connections. This allows users to choose the appropriate VPN type based on their infrastructure.

