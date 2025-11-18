#!/usr/bin/env python3
"""
Real Device Testing: File Transfer Error Handling and Multiplexed Connection Reuse

Tests error handling scenarios and verifies multiplexed SSH connection reuse
with actual hardware.

Copyright (C) 2025 Dynamic Devices Ltd
License: GPL-3.0-or-later
"""

import tempfile
import time
from pathlib import Path

from lab_testing.tools.device_manager import test_device
from lab_testing.tools.file_transfer import (
    copy_file_from_device,
    copy_file_to_device,
    copy_files_to_device_parallel,
)


def test_error_handling():
    """Test error handling scenarios"""
    print("=" * 70)
    print("TESTING ERROR HANDLING")
    print("=" * 70)
    print()

    device_id = "test-sentai-board"

    # Test 1: Device not found
    print("Test 1: Device not found")
    print("-" * 70)
    result = copy_file_to_device("nonexistent_device", "/tmp/test.txt", "/tmp/test.txt")
    print(f"  Success: {result.get('success')}")
    print(f"  Error: {result.get('error', 'N/A')}")
    assert result["success"] is False, "Should fail for nonexistent device"
    assert "not found" in result.get("error", "").lower()
    print("  ✅ PASSED")
    print()

    # Test 2: Local file not found
    print("Test 2: Local file not found")
    print("-" * 70)
    result = copy_file_to_device(device_id, "/nonexistent/local/file.txt", "/tmp/test.txt")
    print(f"  Success: {result.get('success')}")
    print(f"  Error: {result.get('error', 'N/A')}")
    assert result["success"] is False, "Should fail for nonexistent local file"
    assert "not found" in result.get("error", "").lower()
    print("  ✅ PASSED")
    print()

    # Test 3: Permission denied (try to write to readonly location)
    print("Test 3: Permission denied (readonly location)")
    print("-" * 70)
    with tempfile.NamedTemporaryFile(delete=False, mode="w") as tmpfile:
        tmpfile.write("Test content")
        tmpfile_path = tmpfile.name

    try:
        # Try to write to /proc (readonly filesystem)
        result = copy_file_to_device(device_id, tmpfile_path, "/proc/test.txt")
        print(f"  Success: {result.get('success')}")
        print(f"  Error: {result.get('error', 'N/A')}")
        if result["success"] is False:
            print("  ✅ PASSED - Correctly detected permission error")
        else:
            print("  ⚠️  Note: Permission error not detected (may vary by device)")
    finally:
        Path(tmpfile_path).unlink()
    print()

    # Test 4: Remote file not found (download)
    print("Test 4: Remote file not found (download)")
    print("-" * 70)
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = Path(tmpdir) / "downloaded_file.txt"
        result = copy_file_from_device(device_id, "/nonexistent/remote/file.txt", str(local_path))
        print(f"  Success: {result.get('success')}")
        print(f"  Error: {result.get('error', 'N/A')}")
        assert result["success"] is False, "Should fail for nonexistent remote file"
        print("  ✅ PASSED")
    print()

    # Test 5: Empty file list for parallel transfer
    print("Test 5: Empty file list for parallel transfer")
    print("-" * 70)
    result = copy_files_to_device_parallel(device_id, [])
    print(f"  Success: {result.get('success')}")
    print(f"  Error: {result.get('error', 'N/A')}")
    assert result["success"] is False, "Should fail for empty file list"
    print("  ✅ PASSED")
    print()


def test_multiplexed_connection_reuse():
    """Test multiplexed SSH connection reuse"""
    print("=" * 70)
    print("TESTING MULTIPLEXED CONNECTION REUSE")
    print("=" * 70)
    print()

    device_id = "test-sentai-board"

    # Verify device is online
    print("Verifying device connectivity...")
    test_result = test_device(device_id)
    if not test_result.get("success"):
        print(f"  ❌ Device is offline: {test_result.get('error')}")
        return
    print("  ✅ Device is online")
    print()

    # Create test files
    test_files = []
    for i in range(5):
        with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=f"_{i}.txt") as tmpfile:
            tmpfile.write(f"Test content for file {i}\n" * 10)
            test_files.append(tmpfile.name)

    try:
        # Test 1: Sequential transfers (should reuse connection)
        print("Test 1: Sequential transfers (connection reuse)")
        print("-" * 70)
        times = []
        for i, test_file in enumerate(test_files):
            start_time = time.time()
            result = copy_file_to_device(device_id, test_file, f"/tmp/test_sequential_{i}.txt")
            elapsed = time.time() - start_time
            times.append(elapsed)

            if result["success"]:
                print(f"  Transfer {i+1}: {elapsed:.3f}s ✅")
            else:
                print(f"  Transfer {i+1}: FAILED - {result.get('error')}")
                break

        if len(times) == len(test_files):
            print(f"\n  First transfer: {times[0]:.3f}s")
            print(f"  Subsequent transfers: {times[1:5]}")
            avg_subsequent = sum(times[1:]) / len(times[1:])
            print(f"  Average subsequent: {avg_subsequent:.3f}s")

            if times[0] > avg_subsequent * 1.5:
                print("  ✅ Connection reuse detected (first transfer slower)")
            else:
                print("  ⚠️  Connection reuse not clearly detected (may vary)")
        print()

        # Test 2: Parallel transfers (should share connection)
        print("Test 2: Parallel transfers (shared connection)")
        print("-" * 70)
        file_pairs = [[test_files[i], f"/tmp/test_parallel_{i}.txt"] for i in range(5)]

        start_time = time.time()
        result = copy_files_to_device_parallel(device_id, file_pairs, max_workers=5)
        parallel_time = time.time() - start_time

        print(f"  Success: {result.get('success')}")
        if result["success"]:
            print(f"  Files transferred: {result.get('files_transferred', 0)}")
            print(f"  Total time: {parallel_time:.3f}s")
            print(f"  Average per file: {parallel_time/5:.3f}s")

            # Compare with sequential
            sequential_total = sum(times)
            print(f"\n  Sequential total: {sequential_total:.3f}s")
            print(f"  Parallel total: {parallel_time:.3f}s")
            speedup = sequential_total / parallel_time if parallel_time > 0 else 0
            print(f"  Speedup: {speedup:.2f}x")

            if speedup > 1.2:
                print("  ✅ Parallel transfers faster (connection sharing working)")
            else:
                print("  ⚠️  Parallel transfers not significantly faster")
        else:
            print(f"  Error: {result.get('error')}")
        print()

        # Test 3: Mixed operations (upload and download)
        print("Test 3: Mixed operations (upload and download)")
        print("-" * 70)
        # Upload
        start_time = time.time()
        upload_result = copy_file_to_device(device_id, test_files[0], "/tmp/test_mixed.txt")
        upload_time = time.time() - start_time

        # Download
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = Path(tmpdir) / "downloaded.txt"
            start_time = time.time()
            download_result = copy_file_from_device(
                device_id, "/tmp/test_mixed.txt", str(local_path)
            )
            download_time = time.time() - start_time

        print(f"  Upload: {upload_time:.3f}s {'✅' if upload_result['success'] else '❌'}")
        print(f"  Download: {download_time:.3f}s {'✅' if download_result['success'] else '❌'}")

        if upload_result["success"] and download_result["success"]:
            print("  ✅ Mixed operations successful")
        print()

    finally:
        # Cleanup
        for test_file in test_files:
            Path(test_file).unlink()


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("FILE TRANSFER ERROR HANDLING AND CONNECTION REUSE TESTING")
    print("=" * 70)
    print()

    try:
        # Test error handling
        test_error_handling()

        # Test connection reuse
        test_multiplexed_connection_reuse()

        print("=" * 70)
        print("ALL TESTS COMPLETED")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
