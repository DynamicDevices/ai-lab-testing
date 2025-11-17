"""
Device Cache Management

Caches discovered device information (hostname, unique_id, device_type) 
to avoid repeated SSH queries for device identification.

Copyright (C) 2025 Dynamic Devices Ltd
License: GPL-3.0-or-later
"""

import json
import time
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from lab_testing.config import CACHE_DIR
from lab_testing.tools.device_verification import verify_device_by_ip
from lab_testing.utils.logger import get_logger

logger = get_logger()

# Cache file path
DEVICE_CACHE_FILE = CACHE_DIR / "device_cache.json"

# Cache expiration time (24 hours)
CACHE_EXPIRY_SECONDS = 24 * 60 * 60

# Lock for cache file operations (prevents race conditions in parallel execution)
_cache_lock = threading.Lock()


def _ensure_cache_dir():
    """Ensure cache directory exists"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def load_device_cache() -> Dict[str, Any]:
    """Load device cache from file"""
    _ensure_cache_dir()
    
    if not DEVICE_CACHE_FILE.exists():
        return {}
    
    try:
        with open(DEVICE_CACHE_FILE, 'r') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to load device cache (corrupted JSON): {e}")
        # Try to recover by backing up corrupted cache
        try:
            backup_file = DEVICE_CACHE_FILE.with_suffix(".json.bak")
            import shutil
            if DEVICE_CACHE_FILE.exists():
                shutil.copy2(DEVICE_CACHE_FILE, backup_file)
                logger.info(f"Backed up corrupted cache to {backup_file}")
        except Exception:
            pass
        return {}
    except IOError as e:
        logger.warning(f"Failed to read device cache: {e}")
        return {}


def save_device_cache(cache: Dict[str, Any]):
    """Save device cache to file (atomic write to prevent corruption)"""
    # Use lock to prevent race conditions in parallel execution
    with _cache_lock:
        # Ensure cache directory exists - create if needed
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            if not CACHE_DIR.exists():
                raise OSError(f"Failed to create cache directory: {CACHE_DIR}")
        except Exception as e:
            logger.error(f"Failed to create cache directory: {e}")
            return
        
        # Use atomic write: write to temp file, then rename
        # Ensure temp file is in the cache directory
        temp_file = CACHE_DIR / f"{DEVICE_CACHE_FILE.name}.tmp"
        
        try:
            # Write to temporary file first
            with open(temp_file, 'w') as f:
                json.dump(cache, f, indent=2)
                f.flush()
                import os
                os.fsync(f.fileno())
            
            # Verify temp file was created and has content
            if not temp_file.exists():
                raise OSError(f"Temp file was not created: {temp_file}")
            if temp_file.stat().st_size == 0:
                raise OSError(f"Temp file is empty: {temp_file}")
            
            # Atomic rename (works on Unix/Linux)
            # Use replace() which is atomic on Unix systems
            import os
            os.replace(str(temp_file), str(DEVICE_CACHE_FILE))
        except (IOError, OSError) as e:
            logger.warning(f"Failed to save device cache: {e}")
            # Clean up temp file if it exists
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception:
                pass
            # Try to ensure directory exists and retry once
            try:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                # Retry the write
                with open(temp_file, 'w') as f:
                    json.dump(cache, f, indent=2)
                import os
                os.replace(str(temp_file), str(DEVICE_CACHE_FILE))
            except Exception as retry_error:
                logger.error(f"Failed to save device cache after retry: {retry_error}")


def get_cached_device_info(ip: str) -> Optional[Dict[str, Any]]:
    """
    Get cached device information for an IP address.
    
    Args:
        ip: IP address to look up
        
    Returns:
        Cached device info dict or None if not cached or expired
    """
    cache = load_device_cache()
    device_info = cache.get(ip)
    
    if not device_info:
        return None
    
    # Check if cache is expired
    cached_time = device_info.get("cached_at", 0)
    if time.time() - cached_time > CACHE_EXPIRY_SECONDS:
        logger.debug(f"Cache expired for {ip}")
        return None
    
    return device_info


def update_cached_friendly_name(ip: str, friendly_name: str) -> bool:
    """
    Update the friendly name for a cached device.
    
    Args:
        ip: IP address of the device
        friendly_name: New friendly name to set
        
    Returns:
        True if updated successfully, False if device not in cache
    """
    cache = load_device_cache()
    
    if ip not in cache:
        logger.warning(f"Device {ip} not found in cache - cannot update friendly name")
        return False
    
    cache[ip]["friendly_name"] = friendly_name
    cache[ip]["friendly_name_updated"] = time.time()  # Track when it was manually updated
    save_device_cache(cache)
    
    logger.info(f"Updated friendly name for {ip}: {friendly_name}")
    return True


def get_cached_friendly_name(ip: str) -> Optional[str]:
    """
    Get the cached friendly name for a device.
    
    Args:
        ip: IP address of the device
        
    Returns:
        Friendly name or None if not set
    """
    device_info = get_cached_device_info(ip)
    if device_info:
        return device_info.get("friendly_name")
    return None


def cache_device_info(ip: str, device_info: Dict[str, Any]):
    """
    Cache device information for an IP address.
    Merges with existing cache entry to preserve Tasmota/test equipment detection.
    
    Args:
        ip: IP address
        device_info: Device information dict (hostname, unique_id, device_id, etc.)
    """
    cache = load_device_cache()
    
    # Merge with existing cache entry to preserve Tasmota/test equipment detection
    existing = cache.get(ip, {})
    
    # Preserve existing hostname if we're trying to cache a failure
    # (prevents race condition where a failure overwrites a success)
    existing_hostname = existing.get("hostname")
    existing.update(device_info)
    
    # If existing cache had hostname but new data doesn't, preserve it
    if existing_hostname and not device_info.get("hostname"):
        existing["hostname"] = existing_hostname
        existing["device_found"] = existing.get("device_found", False)
    
    # If device was successfully identified (has hostname), clear any old SSH errors
    if existing.get("hostname") or existing.get("device_found"):
        existing.pop("ssh_error", None)
        existing.pop("ssh_error_type", None)
    
    # Add timestamp
    existing["cached_at"] = time.time()
    existing["ip"] = ip
    
    cache[ip] = existing
    save_device_cache(cache)
    
    logger.debug(f"Cached device info for {ip}: {existing.get('device_id', 'unknown')}")


def _get_firmware_version_from_ip(ip: str, username: str = "root", ssh_port: int = 22) -> Optional[Dict[str, Any]]:
    """
    Get firmware version information from a device via SSH.
    
    Args:
        ip: IP address
        username: SSH username
        ssh_port: SSH port
        
    Returns:
        Firmware version dict or None if unable to retrieve
    """
    import subprocess
    
    try:
        # Try with password authentication disabled first (key-based)
        # Use accept-new to handle host key changes gracefully
        # Reduced timeout for faster discovery
        result = subprocess.run(
            [
                "ssh",
                "-o", "StrictHostKeyChecking=accept-new",
                "-o", "ConnectTimeout=3",
                "-o", "PasswordAuthentication=no",
                "-o", "BatchMode=yes",
                "-p", str(ssh_port),
                f"{username}@{ip}",
                "cat /etc/os-release 2>/dev/null || echo ''",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,  # Reduced from 10 to 5 seconds
        )
        
        # If that fails, try with password auth from credentials
        if result.returncode != 0:
            from lab_testing.utils.credentials import get_credential, get_ssh_command
            # Try to get credentials using IP as device identifier
            cred = get_credential(ip, "ssh")
            if cred and cred.get("password"):
                # Use get_ssh_command which handles sshpass properly
                ssh_cmd = get_ssh_command(ip, username, "cat /etc/os-release 2>/dev/null || echo ''", device_id=ip, use_password=True)
                result = subprocess.run(
                    ssh_cmd,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
        
        # If still fails, try with password authentication enabled (interactive)
        if result.returncode != 0:
            result = subprocess.run(
                [
                    "ssh",
                    "-o", "StrictHostKeyChecking=accept-new",
                    "-o", "ConnectTimeout=3",
                    "-p", str(ssh_port),
                    f"{username}@{ip}",
                    "cat /etc/os-release 2>/dev/null || echo ''",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,  # Reduced from 10 to 5 seconds
            )
        
        if result.returncode == 0 and result.stdout.strip():
            os_release = {}
            for line in result.stdout.split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    value = value.strip("\"'")
                    os_release[key] = value
            
            return {
                "name": os_release.get("NAME", "Unknown"),
                "version": os_release.get("VERSION", "Unknown"),
                "version_id": os_release.get("VERSION_ID", "Unknown"),
                "build_id": os_release.get("BUILD_ID", "Unknown"),
                "pretty_name": os_release.get("PRETTY_NAME", "Unknown"),
                "foundries": {
                    "factory": os_release.get("FACTORY", "Unknown"),
                    "target": os_release.get("LMP_FACTORY", "Unknown"),
                    "machine": os_release.get("MACHINE", "Unknown"),
                },
            }
    except Exception as e:
        logger.debug(f"Failed to get firmware version from {ip}: {e}")
    
    return None


def identify_and_cache_device(ip: str, username: str = "root", ssh_port: int = 22) -> Dict[str, Any]:
    """
    Identify a device at an IP address and cache the result.
    
    Uses cached info if available and not expired, otherwise queries the device
    and updates the cache. Also retrieves and caches firmware version.
    
    Args:
        ip: IP address to identify
        username: SSH username
        ssh_port: SSH port
        
    Returns:
        Device information dict
    """
    # Check cache first
    cached_info = get_cached_device_info(ip)
    if cached_info:
        # If cache has SSH error but no hostname, re-verify (previous attempt failed)
        if cached_info.get("ssh_error") and not cached_info.get("hostname"):
            logger.debug(f"Cache has SSH error for {ip}, re-verifying with username {username}")
        else:
            logger.debug(f"Using cached device info for {ip}")
            return cached_info
    
    # Not in cache or expired - identify device
    logger.debug(f"Identifying device at {ip} (not in cache)")
    verification = verify_device_by_ip(ip, username, ssh_port)
    
    # Get firmware version
    firmware_info = _get_firmware_version_from_ip(ip, username, ssh_port)
    
    # Extract device info from verification result
    device_info = {
        "hostname": verification.get("hostname"),
        "unique_id": verification.get("unique_id"),
        "device_id": verification.get("device_id"),
        "friendly_name": verification.get("friendly_name"),
        "device_found": verification.get("device_found", False),
        "matches": verification.get("matches", []),
        "firmware": firmware_info,
        "ssh_error": verification.get("ssh_error"),
        "ssh_error_type": verification.get("ssh_error_type"),
    }
    
    # Cache the result (even if device not found, to avoid repeated queries)
    cache_device_info(ip, device_info)
    
    return device_info


def clear_device_cache():
    """Clear all cached device information"""
    _ensure_cache_dir()
    if DEVICE_CACHE_FILE.exists():
        DEVICE_CACHE_FILE.unlink()
        logger.info("Device cache cleared")

