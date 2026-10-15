---
name: safe-unmount
description: >-
  Safely unmount, spin down, and power off external and removable storage devices (mechanical HDDs,
  SSDs, USB flash drives, SD cards, and LUKS-encrypted containers). Diagnoses and resolves 'device is busy'
  (EBUSY) locks using fast /proc inspection without freezing on multi-terabyte drives. Guarantees cache
  flushing, heads parking on spinning disks, and enforces ironclad protection for system partitions.
---

# Safe Unmount & Storage Teardown Engine

This skill provides an automated, hardware-aware workflow to safely unmount, spin down, and disconnect external storage devices on Linux (Arch / Omarchy, Debian, Fedora, Ubuntu) without risking data loss, filesystem corruption, or mechanical drive wear.

The CLI tool is available system-wide as `safe-unmount` (installed at `~/.local/bin/safe-unmount`), backed by a zero-dependency Python 3 engine at `scripts/safe_unmount.py`.

---

## Triggers

Use this skill when the user asks to:
- Unmount a drive or filesystem
- Eject a USB drive, external HDD, or SD card
- Safely remove a disk
- Fix "target is busy" or "device is busy" errors on a drive
- Spin down an external HDD
- Check what's holding a drive open
- Power off an external drive

---

## Primary Workflow: The 5TB HDD (`/run/media/seren/5TB HDD`)

This is the most common target (~80% of removal requests).

### Quick Safe Removal (Agent or Manual)
```bash
safe-unmount eject "/run/media/seren/5TB HDD"
```

### If Blocked: Diagnostic Check
```bash
safe-unmount check "/run/media/seren/5TB HDD"
```

---

## Why Standard `umount` Is Not Enough

1. **Mechanical HDDs need platters spun down**: `umount` leaves the motor spinning. Unplugging while platters are spinning risks head crashes. `safe-unmount` parks heads and spins down platters via SCSI/ATA standby before cutting bus power.

2. **"Device is Busy" (`EBUSY`)**: Linux rejects unmounting if even one process holds a handle. `safe-unmount` uses fast `/proc` inspection (`fuser -m`, `/proc/<pid>/fd/*`, `/proc/<pid>/cwd`) instead of `lsof +D` which freezes on multi-terabyte drives.

3. **Sibling partition protection**: GPT drives with multiple partitions (e.g. `sda1` EFI + `sda2` Data) must have all partitions unmounted before the parent disk can be powered off. `safe-unmount` discovers and unmounts all siblings together.

4. **In-flight write monitoring**: Instead of a fixed timeout on `sync`, monitors `/proc/meminfo` dirty cache in real-time until pending writes reach 0 kB. No premature cutoff.

5. **Active writer protection**: Never kills `rsync`, `cp`, `dd`, or file manager copy operations. Detects write flags (`O_WRONLY`/`O_RDWR`) on open file descriptors and refuses to proceed if data is actively being written.

6. **Terminal self-lock detection**: Detects if the caller's shell working directory is inside the drive and warns them to `cd ~` instead of failing cryptically.

7. **Ironclad system protection**: `/`, `/boot`, `/home`, `/var`, `/usr`, system swap are blacklisted. Immediate fatal abort before any action.

---

## CLI Reference

### List All Storage Devices
```bash
safe-unmount list
safe-unmount list --json
```

### Diagnostic Check (Non-Destructive)
```bash
safe-unmount check "/run/media/seren/5TB HDD"
safe-unmount check /dev/sda2
safe-unmount check "5TB HDD"    # by label
```

### Safe Eject & Spin-Down
```bash
safe-unmount eject "/run/media/seren/5TB HDD"
safe-unmount eject "/run/media/seren/5TB HDD" -q     # quit file managers
safe-unmount eject "/run/media/seren/5TB HDD" -n     # dry run
safe-unmount eject "/run/media/seren/5TB HDD" -k     # kill blockers
safe-unmount eject "/run/media/seren/5TB HDD" --no-power-off  # unmount only
```

### Target Flexibility
Accepts mountpoints (`/run/media/seren/5TB HDD`), subfolder paths (`/run/media/seren/5TB HDD/Movies`), trailing slashes, block devices (`/dev/sda2`, `sda`), volume labels (`"5TB HDD"`), or UUIDs.

---

## CLI Flags

| Flag | Short | Description |
| :--- | :--- | :--- |
| `--dry-run` | `-n` | Preview actions without executing. |
| `--quit-file-managers` | `-q` | Close idle Nautilus/Thunar windows (refuses if they are mid-copy). |
| `--kill` | `-k` | Terminate blocking processes (SIGTERM → SIGKILL). |
| `--force` | `-f` | Proceed even with active writers or terminal locks. |
| `--no-power-off` | | Unmount only, leave drive spinning. |
| `--lazy` | `-l` | Fallback to `umount -l` if standard unmount fails. |
| `--json` | | Machine-readable JSON output. |
| `--verbose` | `-v` | Debug logging. |

---

## Agent Runbook

When a user asks to safely remove, unmount, or eject a drive:

1. **Run the CLI directly**:
   ```bash
   safe-unmount eject "/run/media/seren/5TB HDD"
   ```
   The tool handles everything: safety checks, lock resolution, cache flushing, unmounting, and spin-down.

2. **If it fails with EBUSY / blocking processes**:
   Run `safe-unmount check <target>` to inspect locks.
   - If `ACTIVE_WRITER`: **Do not kill.** Tell the user to wait for the transfer to finish.
   - If `FILE_MANAGER` (idle): Re-run with `-q` flag.
   - If `caller_cwd_in_mount`: Tell the user to `cd ~`.
   - If `SHELL`: Ask the user to close the terminal tab that's sitting in the drive.

3. **Confirm to user** once the tool prints:
   `✔ SAFE REMOVAL COMPLETE! YOU MAY NOW UNPLUG THE CABLE.`
