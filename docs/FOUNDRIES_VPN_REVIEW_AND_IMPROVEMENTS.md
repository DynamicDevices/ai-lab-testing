# Foundries VPN Setup Review and Improvement Plan

**Date:** 2025-11-20  
**Purpose:** Review learnings, identify improvements, and determine if server code changes are needed

## Executive Summary

After troubleshooting and fixing Foundries VPN connectivity issues, we've identified several areas for improvement. The main question is: **Do we need server code changes, and can we eliminate the need for public IP access?**

**Key Finding:** We currently access the Proxmox WireGuard server via SSH on port 5025 (public IP) for setup and troubleshooting. This is a security and convenience concern.

## What We've Learned

### 1. Server Code Issues (FIXED)

**Issue:** Daemon parsing error with `wg syncconf`  
**Status:** ✅ **FIXED** - Removed `wg syncconf` attempt, always use `wg-quick`  
**Code Change:** Updated `apply_conf()` method in `factory-wireguard.py`  
**Conclusion:** **No further server code changes needed for this issue**

### 2. Client Peer Management (MANUAL)

**Issue:** Client peers are NOT managed by the daemon  
**Current State:**
- Device peers: Automatically managed by daemon (monitors FoundriesFactory API)
- Client peers: Manual registration required (server admin must add)

**Why Manual?**
- Client peers are not part of FoundriesFactory device registry
- Daemon only monitors `FactoryDevice.iter_vpn_enabled()` which returns devices, not client machines
- Client peer registration is a one-time setup per engineer

**Current Workflow:**
1. Engineer generates WireGuard key pair
2. Engineer shares public key with server admin (ajlennon@dynamicdevices.co.uk)
3. Server admin SSHes to Proxmox server (port 5025, public IP)
4. Server admin adds client peer: `wg set factory peer <PUBKEY> allowed-ips 10.42.42.0/24`
5. Server admin saves to config: `wg-quick save factory`
6. Engineer connects to VPN

**Problem:** Requires public IP access to Proxmox server

### 3. VPN-Only Access Challenge (CHICKEN-AND-EGG)

**Question:** Can we do everything through Foundries VPN?

**Answer:** **Partially, but with a bootstrap problem**

**Bootstrap Problem:**
- To connect to Foundries VPN, you need your client peer registered on the server
- To register your client peer, you need server access
- Server access currently requires public IP (SSH port 5025)

**Possible Solutions:**

#### Option A: Initial Setup via FoundriesFactory API (RECOMMENDED)
- **Idea:** Use FoundriesFactory API to register client peers
- **Implementation:** Add client peer management to FoundriesFactory (server config file)
- **Pros:** No public IP needed, uses existing API infrastructure
- **Cons:** Requires FoundriesFactory feature addition (may not exist)

#### Option B: Bootstrap via Standard VPN
- **Idea:** Use standard WireGuard VPN (hardware lab) for initial server access
- **Workflow:**
  1. Connect to standard VPN (hardware lab network)
  2. Access Proxmox server via VPN IP (10.21.21.101 or similar)
  3. Register Foundries VPN client peer
  4. Disconnect standard VPN
  5. Connect to Foundries VPN
- **Pros:** Uses existing infrastructure
- **Cons:** Requires two VPNs, more complex workflow

#### Option C: Server-Side Client Peer Management Tool
- **Idea:** Create a server-side tool that manages client peers via FoundriesFactory API or config file
- **Implementation:** Add client peer management to `factory-wireguard-server` daemon
- **Pros:** Automated, no manual SSH needed
- **Cons:** Requires server code changes, needs secure API for client registration

#### Option D: Self-Service Portal
- **Idea:** Web portal or API endpoint for client peer self-registration
- **Implementation:** Simple web service on Proxmox server (via Foundries VPN IP)
- **Pros:** Self-service, no admin needed
- **Cons:** Requires new infrastructure, security considerations

## Recommended Improvements

### Priority 1: Eliminate Public IP Access (HIGH PRIORITY)

**Goal:** All server management via Foundries VPN (after initial bootstrap)

**Approach:** **Option B (Bootstrap via Standard VPN)** - Most practical

**Implementation Steps:**

1. **Document Bootstrap Workflow:**
   ```
   1. Connect to standard VPN (hardware lab)
   2. Access Proxmox server via VPN IP: ssh root@10.21.21.101 -p 5025
   3. Register Foundries VPN client peer
   4. Disconnect standard VPN
   5. Connect to Foundries VPN
   6. Verify: All future access via Foundries VPN (10.42.42.1)
   ```

2. **Create MCP Tool for Client Peer Registration:**
   - Tool: `register_foundries_vpn_client(client_public_key, assigned_ip)`
   - Connects to Proxmox server via standard VPN (if Foundries VPN not connected)
   - Automates client peer registration
   - Updates server config file

3. **Update Documentation:**
   - Add bootstrap workflow to setup guides
   - Document Proxmox VPN IP for standard VPN access
   - Remove references to public IP access

### Priority 2: Improve Client Peer Management (MEDIUM PRIORITY)

**Goal:** Make client peer registration easier and more automated

**Approach:** **Option C (Server-Side Tool)** - Most scalable

**Implementation Steps:**

1. **Add Client Peer Management to Daemon:**
   - New config file: `/etc/wireguard/factory-clients.conf`
   - Daemon reads client peers from config file
   - Daemon applies client peers on startup
   - Client peers persist across daemon restarts

2. **Create Client Peer Config Format:**
   ```ini
   # /etc/wireguard/factory-clients.conf
   # Format: <public_key> <assigned_ip> <comment>
   mzHaZPGowqqzAa5tVFQJs0zoWuDVLppt44HwgdcPXkg= 10.42.42.10 ajlennon
   7WR3aejgU53i+/MiJcpdboASPgjLihXApnhHj4SRukE= 10.42.42.11 engineer2
   ```

3. **Update Daemon Code:**
   ```python
   def load_client_peers(self, config_file: str):
       """Load client peers from config file"""
       clients = []
       if os.path.exists(config_file):
           with open(config_file) as f:
               for line in f:
                   if line.strip() and not line.startswith('#'):
                       parts = line.strip().split()
                       if len(parts) >= 2:
                           pubkey, ip = parts[0], parts[1]
                           clients.append((pubkey, ip))
       return clients
   
   def apply_client_peers(self, intf_name: str):
       """Apply client peers to WireGuard interface"""
       clients = self.load_client_peers("/etc/wireguard/factory-clients.conf")
       for pubkey, ip in clients:
           subprocess.run(
               ["wg", "set", intf_name, "peer", pubkey, "allowed-ips", f"{ip}/32"],
               check=False
           )
   ```

4. **Benefits:**
   - Client peers managed via config file (easier than manual `wg set`)
   - Daemon ensures client peers are always applied
   - No manual SSH needed (after initial bootstrap)
   - Can be managed via Foundries VPN once connected

### Priority 3: Better Error Messages (LOW PRIORITY)

**Goal:** Provide clearer guidance when client peer is missing

**Current:** Generic "100% packet loss" error  
**Improved:** Specific error message with next steps

**Implementation:**

1. **Add Client Peer Check Tool:**
   ```python
   def check_client_peer_registered(client_public_key: str) -> Dict[str, Any]:
       """Check if client peer is registered on server"""
       # Connect to server via Foundries VPN (if connected) or standard VPN
       # Check: wg show factory | grep <PUBKEY>
       # Return: registered status, assigned IP, next steps
   ```

2. **Update Error Messages:**
   - When ping fails: Check client peer registration
   - Provide specific command to check: `wg show factory | grep <PUBKEY>`
   - Link to troubleshooting guide

### Priority 4: Self-Service Client Registration (FUTURE)

**Goal:** Allow engineers to self-register without admin intervention

**Approach:** **Option D (Self-Service Portal)** - Long-term solution

**Implementation Ideas:**

1. **Simple HTTP API on Proxmox Server:**
   - Endpoint: `POST /api/v1/clients/register`
   - Body: `{"public_key": "...", "requested_ip": "10.42.42.X"}`
   - Validates IP availability
   - Adds to `factory-clients.conf`
   - Restarts WireGuard interface

2. **MCP Tool Integration:**
   - Tool: `self_register_foundries_vpn_client()`
   - Generates key pair
   - Requests IP assignment
   - Registers via API
   - Configures client connection

3. **Security Considerations:**
   - Rate limiting
   - IP validation (prevent conflicts)
   - Audit logging
   - Optional: FoundriesFactory authentication

## Server Code Changes Needed?

### Current State Analysis

**Parsing Error:** ✅ **FIXED** - No further changes needed

**Client Peer Management:** ⚠️ **IMPROVEMENT OPPORTUNITY**

**Recommendation:** **Yes, but minimal changes**

### Required Changes

1. **Add Client Peer Config File Support (Priority 2):**
   - Add `load_client_peers()` method
   - Add `apply_client_peers()` method
   - Call `apply_client_peers()` in `apply_conf()` or daemon startup
   - **Impact:** Low risk, improves maintainability

2. **No Changes Needed For:**
   - Parsing error (already fixed)
   - Device peer management (working correctly)
   - Daemon monitoring (working correctly)

### Code Change Summary

**Files to Modify:**
- `factory-wireguard-server/factory-wireguard.py`
  - Add client peer loading/application methods
  - Integrate into daemon startup

**Estimated Effort:** 2-4 hours  
**Risk Level:** Low (additive changes, doesn't affect existing functionality)  
**Testing:** Verify client peers persist across daemon restarts

## VPN-Only Access Workflow

### Proposed Bootstrap Workflow

**Key Insight:** Once connected to Foundries VPN, you can access the server at `10.42.42.1` and manage everything via VPN. The hardware lab VPN is only for local lab access, not field devices.

**Initial Setup (One-Time, First Admin):**

1. **First Admin Gets Initial Server Access:**
   - Public IP: `ssh root@proxmox.dynamicdevices.co.uk -p 5025` (one-time only)
   - Or direct access if available

2. **Register First Admin's Client Peer:**
   ```bash
   # On Proxmox server
   echo "FIRST_ADMIN_PUBLIC_KEY 10.42.42.10 admin" >> /etc/wireguard/factory-clients.conf
   wg set factory peer FIRST_ADMIN_PUBLIC_KEY allowed-ips 10.42.42.0/24
   wg-quick save factory
   ```

3. **First Admin Connects:**
   ```bash
   connect_foundries_vpn()
   ```

**Subsequent Engineers (Via Foundries VPN):**

1. **Admin Registers Engineer:**
   ```python
   # Admin (connected to Foundries VPN) registers new engineer
   register_foundries_vpn_client(
       client_public_key="ENGINEER_PUBLIC_KEY",
       assigned_ip="10.42.42.11"
   )
   # Tool connects via Foundries VPN (10.42.42.1)
   ```

2. **Engineer Connects:**
   ```bash
   connect_foundries_vpn()
   ```

**Ongoing Access (Via Foundries VPN Only):**

- All server management via Foundries VPN IP: `10.42.42.1`
- No public IP access needed after first admin bootstrap
- Client peer management via config file (`/etc/wireguard/factory-clients.conf`)
- Device management via Foundries VPN
- Field devices accessible via Foundries VPN (not hardware lab VPN)

### Benefits

✅ **Security:** No public IP exposure  
✅ **Convenience:** Single VPN for all access  
✅ **Scalability:** Easier to manage multiple engineers  
✅ **Documentation:** Clear workflow for new engineers

## Implementation Plan

### Phase 1: Documentation and Workflow (IMMEDIATE)

**Tasks:**
1. ✅ Document bootstrap workflow
2. ✅ Update setup guides with VPN-only access
3. ✅ Create troubleshooting guide (already done)
4. ⏳ Document Proxmox VPN IP for standard VPN access

**Effort:** 2-4 hours  
**Risk:** None (documentation only)

### Phase 2: Client Peer Management Tool (SHORT-TERM)

**Tasks:**
1. ⏳ Create MCP tool: `register_foundries_vpn_client()`
2. ⏳ Tool connects via standard VPN (if Foundries VPN not connected)
3. ⏳ Tool automates client peer registration
4. ⏳ Tool updates server config file

**Effort:** 4-8 hours  
**Risk:** Low (additive tool, doesn't affect existing functionality)

### Phase 3: Server Code Changes (MEDIUM-TERM)

**Tasks:**
1. ⏳ Add client peer config file support to daemon
2. ⏳ Add `load_client_peers()` and `apply_client_peers()` methods
3. ⏳ Integrate into daemon startup
4. ⏳ Test client peers persist across restarts

**Effort:** 2-4 hours  
**Risk:** Low (additive changes)

### Phase 4: Self-Service Portal (LONG-TERM)

**Tasks:**
1. ⏳ Design HTTP API for client registration
2. ⏳ Implement API endpoint on Proxmox server
3. ⏳ Add security (rate limiting, validation)
4. ⏳ Create MCP tool integration
5. ⏳ Test end-to-end workflow

**Effort:** 16-24 hours  
**Risk:** Medium (new infrastructure)

## Recommendations Summary

### Immediate Actions (This Week)

1. ✅ **Document bootstrap workflow** - Use standard VPN for initial server access
2. ✅ **Update setup guides** - Remove public IP references, add VPN-only workflow
3. ⏳ **Create client peer registration tool** - Automate via standard VPN

### Short-Term (Next Sprint)

1. ⏳ **Add client peer config file support** - Server code changes (Priority 2)
2. ⏳ **Improve error messages** - Better guidance when client peer missing
3. ⏳ **Test VPN-only workflow** - Verify all operations work via Foundries VPN

### Long-Term (Future)

1. ⏳ **Self-service portal** - Allow engineers to self-register
2. ⏳ **FoundriesFactory API integration** - If API supports client peer management

## Conclusion

**Server Code Changes:** **Yes, but minimal** - Add client peer config file support (Priority 2)

**VPN-Only Access:** **Yes, achievable** - Bootstrap via standard VPN, then use Foundries VPN exclusively

**Key Improvements:**
1. Eliminate public IP access (bootstrap via standard VPN)
2. Automate client peer registration (MCP tool + config file)
3. Better error messages (client peer check tool)
4. Self-service portal (long-term)

**Next Steps:**
1. Document bootstrap workflow
2. Create client peer registration MCP tool
3. Implement server-side client peer config file support
4. Test end-to-end VPN-only workflow

