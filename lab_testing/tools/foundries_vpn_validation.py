"""
Foundries.io VPN Management Tools for MCP Server

Provides tools for managing Foundries VPN connections and devices.
Foundries VPN uses WireGuard but with a server-based architecture where
devices connect to a centralized VPN server managed by FoundriesFactory.

Copyright (C) 2025 Dynamic Devices Ltd
License: GPL-3.0-or-later
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from lab_testing.config import get_foundries_vpn_config
from lab_testing.utils.foundries_vpn_cache import (
    cache_vpn_ip,
    get_all_cached_ips,
    get_vpn_ip,
    remove_vpn_ip,
)
from lab_testing.utils.logger import get_logger

logger = get_logger()

import subprocess
from typing import Any, Dict, Optional

from lab_testing.tools.foundries_devices import list_foundries_devices
from lab_testing.tools.foundries_vpn_core import (
    connect_foundries_vpn,
    foundries_vpn_status,
    verify_foundries_vpn_connection,
)
from lab_testing.tools.foundries_vpn_server import get_foundries_vpn_server_config
from lab_testing.utils.logger import get_logger

logger = get_logger()


def validate_foundries_device_connectivity(
    device_name: Optional[str] = None,
    factory: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Comprehensive validation of Foundries VPN and device connectivity.

    Performs a step-by-step validation sequence:
    1. Check connection to Foundries VPN server
    2. List relevant Foundries devices
    3. Check devices are online and VPN is enabled
    4. Test ping and SSH connectivity to devices

    This function provides clear, sequential validation results to help diagnose
    connectivity issues.

    Args:
        device_name: Optional specific device name to validate. If not provided,
                    validates all Foundries devices with VPN enabled.
        factory: Optional factory name. If not provided, uses default factory from fioctl config.

    Returns:
        Dictionary with comprehensive validation results including:
        - Step-by-step validation status
        - VPN server connectivity status
        - Device listing results
        - Device online/VPN status
        - Ping and SSH test results
    """
    try:
        validation_steps = []
        validation_errors = []
        validation_warnings = []

        # Step 1: Check connection to Foundries VPN server
        step1_result = {
            "step": 1,
            "name": "Check Foundries VPN Server Connection",
            "status": "pending",
            "details": {},
        }

        vpn_status = foundries_vpn_status()
        if not vpn_status.get("success"):
            step1_result["status"] = "failed"
            step1_result["error"] = vpn_status.get("error", "Unknown error")
            validation_errors.append(f"Step 1 failed: {step1_result['error']}")
            validation_steps.append(step1_result)
            return {
                "success": False,
                "validation_steps": validation_steps,
                "errors": validation_errors,
                "message": "Failed at Step 1: Foundries VPN server connection check",
                "suggestions": vpn_status.get("suggestions", []),
            }

        if not vpn_status.get("connected"):
            step1_result["status"] = "failed"
            step1_result["error"] = "Foundries VPN is not connected"
            validation_errors.append("Step 1 failed: VPN not connected")
            validation_steps.append(step1_result)
            return {
                "success": False,
                "validation_steps": validation_steps,
                "errors": validation_errors,
                "message": "Failed at Step 1: Foundries VPN not connected",
                "suggestions": [
                    "Connect to Foundries VPN: connect_foundries_vpn()",
                    "Or run automated setup: setup_foundries_vpn()",
                ],
            }

        # Verify VPN server connectivity
        server_config = get_foundries_vpn_server_config(factory)
        if not server_config.get("success"):
            step1_result["status"] = "failed"
            step1_result["error"] = "Failed to get VPN server configuration"
            validation_errors.append("Step 1 failed: Cannot get server config")
            validation_steps.append(step1_result)
            return {
                "success": False,
                "validation_steps": validation_steps,
                "errors": validation_errors,
                "message": "Failed at Step 1: Cannot get VPN server configuration",
            }

        server_ip = server_config.get("address", "").split("/")[0]
        if not server_ip:
            step1_result["status"] = "failed"
            step1_result["error"] = "Server IP not found in configuration"
            validation_errors.append("Step 1 failed: Server IP not found")
            validation_steps.append(step1_result)
            return {
                "success": False,
                "validation_steps": validation_steps,
                "errors": validation_errors,
                "message": "Failed at Step 1: Server IP not found",
            }

        # Test ping to VPN server
        ping_result = subprocess.run(
            ["ping", "-c", "2", "-W", "2", server_ip],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )

        ping_success = ping_result.returncode == 0
        step1_result["status"] = "passed" if ping_success else "warning"
        step1_result["details"] = {
            "vpn_connected": True,
            "server_ip": server_ip,
            "server_endpoint": server_config.get("endpoint", "Unknown"),
            "ping_to_server": ping_success,
            "ping_output": ping_result.stdout if ping_success else ping_result.stderr,
        }

        if not ping_success:
            validation_warnings.append(f"Step 1 warning: Cannot ping VPN server {server_ip}")
            step1_result["warning"] = f"Cannot ping VPN server {server_ip}"

        validation_steps.append(step1_result)

        # Step 2: List relevant Foundries devices
        step2_result = {
            "step": 2,
            "name": "List Foundries Devices",
            "status": "pending",
            "details": {},
        }

        from lab_testing.tools.foundries_devices import list_foundries_devices

        devices_result = list_foundries_devices(factory)
        if not devices_result.get("success"):
            step2_result["status"] = "failed"
            step2_result["error"] = devices_result.get("error", "Unknown error")
            validation_errors.append(f"Step 2 failed: {step2_result['error']}")
            validation_steps.append(step2_result)
            return {
                "success": False,
                "validation_steps": validation_steps,
                "errors": validation_errors,
                "message": "Failed at Step 2: Cannot list Foundries devices",
                "suggestions": devices_result.get("suggestions", []),
            }

        all_devices = devices_result.get("devices", [])
        if not all_devices:
            step2_result["status"] = "warning"
            step2_result["warning"] = "No Foundries devices found in factory"
            validation_warnings.append("Step 2 warning: No devices found")
            validation_steps.append(step2_result)
            return {
                "success": True,
                "validation_steps": validation_steps,
                "warnings": validation_warnings,
                "message": "Validation completed with warnings: No devices found",
            }

        # Filter devices if device_name specified
        if device_name:
            matching_devices = [d for d in all_devices if d.get("name") == device_name]
            if not matching_devices:
                step2_result["status"] = "failed"
                step2_result["error"] = f"Device '{device_name}' not found in factory"
                validation_errors.append(f"Step 2 failed: Device '{device_name}' not found")
                validation_steps.append(step2_result)
                return {
                    "success": False,
                    "validation_steps": validation_steps,
                    "errors": validation_errors,
                    "message": f"Failed at Step 2: Device '{device_name}' not found",
                    "suggestions": [
                        f"Check device name spelling: '{device_name}'",
                        "List all devices: list_foundries_devices()",
                    ],
                }
            devices_to_validate = matching_devices
        else:
            # Filter to only devices with VPN IP (VPN enabled)
            devices_to_validate = [d for d in all_devices if d.get("vpn_ip")]
            if not devices_to_validate:
                step2_result["status"] = "warning"
                step2_result["warning"] = "No devices with VPN enabled found"
                validation_warnings.append("Step 2 warning: No VPN-enabled devices")
                validation_steps.append(step2_result)
                return {
                    "success": True,
                    "validation_steps": validation_steps,
                    "warnings": validation_warnings,
                    "message": "Validation completed with warnings: No VPN-enabled devices",
                }

        step2_result["status"] = "passed"
        step2_result["details"] = {
            "total_devices": len(all_devices),
            "devices_to_validate": len(devices_to_validate),
            "device_names": [d.get("name") for d in devices_to_validate],
        }
        validation_steps.append(step2_result)

        # Step 3: Check devices are online and VPN is enabled
        step3_result = {
            "step": 3,
            "name": "Check Devices Online and VPN Enabled",
            "status": "pending",
            "details": {"devices": []},
        }

        devices_status = []
        for device in devices_to_validate:
            device_name_check = device.get("name")
            device_status = device.get("status", "Unknown")
            vpn_ip = device.get("vpn_ip")
            last_seen = device.get("last_seen")

            device_check = {
                "device_name": device_name_check,
                "status": device_status,
                "vpn_ip": vpn_ip,
                "last_seen": last_seen,
                "vpn_enabled": vpn_ip is not None,
                "online": device_status == "OK",
            }

            if not vpn_ip:
                device_check["warning"] = "VPN IP not found - VPN may not be enabled"
                validation_warnings.append(f"Device {device_name_check}: VPN IP not found")

            if device_status != "OK":
                device_check["warning"] = f"Device status is '{device_status}', not 'OK'"
                validation_warnings.append(
                    f"Device {device_name_check}: Status is '{device_status}'"
                )

            devices_status.append(device_check)

        step3_result["status"] = "passed"
        step3_result["details"]["devices"] = devices_status
        validation_steps.append(step3_result)

        # Step 4: Test ping and SSH connectivity
        step4_result = {
            "step": 4,
            "name": "Test Ping and SSH Connectivity",
            "status": "pending",
            "details": {"devices": []},
        }

        connectivity_results = []
        for device in devices_to_validate:
            device_name_check = device.get("name")
            vpn_ip = device.get("vpn_ip")

            if not vpn_ip:
                connectivity_results.append(
                    {
                        "device_name": device_name_check,
                        "vpn_ip": None,
                        "ping_test": "skipped",
                        "ssh_test": "skipped",
                        "error": "No VPN IP available",
                    }
                )
                continue

            device_connectivity = {
                "device_name": device_name_check,
                "vpn_ip": vpn_ip,
            }

            # Test ping
            ping_result = subprocess.run(
                ["ping", "-c", "2", "-W", "2", vpn_ip],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )

            ping_success = ping_result.returncode == 0
            device_connectivity["ping_test"] = {
                "success": ping_success,
                "output": ping_result.stdout if ping_success else ping_result.stderr,
            }

            if not ping_success:
                validation_warnings.append(f"Device {device_name_check} ({vpn_ip}): Cannot ping")
                device_connectivity["ping_test"]["suggestion"] = (
                    "Device may not have device-to-device communication enabled. "
                    "Run: enable_foundries_device_to_device(device_name='...')"
                )

            # Test SSH connectivity
            ssh_success = False
            ssh_error = None
            ssh_output = None

            # Try SSH with default credentials (fio/fio for Foundries devices)
            try:
                ssh_test_cmd = [
                    "sshpass",
                    "-p",
                    "fio",
                    "ssh",
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "ConnectTimeout=5",
                    "-o",
                    "BatchMode=yes",
                    "fio@" + vpn_ip,
                    "echo 'SSH test successful'",
                ]

                ssh_result = subprocess.run(
                    ssh_test_cmd,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                ssh_success = ssh_result.returncode == 0
                ssh_output = ssh_result.stdout if ssh_success else ssh_result.stderr
                if not ssh_success:
                    ssh_error = ssh_result.stderr.strip() or "SSH connection failed"

            except Exception as e:
                ssh_error = f"SSH test exception: {e!s}"

            device_connectivity["ssh_test"] = {
                "success": ssh_success,
                "output": ssh_output,
                "error": ssh_error,
            }

            if not ssh_success:
                validation_warnings.append(f"Device {device_name_check} ({vpn_ip}): Cannot SSH")
                device_connectivity["ssh_test"]["suggestion"] = (
                    "Device may not have device-to-device communication enabled. "
                    "Run: enable_foundries_device_to_device(device_name='...')"
                )

            connectivity_results.append(device_connectivity)

        step4_result["status"] = (
            "passed"
            if all(
                d.get("ping_test", {}).get("success", False)
                and d.get("ssh_test", {}).get("success", False)
                for d in connectivity_results
                if d.get("ping_test") != "skipped"
            )
            else "warning"
        )
        step4_result["details"]["devices"] = connectivity_results
        validation_steps.append(step4_result)

        # Summary
        all_passed = len(validation_errors) == 0 and all(
            step.get("status") == "passed" for step in validation_steps
        )

        return {
            "success": all_passed,
            "validation_steps": validation_steps,
            "errors": validation_errors if validation_errors else None,
            "warnings": validation_warnings if validation_warnings else None,
            "devices_validated": len(devices_to_validate),
            "devices_connectivity": connectivity_results,
            "message": (
                "All validation steps passed successfully"
                if all_passed
                else f"Validation completed with {len(validation_errors)} error(s) and {len(validation_warnings)} warning(s)"
            ),
            "next_steps": (
                []
                if all_passed
                else _generate_next_steps(
                    validation_errors, validation_warnings, connectivity_results
                )
            ),
        }

    except Exception as e:
        logger.error(f"Failed to validate Foundries device connectivity: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Validation failed: {e!s}",
            "validation_steps": validation_steps if "validation_steps" in locals() else [],
            "suggestions": [
                "Check fioctl is installed and configured: fioctl --version",
                "Check Foundries VPN is connected: foundries_vpn_status()",
                "Connect to VPN if needed: connect_foundries_vpn()",
                "Review error details above",
            ],
        }


def _generate_next_steps(
    validation_errors: List[str],
    validation_warnings: List[str],
    connectivity_results: List[Dict[str, Any]],
) -> List[str]:
    """Generate specific, actionable next steps based on validation results."""
    next_steps = []

    # Check for connectivity failures
    ping_failures = [
        d
        for d in connectivity_results
        if d.get("ping_test") != "skipped" and not d.get("ping_test", {}).get("success", False)
    ]
    ssh_failures = [
        d
        for d in connectivity_results
        if d.get("ssh_test") != "skipped" and not d.get("ssh_test", {}).get("success", False)
    ]

    if ping_failures or ssh_failures:
        failed_devices = set()
        for d in ping_failures + ssh_failures:
            device_name = d.get("device_name")
            if device_name:
                failed_devices.add(device_name)

        if failed_devices:
            device_list = ", ".join([f"'{d}'" for d in failed_devices])
            next_steps.append(
                f"⚠️ CRITICAL: Enable device-to-device communication for devices: {device_list}"
            )
            next_steps.append(
                f"   Run: enable_foundries_device_to_device(device_name='{list(failed_devices)[0]}')"
            )
            next_steps.append(
                "   See MCP resource docs://foundries_vpn/clean_installation Part 3.3 for details"
            )

    # Add general troubleshooting steps
    if validation_errors:
        next_steps.append("Review validation errors above")

    if not next_steps:
        next_steps.extend(
            [
                "Check VPN connection: foundries_vpn_status()",
                "List devices: list_foundries_devices()",
                "Test specific device: test_device(device_id)",
            ]
        )

    return next_steps
