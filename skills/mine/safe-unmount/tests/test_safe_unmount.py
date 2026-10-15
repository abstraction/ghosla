#!/usr/bin/env python3
"""
Unit and Integration Tests for safe-unmount skill CLI engine.
Hardened with tests for data integrity, sibling partitions, and caller terminal locks.
"""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add scripts directory to module path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts")))
import safe_unmount
from safe_unmount import (
    CacheManager,
    ProcessLock,
    ProcessLockInspector,
    SafetyGuard,
    StorageDevice,
    StorageTopology,
    check_caller_terminal_in_mount,
)


class TestSafetyGuard(unittest.TestCase):
    def test_system_mounts_identified(self):
        """Validates that system mountpoints are protected."""
        self.assertTrue(SafetyGuard.is_system_mount("/"))
        self.assertTrue(SafetyGuard.is_system_mount("/boot"))
        self.assertTrue(SafetyGuard.is_system_mount("/boot/efi"))
        self.assertTrue(SafetyGuard.is_system_mount("/home"))
        self.assertTrue(SafetyGuard.is_system_mount("/var"))
        self.assertTrue(SafetyGuard.is_system_mount("/usr"))
        self.assertTrue(SafetyGuard.is_system_mount("/etc"))

    def test_non_system_mounts_allowed(self):
        """Validates that non-system mountpoints are allowed."""
        self.assertFalse(SafetyGuard.is_system_mount("/run/media/seren/5TB HDD"))
        self.assertFalse(SafetyGuard.is_system_mount("/mnt/BackupDrive"))
        self.assertFalse(SafetyGuard.is_system_mount("/media/usb"))

    def test_validate_system_device_rejected(self):
        """Validates that a device containing root or boot is rejected."""
        root_dev = StorageDevice(
            name="nvme0n1",
            path="/dev/nvme0n1",
            type="disk",
            fstype=None,
            label=None,
            uuid=None,
            size="1T",
            mountpoints=[],
            children=[
                StorageDevice(
                    name="nvme0n1p1",
                    path="/dev/nvme0n1p1",
                    type="part",
                    fstype="vfat",
                    label=None,
                    uuid="1234",
                    size="2G",
                    mountpoints=["/boot"],
                ),
                StorageDevice(
                    name="nvme0n1p2",
                    path="/dev/nvme0n1p2",
                    type="part",
                    fstype="crypto_LUKS",
                    label=None,
                    uuid="5678",
                    size="998G",
                    mountpoints=[],
                    children=[
                        StorageDevice(
                            name="root",
                            path="/dev/mapper/root",
                            type="crypt",
                            fstype="btrfs",
                            label=None,
                            uuid="9999",
                            size="998G",
                            mountpoints=["/"],
                        )
                    ],
                ),
            ],
        )

        is_safe, reason = SafetyGuard.validate_device(root_dev, root_dev)
        self.assertFalse(is_safe)
        self.assertIn("critical system mountpoint", reason)

    def test_validate_removable_drive_allowed(self):
        """Validates that an external drive without system mounts is accepted."""
        usb_dev = StorageDevice(
            name="sdb",
            path="/dev/sdb",
            type="disk",
            fstype=None,
            label=None,
            uuid=None,
            size="5T",
            is_removable=True,
            is_rotational=True,
            transport="usb",
            mountpoints=[],
            children=[
                StorageDevice(
                    name="sdb1",
                    path="/dev/sdb1",
                    type="part",
                    fstype="exfat",
                    label="5TB HDD",
                    uuid="ABCD-1234",
                    size="5T",
                    mountpoints=["/run/media/seren/5TB HDD"],
                )
            ],
        )

        is_safe, reason = SafetyGuard.validate_device(usb_dev, usb_dev)
        self.assertTrue(is_safe)
        self.assertEqual(reason, "Safe")


class TestStorageTopology(unittest.TestCase):
    def setUp(self):
        self.sample_lsblk = {
            "blockdevices": [
                {
                    "name": "sdb",
                    "path": "/dev/sdb",
                    "type": "disk",
                    "size": "4.5T",
                    "rm": True,
                    "rota": "1",
                    "tran": "usb",
                    "model": "Elements 25A3",
                    "vendor": "WD",
                    "mountpoints": [],
                    "children": [
                        {
                            "name": "sdb1",
                            "path": "/dev/sdb1",
                            "type": "part",
                            "size": "200M",
                            "fstype": "vfat",
                            "label": "EFI",
                            "mountpoints": ["/run/media/seren/EFI"],
                        },
                        {
                            "name": "sdb2",
                            "path": "/dev/sdb2",
                            "type": "part",
                            "size": "4.5T",
                            "fstype": "exfat",
                            "label": "5TB HDD",
                            "uuid": "E2F1-8B39",
                            "mountpoints": ["/run/media/seren/5TB HDD"],
                        },
                    ],
                }
            ]
        }

    def test_parse_device_node(self):
        root = StorageTopology._parse_device_node(self.sample_lsblk["blockdevices"][0])
        self.assertEqual(root.name, "sdb")
        self.assertEqual(root.path, "/dev/sdb")
        self.assertTrue(root.is_removable)
        self.assertTrue(root.is_rotational)  # Mechanical HDD
        self.assertEqual(root.transport, "usb")
        self.assertEqual(len(root.children), 2)
        # Sibling mountpoints collected
        self.assertEqual(
            sorted(root.get_all_mountpoints()),
            ["/run/media/seren/5TB HDD", "/run/media/seren/EFI"],
        )

    @patch("safe_unmount.StorageTopology.get_all_devices")
    @patch("subprocess.run")
    def test_resolve_target_with_trailing_slash(self, mock_subproc, mock_get_devs):
        mock_subproc.return_value = MagicMock(returncode=1)
        dev = StorageTopology._parse_device_node(self.sample_lsblk["blockdevices"][0])
        mock_get_devs.return_value = [dev]

        # Trailing slash resolution
        matched, root = StorageTopology.resolve_target("/run/media/seren/5TB HDD/")
        self.assertIsNotNone(matched)
        self.assertEqual(matched.name, "sdb2")
        self.assertEqual(root.name, "sdb")

        # Label resolution
        matched, root = StorageTopology.resolve_target("5TB HDD")
        self.assertIsNotNone(matched)
        self.assertEqual(matched.name, "sdb2")


class TestProcessLockInspector(unittest.TestCase):
    def test_categorize_process(self):
        # File manager
        self.assertEqual(
            ProcessLockInspector.categorize_process("nautilus", "/usr/bin/nautilus --gapplication-service"),
            "FILE_MANAGER",
        )
        # Active writer
        self.assertEqual(
            ProcessLockInspector.categorize_process("rsync", "rsync -avP /source /dest"),
            "ACTIVE_WRITER",
        )

    def test_active_writer_risk(self):
        p_write = ProcessLock(
            pid=1001,
            user="seren",
            command="rsync",
            full_command="rsync -avP /src /run/media/seren/5TB HDD/",
            category="ACTIVE_WRITER",
            access_types=["open_file", "file_write"],
            open_files=["/run/media/seren/5TB HDD/data.tar"],
            is_writing=True,
            risk="HIGH",
        )
        self.assertEqual(p_write.risk, "HIGH")
        self.assertTrue(p_write.is_writing)


class TestCallerTerminalLock(unittest.TestCase):
    def test_caller_terminal_in_mount_detected(self):
        with patch("os.getcwd", return_value="/run/media/seren/5TB HDD/Subfolder"):
            detected = check_caller_terminal_in_mount(["/run/media/seren/5TB HDD"])
            self.assertIsNotNone(detected)
            self.assertIn("5TB HDD", detected)

    def test_caller_terminal_outside_mount(self):
        with patch("os.getcwd", return_value="/home/seren"):
            detected = check_caller_terminal_in_mount(["/run/media/seren/5TB HDD"])
            self.assertIsNone(detected)


class TestCacheManager(unittest.TestCase):
    def test_dirty_memory_reading(self):
        dirty, writeback = CacheManager.get_dirty_memory_kb()
        self.assertIsInstance(dirty, int)
        self.assertIsInstance(writeback, int)
        self.assertGreaterEqual(dirty, 0)
        self.assertGreaterEqual(writeback, 0)


if __name__ == "__main__":
    unittest.main()
