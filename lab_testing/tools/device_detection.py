"""
Device Detection Utilities

Detects device types via network protocols (HTTP for Tasmota, etc.)
"""

import socket
import subprocess
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


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
                            with urllib.request.urlopen(
                                energy_req, timeout=timeout
                            ) as energy_response:
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
    Detect if a device is test equipment (DMM, etc.) by checking common ports
    and querying via SCPI if a port is open.

    Test equipment often uses SCPI over TCP/IP on various ports.
    When an SCPI port is found, queries *IDN? to identify the device.

    Args:
        ip: IP address to check
        timeout: Connection timeout in seconds

    Returns:
        Dict with device info if test equipment detected, None otherwise
    """
    # Common test equipment ports (SCPI/TCP and VXI-11)
    test_ports = [5025, 5024, 3490, 3491]

    for port in test_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()

            if result == 0:
                # Port is open - try to query device via SCPI
                device_info = {
                    "device_type": "test_equipment",
                    "test_equipment_detected": True,
                    "port": port,
                    "scpi_port": port if port in [5025, 5024] else None,
                }

                # Try SCPI identification query (*IDN?) for SCPI ports
                if port in [5025, 5024]:
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(timeout)
                        sock.connect((ip, port))

                        # Send *IDN? query (standard SCPI identification)
                        query = "*IDN?\n"
                        sock.send(query.encode())

                        # Read response (SCPI responses end with \n)
                        response = sock.recv(1024).decode().strip()
                        sock.close()

                        if response:
                            # Parse *IDN? response: "Manufacturer,Model,Serial,Version"
                            parts = [p.strip() for p in response.split(",")]
                            if len(parts) >= 2:
                                device_info["manufacturer"] = parts[0]
                                device_info["model"] = parts[1] if len(parts) > 1 else None
                                device_info["serial"] = parts[2] if len(parts) > 2 else None
                                device_info["version"] = parts[3] if len(parts) > 3 else None
                                device_info["scpi_idn"] = response

                                # Infer device type from model/manufacturer
                                model_lower = (parts[1] or "").lower()
                                manufacturer_lower = (parts[0] or "").lower()
                                
                                # Known DMM model patterns (Keysight/Agilent 34461A, 34465A, etc.)
                                dmm_patterns = ["dmm", "multimeter", "34461", "34465", "34470", "34401"]
                                scope_patterns = ["scope", "oscilloscope", "dso", "mso"]
                                power_supply_patterns = ["power", "supply", "psu"]
                                
                                if any(pattern in model_lower for pattern in dmm_patterns):
                                    device_info["equipment_type"] = "dmm"
                                elif any(pattern in model_lower for pattern in scope_patterns):
                                    device_info["equipment_type"] = "oscilloscope"
                                elif any(pattern in model_lower for pattern in power_supply_patterns) and "supply" in model_lower:
                                    device_info["equipment_type"] = "power_supply"
                                # Check manufacturer for Keysight/Agilent - they make DMMs
                                elif "agilent" in manufacturer_lower or "keysight" in manufacturer_lower:
                                    # Keysight/Agilent test equipment - check if it's a known DMM model
                                    if "344" in model_lower or "3458" in model_lower:
                                        device_info["equipment_type"] = "dmm"
                                    else:
                                        device_info["equipment_type"] = "test_equipment"
                                else:
                                    device_info["equipment_type"] = "test_equipment"
                    except Exception:
                        # SCPI query failed, but port is open so it's still test equipment
                        pass

                return device_info
        except Exception:
            continue

    return None
