#!/usr/bin/env python3
"""
safe_unmount.py - Production-grade Safe Storage Unmount & Ejection Tool
Part of the Antigravity 'safe-unmount' skill.

Zero external dependencies (pure Python 3.10+ standard library).
Designed for Linux (Arch / Omarchy / Debian / Fedora / Ubuntu).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import pwd
import re
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# Terminal color formatting (disabled if not a TTY or NO_COLOR is set)
USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")

def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text

BOLD = "1"
DIM = "2"
RED = "31"
GREEN = "32"
YELLOW = "33"
BLUE = "34"
MAGENTA = "35"
CYAN = "36"


# ==============================================================================
# DATA MODELS
# ==============================================================================

@dataclass
class ProcessLock:
    pid: int
    user: str
    command: str
    full_command: str
    category: str  # FILE_MANAGER, SHELL, INDEXER, ACTIVE_WRITER, MEDIA_VIEWER, OTHER
    access_types: List[str]  # cwd, open_file, file_write, mmap, root
    open_files: List[str]
    is_writing: bool
    risk: str  # LOW, MEDIUM, HIGH


@dataclass
class StorageDevice:
    name: str
    path: str
    type: str  # disk, part, crypt, loop, lvm, etc.
    fstype: Optional[str]
    label: Optional[str]
    uuid: Optional[str]
    size: str
    mountpoints: List[str] = field(default_factory=list)
    children: List[StorageDevice] = field(default_factory=list)
    is_removable: bool = False
    is_rotational: bool = False  # True = HDD (spinning platters), False = SSD/Flash
    transport: str = ""  # usb, sata, nvme, mmc, etc.
    model: str = ""
    vendor: str = ""

    def get_all_mountpoints(self) -> List[str]:
        mps = [mp for mp in self.mountpoints if mp]
        for child in self.children:
            mps.extend(child.get_all_mountpoints())
        return list(dict.fromkeys(mps))

    def get_all_device_paths(self) -> List[str]:
        paths = [self.path]
        for child in self.children:
            paths.extend(child.get_all_device_paths())
        return list(dict.fromkeys(paths))

    def find_node(self, matcher: Callable[[StorageDevice], bool]) -> Optional[StorageDevice]:
        if matcher(self):
            return self
        for child in self.children:
            found = child.find_node(matcher)
            if found:
                return found
        return None


# ==============================================================================
# SYSTEM SAFETY GUARDRAILS
# ==============================================================================

class SafetyGuard:
    """Strictly prevents accidental unmounting or power-off of critical system storage."""

    SYSTEM_MOUNTS: Set[str] = {
        "/",
        "/boot",
        "/boot/efi",
        "/efi",
        "/home",
        "/var",
        "/var/log",
        "/usr",
        "/etc",
        "/opt",
    }

    @classmethod
    def is_system_mount(cls, path: str) -> bool:
        clean = path.rstrip("/")
        if not clean:
            clean = "/"
        normalized = os.path.realpath(clean)
        return normalized in cls.SYSTEM_MOUNTS

    @classmethod
    def validate_device(cls, device: StorageDevice, root_device: StorageDevice) -> Tuple[bool, str]:
        """Validates that a device or tree does not contain protected system mountpoints."""
        all_mps = root_device.get_all_mountpoints()
        for mp in all_mps:
            if cls.is_system_mount(mp):
                return False, f"Device contains critical system mountpoint '{mp}'."

        # Recursive swap check
        def _has_swap(node: StorageDevice) -> bool:
            if node.fstype == "swap":
                return True
            return any(_has_swap(c) for c in node.children)

        if _has_swap(root_device):
            return False, "Device contains an active system swap partition."

        return True, "Safe"


# ==============================================================================
# HARDWARE & TOPOLOGY DISCOVERY
# ==============================================================================

class StorageTopology:
    @staticmethod
    def _parse_device_node(data: Dict[str, Any]) -> StorageDevice:
        name = data.get("name", "")
        path = data.get("path") or f"/dev/{name}"
        fstype = data.get("fstype")
        label = data.get("label")
        uuid = data.get("uuid")
        size = data.get("size", "")
        dev_type = data.get("type", "")
        model = (data.get("model") or "").strip()
        vendor = (data.get("vendor") or "").strip()
        transport = (data.get("tran") or "").strip().lower()

        # Mountpoints handling
        mps_raw = data.get("mountpoints") or []
        if isinstance(mps_raw, str):
            mountpoints = [mps_raw] if mps_raw else []
        elif isinstance(mps_raw, list):
            mountpoints = [m for m in mps_raw if m]
        else:
            mountpoints = []

        single_mp = data.get("mountpoint")
        if single_mp and single_mp not in mountpoints:
            mountpoints.append(single_mp)

        # Removable flag
        rm_val = data.get("rm")
        is_removable = bool(rm_val is True or rm_val == "1" or rm_val == 1 or data.get("hotplug") in (1, True, "1"))
        if transport == "usb":
            is_removable = True

        # Rotational flag (1 = HDD spinning platters, 0 = SSD/Flash)
        rota_val = data.get("rota")
        is_rotational = bool(rota_val is True or rota_val == "1" or rota_val == 1)

        # Parse children recursively
        children_raw = data.get("children", [])
        children = [StorageTopology._parse_device_node(c) for c in children_raw]

        return StorageDevice(
            name=name,
            path=path,
            type=dev_type,
            fstype=fstype,
            label=label,
            uuid=uuid,
            size=size,
            mountpoints=mountpoints,
            children=children,
            is_removable=is_removable,
            is_rotational=is_rotational,
            transport=transport,
            model=model,
            vendor=vendor,
        )

    @classmethod
    def get_all_devices(cls) -> List[StorageDevice]:
        """Runs `lsblk -J -O` to get a structured JSON tree of all block devices."""
        try:
            res = subprocess.run(
                ["lsblk", "-J", "-O"],
                capture_output=True,
                text=True,
                check=True,
            )
            data = json.loads(res.stdout)
            raw_devices = data.get("blockdevices", [])
            return [cls._parse_device_node(d) for d in raw_devices]
        except Exception:
            try:
                res = subprocess.run(
                    ["lsblk", "-J", "-o", "NAME,PATH,TYPE,FSTYPE,LABEL,UUID,SIZE,MOUNTPOINTS,RM,ROTA,TRAN,MODEL,VENDOR,HOTPLUG"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                data = json.loads(res.stdout)
                return [cls._parse_device_node(d) for d in data.get("blockdevices", [])]
            except Exception as e:
                logging.error(f"Failed to query block devices: {e}")
                return []

    @classmethod
    def resolve_target(cls, target_query: str) -> Tuple[Optional[StorageDevice], Optional[StorageDevice]]:
        """
        Resolves a user-provided target string to:
        (matched_node, root_disk_node)
        
        Handles:
        - Exact mountpoint: /run/media/seren/5TB HDD
        - Trailing slashes: /run/media/seren/5TB HDD/
        - Subdirectory paths: /run/media/seren/5TB HDD/Movies
        - Device nodes: /dev/sda, /dev/sda2, sda, sda2
        - Volume labels: '5TB HDD'
        - UUIDs
        """
        devices = cls.get_all_devices()
        raw_query = target_query.strip().strip("'\"")
        if not raw_query:
            return None, None

        # Normalize path if it exists
        clean_path = raw_query.rstrip("/")
        if not clean_path:
            clean_path = "/"
        real_query = os.path.realpath(clean_path) if os.path.exists(clean_path) else clean_path

        # Step 1: Use findmnt to resolve mountpoint and backing source device
        target_source = None
        target_mount = None
        try:
            res = subprocess.run(["findmnt", "-T", real_query, "-J"], capture_output=True, text=True)
            if res.returncode == 0:
                fm_data = json.loads(res.stdout).get("filesystems", [])
                if fm_data:
                    raw_source = fm_data[0].get("source", "")
                    # Strip btrfs subvolumes like /dev/mapper/root[/@home]
                    target_source = raw_source.split("[")[0].strip()
                    target_mount = fm_data[0].get("target", "").strip()
        except Exception:
            pass

        # Helper to search tree
        def find_in_tree(root: StorageDevice) -> Optional[StorageDevice]:
            # Priority 1: Match findmnt exact target mount or source
            if target_mount and target_mount in root.mountpoints:
                return root
            if target_source and (root.path == target_source or root.name == target_source):
                return root

            # Priority 2: Direct match by path, name, label, uuid, mountpoints
            norm_mps = [m.rstrip("/") for m in root.mountpoints]
            if clean_path in norm_mps or real_query in norm_mps:
                return root
            if root.path == clean_path or root.path == real_query or root.name == clean_path:
                return root
            if root.path == f"/dev/{clean_path}":
                return root
            if root.label and (root.label == clean_path or root.label == raw_query):
                return root
            if root.uuid and root.uuid == clean_path:
                return root

            # Check children
            for child in root.children:
                found = find_in_tree(child)
                if found:
                    return found
            return None

        # Search across all root disks
        for root in devices:
            matched = find_in_tree(root)
            if matched:
                return matched, root

        return None, None


# ==============================================================================
# PROCESS & LOCK INSPECTION
# ==============================================================================

class ProcessLockInspector:
    CATEGORIES = {
        "FILE_MANAGER": {"nautilus", "dolphin", "thunar", "nemo", "pcmanfm"},
        "SHELL": {"bash", "zsh", "fish", "sh", "dash"},
        "INDEXER": {"tracker-miner-fs", "tracker-miner-fs-3", "tracker-miner-f", "baloo_file", "recollindex", "updatedb"},
        "ACTIVE_WRITER": {"rsync", "cp", "dd", "tar", "transmission-da", "qbittorrent", "mysqld", "postgres", "ffmpeg", "wget", "curl", "aria2c", "mv", "install", "bsdtar"},
        "MEDIA_VIEWER": {"mpv", "vlc", "feh", "evince", "eog", "okular", "imv", "gwenview"},
    }

    @classmethod
    def get_command_line(cls, pid: int) -> str:
        try:
            with open(f"/proc/{pid}/cmdline", "r", encoding="utf-8", errors="replace") as f:
                return f.read().replace("\x00", " ").strip()
        except Exception:
            return ""

    @classmethod
    def categorize_process(cls, comm: str, full_cmd: str) -> str:
        # Match on the comm name (max 15 chars from /proc/pid/comm) which is the
        # actual executable basename, not a substring of the full command line.
        # This prevents "cp" from matching "scp", "apcupsd", etc.
        comm_lower = comm.lower().strip()
        for cat, names in cls.CATEGORIES.items():
            if comm_lower in names:
                return cat
        return "OTHER"

    @classmethod
    def get_mount_candidate_pids(cls, mountpoint: str) -> List[int]:
        """Calls fuser -m to get candidate PIDs, or scans /proc if fuser is unavailable."""
        pids: Set[int] = set()
        try:
            res = subprocess.run(["fuser", "-m", mountpoint], capture_output=True, text=True)
            raw = res.stdout + " " + res.stderr
            for tok in raw.split():
                clean = tok.strip(":")
                if clean.isdigit():
                    pids.add(int(clean))
        except FileNotFoundError:
            # Fallback: scan all numeric directories in /proc
            try:
                for entry in os.listdir("/proc"):
                    if entry.isdigit():
                        pids.add(int(entry))
            except Exception:
                pass
        return sorted(pids)

    @classmethod
    def scan_mountpoint(cls, mountpoint: str) -> List[ProcessLock]:
        """
        Inspects process locks on the given mountpoint without directory tree walks.
        Returns detailed ProcessLock objects.
        """
        results: List[ProcessLock] = []
        candidate_pids = cls.get_mount_candidate_pids(mountpoint)
        mp_slash = mountpoint.rstrip("/") + "/"
        my_pid = os.getpid()

        for pid in candidate_pids:
            if pid == my_pid:
                continue

            access_types: Set[str] = set()
            is_writing = False
            open_files: List[str] = []

            # 1. Check working directory (cwd)
            try:
                cwd = os.readlink(f"/proc/{pid}/cwd")
                if cwd == mountpoint or cwd.startswith(mp_slash):
                    access_types.add("cwd")
            except Exception:
                pass

            # 2. Check open file descriptors
            try:
                fd_path = f"/proc/{pid}/fd"
                for entry in os.scandir(fd_path):
                    try:
                        target = os.readlink(entry.path)
                        if target == mountpoint or target.startswith(mp_slash):
                            access_types.add("open_file")
                            if target not in open_files:
                                open_files.append(target)

                            # Inspect fdinfo for write access
                            try:
                                with open(f"/proc/{pid}/fdinfo/{entry.name}", "r") as f_info:
                                    for line in f_info:
                                        if line.startswith("flags:"):
                                            flags = int(line.split()[1], 8)
                                            # O_WRONLY = 01, O_RDWR = 02
                                            if (flags & 3) in (os.O_WRONLY, os.O_RDWR):
                                                is_writing = True
                                                access_types.add("file_write")
                                            break
                            except Exception:
                                pass
                    except Exception:
                        continue
            except Exception:
                pass

            # 3. Check memory mappings (executables, libraries, mmap files)
            if not access_types:
                try:
                    with open(f"/proc/{pid}/maps", "r", encoding="utf-8", errors="replace") as f_maps:
                        for line in f_maps:
                            if mountpoint in line:
                                access_types.add("mmap")
                                break
                except Exception:
                    pass

            # 4. Check root directory (for containers / chroot)
            if not access_types:
                try:
                    root_link = os.readlink(f"/proc/{pid}/root")
                    if root_link == mountpoint or root_link.startswith(mp_slash):
                        access_types.add("root")
                except Exception:
                    pass

            if not access_types:
                continue

            # Resolve process details
            comm = "unknown"
            try:
                with open(f"/proc/{pid}/comm", "r", encoding="utf-8", errors="replace") as f_comm:
                    comm = f_comm.read().strip()
            except Exception:
                pass

            user = "unknown"
            try:
                stat_info = os.stat(f"/proc/{pid}")
                user = pwd.getpwuid(stat_info.st_uid).pw_name
            except Exception:
                pass

            full_cmd = cls.get_command_line(pid)
            category = cls.categorize_process(comm, full_cmd)

            # Determine Risk
            risk = "LOW"
            if is_writing or category == "ACTIVE_WRITER":
                risk = "HIGH"
            elif category in ("INDEXER", "SHELL"):
                risk = "MEDIUM"

            results.append(
                ProcessLock(
                    pid=pid,
                    user=user,
                    command=comm,
                    full_command=full_cmd,
                    category=category,
                    access_types=sorted(list(access_types)),
                    open_files=open_files,
                    is_writing=is_writing,
                    risk=risk,
                )
            )

        return results

    @staticmethod
    def quit_file_managers() -> List[str]:
        """Cleanly asks desktop file managers to quit via DBus or official CLI."""
        closed = []
        try:
            res = subprocess.run(["nautilus", "-q"], capture_output=True, text=True, timeout=5)
            if res.returncode in (0, 255):
                closed.append("nautilus")
        except Exception:
            pass

        try:
            res = subprocess.run(["thunar", "-q"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                closed.append("thunar")
        except Exception:
            pass

        return closed

    @staticmethod
    def terminate_processes(pids: List[int], timeout: float = 3.0) -> Tuple[List[int], List[int]]:
        """Sends SIGTERM, waits up to timeout, then escalates to SIGKILL if still holding."""
        killed: List[int] = []
        failed: List[int] = []

        # 1. SIGTERM
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                killed.append(pid)
            except PermissionError:
                failed.append(pid)

        # 2. Wait
        deadline = time.time() + timeout
        while time.time() < deadline:
            remaining = [p for p in pids if is_pid_alive(p)]
            if not remaining:
                break
            time.sleep(0.2)

        # 3. SIGKILL escalation
        for pid in pids:
            if is_pid_alive(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                    killed.append(pid)
                except Exception:
                    failed.append(pid)
            else:
                if pid not in killed:
                    killed.append(pid)

        return killed, failed


def is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def check_caller_terminal_in_mount(mountpoints: List[str]) -> Optional[str]:
    """Detects if the calling terminal or parent process has its CWD inside the mountpoint."""
    check_dirs = []
    try:
        check_dirs.append(os.path.realpath(os.getcwd()))
    except Exception:
        pass

    try:
        ppid = os.getppid()
        parent_cwd = os.readlink(f"/proc/{ppid}/cwd")
        check_dirs.append(os.path.realpath(parent_cwd))
    except Exception:
        pass

    for d in check_dirs:
        for mp in mountpoints:
            mp_real = os.path.realpath(mp.rstrip("/"))
            if d == mp_real or d.startswith(mp_real + "/"):
                return d
    return None


# ==============================================================================
# CACHE AND BUFFER MANAGEMENT (Live progress, no premature timeout)
# ==============================================================================

class CacheManager:
    @staticmethod
    def get_dirty_memory_kb() -> Tuple[int, int]:
        """Returns (Dirty_kB, Writeback_kB) from /proc/meminfo."""
        dirty, writeback = 0, 0
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("Dirty:"):
                        dirty = int(line.split()[1])
                    elif line.startswith("Writeback:"):
                        writeback = int(line.split()[1])
        except Exception:
            pass
        return dirty, writeback

    @classmethod
    def sync_target(cls, mountpoints: List[str]):
        """
        Flushes dirty page caches to filesystem and invokes sync.
        Monitors in-flight writes without cutting off sync prematurely.
        """
        # 1. Per-mount syncfs
        for mp in mountpoints:
            try:
                subprocess.run(["sync", "-f", mp], check=False)
            except Exception:
                pass

        # 2. Check pending dirty memory
        dirty_kb, writeback_kb = cls.get_dirty_memory_kb()
        total_pending = dirty_kb + writeback_kb

        if total_pending > 5120:  # > 5 MB
            print(_c(f"  Flushing {total_pending / 1024:.1f} MB of dirty write cache to disk... DO NOT UNPLUG!", YELLOW))

        # 3. Launch global sync with live monitoring
        sync_proc = subprocess.Popen(["sync"])
        last_report = 0.0

        while sync_proc.poll() is None:
            now = time.time()
            if now - last_report >= 2.0:
                d_kb, wb_kb = cls.get_dirty_memory_kb()
                remaining = d_kb + wb_kb
                if remaining > 1024:
                    print(_c(f"  ↳ In-flight writes: {remaining / 1024:.1f} MB remaining...", DIM))
                last_report = now
            time.sleep(0.3)

        # 4. Wait for writeback to settle
        settle_start = time.time()
        while time.time() - settle_start < 5.0:
            _, wb_kb = cls.get_dirty_memory_kb()
            if wb_kb == 0:
                break
            time.sleep(0.2)


# ==============================================================================
# CLI PRESENTATION & COMMANDS
# ==============================================================================

def format_device_tree(node: StorageDevice, indent: int = 1) -> List[str]:
    """Recursively formats child partitions, LUKS containers, and sub-mounts."""
    lines = []
    prefix = "  " * indent + "└─ "
    for child in node.children:
        label_str = f" [{child.label}]" if child.label else ""
        fs_str = f" ({child.fstype})" if child.fstype else ""
        mps = ", ".join(child.mountpoints) if child.mountpoints else _c("Unmounted", DIM)
        lines.append(f"{prefix}{_c(child.path, CYAN)}{label_str}{fs_str}: {mps}")
        lines.extend(format_device_tree(child, indent + 1))
    return lines


def cmd_list(args: argparse.Namespace):
    devices = StorageTopology.get_all_devices()

    output_list = []
    for root in devices:
        is_sys, _ = SafetyGuard.validate_device(root, root)
        is_system = not is_sys

        all_mps = root.get_all_mountpoints()
        info = {
            "name": root.name,
            "path": root.path,
            "type": root.type,
            "model": root.model,
            "vendor": root.vendor,
            "size": root.size,
            "transport": root.transport or ("usb" if root.is_removable else "internal"),
            "rotational": root.is_rotational,
            "media_type": "HDD (Mechanical)" if root.is_rotational else "SSD/Flash",
            "is_removable": root.is_removable,
            "is_system": is_system,
            "mountpoints": all_mps,
            "tree_lines": format_device_tree(root, 1),
        }
        output_list.append(info)

    if args.json:
        clean_json = [{k: v for k, v in item.items() if k != "tree_lines"} for item in output_list]
        print(json.dumps(clean_json, indent=2))
        return

    print(_c("AVAILABLE STORAGE DEVICES:", BOLD))
    print("=" * 78)

    for item in output_list:
        media_tag = _c(f"[{item['media_type']}]", YELLOW if item["rotational"] else CYAN)
        tran_tag = _c(f"({item['transport'].upper()})", DIM)

        status_badges = []
        if item["is_system"]:
            status_badges.append(_c("SYSTEM/PROTECTED", RED))
        if item["is_removable"]:
            status_badges.append(_c("REMOVABLE", GREEN))
        badges_str = " ".join(status_badges)

        dev_title = f"{_c(item['path'], BOLD)} ({item['size']}) {media_tag} {tran_tag} {badges_str}".strip()
        print(f"\n{dev_title}")
        if item["model"] or item["vendor"]:
            print(f"  Model: {item['vendor']} {item['model']}".strip())

        if not item["tree_lines"]:
            mps = ", ".join(item["mountpoints"]) if item["mountpoints"] else _c("Not mounted", DIM)
            print(f"  Mounts: {mps}")
        else:
            for line in item["tree_lines"]:
                print(line)

    print("\n" + "=" * 78)
    print(_c("Tip: Run 'safe-unmount check <device_or_path>' to inspect locks and dirty cache.", DIM))


def cmd_check(args: argparse.Namespace):
    target_query = args.target
    matched, root = StorageTopology.resolve_target(target_query)

    if not root or not matched:
        print(_c(f"Error: Target '{target_query}' could not be resolved to any device or mountpoint.", RED), file=sys.stderr)
        sys.exit(1)

    is_safe, reason = SafetyGuard.validate_device(matched, root)
    dirty_kb, writeback_kb = CacheManager.get_dirty_memory_kb()

    # Collect mountpoints: check if sibling partitions exist on parent disk
    parent_mps = root.get_all_mountpoints()
    target_mps = matched.get_all_mountpoints()

    # Scan blocking processes across all partitions of the parent drive
    blocking_procs: Dict[int, ProcessLock] = {}
    for mp in parent_mps:
        for p in ProcessLockInspector.scan_mountpoint(mp):
            blocking_procs[p.pid] = p

    caller_cwd = check_caller_terminal_in_mount(parent_mps)

    report = {
        "target": target_query,
        "resolved_target": matched.path,
        "root_disk": root.path,
        "is_rotational": root.is_rotational,
        "media_type": "HDD (Mechanical)" if root.is_rotational else "SSD/Flash",
        "transport": root.transport,
        "is_system_protected": not is_safe,
        "safety_reason": reason,
        "dirty_cache_kb": dirty_kb,
        "writeback_cache_kb": writeback_kb,
        "target_mountpoints": target_mps,
        "parent_disk_mountpoints": parent_mps,
        "caller_cwd_in_mount": caller_cwd,
        "blocking_processes": [asdict(p) for p in blocking_procs.values()],
    }

    if args.json:
        print(json.dumps(report, indent=2))
        return

    print(_c("\nDEVICE DIAGNOSTIC REPORT", BOLD))
    print("=" * 65)
    print(f"  Target:            {_c(matched.path, BOLD)}")
    print(f"  Parent Disk:       {root.path}")
    print(f"  Media Type:        {'Mechanical HDD (Spin-down required)' if root.is_rotational else 'Solid State (SSD/Flash)'}")
    print(f"  Transport:         {root.transport or 'Unknown'}")

    if not is_safe:
        print(f"  System Status:     {_c('PROTECTED SYSTEM DEVICE - ' + reason, RED)}")
    else:
        print(f"  System Status:     {_c('Safe for removal (Not a system device)', GREEN)}")

    print(f"  Dirty Cache:       {dirty_kb} kB (Writeback: {writeback_kb} kB)")
    print(f"  Target Mounts:     {', '.join(target_mps) if target_mps else _c('None', DIM)}")
    if len(parent_mps) > len(target_mps):
        print(f"  All Disk Mounts:   {', '.join(parent_mps)}")

    if caller_cwd:
        print(_c(f"\n  [!] CALLER WARNING: Your current terminal is inside the drive!", YELLOW))
        print(_c(f"      CWD: {caller_cwd}", DIM))
        print(_c("      Tip: Run 'cd ~' before unmounting to release this shell lock.", YELLOW))

    print("\n" + _c("BLOCKING PROCESSES / LOCKS:", BOLD))
    print("-" * 65)
    if not blocking_procs:
        print(_c("  ✓ No blocking processes detected. Ready for clean unmount.", GREEN))
    else:
        print(_c(f"  ⚠ {len(blocking_procs)} processes holding locks on this device:", YELLOW))
        header = f"  {'PID':<7} | {'USER':<10} | {'COMMAND':<15} | {'CATEGORY':<14} | {'RISK':<6} | {'ACCESS'}"
        print(header)
        print("  " + "-" * (len(header) - 2))
        for p in blocking_procs.values():
            risk_color = RED if p.risk == "HIGH" else (YELLOW if p.risk == "MEDIUM" else GREEN)
            risk_str = _c(p.risk, risk_color)
            acc_str = ",".join(p.access_types)
            print(f"  {p.pid:<7} | {p.user:<10} | {p.command[:15]:<15} | {p.category:<14} | {risk_str:<15} | {acc_str}")
            if p.is_writing:
                print(_c(f"    ↳ WARNING: Process PID {p.pid} is actively writing to disk!", RED))
            if p.full_command and len(p.full_command) > 20:
                print(_c(f"    ↳ CMD: {p.full_command[:80]}...", DIM))

    print("=" * 65 + "\n")


def cmd_eject(args: argparse.Namespace):
    target_query = args.target
    matched, root = StorageTopology.resolve_target(target_query)

    if not root or not matched:
        print(_c(f"Error: Target '{target_query}' could not be resolved to any device or mountpoint.", RED), file=sys.stderr)
        sys.exit(1)

    # 1. Safety Guardrail
    is_safe, reason = SafetyGuard.validate_device(matched, root)
    if not is_safe:
        print(_c(f"\n[FATAL] Safety guardrail triggered: {reason}", RED), file=sys.stderr)
        print("Aborting to prevent system corruption.\n", file=sys.stderr)
        sys.exit(1)

    # Determine all mountpoints that need to be unmounted
    # If powering off the parent disk, ALL mounted partitions on that disk must be unmounted!
    if args.no_power_off:
        mps_to_unmount = matched.get_all_mountpoints()
    else:
        mps_to_unmount = root.get_all_mountpoints()

    print(_c(f"\n=== SAFE REMOVAL PIPELINE FOR {root.path} ===", BOLD))
    print(f"Target: {matched.path} ({'Whole Disk' if matched == root else 'Partition'})")
    print(f"Drive Type: {'Mechanical HDD (Spins down platters)' if root.is_rotational else 'SSD/Flash'}")
    if mps_to_unmount:
        print(f"Mountpoint(s) to unmount: {', '.join(mps_to_unmount)}")

    # Check caller terminal working directory
    caller_cwd = check_caller_terminal_in_mount(mps_to_unmount)
    if caller_cwd:
        print(_c(f"\n[!] TERMINAL LOCK DETECTED:", YELLOW + ";" + BOLD))
        print(_c(f"    Your active terminal shell is currently inside the drive!", YELLOW))
        print(_c(f"    Location: {caller_cwd}", DIM))
        print(_c("    Please 'cd ~' in that terminal to release the lock, then re-run.", YELLOW))
        if not args.force:
            sys.exit(1)

    # 2. Check for locks
    blocking_procs: Dict[int, ProcessLock] = {}
    for mp in mps_to_unmount:
        for p in ProcessLockInspector.scan_mountpoint(mp):
            blocking_procs[p.pid] = p

    # Check for active writers in file managers (Nautilus mid-copy protection)
    fm_writers = [
        p for p in blocking_procs.values()
        if p.category == "FILE_MANAGER" and (p.is_writing or "file_write" in p.access_types)
    ]
    if fm_writers:
        print(_c("\n[DANGER] File manager (Nautilus/Dolphin) is currently COPYING or WRITING files to this drive!", RED + ";" + BOLD))
        print(_c("Aborting safe removal to prevent file corruption. Please wait for the file transfer to complete!", RED))
        sys.exit(1)

    # Handle idle file managers viewing the mount (ONLY with explicit --quit-file-managers)
    if blocking_procs and any(p.category == "FILE_MANAGER" for p in blocking_procs.values()):
        if args.quit_file_managers:
            print(_c("\nClosing idle file manager windows viewing this mount...", CYAN))
            if not args.dry_run:
                ProcessLockInspector.quit_file_managers()
                time.sleep(0.5)
                # Rescan locks
                blocking_procs.clear()
                for mp in mps_to_unmount:
                    for p in ProcessLockInspector.scan_mountpoint(mp):
                        blocking_procs[p.pid] = p

    # If blocking processes remain
    if blocking_procs:
        print(_c(f"\n[!] Target is busy ({len(blocking_procs)} processes holding locks):", YELLOW))
        for p in blocking_procs.values():
            print(f"  - PID {p.pid} ({p.user}): {p.command} [{p.category}] - Access: {','.join(p.access_types)}")

        has_active_writer = any(p.is_writing or p.risk == "HIGH" for p in blocking_procs.values())
        if has_active_writer:
            print(_c("\n[DANGER] One or more processes are ACTIVELY WRITING to the drive!", RED + ";" + BOLD))
            if not args.force:
                print(_c("Aborting to prevent data corruption. Wait for file write to finish, or pass --force.", RED))
                sys.exit(1)

        if args.kill:
            # NEVER kill active writers — only kill non-writing processes.
            # Killing a writer (rsync, cp, dd) mid-flight truncates files.
            writers = {p.pid for p in blocking_procs.values() if p.is_writing or p.risk == "HIGH"}
            safe_to_kill = [pid for pid in blocking_procs if pid not in writers]
            if writers:
                print(_c(f"\n  Skipping {len(writers)} active writer(s) to prevent data corruption: {sorted(writers)}", YELLOW))
            if safe_to_kill:
                print(_c(f"\n  Terminating {len(safe_to_kill)} non-writing blocking processes...", YELLOW))
                if not args.dry_run:
                    killed, failed = ProcessLockInspector.terminate_processes(safe_to_kill)
                    print(f"  Terminated PIDs: {killed}")
                    if failed:
                        print(_c(f"  Could not terminate PIDs (insufficient permissions?): {failed}", RED))
            if writers:
                print(_c("\n  Active writers are still holding the drive. Cannot proceed.", RED))
                print(_c("  Wait for writes to finish, then re-run.", RED))
                sys.exit(1)
        else:
            print(_c("\nCannot unmount busy filesystem.", RED))
            print("Options to resolve:")
            print("  1. Close open files, media players, or terminal windows viewing this drive.")
            print("  2. Re-run with --quit-file-managers to cleanly close GUI file managers.")
            print("  3. Re-run with --kill to terminate non-writing blocking processes.")
            sys.exit(1)

    # 3. Flush Dirty Buffers (Live monitor, no premature timeout!)
    print(_c("\n[1/4] Flushing dirty memory cache & syncing filesystem...", CYAN))
    if args.dry_run:
        print(_c("  [DRY-RUN] Would sync dirty buffers to disk.", DIM))
    else:
        CacheManager.sync_target(mps_to_unmount)
        print(_c("  ✓ Filesystem buffers synchronized.", GREEN))

    # 4. Unmount filesystems (deepest first)
    print(_c("\n[2/4] Unmounting partition(s)...", CYAN))
    sorted_mps = sorted(mps_to_unmount, key=len, reverse=True)
    for mp in sorted_mps:
        if args.dry_run:
            print(_c(f"  [DRY-RUN] Would unmount {mp}", DIM))
            continue

        # Check if mount is still active (it may have disappeared between scan and now)
        still_mounted = subprocess.run(["findmnt", "-n", mp], capture_output=True, text=True)
        if still_mounted.returncode != 0:
            print(_c(f"  ✓ {mp} is already unmounted.", GREEN))
            continue

        print(f"  Unmounting {mp}...")
        unmounted = False

        # Try udisksctl unmount
        dev_res = subprocess.run(["findmnt", "-n", "-o", "SOURCE", mp], capture_output=True, text=True)
        src_dev = dev_res.stdout.strip().split("[")[0]
        if src_dev and os.path.exists(src_dev):
            res = subprocess.run(["udisksctl", "unmount", "-b", src_dev], capture_output=True, text=True)
            if res.returncode == 0:
                print(_c(f"  ✓ Unmounted {mp} via udisksctl.", GREEN))
                unmounted = True

        # Fallback to standard umount
        if not unmounted:
            res = subprocess.run(["umount", mp], capture_output=True, text=True)
            if res.returncode == 0:
                print(_c(f"  ✓ Unmounted {mp} via umount.", GREEN))
                unmounted = True
            else:
                if args.lazy:
                    # Warn about exFAT dirty volume bit
                    if matched.fstype and matched.fstype.lower() in ("exfat", "vfat", "fat32"):
                        print(_c(f"  [!] WARNING: Lazy unmount on {matched.fstype} filesystem may leave the", YELLOW))
                        print(_c(f"      volume dirty bit set. Windows/macOS will prompt for disk repair.", YELLOW))
                    print(_c(f"  Standard unmount failed, attempting lazy unmount (umount -l)...", YELLOW))
                    l_res = subprocess.run(["umount", "-l", mp], capture_output=True, text=True)
                    if l_res.returncode == 0:
                        print(_c(f"  ✓ Lazy unmounted {mp}.", YELLOW))
                        unmounted = True
                    else:
                        print(_c(f"  ✗ Failed to unmount {mp}: {l_res.stderr.strip()}", RED))
                        sys.exit(1)
                else:
                    print(_c(f"  ✗ Failed to unmount {mp}: {res.stderr.strip()}", RED))
                    sys.exit(1)

    # 5. Crypto / LUKS Teardown
    print(_c("\n[3/4] Checking mapped crypto devices...", CYAN))
    crypto_nodes: List[StorageDevice] = []
    def find_crypt(node: StorageDevice):
        if node.type == "crypt":
            crypto_nodes.append(node)
        for c in node.children:
            find_crypt(c)
    find_crypt(root)

    for cnode in crypto_nodes:
        if args.dry_run:
            print(_c(f"  [DRY-RUN] Would lock crypto device {cnode.path}", DIM))
        else:
            print(f"  Locking encrypted volume {cnode.path}...")
            subprocess.run(["udisksctl", "lock", "-b", cnode.path], check=False)

    # 6. Spin-down & Power Off Parent Disk
    if args.no_power_off:
        print(_c("\n[4/4] Skipping power-off (--no-power-off set). Drive partitions are unmounted.", GREEN))
    else:
        print(_c(f"\n[4/4] Powering off and spinning down {root.path}...", CYAN))
        if args.dry_run:
            print(_c(f"  [DRY-RUN] Would power off {root.path} via udisksctl power-off.", DIM))
        else:
            powered_off = False
            # Golden standard: udisksctl power-off -b /dev/sdX
            res = subprocess.run(["udisksctl", "power-off", "-b", root.path], capture_output=True, text=True)
            if res.returncode == 0:
                print(_c(f"  ✓ Device {root.path} powered off cleanly.", GREEN))
                powered_off = True
            else:
                logging.debug(f"udisksctl power-off failed: {res.stderr.strip()}")
                if root.is_rotational:
                    print(_c("  Flushing disk internal cache & putting in standby...", YELLOW))
                    subprocess.run(["hdparm", "-F", root.path], capture_output=True)
                    subprocess.run(["hdparm", "-y", root.path], capture_output=True)
                res_ej = subprocess.run(["eject", root.path], capture_output=True)
                if res_ej.returncode == 0:
                    print(_c(f"  ✓ Device {root.path} ejected.", GREEN))
                    powered_off = True
                else:
                    print(_c(f"  ✗ Failed to power off or eject {root.path}.", RED))
                    print(_c("  [DANGER] Do NOT unplug the drive yet! The platters may still be spinning.", RED + ";" + BOLD))
                    sys.exit(1)

            # Verify device detachment
            time.sleep(0.5)
            if not os.path.exists(root.path):
                print(_c(f"  ✓ Confirmed: {root.path} node removed from system bus.", GREEN))

    print(_c("\n=======================================================", BOLD))
    print(_c("✔ SAFE REMOVAL COMPLETE! YOU MAY NOW UNPLUG THE CABLE.", GREEN + ";" + BOLD))
    if root.is_rotational:
        print(_c("Note: Disk platters are spun down and heads are parked.", DIM))
        print(_c("If the enclosure LED stays dimly on, it is normal USB standby power from the port.", DIM))
    print(_c("=======================================================\n", BOLD))


# ==============================================================================
# MAIN PARSER ENTRYPOINT
# ==============================================================================

def main():
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose debug logging")
    common_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON for agents/scripts")

    parser = argparse.ArgumentParser(
        prog="safe_unmount.py",
        description="Safe unmounting, spin-down, and removal of external storage devices.",
        parents=[common_parser],
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser(
        "list",
        parents=[common_parser],
        help="List all storage devices, media types (HDD/SSD), and mounts",
    )

    # check
    check_p = subparsers.add_parser(
        "check",
        parents=[common_parser],
        help="Non-destructive diagnostics (inspect locks, dirty cache, topology)",
    )
    check_p.add_argument("target", help="Device path (/dev/sda2), mountpoint (/run/media/...), or label")

    # eject / unmount
    eject_p = subparsers.add_parser(
        "eject",
        aliases=["unmount"],
        parents=[common_parser],
        help="Safely sync, unmount, and power off/spin down",
    )
    eject_p.add_argument("target", help="Device path (/dev/sda), partition (/dev/sda2), mountpoint, or label")
    eject_p.add_argument("--dry-run", "-n", action="store_true", help="Simulate actions without executing them")
    eject_p.add_argument("--quit-file-managers", "-q", action="store_true", help="Automatically close GUI file managers holding locks")
    eject_p.add_argument("--kill", "-k", action="store_true", help="Terminate processes blocking the unmount")
    eject_p.add_argument("--force", "-f", action="store_true", help="Proceed even if active writers are detected")
    eject_p.add_argument("--no-power-off", action="store_true", help="Unmount partitions but leave drive powered on")
    eject_p.add_argument("--lazy", "-l", action="store_true", help="Use lazy unmount (umount -l) if standard fails")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if args.command == "list":
        cmd_list(args)
    elif args.command == "check":
        cmd_check(args)
    elif args.command in ("eject", "unmount"):
        cmd_eject(args)


if __name__ == "__main__":
    main()
