"""
File Transfer Tools for Remote Devices

Tools for copying files to/from remote devices and syncing directories.
Optimized for speed using multiplexed SSH connections (ControlMaster) and parallel transfers.

Copyright (C) 2025 Dynamic Devices Ltd
License: GPL-3.0-or-later
"""

import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from lab_testing.exceptions import DeviceNotFoundError
from lab_testing.tools.device_manager import load_device_config, resolve_device_identifier
from lab_testing.utils.credentials import get_credential
from lab_testing.utils.logger import get_logger
from lab_testing.utils.ssh_pool import get_persistent_ssh_connection

logger = get_logger()


def _extract_scp_error(stderr_text: str) -> str:
    """
    Extract the actual error message from scp/ssh stderr output.
    Filters out banners/motd and returns the actual error line.

    Args:
        stderr_text: Raw stderr output from scp/ssh command

    Returns:
        Clean error message
    """
    if not stderr_text:
        return "Unknown error"

    # Split into lines and filter out empty lines
    error_lines = [line.strip() for line in stderr_text.split("\n") if line.strip()]

    # Look for actual error lines (usually start with "scp:" or "ssh:")
    for line in reversed(error_lines):  # Check from end (most recent)
        if line.startswith("scp:") or line.startswith("ssh:"):
            return line

    # If no scp/ssh prefix found, use the last non-empty line
    if error_lines:
        return error_lines[-1]

    return "Unknown error"


def copy_file_to_device(
    device_id: str,
    local_path: str,
    remote_path: str,
    username: Optional[str] = None,
    preserve_permissions: bool = True,
) -> Dict[str, Any]:
    """
    Copy a file from local machine to remote device.

    Args:
        device_id: Device identifier (device_id or friendly_name)
        local_path: Local file path to copy
        remote_path: Remote destination path on device
        username: SSH username (optional, uses device default)
        preserve_permissions: Preserve file permissions and timestamps (default: True)

    Returns:
        Dictionary with operation results
    """
    # Resolve to actual device_id
    resolved_device_id = resolve_device_identifier(device_id)
    if not resolved_device_id:
        error_msg = f"Device '{device_id}' not found"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "device_id": device_id,
        }

    config = load_device_config()
    devices = config.get("devices", {})
    device = devices.get(resolved_device_id)

    if not device:
        error_msg = f"Device '{resolved_device_id}' not found in config"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "device_id": resolved_device_id,
        }

    ip = device.get("ip")
    if not ip:
        error_msg = f"Device '{resolved_device_id}' has no IP address"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "device_id": resolved_device_id,
        }

    # Check local file exists
    local_file = Path(local_path)
    if not local_file.exists():
        error_msg = f"Local file not found: {local_path}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "local_path": local_path,
        }

    if not local_file.is_file():
        error_msg = f"Local path is not a file: {local_path}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "local_path": local_path,
        }

    # Determine username
    if not username:
        username = device.get("ssh_user", "root")
        # Try to get from cached credentials
        cred = get_credential(resolved_device_id, "ssh")
        if cred and cred.get("username"):
            username = cred["username"]

    ssh_port = device.get("ssh_port", 22)

    try:
        # Get or create multiplexed SSH connection for faster transfers
        control_path = f"/tmp/ssh_mcp_{resolved_device_id}_{ip.replace('.', '_')}"
        master = get_persistent_ssh_connection(ip, username, resolved_device_id, ssh_port)

        # Build scp command with ControlMaster for multiplexing
        scp_cmd = ["scp"]

        if master and master.poll() is None:
            # Use existing multiplexed connection (much faster)
            scp_cmd.extend(["-o", f"ControlPath={control_path}"])
            logger.debug(f"Using multiplexed SSH connection for {resolved_device_id}")
        else:
            # Fallback to direct connection
            scp_cmd.extend(["-o", "StrictHostKeyChecking=no"])
            scp_cmd.extend(["-o", "BatchMode=yes"])
            logger.debug(f"Using direct SSH connection for {resolved_device_id}")

        # Preserve permissions if requested
        if preserve_permissions:
            scp_cmd.append("-p")  # Preserve modification times, access times, and modes

        # Add compression for faster transfers over slow links
        scp_cmd.append("-C")  # Enable compression

        # Add source and destination
        scp_cmd.append(str(local_file))
        scp_cmd.append(f"{username}@{ip}:{remote_path}")

        # Execute scp
        result = subprocess.run(scp_cmd, check=False, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            logger.info(f"Successfully copied {local_path} to {resolved_device_id}:{remote_path}")
            return {
                "success": True,
                "device_id": resolved_device_id,
                "friendly_name": device.get("friendly_name")
                or device.get("name", resolved_device_id),
                "ip": ip,
                "local_path": str(local_path),
                "remote_path": remote_path,
                "message": f"File copied successfully to {remote_path}",
                "next_steps": [
                    f"Verify file on device: ssh_to_device(device_id, 'ls -lh {remote_path}')",
                    f"Check file contents: ssh_to_device(device_id, 'cat {remote_path}')",
                ],
            }

        actual_error = _extract_scp_error(result.stderr.strip() if result.stderr else "")
        error_msg = f"Failed to copy file: {actual_error}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "device_id": resolved_device_id,
            "local_path": str(local_path),
            "remote_path": remote_path,
            "suggestions": [
                "Check SSH key is installed: check_ssh_key_status(device_id)",
                "Verify device is online: test_device(device_id)",
                "Check remote directory exists: ssh_to_device(device_id, 'mkdir -p $(dirname remote_path)')",
            ],
        }

    except subprocess.TimeoutExpired:
        error_msg = "File copy timed out (60 seconds)"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "device_id": resolved_device_id,
        }
    except Exception as e:
        error_msg = f"Failed to copy file: {e!s}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "error": error_msg,
            "device_id": resolved_device_id,
        }


def copy_file_from_device(
    device_id: str,
    remote_path: str,
    local_path: str,
    username: Optional[str] = None,
    preserve_permissions: bool = True,
) -> Dict[str, Any]:
    """
    Copy a file from remote device to local machine.

    Args:
        device_id: Device identifier (device_id or friendly_name)
        remote_path: Remote file path on device
        local_path: Local destination path
        username: SSH username (optional, uses device default)
        preserve_permissions: Preserve file permissions and timestamps (default: True)

    Returns:
        Dictionary with operation results
    """
    # Resolve to actual device_id
    resolved_device_id = resolve_device_identifier(device_id)
    if not resolved_device_id:
        error_msg = f"Device '{device_id}' not found"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "device_id": device_id,
        }

    config = load_device_config()
    devices = config.get("devices", {})
    device = devices.get(resolved_device_id)

    if not device:
        error_msg = f"Device '{resolved_device_id}' not found in config"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "device_id": resolved_device_id,
        }

    ip = device.get("ip")
    if not ip:
        error_msg = f"Device '{resolved_device_id}' has no IP address"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "device_id": resolved_device_id,
        }

    # Determine username
    if not username:
        username = device.get("ssh_user", "root")
        # Try to get from cached credentials
        cred = get_credential(resolved_device_id, "ssh")
        if cred and cred.get("username"):
            username = cred["username"]

    ssh_port = device.get("ssh_port", 22)

    # Ensure local directory exists
    local_file = Path(local_path)
    local_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Get or create multiplexed SSH connection for faster transfers
        control_path = f"/tmp/ssh_mcp_{resolved_device_id}_{ip.replace('.', '_')}"
        master = get_persistent_ssh_connection(ip, username, resolved_device_id, ssh_port)

        # Build scp command with ControlMaster for multiplexing
        scp_cmd = ["scp"]

        if master and master.poll() is None:
            # Use existing multiplexed connection (much faster)
            scp_cmd.extend(["-o", f"ControlPath={control_path}"])
            logger.debug(f"Using multiplexed SSH connection for {resolved_device_id}")
        else:
            # Fallback to direct connection
            scp_cmd.extend(["-o", "StrictHostKeyChecking=no"])
            scp_cmd.extend(["-o", "BatchMode=yes"])
            logger.debug(f"Using direct SSH connection for {resolved_device_id}")

        # Preserve permissions if requested
        if preserve_permissions:
            scp_cmd.append("-p")  # Preserve modification times, access times, and modes

        # Add compression for faster transfers over slow links
        scp_cmd.append("-C")  # Enable compression

        # Add source and destination
        scp_cmd.append(f"{username}@{ip}:{remote_path}")
        scp_cmd.append(str(local_file))

        # Execute scp
        result = subprocess.run(scp_cmd, check=False, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            logger.info(
                f"Successfully copied {remote_path} from {resolved_device_id} to {local_path}"
            )
            return {
                "success": True,
                "device_id": resolved_device_id,
                "friendly_name": device.get("friendly_name")
                or device.get("name", resolved_device_id),
                "ip": ip,
                "remote_path": remote_path,
                "local_path": str(local_file),
                "message": f"File copied successfully to {local_path}",
                "next_steps": [
                    f"File is available locally at: {local_path}",
                    f"Check file: cat {local_path}",
                ],
            }

        actual_error = _extract_scp_error(result.stderr.strip() if result.stderr else "")
        error_msg = f"Failed to copy file: {actual_error}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "device_id": resolved_device_id,
            "remote_path": remote_path,
            "local_path": str(local_path),
            "suggestions": [
                "Check SSH key is installed: check_ssh_key_status(device_id)",
                "Verify device is online: test_device(device_id)",
                f"Check remote file exists: ssh_to_device(device_id, 'ls -lh {remote_path}')",
            ],
        }

    except subprocess.TimeoutExpired:
        error_msg = "File copy timed out (60 seconds)"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "device_id": resolved_device_id,
        }
    except Exception as e:
        error_msg = f"Failed to copy file: {e!s}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "error": error_msg,
            "device_id": resolved_device_id,
        }


def sync_directory_to_device(
    device_id: str,
    local_dir: str,
    remote_dir: str,
    username: Optional[str] = None,
    exclude: Optional[list] = None,
    delete: bool = False,
) -> Dict[str, Any]:
    """
    Sync a local directory to remote device using rsync.
    More efficient than copying individual files for multiple files.

    Args:
        device_id: Device identifier (device_id or friendly_name)
        local_dir: Local directory to sync
        remote_dir: Remote destination directory on device
        username: SSH username (optional, uses device default)
        exclude: List of patterns to exclude (e.g., ['*.pyc', '__pycache__'])
        delete: Delete files on remote that don't exist locally (default: False)

    Returns:
        Dictionary with operation results
    """
    # Resolve to actual device_id
    resolved_device_id = resolve_device_identifier(device_id)
    if not resolved_device_id:
        error_msg = f"Device '{device_id}' not found"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "device_id": device_id,
        }

    config = load_device_config()
    devices = config.get("devices", {})
    device = devices.get(resolved_device_id)

    if not device:
        error_msg = f"Device '{resolved_device_id}' not found in config"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "device_id": resolved_device_id,
        }

    ip = device.get("ip")
    if not ip:
        error_msg = f"Device '{resolved_device_id}' has no IP address"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "device_id": resolved_device_id,
        }

    # Check local directory exists
    local_path = Path(local_dir)
    if not local_path.exists():
        error_msg = f"Local directory not found: {local_dir}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "local_dir": local_dir,
        }

    if not local_path.is_dir():
        error_msg = f"Local path is not a directory: {local_dir}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "local_dir": local_dir,
        }

    # Determine username
    if not username:
        username = device.get("ssh_user", "root")
        # Try to get from cached credentials
        cred = get_credential(resolved_device_id, "ssh")
        if cred and cred.get("username"):
            username = cred["username"]

    ssh_port = device.get("ssh_port", 22)

    try:
        # Check if rsync is available on remote device
        check_rsync_cmd = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "BatchMode=yes",
            f"{username}@{ip}",
            "-p",
            str(ssh_port),
            "which rsync",
        ]
        rsync_check = subprocess.run(check_rsync_cmd, check=False, capture_output=True, timeout=10)
        if rsync_check.returncode != 0:
            error_msg = "rsync is not installed on the remote device"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "device_id": resolved_device_id,
                "local_dir": str(local_path),
                "remote_dir": remote_dir,
                "suggestions": [
                    "Install rsync on device: ssh_to_device(device_id, 'opkg install rsync') or equivalent",
                    "Use copy_files_to_device_parallel for multiple files instead",
                    "Use copy_file_to_device for individual files",
                    "Check device package manager: ssh_to_device(device_id, 'which opkg || which apt || which yum')",
                ],
            }

        # Get or create multiplexed SSH connection for faster transfers
        control_path = f"/tmp/ssh_mcp_{resolved_device_id}_{ip.replace('.', '_')}"
        master = get_persistent_ssh_connection(ip, username, resolved_device_id, ssh_port)

        # Build rsync command optimized for speed
        rsync_cmd = [
            "rsync",
            "-avz",  # -a: archive, -v: verbose, -z: compress
            "--partial",  # Keep partial files for resume
            "--progress",  # Show progress
        ]

        # Use multiplexed SSH connection if available
        if master and master.poll() is None:
            # Use existing multiplexed connection (much faster for multiple files)
            rsync_cmd.extend(["-e", f"ssh -o ControlPath={control_path} -o BatchMode=yes"])
            logger.debug(f"Using multiplexed SSH connection for rsync to {resolved_device_id}")
        else:
            # Fallback to direct connection
            rsync_cmd.extend(["-e", "ssh -o StrictHostKeyChecking=no -o BatchMode=yes"])
            logger.debug(f"Using direct SSH connection for rsync to {resolved_device_id}")

        # Add exclude patterns
        if exclude:
            for pattern in exclude:
                rsync_cmd.extend(["--exclude", pattern])

        # Add delete flag
        if delete:
            rsync_cmd.append("--delete")

        # Add source and destination (trailing slash ensures directory contents are synced)
        source = str(local_path)
        if not source.endswith("/"):
            source += "/"
        rsync_cmd.append(source)
        rsync_cmd.append(f"{username}@{ip}:{remote_dir}")

        # Execute rsync
        result = subprocess.run(rsync_cmd, check=False, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            logger.info(f"Successfully synced {local_dir} to {resolved_device_id}:{remote_dir}")
            return {
                "success": True,
                "device_id": resolved_device_id,
                "friendly_name": device.get("friendly_name")
                or device.get("name", resolved_device_id),
                "ip": ip,
                "local_dir": str(local_path),
                "remote_dir": remote_dir,
                "message": f"Directory synced successfully to {remote_dir}",
                "next_steps": [
                    f"Verify files on device: ssh_to_device(device_id, 'ls -lh {remote_dir}')",
                    f"Check sync status: ssh_to_device(device_id, 'du -sh {remote_dir}')",
                ],
            }

        error_msg = f"Failed to sync directory: {result.stderr.strip() or 'Unknown error'}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "device_id": resolved_device_id,
            "local_dir": str(local_path),
            "remote_dir": remote_dir,
            "suggestions": [
                "Check SSH key is installed: check_ssh_key_status(device_id)",
                "Verify device is online: test_device(device_id)",
                "Check rsync is installed on device: ssh_to_device(device_id, 'which rsync')",
                f"Ensure remote directory exists: ssh_to_device(device_id, 'mkdir -p {remote_dir}')",
            ],
        }

    except subprocess.TimeoutExpired:
        error_msg = "Directory sync timed out (300 seconds)"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "device_id": resolved_device_id,
        }
    except Exception as e:
        error_msg = f"Failed to sync directory: {e!s}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "error": error_msg,
            "device_id": resolved_device_id,
        }


def copy_files_to_device_parallel(
    device_id: str,
    file_pairs: List[Tuple[str, str]],
    username: Optional[str] = None,
    preserve_permissions: bool = True,
    max_workers: int = 5,
) -> Dict[str, Any]:
    """
    Copy multiple files to remote device in parallel using multiplexed SSH connections.
    Much faster than copying files sequentially - all transfers share the same SSH connection.

    Args:
        device_id: Device identifier (device_id or friendly_name)
        file_pairs: List of (local_path, remote_path) tuples
        username: SSH username (optional, uses device default)
        preserve_permissions: Preserve file permissions and timestamps (default: True)
        max_workers: Maximum number of parallel transfers (default: 5)

    Returns:
        Dictionary with operation results including individual file results
    """
    # Validate file_pairs
    if not file_pairs:
        error_msg = "No files to transfer (file_pairs is empty)"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "device_id": device_id,
        }

    # Validate file_pairs format
    for pair in file_pairs:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            error_msg = f"Invalid file pair format: {pair}. Expected [local_path, remote_path]"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "device_id": device_id,
            }

    # Resolve to actual device_id
    resolved_device_id = resolve_device_identifier(device_id)
    if not resolved_device_id:
        error_msg = f"Device '{device_id}' not found"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "device_id": device_id,
        }

    config = load_device_config()
    devices = config.get("devices", {})
    device = devices.get(resolved_device_id)

    if not device:
        error_msg = f"Device '{resolved_device_id}' not found in config"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "device_id": resolved_device_id,
        }

    ip = device.get("ip")
    if not ip:
        error_msg = f"Device '{resolved_device_id}' has no IP address"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "device_id": resolved_device_id,
        }

    # Determine username
    if not username:
        username = device.get("ssh_user", "root")
        cred = get_credential(resolved_device_id, "ssh")
        if cred and cred.get("username"):
            username = cred["username"]

    ssh_port = device.get("ssh_port", 22)

    # Ensure all local files exist
    missing_files = []
    for local_path, _ in file_pairs:
        if not Path(local_path).exists():
            missing_files.append(local_path)

    if missing_files:
        return {
            "success": False,
            "error": f"Local files not found: {', '.join(missing_files)}",
            "missing_files": missing_files,
        }

    # Ensure multiplexed connection exists (shared by all transfers for maximum speed)
    control_path = f"/tmp/ssh_mcp_{resolved_device_id}_{ip.replace('.', '_')}"
    master = get_persistent_ssh_connection(ip, username, resolved_device_id, ssh_port)

    if not master or master.poll() is not None:
        logger.warning(
            f"Could not establish multiplexed connection for {resolved_device_id}, transfers will be slower"
        )

    # Copy files in parallel
    results = []
    successful = 0
    failed = 0

    def _copy_single_file(local_path: str, remote_path: str) -> Dict[str, Any]:
        """Copy a single file (used by ThreadPoolExecutor)"""
        try:
            # Build scp command with multiplexed connection
            scp_cmd = ["scp"]

            if master and master.poll() is None:
                scp_cmd.extend(["-o", f"ControlPath={control_path}"])
            else:
                scp_cmd.extend(["-o", "StrictHostKeyChecking=no"])
                scp_cmd.extend(["-o", "BatchMode=yes"])

            if preserve_permissions:
                scp_cmd.append("-p")

            scp_cmd.append("-C")  # Compression
            scp_cmd.append(str(local_path))
            scp_cmd.append(f"{username}@{ip}:{remote_path}")

            result = subprocess.run(
                scp_cmd, check=False, capture_output=True, text=True, timeout=120
            )

            return {
                "local_path": local_path,
                "remote_path": remote_path,
                "success": result.returncode == 0,
                "error": result.stderr.strip() if result.returncode != 0 else None,
            }
        except Exception as e:
            return {
                "local_path": local_path,
                "remote_path": remote_path,
                "success": False,
                "error": str(e),
            }

    # Execute transfers in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_copy_single_file, local_path, remote_path): (local_path, remote_path)
            for local_path, remote_path in file_pairs
        }

        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            if result["success"]:
                successful += 1
            else:
                failed += 1

    logger.info(
        f"Parallel file transfer to {resolved_device_id}: {successful} successful, {failed} failed"
    )

    return {
        "success": failed == 0,
        "device_id": resolved_device_id,
        "friendly_name": device.get("friendly_name") or device.get("name", resolved_device_id),
        "ip": ip,
        "total_files": len(file_pairs),
        "successful": successful,
        "failed": failed,
        "results": results,
        "message": f"Transferred {successful}/{len(file_pairs)} files successfully",
        "next_steps": (
            [
                "Review individual file results in 'results' field",
                "Verify files on device: ssh_to_device(device_id, 'ls -lh <remote_path>')",
            ]
            if failed == 0
            else [
                "Some files failed to transfer - check 'results' field for details",
                "Retry failed files individually: copy_file_to_device(device_id, local_path, remote_path)",
            ]
        ),
    }
