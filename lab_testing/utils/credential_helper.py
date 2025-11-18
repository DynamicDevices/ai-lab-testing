"""
Helper functions for credential management during device discovery.

When discovering devices, we may need credentials but don't have a device_id yet.
This module provides helpers to cache credentials by IP address temporarily.
"""

from typing import Optional

from lab_testing.utils.credentials import cache_credential, get_credential


def get_credential_by_ip(ip: str, credential_type: str = "ssh") -> Optional[dict]:
    """
    Get credential for a device by IP address (used during discovery).

    Args:
        ip: IP address
        credential_type: Type of credential (ssh, sudo, etc.)

    Returns:
        Credential dict with username/password or None
    """
    return get_credential(ip, credential_type)


def cache_credential_by_ip(
    ip: str, username: str, password: Optional[str] = None, credential_type: str = "ssh"
):
    """
    Cache credential for a device by IP address (used during discovery).

    Args:
        ip: IP address
        username: Username
        password: Password (optional, prefer SSH keys)
        credential_type: Type of credential (ssh, sudo, etc.)
    """
    cache_credential(ip, username, password, credential_type)
