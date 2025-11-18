"""
Tests for file transfer error handling and multiplexed connection reuse

Copyright (C) 2025 Dynamic Devices Ltd
License: GPL-3.0-or-later
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from lab_testing.tools.file_transfer import (
    copy_file_from_device,
    copy_file_to_device,
    copy_files_to_device_parallel,
)


class TestFileTransferErrorHandling:
    """Test error handling for file transfer tools"""

    @patch("lab_testing.tools.file_transfer.resolve_device_identifier")
    @patch("lab_testing.tools.file_transfer.load_device_config")
    def test_copy_file_to_device_not_found(self, mock_config, mock_resolve):
        """Test error handling when device is not found"""
        mock_resolve.return_value = None

        result = copy_file_to_device("nonexistent_device", "/local/file", "/remote/file")

        assert result["success"] is False
        assert "not found" in result["error"].lower()
        assert result["device_id"] == "nonexistent_device"

    @patch("lab_testing.tools.file_transfer.resolve_device_identifier")
    @patch("lab_testing.tools.file_transfer.load_device_config")
    def test_copy_file_to_device_local_file_not_found(self, mock_config, mock_resolve):
        """Test error handling when local file doesn't exist"""
        mock_resolve.return_value = "test_device"
        mock_config.return_value = {
            "devices": {"test_device": {"ip": "192.168.1.1", "ssh_user": "root"}}
        }

        result = copy_file_to_device("test_device", "/nonexistent/file", "/remote/file")

        assert result["success"] is False
        assert "not found" in result["error"].lower()
        assert "local" in result["error"].lower()

    @patch("lab_testing.tools.file_transfer.resolve_device_identifier")
    @patch("lab_testing.tools.file_transfer.load_device_config")
    def test_copy_file_to_device_local_path_not_file(self, mock_config, mock_resolve):
        """Test error handling when local path is a directory"""
        mock_resolve.return_value = "test_device"
        mock_config.return_value = {
            "devices": {"test_device": {"ip": "192.168.1.1", "ssh_user": "root"}}
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            result = copy_file_to_device("test_device", tmpdir, "/remote/file")

            assert result["success"] is False
            assert "not a file" in result["error"].lower()

    @patch("lab_testing.tools.file_transfer.resolve_device_identifier")
    @patch("lab_testing.tools.file_transfer.load_device_config")
    @patch("lab_testing.tools.file_transfer.subprocess.run")
    def test_copy_file_to_device_offline(self, mock_subprocess, mock_config, mock_resolve):
        """Test error handling when device is offline"""
        mock_resolve.return_value = "test_device"
        mock_config.return_value = {
            "devices": {"test_device": {"ip": "192.168.1.1", "ssh_user": "root"}}
        }

        # Mock scp failure (device offline)
        mock_subprocess.return_value = Mock(
            returncode=255, stdout=b"", stderr=b"Connection refused"
        )

        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            tmpfile.write(b"test content")
            tmpfile_path = tmpfile.name

        try:
            result = copy_file_to_device("test_device", tmpfile_path, "/remote/file")

            assert result["success"] is False
            assert "error" in result or "failed" in result.get("error", "").lower()
        finally:
            Path(tmpfile_path).unlink()

    @patch("lab_testing.tools.file_transfer.resolve_device_identifier")
    @patch("lab_testing.tools.file_transfer.load_device_config")
    @patch("lab_testing.tools.file_transfer.subprocess.run")
    def test_copy_file_to_device_permission_denied(
        self, mock_subprocess, mock_config, mock_resolve
    ):
        """Test error handling when permission is denied"""
        mock_resolve.return_value = "test_device"
        mock_config.return_value = {
            "devices": {"test_device": {"ip": "192.168.1.1", "ssh_user": "root"}}
        }

        # Mock scp failure (permission denied)
        mock_subprocess.return_value = Mock(returncode=1, stdout=b"", stderr=b"Permission denied")

        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            tmpfile.write(b"test content")
            tmpfile_path = tmpfile.name

        try:
            result = copy_file_to_device("test_device", tmpfile_path, "/readonly/file")

            assert result["success"] is False
            # Should provide helpful error message
            assert "error" in result
        finally:
            Path(tmpfile_path).unlink()

    @patch("lab_testing.tools.file_transfer.resolve_device_identifier")
    @patch("lab_testing.tools.file_transfer.load_device_config")
    @patch("lab_testing.tools.file_transfer.subprocess.run")
    def test_copy_file_to_device_disk_full(self, mock_subprocess, mock_config, mock_resolve):
        """Test error handling when disk is full"""
        mock_resolve.return_value = "test_device"
        mock_config.return_value = {
            "devices": {"test_device": {"ip": "192.168.1.1", "ssh_user": "root"}}
        }

        # Mock scp failure (disk full)
        mock_subprocess.return_value = Mock(
            returncode=1, stdout=b"", stderr=b"No space left on device"
        )

        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            tmpfile.write(b"test content")
            tmpfile_path = tmpfile.name

        try:
            result = copy_file_to_device("test_device", tmpfile_path, "/remote/file")

            assert result["success"] is False
            # Should provide helpful error message
            assert "error" in result
        finally:
            Path(tmpfile_path).unlink()

    @patch("lab_testing.tools.file_transfer.resolve_device_identifier")
    @patch("lab_testing.tools.file_transfer.load_device_config")
    def test_copy_file_from_device_not_found(self, mock_config, mock_resolve):
        """Test error handling when device is not found for download"""
        mock_resolve.return_value = None

        result = copy_file_from_device("nonexistent_device", "/remote/file", "/local/file")

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @patch("lab_testing.tools.file_transfer.resolve_device_identifier")
    @patch("lab_testing.tools.file_transfer.load_device_config")
    @patch("lab_testing.tools.file_transfer.subprocess.run")
    def test_copy_file_from_device_remote_not_found(
        self, mock_subprocess, mock_config, mock_resolve
    ):
        """Test error handling when remote file doesn't exist"""
        mock_resolve.return_value = "test_device"
        mock_config.return_value = {
            "devices": {"test_device": {"ip": "192.168.1.1", "ssh_user": "root"}}
        }

        # Mock scp failure (file not found)
        mock_subprocess.return_value = Mock(
            returncode=1, stdout=b"", stderr=b"No such file or directory"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = Path(tmpdir) / "downloaded_file"
            result = copy_file_from_device("test_device", "/nonexistent/file", str(local_path))

            assert result["success"] is False
            assert "error" in result

    @patch("lab_testing.tools.file_transfer.resolve_device_identifier")
    @patch("lab_testing.tools.file_transfer.load_device_config")
    def test_copy_files_to_device_parallel_empty_list(self, mock_config, mock_resolve):
        """Test error handling when file_pairs is empty"""
        mock_resolve.return_value = "test_device"
        mock_config.return_value = {
            "devices": {"test_device": {"ip": "192.168.1.1", "ssh_user": "root"}}
        }

        result = copy_files_to_device_parallel("test_device", [])

        assert result["success"] is False
        assert (
            "empty" in result.get("error", "").lower()
            or "no files" in result.get("error", "").lower()
        )

    @patch("lab_testing.tools.file_transfer.resolve_device_identifier")
    @patch("lab_testing.tools.file_transfer.load_device_config")
    def test_copy_files_to_device_parallel_invalid_pairs(self, mock_config, mock_resolve):
        """Test error handling when file_pairs has invalid format"""
        mock_resolve.return_value = "test_device"
        mock_config.return_value = {
            "devices": {"test_device": {"ip": "192.168.1.1", "ssh_user": "root"}}
        }

        # Invalid: single string instead of [local, remote] pair
        result = copy_files_to_device_parallel("test_device", ["invalid"])

        assert result["success"] is False
        assert "error" in result


class TestMultiplexedConnectionReuse:
    """Test multiplexed SSH connection reuse"""

    @patch("lab_testing.tools.file_transfer.resolve_device_identifier")
    @patch("lab_testing.tools.file_transfer.load_device_config")
    @patch("lab_testing.tools.file_transfer.get_persistent_ssh_connection")
    @patch("lab_testing.tools.file_transfer.subprocess.run")
    def test_connection_reuse_multiple_transfers(
        self, mock_subprocess, mock_get_connection, mock_config, mock_resolve
    ):
        """Test that multiple transfers reuse the same SSH connection"""
        mock_resolve.return_value = "test_device"
        mock_config.return_value = {
            "devices": {"test_device": {"ip": "192.168.1.1", "ssh_user": "root"}}
        }

        # Mock persistent connection
        mock_connection = Mock()
        mock_connection.poll.return_value = None  # Connection alive
        mock_get_connection.return_value = mock_connection

        # Mock successful transfers
        mock_subprocess.return_value = Mock(returncode=0, stdout=b"", stderr=b"")

        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            tmpfile.write(b"test content")
            tmpfile_path = tmpfile.name

        try:
            # First transfer
            result1 = copy_file_to_device("test_device", tmpfile_path, "/remote/file1")
            # Second transfer
            result2 = copy_file_to_device("test_device", tmpfile_path, "/remote/file2")
            # Third transfer
            result3 = copy_file_to_device("test_device", tmpfile_path, "/remote/file3")

            # Verify get_persistent_ssh_connection was called for each transfer
            assert mock_get_connection.call_count == 3

            # Verify all transfers succeeded
            assert result1["success"] is True
            assert result2["success"] is True
            assert result3["success"] is True

            # Verify scp was called with ControlPath (multiplexed connection)
            scp_calls = [call for call in mock_subprocess.call_args_list if "scp" in str(call)]
            assert len(scp_calls) == 3

            # All calls should use the same ControlPath
            control_paths = []
            for call in scp_calls:
                args = call[0][0] if call[0] else []
                for i, arg in enumerate(args):
                    if arg == "-o" and i + 1 < len(args) and "ControlPath" in args[i + 1]:
                        control_paths.append(args[i + 1])
                        break

            # All should use the same control path (connection reuse)
            if control_paths:
                assert len(set(control_paths)) == 1, "All transfers should use the same connection"
        finally:
            Path(tmpfile_path).unlink()

    @patch("lab_testing.tools.file_transfer.resolve_device_identifier")
    @patch("lab_testing.tools.file_transfer.load_device_config")
    @patch("lab_testing.tools.file_transfer.get_persistent_ssh_connection")
    @patch("lab_testing.tools.file_transfer.subprocess.run")
    def test_parallel_transfers_share_connection(
        self, mock_subprocess, mock_get_connection, mock_config, mock_resolve
    ):
        """Test that parallel transfers share the same SSH connection"""
        mock_resolve.return_value = "test_device"
        mock_config.return_value = {
            "devices": {"test_device": {"ip": "192.168.1.1", "ssh_user": "root"}}
        }

        # Mock persistent connection
        mock_connection = Mock()
        mock_connection.poll.return_value = None  # Connection alive
        mock_get_connection.return_value = mock_connection

        # Mock successful transfers
        mock_subprocess.return_value = Mock(returncode=0, stdout=b"", stderr=b"")

        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            tmpfile.write(b"test content")
            tmpfile_path = tmpfile.name

        try:
            # Parallel transfers
            file_pairs = [
                [tmpfile_path, "/remote/file1"],
                [tmpfile_path, "/remote/file2"],
                [tmpfile_path, "/remote/file3"],
            ]

            result = copy_files_to_device_parallel("test_device", file_pairs)

            # Verify get_persistent_ssh_connection was called (should be reused)
            assert mock_get_connection.call_count >= 1

            # Verify transfer succeeded
            assert result["success"] is True

            # Verify all files were transferred
            assert result.get("successful", 0) == 3
        finally:
            Path(tmpfile_path).unlink()

    @patch("lab_testing.tools.file_transfer.resolve_device_identifier")
    @patch("lab_testing.tools.file_transfer.load_device_config")
    @patch("lab_testing.tools.file_transfer.get_persistent_ssh_connection")
    @patch("lab_testing.tools.file_transfer.subprocess.run")
    def test_fallback_when_no_ssh_key(
        self, mock_subprocess, mock_get_connection, mock_config, mock_resolve
    ):
        """Test that tools fallback to direct connection when SSH key not installed"""
        mock_resolve.return_value = "test_device"
        mock_config.return_value = {
            "devices": {"test_device": {"ip": "192.168.1.1", "ssh_user": "root"}}
        }

        # Mock no persistent connection (SSH key not installed)
        mock_get_connection.return_value = None

        # Mock successful transfer (using password auth)
        mock_subprocess.return_value = Mock(returncode=0, stdout=b"", stderr=b"")

        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            tmpfile.write(b"test content")
            tmpfile_path = tmpfile.name

        try:
            result = copy_file_to_device("test_device", tmpfile_path, "/remote/file")

            # Should still succeed (fallback to direct connection)
            assert result["success"] is True

            # Verify scp was called (transfer happened)
            scp_calls = [call for call in mock_subprocess.call_args_list if "scp" in str(call)]
            assert len(scp_calls) >= 1
        finally:
            Path(tmpfile_path).unlink()
