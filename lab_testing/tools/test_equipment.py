"""
Test Equipment Management Tools for MCP Server
"""

import json
from typing import Any, Dict, List

from lab_testing.config import get_lab_devices_config
from lab_testing.utils.device_cache import load_device_cache


def list_test_equipment() -> Dict[str, Any]:
    """
    List all test equipment devices (DMM, oscilloscopes, etc.).

    Includes both configured devices and discovered devices from cache.

    Returns:
        Dictionary with test equipment device list
    """
    try:
        # Load configured devices
        config_path = get_lab_devices_config()
        with open(config_path) as f:
            config = json.load(f)
            devices = config.get("devices", {})

        # Load discovered devices from cache
        cache = load_device_cache()

        test_equipment = []

        # Add configured test equipment
        for device_id, device_info in devices.items():
            if device_info.get("device_type") == "test_equipment":
                test_equipment.append(
                    {
                        "id": device_id,
                        "name": device_info.get("name", "Unknown"),
                        "friendly_name": device_info.get("friendly_name")
                        or device_info.get("name", device_id),
                        "ip": device_info.get("ip", "Unknown"),
                        "model": device_info.get("model", "Unknown"),
                        "manufacturer": device_info.get("manufacturer", "Unknown"),
                        "ports": device_info.get("ports", {}),
                        "equipment_type": device_info.get("equipment_type", "test_equipment"),
                        "configured": True,
                    }
                )

        # Add discovered test equipment from cache (not already in config)
        for ip, cached_info in cache.items():
            if cached_info.get("test_equipment_detected"):
                # Check if already in configured list
                already_listed = any(
                    te.get("ip") == ip for te in test_equipment
                )

                if not already_listed:
                    # Get device info from cache
                    model = cached_info.get("model", "Unknown")
                    manufacturer = cached_info.get("manufacturer", "Unknown")
                    equipment_type = cached_info.get("equipment_type", "test_equipment")
                    port = cached_info.get("port", "Unknown")
                    scpi_idn = cached_info.get("scpi_idn")

                    test_equipment.append(
                        {
                            "id": f"device_{ip.replace('.', '_')}",
                            "name": f"Test Equipment at {ip}",
                            "friendly_name": f"{manufacturer} {model}" if model != "Unknown" else f"Test Equipment at {ip}",
                            "ip": ip,
                            "model": model,
                            "manufacturer": manufacturer,
                            "ports": {"scpi": port} if port != "Unknown" else {},
                            "equipment_type": equipment_type,
                            "scpi_idn": scpi_idn,
                            "configured": False,
                        }
                    )

        return {
            "success": True,
            "devices": test_equipment,
            "count": len(test_equipment),
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to load test equipment: {e!s}"}


def query_test_equipment(device_id_or_ip: str, scpi_command: str) -> Dict[str, Any]:
    """
    Send a SCPI command to test equipment and return the response.

    Args:
        device_id_or_ip: Device ID from config or IP address
        scpi_command: SCPI command to send (e.g., "*IDN?", "MEAS:VOLT:DC?")

    Returns:
        Dictionary with command result
    """
    import socket

    from lab_testing.config import get_lab_devices_config
    from lab_testing.tools.device_manager import resolve_device_identifier

    try:
        # Try to resolve device_id to IP
        device_id = resolve_device_identifier(device_id_or_ip)
        ip = None
        port = 5025  # Default SCPI port

        if device_id:
            # Load config to get IP and port
            with open(get_lab_devices_config()) as f:
                config = json.load(f)
                devices = config.get("devices", {})
                if device_id in devices:
                    device_info = devices[device_id]
                    ip = device_info.get("ip")
                    ports = device_info.get("ports", {})
                    port = ports.get("scpi", 5025)

        # If not found in config, assume device_id_or_ip is an IP
        if not ip:
            ip = device_id_or_ip
            # Try to get port from cache
            cache = load_device_cache()
            if ip in cache:
                cached_info = cache[ip]
                port = cached_info.get("port", 5025)

        if not ip:
            return {
                "success": False,
                "error": f"Device '{device_id_or_ip}' not found and not a valid IP address",
            }

        # Send SCPI command
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((ip, port))

            # Send command (SCPI commands should end with \n)
            if not scpi_command.endswith("\n"):
                scpi_command += "\n"
            sock.send(scpi_command.encode())

            # Read response
            response = sock.recv(4096).decode().strip()
            sock.close()

            return {
                "success": True,
                "device_id": device_id_or_ip,
                "ip": ip,
                "port": port,
                "command": scpi_command.strip(),
                "response": response,
            }

        except socket.timeout:
            return {
                "success": False,
                "error": f"Timeout connecting to {ip}:{port}",
            }
        except ConnectionRefusedError:
            return {
                "success": False,
                "error": f"Connection refused to {ip}:{port}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to send SCPI command: {e!s}",
            }

    except Exception as e:
        return {"success": False, "error": f"Failed to query test equipment: {e!s}"}




