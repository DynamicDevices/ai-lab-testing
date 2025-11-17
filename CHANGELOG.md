# Changelog

[Semantic Versioning](https://semver.org/)

## [0.3.0] - 2025-11-17

### Added
- **Tasmota Power State Display**: Tasmota devices now show power state (ON/OFF) and power consumption (Watts) in the device list
- **Enhanced Device Detection**: Automatic detection of Tasmota devices and test equipment (DMMs) via network protocols
- **Device Type Detection**: Improved device type inference from hostname patterns (eink, sentai boards)
- **SSH Status Display**: Device list now shows detailed SSH connection status (OK, Timeout, Refused, Auth Failed)
- **Firmware Version Display**: Device list displays firmware version information from `/etc/os-release`
- **VPN Discovery Indicator**: Devices discovered over VPN are marked with a VPN indicator
- **Device Cache System**: JSON-based caching of device information (hostname, unique ID, firmware) to reduce repeated SSH queries
- **Friendly Name Management**: Ability to update friendly names for discovered devices via `update_device_friendly_name` tool
- **Parallel Device Identification**: Optimized device discovery with parallel SSH identification attempts

### Fixed
- **Tasmota Detection Bug**: Fixed timeout parameter in Tasmota HTTP API detection (was incorrectly passed to Request instead of urlopen)
- **SSH Authentication**: Fixed credential caching to use correct function signature (username/password parameters)
- **SSH Error Handling**: Fixed cache to re-verify devices with SSH errors but no hostname instead of returning stale errors
- **Cache Race Conditions**: Fixed cache merge logic to preserve successful identifications and prevent failures from overwriting successes
- **Host Key Verification**: Improved SSH host key handling with `StrictHostKeyChecking=accept-new` for new/changed host keys
- **Device Type Detection**: Fixed device type detection to properly use cached Tasmota/test equipment detection results
- **Cache Persistence**: Tasmota and test equipment detection results are now properly saved to persistent cache

### Changed
- **Device List Format**: Device list now displays as a markdown table with improved readability
- **Device Discovery**: Optimized device discovery to check all devices for Tasmota/test equipment detection, not just uncached ones
- **SSH Credential Priority**: SSH authentication now prioritizes "fio" user over "root" for device identification

## [0.2.0] - 2025-11-16

### Changed
- **Package Rename**: Renamed from `lab-testing` to `ai-lab-testing` for better clarity
- **Repository Rename**: Repository renamed from `mcp-remote-testing` to `ai-lab-testing`
- **Cache Directory**: Updated cache directory from `~/.cache/lab-testing` to `~/.cache/ai-lab-testing`
- **Documentation Cleanup**: Removed redundant planning documents (FEATURES.md, IMPROVEMENTS.md, ROADMAP.md)

### Fixed
- Updated all references to new package and repository names
- Updated .gitignore for new cache directory paths
- Updated CI workflows and scripts for new repository name

## [0.1.0] - 2025-11-16

### Added
- **Tasmota Power Switch Mapping**: Map Tasmota switches to devices they control
- **Power Cycling**: `power_cycle_device` tool to power cycle devices via Tasmota switches
- **Enhanced Network Mapping**: Network visualization now shows device type, uptime, friendly names, and power switch mappings
- **Dual Power Monitoring**: Power monitoring supports both DMM (Digital Multimeter via SCPI) and Tasmota devices (via energy monitoring)
- MCP server for remote lab testing
- **Device Management**: list, test, SSH access
- **VPN Management**: connect, disconnect, status
- **Power Monitoring**: basic monitoring and logging
- **Tasmota Control**: power switch control
- **OTA Management**: Foundries.io OTA status, updates, container deployment
- **System Status**: comprehensive device health monitoring
- **Batch Operations**: async parallel operations on multiple devices (5-10x faster)
- **Regression Testing**: automated parallel test sequences for device groups
- **Power Analysis**: low power detection, suspend/resume analysis, profile comparison
- **Device Grouping**: tag-based organization for rack management
- **Self-Describing Help**: built-in documentation and usage examples
- **Structured Logging**: file and console logging with request IDs
- **Health Check Resource**: server health, metrics, SSH pool status
- **Enhanced Error Types**: custom exception hierarchy with detailed context
- **SSH Connection Pooling**: persistent connections for faster execution
- **Process Management**: track and kill stale/duplicate processes to prevent conflicts
- **Firmware Version Detection**: read /etc/os-release for version information
- **Foundries.io Registration Status**: check device registration, connection, and update status via /var/sota and aktualizr
- **Secure Boot Status**: detailed secure boot information (U-Boot, kernel, EFI, HAB/CAAM for i.MX devices)
- **Device Identity**: hostname, SOC unique ID, and Foundries registration name tracking
- **Change Tracking**: track all changes made to devices for security/debugging, with revert capability
- **SSH Tunnels**: create and manage SSH tunnels through VPN for direct device access
- **Serial Port Access**: access serial ports on remote Linux laptops for low power/bootup debugging
- Resources: device inventory, network status, config, help, health
- Pre-commit/pre-push hooks
- Documentation and architecture diagram
- CI workflow

