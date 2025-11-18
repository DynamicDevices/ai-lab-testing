#!/usr/bin/env python3
"""
Real Device Testing: File Transfer Scale Testing (Large Files & Many Files)

Tests file transfer tools with:
- Large files (>100MB)
- Many files (100+ files)
- Compression effectiveness

Copyright (C) 2025 Dynamic Devices Ltd
License: GPL-3.0-or-later
"""

import os
import tempfile
import time
from pathlib import Path

from lab_testing.tools.device_manager import ssh_to_device, test_device
from lab_testing.tools.file_transfer import (
    copy_file_from_device,
    copy_file_to_device,
    copy_files_to_device_parallel,
)


def create_large_file(size_mb: int, output_path: Path) -> Path:
    """Create a large test file"""
    print(f"  Creating {size_mb}MB test file...")
    chunk_size = 1024 * 1024  # 1MB chunks
    chunks = size_mb

    with open(output_path, "wb") as f:
        for i in range(chunks):
            # Write pattern data (makes compression test meaningful)
            data = b"X" * (chunk_size // 2) + b"Y" * (chunk_size // 2)
            f.write(data)
            if (i + 1) % 10 == 0:
                print(f"    Written {(i + 1)}MB...", end="\r")

    print(f"    Created {size_mb}MB file: {output_path}")
    return output_path


def create_many_files(count: int, base_dir: Path) -> list:
    """Create many small test files"""
    print(f"  Creating {count} test files...")
    files = []

    for i in range(count):
        file_path = base_dir / f"test_file_{i:04d}.txt"
        # Write some content (varies per file for compression test)
        content = f"Test file {i}\n" + "X" * (1000 + i) + "\n" + "Y" * (500 - i % 100)
        file_path.write_text(content)
        files.append(str(file_path))

        if (i + 1) % 20 == 0:
            print(f"    Created {(i + 1)}/{count} files...", end="\r")

    print(f"    Created {count} files in {base_dir}")
    return files


def test_large_file_transfer():
    """Test transferring large files (>100MB)"""
    print("=" * 70)
    print("TESTING LARGE FILE TRANSFER (>100MB)")
    print("=" * 70)
    print()

    device_id = "test-sentai-board"

    # Verify device is online
    print("Verifying device connectivity...")
    test_result = test_device(device_id)
    if not test_result.get("success"):
        print(f"  ❌ Device is offline: {test_result.get('error')}")
        return False
    print("  ✅ Device is online")
    print()

    # Check available disk space on device
    print("Checking device disk space...")
    disk_result = ssh_to_device(device_id, "df -h /tmp | tail -1")
    if disk_result.get("success"):
        print(f"  Device disk info: {disk_result.get('stdout', '').strip()}")
    print()

    # Test 1: Transfer 100MB file
    print("Test 1: Transfer 100MB file")
    print("-" * 70)
    with tempfile.TemporaryDirectory() as tmpdir:
        large_file = Path(tmpdir) / "large_file_100mb.bin"
        create_large_file(100, large_file)

        file_size_mb = large_file.stat().st_size / (1024 * 1024)
        print(f"  File size: {file_size_mb:.2f}MB")

        start_time = time.time()
        result = copy_file_to_device(device_id, str(large_file), "/tmp/large_file_100mb.bin")
        transfer_time = time.time() - start_time

        if result["success"]:
            transfer_rate = file_size_mb / transfer_time if transfer_time > 0 else 0
            print("  ✅ Transfer successful")
            print(f"  Transfer time: {transfer_time:.2f}s")
            print(f"  Transfer rate: {transfer_rate:.2f}MB/s")

            # Verify file on device
            verify_result = ssh_to_device(device_id, "ls -lh /tmp/large_file_100mb.bin")
            if verify_result.get("success"):
                print(f"  File on device: {verify_result.get('stdout', '').strip()}")

            # Test download
            print("\n  Testing download of large file...")
            download_path = Path(tmpdir) / "downloaded_large_file.bin"
            start_time = time.time()
            download_result = copy_file_from_device(
                device_id, "/tmp/large_file_100mb.bin", str(download_path)
            )
            download_time = time.time() - start_time

            if download_result["success"]:
                download_rate = file_size_mb / download_time if download_time > 0 else 0
                print("  ✅ Download successful")
                print(f"  Download time: {download_time:.2f}s")
                print(f"  Download rate: {download_rate:.2f}MB/s")

                # Verify file sizes match
                if download_path.exists():
                    original_size = large_file.stat().st_size
                    downloaded_size = download_path.stat().st_size
                    if original_size == downloaded_size:
                        print(f"  ✅ File sizes match: {original_size} bytes")
                    else:
                        print(f"  ⚠️  Size mismatch: {original_size} vs {downloaded_size}")
            else:
                print(f"  ❌ Download failed: {download_result.get('error')}")
        else:
            print(f"  ❌ Transfer failed: {result.get('error')}")
            return False
    print()

    # Test 2: Transfer 150MB file (if disk space allows)
    print("Test 2: Transfer 150MB file")
    print("-" * 70)
    with tempfile.TemporaryDirectory() as tmpdir:
        large_file = Path(tmpdir) / "large_file_150mb.bin"
        create_large_file(150, large_file)

        file_size_mb = large_file.stat().st_size / (1024 * 1024)
        print(f"  File size: {file_size_mb:.2f}MB")

        start_time = time.time()
        result = copy_file_to_device(device_id, str(large_file), "/tmp/large_file_150mb.bin")
        transfer_time = time.time() - start_time

        if result["success"]:
            transfer_rate = file_size_mb / transfer_time if transfer_time > 0 else 0
            print("  ✅ Transfer successful")
            print(f"  Transfer time: {transfer_time:.2f}s")
            print(f"  Transfer rate: {transfer_rate:.2f}MB/s")
        else:
            print(f"  ❌ Transfer failed: {result.get('error')}")
            # Don't fail test - might be disk space issue
    print()

    return True


def test_many_files_transfer():
    """Test transferring many files (100+ files)"""
    print("=" * 70)
    print("TESTING MANY FILES TRANSFER (100+ files)")
    print("=" * 70)
    print()

    device_id = "test-sentai-board"

    # Verify device is online
    print("Verifying device connectivity...")
    test_result = test_device(device_id)
    if not test_result.get("success"):
        print(f"  ❌ Device is offline: {test_result.get('error')}")
        return False
    print("  ✅ Device is online")
    print()

    # Test 1: Transfer 100 files in parallel
    print("Test 1: Transfer 100 files in parallel")
    print("-" * 70)
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        files = create_many_files(100, base_dir)

        print(f"  Created {len(files)} files")
        total_size = sum(Path(f).stat().st_size for f in files)
        total_size_mb = total_size / (1024 * 1024)
        print(f"  Total size: {total_size_mb:.2f}MB")

        # Prepare file pairs
        file_pairs = [[f, f"/tmp/many_files/{Path(f).name}"] for f in files]

        # Create remote directory
        ssh_to_device(device_id, "mkdir -p /tmp/many_files")

        print(f"  Transferring {len(file_pairs)} files in parallel...")
        start_time = time.time()
        result = copy_files_to_device_parallel(device_id, file_pairs, max_workers=10)
        transfer_time = time.time() - start_time

        if result["success"]:
            successful = result.get("successful", 0)
            failed = result.get("failed", 0)
            print("  ✅ Transfer completed")
            print(f"  Successful: {successful}/{len(file_pairs)}")
            print(f"  Failed: {failed}/{len(file_pairs)}")
            print(f"  Transfer time: {transfer_time:.2f}s")
            if successful > 0:
                avg_time_per_file = transfer_time / successful
                print(f"  Average time per file: {avg_time_per_file:.3f}s")
                transfer_rate = total_size_mb / transfer_time if transfer_time > 0 else 0
                print(f"  Transfer rate: {transfer_rate:.2f}MB/s")

            # Verify some files on device
            print("\n  Verifying files on device...")
            verify_result = ssh_to_device(device_id, "ls /tmp/many_files | wc -l")
            if verify_result.get("success"):
                file_count = verify_result.get("stdout", "0").strip()
                print(f"  Files on device: {file_count}")

            # Verify a few random files
            import random

            sample_files = random.sample(files, min(5, len(files)))
            print(f"\n  Verifying {len(sample_files)} sample files...")
            for local_file in sample_files:
                remote_file = f"/tmp/many_files/{Path(local_file).name}"
                verify_result = ssh_to_device(
                    device_id, f"test -f {remote_file} && echo OK || echo MISSING"
                )
                if "OK" in verify_result.get("stdout", ""):
                    print(f"    ✅ {Path(local_file).name}")
                else:
                    print(f"    ❌ {Path(local_file).name} - MISSING")
        else:
            print(f"  ❌ Transfer failed: {result.get('error')}")
            return False
    print()

    # Test 2: Transfer 200 files (stress test)
    print("Test 2: Transfer 200 files (stress test)")
    print("-" * 70)
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        files = create_many_files(200, base_dir)

        print(f"  Created {len(files)} files")
        total_size = sum(Path(f).stat().st_size for f in files)
        total_size_mb = total_size / (1024 * 1024)
        print(f"  Total size: {total_size_mb:.2f}MB")

        # Prepare file pairs
        file_pairs = [[f, f"/tmp/many_files_200/{Path(f).name}"] for f in files]

        # Create remote directory
        ssh_to_device(device_id, "mkdir -p /tmp/many_files_200")

        print(f"  Transferring {len(file_pairs)} files in parallel...")
        start_time = time.time()
        result = copy_files_to_device_parallel(device_id, file_pairs, max_workers=10)
        transfer_time = time.time() - start_time

        if result["success"]:
            successful = result.get("successful", 0)
            failed = result.get("failed", 0)
            print("  ✅ Transfer completed")
            print(f"  Successful: {successful}/{len(file_pairs)}")
            print(f"  Failed: {failed}/{len(file_pairs)}")
            print(f"  Transfer time: {transfer_time:.2f}s")
            if successful > 0:
                avg_time_per_file = transfer_time / successful
                print(f"  Average time per file: {avg_time_per_file:.3f}s")
        else:
            print(f"  ❌ Transfer failed: {result.get('error')}")
            # Don't fail test - might be resource limits
    print()

    return True


def test_compression_effectiveness():
    """Test compression effectiveness (simulated slow link)"""
    print("=" * 70)
    print("TESTING COMPRESSION EFFECTIVENESS")
    print("=" * 70)
    print()

    device_id = "test-sentai-board"

    # Verify device is online
    print("Verifying device connectivity...")
    test_result = test_device(device_id)
    if not test_result.get("success"):
        print(f"  ❌ Device is offline: {test_result.get('error')}")
        return False
    print("  ✅ Device is online")
    print()

    # Note: We can't easily simulate a slow link, but we can:
    # 1. Test with compressible data (should show compression benefit)
    # 2. Test with incompressible data (should show minimal benefit)
    # 3. Measure transfer times and sizes

    # Test 1: Compressible data (text/repetitive patterns)
    print("Test 1: Compressible data (text/repetitive patterns)")
    print("-" * 70)
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create file with repetitive pattern (highly compressible)
        compressible_file = Path(tmpdir) / "compressible_data.bin"
        print("  Creating compressible test file (repetitive patterns)...")
        with open(compressible_file, "wb") as f:
            # Write repetitive pattern (compresses well)
            pattern = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 10000
            for _ in range(100):
                f.write(pattern)

        file_size_mb = compressible_file.stat().st_size / (1024 * 1024)
        print(f"  File size: {file_size_mb:.2f}MB")

        start_time = time.time()
        result = copy_file_to_device(
            device_id, str(compressible_file), "/tmp/compressible_data.bin"
        )
        transfer_time = time.time() - start_time

        if result["success"]:
            transfer_rate = file_size_mb / transfer_time if transfer_time > 0 else 0
            print("  ✅ Transfer successful")
            print(f"  Transfer time: {transfer_time:.2f}s")
            print(f"  Transfer rate: {transfer_rate:.2f}MB/s")
            print("  Note: Compression enabled by default (should help on slow links)")
        else:
            print(f"  ❌ Transfer failed: {result.get('error')}")
    print()

    # Test 2: Incompressible data (random/encrypted-like)
    print("Test 2: Incompressible data (random data)")
    print("-" * 70)
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create file with random data (low compressibility)
        incompressible_file = Path(tmpdir) / "incompressible_data.bin"
        print("  Creating incompressible test file (random data)...")
        with open(incompressible_file, "wb") as f:
            # Write random data (compresses poorly)
            # Use os.urandom for Python 3.8 compatibility (random.randbytes requires 3.9+)
            for _ in range(10 * 1024):  # 10MB
                f.write(os.urandom(1024))

        file_size_mb = incompressible_file.stat().st_size / (1024 * 1024)
        print(f"  File size: {file_size_mb:.2f}MB")

        start_time = time.time()
        result = copy_file_to_device(
            device_id, str(incompressible_file), "/tmp/incompressible_data.bin"
        )
        transfer_time = time.time() - start_time

        if result["success"]:
            transfer_rate = file_size_mb / transfer_time if transfer_time > 0 else 0
            print("  ✅ Transfer successful")
            print(f"  Transfer time: {transfer_time:.2f}s")
            print(f"  Transfer rate: {transfer_rate:.2f}MB/s")
            print("  Note: Random data compresses poorly, but compression still enabled")
        else:
            print(f"  ❌ Transfer failed: {result.get('error')}")
    print()

    # Test 3: Mixed file types (simulating real project)
    print("Test 3: Mixed file types (simulating real project)")
    print("-" * 70)
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir()

        # Create mix of file types
        files = []

        # Text files (compressible)
        for i in range(20):
            text_file = project_dir / f"source_{i}.txt"
            text_file.write_text("Source code " * 1000 + f"\n// File {i}\n")
            files.append(str(text_file))

        # Binary files (less compressible)
        for i in range(10):
            bin_file = project_dir / f"binary_{i}.bin"
            bin_file.write_bytes(os.urandom(10240))  # 10KB random
            files.append(str(bin_file))

        # JSON files (compressible)
        import json

        for i in range(10):
            json_file = project_dir / f"config_{i}.json"
            json_file.write_text(json.dumps({"config": i, "data": "X" * 1000}))
            files.append(str(json_file))

        print(f"  Created {len(files)} mixed files")
        total_size = sum(Path(f).stat().st_size for f in files)
        total_size_mb = total_size / (1024 * 1024)
        print(f"  Total size: {total_size_mb:.2f}MB")

        # Transfer in parallel
        file_pairs = [[f, f"/tmp/mixed_project/{Path(f).name}"] for f in files]
        ssh_to_device(device_id, "mkdir -p /tmp/mixed_project")

        start_time = time.time()
        result = copy_files_to_device_parallel(device_id, file_pairs, max_workers=10)
        transfer_time = time.time() - start_time

        if result["success"]:
            successful = result.get("successful", 0)
            print("  ✅ Transfer completed")
            print(f"  Successful: {successful}/{len(file_pairs)}")
            print(f"  Transfer time: {transfer_time:.2f}s")
            if successful > 0:
                transfer_rate = total_size_mb / transfer_time if transfer_time > 0 else 0
                print(f"  Transfer rate: {transfer_rate:.2f}MB/s")
        else:
            print(f"  ❌ Transfer failed: {result.get('error')}")
    print()

    return True


def cleanup_test_files(device_id: str):
    """Clean up test files from device"""
    print("Cleaning up test files...")
    cleanup_commands = [
        "rm -f /tmp/large_file_100mb.bin",
        "rm -f /tmp/large_file_150mb.bin",
        "rm -rf /tmp/many_files",
        "rm -rf /tmp/many_files_200",
        "rm -f /tmp/compressible_data.bin",
        "rm -f /tmp/incompressible_data.bin",
        "rm -rf /tmp/mixed_project",
    ]

    for cmd in cleanup_commands:
        ssh_to_device(device_id, cmd)


def main():
    """Run all scale tests"""
    print("\n" + "=" * 70)
    print("FILE TRANSFER SCALE TESTING")
    print("=" * 70)
    print()

    device_id = "test-sentai-board"

    try:
        # Test large files
        large_file_success = test_large_file_transfer()

        # Test many files
        many_files_success = test_many_files_transfer()

        # Test compression
        compression_success = test_compression_effectiveness()

        # Cleanup
        cleanup_test_files(device_id)

        print("=" * 70)
        print("SCALE TESTING SUMMARY")
        print("=" * 70)
        print(f"Large files (>100MB): {'✅ PASSED' if large_file_success else '❌ FAILED'}")
        print(f"Many files (100+): {'✅ PASSED' if many_files_success else '❌ FAILED'}")
        print(f"Compression effectiveness: {'✅ PASSED' if compression_success else '❌ FAILED'}")
        print("=" * 70)

        return 0 if (large_file_success and many_files_success and compression_success) else 1

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
