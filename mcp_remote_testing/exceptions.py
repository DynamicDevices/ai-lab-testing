"""
Custom Exceptions for MCP Remote Testing

Copyright (C) 2025 Dynamic Devices Ltd
License: GPL-3.0-or-later
"""

from typing import Optional


class MCPError(Exception):
    """Base exception for all MCP errors"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary for JSON serialization"""
        return {
            "error": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


class ConfigurationError(MCPError):
    """Configuration-related errors"""
    pass


class DeviceError(MCPError):
    """Device-related errors"""
    
    def __init__(self, message: str, device_id: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.device_id = device_id
        if device_id:
            self.details["device_id"] = device_id


class DeviceNotFoundError(DeviceError):
    """Device not found in configuration"""
    pass


class DeviceConnectionError(DeviceError):
    """Failed to connect to device"""
    pass


class DeviceTimeoutError(DeviceError):
    """Device operation timed out"""
    pass


class NetworkError(MCPError):
    """Network-related errors"""
    pass


class VPNError(NetworkError):
    """VPN connection errors"""
    pass


class SSHError(MCPError):
    """SSH-related errors"""
    
    def __init__(self, message: str, device_id: Optional[str] = None, command: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.device_id = device_id
        self.command = command
        if device_id:
            self.details["device_id"] = device_id
        if command:
            self.details["command"] = command


class AuthenticationError(SSHError):
    """SSH authentication errors"""
    pass


class PowerMonitoringError(MCPError):
    """Power monitoring errors"""
    pass


class OTAError(MCPError):
    """OTA update errors"""
    
    def __init__(self, message: str, device_id: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.device_id = device_id
        if device_id:
            self.details["device_id"] = device_id


class ContainerError(MCPError):
    """Container deployment errors"""
    
    def __init__(self, message: str, device_id: Optional[str] = None, container_name: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.device_id = device_id
        self.container_name = container_name
        if device_id:
            self.details["device_id"] = device_id
        if container_name:
            self.details["container_name"] = container_name

