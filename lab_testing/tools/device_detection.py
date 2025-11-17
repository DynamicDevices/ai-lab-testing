"""
Device Detection Utilities

Detects device types via network protocols (HTTP for Tasmota, etc.)
"""

import subprocess
import socket
from typing import Dict, Any, Optional
import urllib.request
import urllib.error


def detect_tasmota_device(ip: str, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
    """
    Detect if a device is a Tasmota device by checking HTTP API on port 80.
    
    Tasmota devices typically respond to /cm?cmnd=Status on port 80.
    
    Args:
        ip: IP address to check
        timeout: Request timeout in seconds
        
    Returns:
        Dict with device info if Tasmota detected, None otherwise
    """
    try:
        # Try to connect to port 80
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, 80))
        sock.close()
        
        if result != 0:
            return None  # Port 80 not open
        
        # Try Tasmota API endpoint - get Status for power state
        url = f"http://{ip}/cm?cmnd=Status"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    import json
                    data = json.loads(response.read().decode())
                    # Check if response looks like Tasmota
                    if "Status" in data or "StatusSNS" in data or "StatusNET" in data:
                        status_data = data.get("Status", {})
                        
                        # Extract power state (Power: "1" = on, "0" = off)
                        power_state = status_data.get("Power", "0")
                        power_on = power_state == "1" or power_state == 1
                        
                        # Try to get energy consumption data
                        energy_data = None
                        power_watts = None
                        try:
                            energy_url = f"http://{ip}/cm?cmnd=Status%208"
                            energy_req = urllib.request.Request(energy_url)
                            with urllib.request.urlopen(energy_req, timeout=timeout) as energy_response:
                                if energy_response.status == 200:
                                    energy_json = json.loads(energy_response.read().decode())
                                    status_sns = energy_json.get("StatusSNS", {})
                                    energy = status_sns.get("ENERGY", {})
                                    if energy:
                                        # Power in Watts
                                        power_watts = energy.get("Power", None)
                                        energy_data = {
                                            "power": power_watts,
                                            "voltage": energy.get("Voltage", None),
                                            "current": energy.get("Current", None),
                                            "total": energy.get("Total", None),
                                        }
                        except Exception:
                            # Energy monitoring not available or failed
                            pass
                        
                        return {
                            "device_type": "tasmota_device",
                            "tasmota_detected": True,
                            "tasmota_status": status_data,
                            "tasmota_power_on": power_on,
                            "tasmota_power_state": "on" if power_on else "off",
                            "tasmota_energy": energy_data,
                            "tasmota_power_watts": power_watts,
                        }
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, ValueError):
            # Not a Tasmota device or not responding
            pass
        
        return None
    except Exception:
        return None


def detect_test_equipment(ip: str, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
    """
    Detect if a device is test equipment (DMM, etc.) by checking common ports.
    
    Test equipment often uses SCPI over TCP/IP on various ports.
    
    Args:
        ip: IP address to check
        timeout: Connection timeout in seconds
        
    Returns:
        Dict with device info if test equipment detected, None otherwise
    """
    # Common test equipment ports
    test_ports = [5025, 5024, 3490, 3491]  # SCPI, VXI-11, etc.
    
    for port in test_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            
            if result == 0:
                return {
                    "device_type": "test_equipment",
                    "test_equipment_detected": True,
                    "port": port,
                }
        except Exception:
            continue
    
    return None

