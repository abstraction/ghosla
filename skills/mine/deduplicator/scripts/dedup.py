#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pillow",
# ]
# ///
"""Intelligent Content and Binary Deduplication Engine.

Performs multi-stage deduplication:
1. Fast cryptographic binary matching (size bucketing, partial hash, SHA-256).
2. Intelligent semantic matching:
   - Normalized PDF text comparison (handling transient timestamps and print metadata).
   - Perceptual image hashing (dHash and dimension matching via Pillow).
   - Markdown and text document comparison (stripping transient export headers).
   - Incomplete and corrupt archive download detection.

Safe by design:
- Dry-run by default.
- Non-destructive: moves files to a designated recycle bin directory.
- Atomic JSON transaction manifests with complete one-command undo support.

Usage:
  # 1. Simulation (Dry-Run)
  uv run ~/.gemini/config/skills/deduplicator/scripts/dedup.py /path/to/target

  # 2. Live Execution
  uv run ~/.gemini/config/skills/deduplicator/scripts/dedup.py /path/to/target --execute

  # 3. Pure Binary Mode (Skip Semantic Normalization)
  uv run ~/.gemini/config/skills/deduplicator/scripts/dedup.py /path/to/target --execute --no-semantic

  # 4. Undo / Rollback
  uv run ~/.gemini/config/skills/deduplicator/scripts/dedup.py --undo /path/to/target/_recycle_bin/.dedup_manifest_YYYYMMDD_HHMMSS.json
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from collections import defaultdict
from collections.abc import Generator, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Try importing Pillow for perceptual image hashing
try:
    from PIL import Image

    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

logger = logging.getLogger("dedup")


# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FileMeta:
    """Metadata representation for candidate files."""

    path: Path
    size: int
    mtime: float


@dataclass
class DuplicateGroup:
    """Represents a set of duplicate files with a selected canonical keeper."""

    keeper: Path
    duplicates: list[Path]
    reason: str
    size: int
    content_hash: str | None = None


@dataclass
class RunSummary:
    """Execution statistics and results."""

    total_scanned: int = 0
    total_bytes_scanned: int = 0
    binary_groups: int = 0
    binary_duplicates: int = 0
    binary_bytes: int = 0
    semantic_groups: int = 0
    semantic_duplicates: int = 0
    semantic_bytes: int = 0
    moved_files: int = 0
    moved_bytes: int = 0
    empty_dirs_removed: int = 0
    manifest_path: Path | None = None


# -----------------------------------------------------------------------------
# Canonical Keeper Selection
# -----------------------------------------------------------------------------

COPY_PATTERNS = [
    re.compile(r"[\s_.-]*\(\d+\)[\s_.-]*", re.IGNORECASE),
    re.compile(r"[\s_.-]+copy(?:[\s_.-]+\d+)?", re.IGNORECASE),
    re.compile(r"\bcopy\s+of\b", re.IGNORECASE),
    re.compile(r"[\s_.-]+backup[\s_.-]*", re.IGNORECASE),
    re.compile(r"[\s_.-]+dup(?:licate)?[\s_.-]*", re.IGNORECASE),
]

DOUBLE_EXT_PATTERN = re.compile(
    r"\.(?:jpg|jpeg|png|webp|pdf|docx|xlsx|csv|txt|md)\.(?:jpg|jpeg|png|webp|pdf|docx|xlsx|csv|txt|md)$",
    re.IGNORECASE,
)

STAGING_DIR_NAMES = {
    "downloads",
    "download",
    "inbox",
    "temp",
    "tmp",
    "incoming",
    "intake",
    "01 intake & inbox",
    "unsorted",
}


def score_keeper_candidate(path: Path) -> tuple[int, int, int, float, str]:
    """Score a candidate path to determine the best canonical keeper.

    Higher scores indicate a better canonical file.
    Criteria:
    1. Penalty for copy markers in filename like '(1)', ' - Copy'.
    2. Penalty for double extensions like '.jpg.jpg'.
    3. Penalty for residing in staging/inbox/downloads directories.
    4. Bonus for directory depth (indicating intentional organization).
    5. Preference for older modification time (original creation).
    6. Deterministic tie-breaker based on path length and string.
    """
    name = path.name
    penalty = 0

    # 1. Copy pattern penalty
    for pat in COPY_PATTERNS:
        if pat.search(name):
            penalty -= 100
            break

    # 2. Double extension penalty
    if DOUBLE_EXT_PATTERN.search(name):
        penalty -= 80

    # 3. Staging directory penalty
    path_parts_lower = {part.lower() for part in path.parts[:-1]}
    if path_parts_lower.intersection(STAGING_DIR_NAMES):
        penalty -= 40

    # 4. Organization depth bonus (capped at 10)
    depth = min(len(path.parts), 10)
    depth_bonus = depth * 5

    # 5. File modification time (older is preferred)
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0.0

    # Primary score combines penalties and depth bonus
    primary_score = penalty + depth_bonus

    # Return tuple for sorting (higher is better)
    # Note: -mtime means older files (smaller timestamp) yield higher sort value
    return (primary_score, -len(name), depth, -mtime, str(path))


def pick_canonical_keeper(candidates: Iterable[Path]) -> tuple[Path, list[Path]]:
    """Select the best keeper file from a list of candidate duplicates."""
    sorted_candidates = sorted(candidates, key=score_keeper_candidate, reverse=True)
    keeper = sorted_candidates[0]
    duplicates = sorted_candidates[1:]
    return keeper, duplicates


# -----------------------------------------------------------------------------
# File Hashing & Binary Matching
# -----------------------------------------------------------------------------


def compute_partial_hash(path: Path, chunk_size: int = 65536) -> str:
    """Compute a fast partial hash of head and tail blocks."""
    hasher = hashlib.sha256()
    size = path.stat().st_size
    with open(path, "rb") as f:
        # Read head
        head = f.read(chunk_size)
        hasher.update(head)
        # Read tail if file is larger than 2 chunks
        if size > chunk_size * 2:
            f.seek(size - chunk_size)
            tail = f.read(chunk_size)
            hasher.update(tail)
    return hasher.hexdigest()


def compute_full_sha256(path: Path, block_size: int = 1048576) -> str:
    """Compute complete SHA-256 hash using streaming blocks."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(block_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


# -----------------------------------------------------------------------------
# Perceptual Image Hashing (dHash)
# -----------------------------------------------------------------------------


def compute_image_dhash(path: Path, hash_size: int = 8) -> tuple[tuple[int, int], str] | None:
    """Compute image dimensions and difference hash (dHash).

    Returns ((width, height), dhash_hex_str) or None if unreadable.
    """
    if not HAS_PILLOW:
        return None

    try:
        with Image.open(path) as img:
            dims = (img.width, img.height)
            # Resize to (hash_size + 1, hash_size) grayscale
            resized = img.convert("L").resize(
                (hash_size + 1, hash_size),
                Image.Resampling.LANCZOS,
            )
            def _pixel_val(px: Any) -> int:
                if isinstance(px, (int, float)):
                    return int(px)
                if isinstance(px, (tuple, list)) and px:
                    return int(px[0])
                return 0

            pixels = resized.load()
            if pixels is None:
                return None
            diff: list[bool] = []
            for row in range(hash_size):
                for col in range(hash_size):
                    val1 = _pixel_val(pixels[col, row])
                    val2 = _pixel_val(pixels[col + 1, row])
                    diff.append(val1 > val2)

            # Convert boolean array to hex string
            val = 0
            for bit in diff:
                val = (val << 1) | int(bit)
            hash_str = f"{val:016x}"
            return dims, hash_str
    except (OSError, ValueError) as exc:
        logger.debug("Failed to compute image hash for %s: %s", path, exc)
        return None


def hamming_distance(h1: str, h2: str) -> int:
    """Calculate the Hamming distance between two hex hash strings."""
    v1 = int(h1, 16)
    v2 = int(h2, 16)
    xor = v1 ^ v2
    return xor.bit_count()


# -----------------------------------------------------------------------------
# Text & Document Normalization
# -----------------------------------------------------------------------------

TRANSIENT_HEADER_PATTERNS = [
    re.compile(r"^#?\s*exported\s+(?:at|on)\s*:?.*$", re.IGNORECASE),
    re.compile(r"^#?\s*export\s+date\s*:?.*$", re.IGNORECASE),
    re.compile(r"^#?\s*generated\s+(?:at|on)\s*:?.*$", re.IGNORECASE),
    re.compile(r"^#?\s*print(?:ed)?\s+(?:at|on|date)\s*:?.*$", re.IGNORECASE),
    re.compile(r"^#?\s*downloaded\s+(?:at|on)\s*:?.*$", re.IGNORECASE),
    re.compile(r"^(?:date|updated|created)\s*:\s*[\"']?\d{4}-\d{2}-\d{2}.*[\"']?$", re.IGNORECASE),
]


def normalize_markdown_or_text(path: Path) -> str | None:
    """Read a markdown or text file and strip transient export headers."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError as exc:
        logger.debug("Failed to read text file %s: %s", path, exc)
        return None

    cleaned_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        is_transient = False
        for pat in TRANSIENT_HEADER_PATTERNS:
            if pat.match(stripped):
                is_transient = True
                break
        if not is_transient:
            cleaned_lines.append(stripped)

    if not cleaned_lines:
        return None

    return "\n".join(cleaned_lines)


def extract_pdf_normalized_text(path: Path) -> str | None:
    """Extract and normalize text from a PDF file using pdftotext CLI."""
    if shutil.which("pdftotext") is None:
        return None

    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            capture_output=True,
            text=True,
            timeout=30.0,
            check=False,
        )
        if result.returncode != 0:
            return None
        raw_text = result.stdout
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("pdftotext failed for %s: %s", path, exc)
        return None

    lines = raw_text.splitlines()
    cleaned_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        is_transient = False
        for pat in TRANSIENT_HEADER_PATTERNS:
            if pat.search(stripped):
                is_transient = True
                break
        if not is_transient:
            cleaned_lines.append(stripped)

    if not cleaned_lines:
        return None

    return "\n".join(cleaned_lines)


def test_archive_validity(path: Path) -> tuple[bool, str | None]:
    """Test if a zip archive is complete and uncorrupted.

    Returns (is_valid, error_message).
    """
    if not path.name.lower().endswith(".zip"):
        return True, None

    try:
        with zipfile.ZipFile(path, "r") as zf:
            bad_file = zf.testzip()
            if bad_file:
                return False, f"Corrupted file inside archive: {bad_file}"
        return True, None
    except zipfile.BadZipFile as exc:
        return False, f"Bad zip file: {exc}"
    except (OSError, zipfile.LargeZipFile) as exc:
        return False, str(exc)


# -----------------------------------------------------------------------------
# Name Normalization for Candidate Clustering
# -----------------------------------------------------------------------------


def get_normalized_stem(path: Path) -> str:
    """Normalize a filename stem to cluster potential copies together.

    Removes '(1)', ' - Copy', duplicate extensions, and whitespace.
    """
    stem = path.stem.lower()
    # Strip double extension if present in stem (e.g. 'foo.jpg' from 'foo.jpg.jpg')
    for ext in [".jpg", ".jpeg", ".png", ".webp", ".pdf", ".txt", ".md", ".zip", ".csv"]:
        if stem.endswith(ext):
            stem = stem[: -len(ext)]
            break

    # Strip copy markers
    stem = re.sub(r"\s*\(\d+\)\s*", "", stem)
    stem = re.sub(r"[\s_.-]+copy(?:[\s_.-]+\d+)?", "", stem)
    stem = re.sub(r"\bcopy\s+of\b", "", stem)
    stem = re.sub(r"[\s_.-]+dup(?:licate)?", "", stem)
    stem = stem.strip(" ._-")
    return stem


# -----------------------------------------------------------------------------
# Engine Implementation
# -----------------------------------------------------------------------------


class DeduplicationEngine:
    """Main execution engine for binary and intelligent deduplication."""

    def __init__(
        self,
        target_dir: Path,
        recycle_bin: Path,
        dry_run: bool = True,
        enable_binary: bool = True,
        enable_semantic: bool = True,
        exclude_patterns: list[str] | None = None,
        min_size: int = 0,
        clean_empty_dirs: bool = True,
    ) -> None:
        self.target_dir = target_dir.resolve()
        self.recycle_bin = recycle_bin.resolve()
        self.staged_duplicates_dir = self.recycle_bin / "staged_duplicates"
        self.dry_run = dry_run
        self.enable_binary = enable_binary
        self.enable_semantic = enable_semantic
        self.exclude_patterns = exclude_patterns or []
        self.min_size = min_size
        self.clean_empty_dirs = clean_empty_dirs

    def is_excluded(self, path: Path) -> bool:
        """Check if a path matches exclusion rules."""
        # Always exclude the recycle bin and its subdirectories
        try:
            path.relative_to(self.recycle_bin)
            return True
        except ValueError:
            pass

        # Exclude standard VCS and virtualenv directories
        excluded_dir_names = {
            ".git",
            ".svn",
            ".hg",
            "node_modules",
            "__pycache__",
            ".venv",
            "venv",
            ".specstory",
            ".gemini",
        }
        for part in path.parts:
            if part in excluded_dir_names:
                return True

        # Check custom exclusion patterns
        path_str = str(path)
        for pat in self.exclude_patterns:
            if pat in path_str:
                return True

        return False

    def scan_files(self) -> Generator[FileMeta, None, None]:
        """Recursively scan target directory for regular files."""
        for root, dirs, files in os.walk(self.target_dir, topdown=True, followlinks=False):
            root_path = Path(root)
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if not self.is_excluded(root_path / d)]

            for fname in files:
                file_path = root_path / fname
                if file_path.is_symlink():
                    continue
                if self.is_excluded(file_path):
                    continue

                try:
                    stat_res = file_path.stat()
                except OSError as exc:
                    logger.debug("Failed to stat %s: %s", file_path, exc)
                    continue

                size = stat_res.st_size
                if size < self.min_size:
                    continue

                yield FileMeta(path=file_path, size=size, mtime=stat_res.st_mtime)

    def find_binary_duplicates(
        self, files: list[FileMeta]
    ) -> tuple[list[DuplicateGroup], set[Path]]:
        """Identify exact byte-for-byte binary duplicates."""
        groups: list[DuplicateGroup] = []
        handled_paths: set[Path] = set()

        # Step 1: Bucket by size
        by_size: dict[int, list[Path]] = defaultdict(list)
        for meta in files:
            by_size[meta.size].append(meta.path)

        candidate_size_groups = [paths for size, paths in by_size.items() if len(paths) >= 2]

        # Step 2: Bucket by partial hash (head + tail)
        by_partial: dict[tuple[int, str], list[Path]] = defaultdict(list)
        for paths in candidate_size_groups:
            for p in paths:
                try:
                    p_hash = compute_partial_hash(p)
                    by_partial[(p.stat().st_size, p_hash)].append(p)
                except OSError as exc:
                    logger.debug("Error computing partial hash for %s: %s", p, exc)

        candidate_partial_groups = [
            paths for key, paths in by_partial.items() if len(paths) >= 2
        ]

        # Step 3: Full SHA-256 confirmation
        by_full_sha: dict[tuple[int, str], list[Path]] = defaultdict(list)
        for paths in candidate_partial_groups:
            for p in paths:
                try:
                    full_sha = compute_full_sha256(p)
                    by_full_sha[(p.stat().st_size, full_sha)].append(p)
                except OSError as exc:
                    logger.debug("Error computing full hash for %s: %s", p, exc)

        for (size, sha), paths in by_full_sha.items():
            if len(paths) >= 2:
                keeper, duplicates = pick_canonical_keeper(paths)
                groups.append(
                    DuplicateGroup(
                        keeper=keeper,
                        duplicates=duplicates,
                        reason="Exact binary match (SHA-256)",
                        size=size,
                        content_hash=sha,
                    )
                )
                handled_paths.update(paths)

        return groups, handled_paths

    def find_semantic_duplicates(
        self, files: list[FileMeta], exclude_paths: set[Path]
    ) -> list[DuplicateGroup]:
        """Identify semantic duplicates (PDFs, images, text, and incomplete archives)."""
        groups: list[DuplicateGroup] = []
        remaining_files = [f for f in files if f.path not in exclude_paths]

        # Cluster files by (normalized_stem, extension_category)
        clusters: dict[tuple[str, str], list[FileMeta]] = defaultdict(list)
        for meta in remaining_files:
            ext = meta.path.suffix.lower()
            category = "other"
            if ext in {".pdf"}:
                category = "pdf"
            elif ext in {".png", ".jpg", ".jpeg", ".webp"}:
                category = "image"
            elif ext in {".md", ".txt", ".csv"}:
                category = "text"
            elif ext in {".zip"}:
                category = "archive"

            stem = get_normalized_stem(meta.path)
            if stem:
                clusters[(stem, category)].append(meta)

        processed_paths: set[Path] = set()

        for (stem, category), cluster in clusters.items():
            if len(cluster) < 2:
                continue

            # Process by category
            if category == "pdf":
                self._dedup_pdf_cluster(cluster, groups, processed_paths)
            elif category == "image" and HAS_PILLOW:
                self._dedup_image_cluster(cluster, groups, processed_paths)
            elif category == "text":
                self._dedup_text_cluster(cluster, groups, processed_paths)
            elif category == "archive":
                self._dedup_archive_cluster(cluster, groups, processed_paths)

        return groups

    def _dedup_pdf_cluster(
        self,
        cluster: list[FileMeta],
        groups: list[DuplicateGroup],
        processed: set[Path],
    ) -> None:
        """Compare normalized text extracted from candidate PDF files."""
        text_map: dict[Path, str] = {}
        for item in cluster:
            if item.path in processed:
                continue
            text = extract_pdf_normalized_text(item.path)
            if text:
                text_map[item.path] = text

        # Group by normalized text hash
        by_text_hash: dict[str, list[Path]] = defaultdict(list)
        for p, txt in text_map.items():
            thash = hashlib.sha256(txt.encode("utf-8")).hexdigest()
            by_text_hash[thash].append(p)

        for thash, paths in by_text_hash.items():
            if len(paths) >= 2:
                keeper, duplicates = pick_canonical_keeper(paths)
                groups.append(
                    DuplicateGroup(
                        keeper=keeper,
                        duplicates=duplicates,
                        reason="Normalized PDF text equality",
                        size=keeper.stat().st_size,
                        content_hash=thash,
                    )
                )
                processed.update(paths)

    def _dedup_image_cluster(
        self,
        cluster: list[FileMeta],
        groups: list[DuplicateGroup],
        processed: set[Path],
    ) -> None:
        """Compare perceptual hashes and dimensions for candidate images."""
        hash_map: dict[Path, tuple[tuple[int, int], str]] = {}
        for item in cluster:
            if item.path in processed:
                continue
            res = compute_image_dhash(item.path)
            if res:
                hash_map[item.path] = res

        # Group by matching dimensions and dHash
        by_sig: dict[tuple[tuple[int, int], str], list[Path]] = defaultdict(list)
        for p, sig in hash_map.items():
            by_sig[sig].append(p)

        for (dims, dhash), paths in by_sig.items():
            if len(paths) >= 2:
                keeper, duplicates = pick_canonical_keeper(paths)
                groups.append(
                    DuplicateGroup(
                        keeper=keeper,
                        duplicates=duplicates,
                        reason=f"Perceptual image match ({dims[0]}x{dims[1]}, dHash {dhash})",
                        size=keeper.stat().st_size,
                        content_hash=dhash,
                    )
                )
                processed.update(paths)

    def _dedup_text_cluster(
        self,
        cluster: list[FileMeta],
        groups: list[DuplicateGroup],
        processed: set[Path],
    ) -> None:
        """Compare body text stripped of transient export headers."""
        text_map: dict[Path, str] = {}
        for item in cluster:
            if item.path in processed:
                continue
            text = normalize_markdown_or_text(item.path)
            if text:
                text_map[item.path] = text

        by_text_hash: dict[str, list[Path]] = defaultdict(list)
        for p, txt in text_map.items():
            thash = hashlib.sha256(txt.encode("utf-8")).hexdigest()
            by_text_hash[thash].append(p)

        for thash, paths in by_text_hash.items():
            if len(paths) >= 2:
                keeper, duplicates = pick_canonical_keeper(paths)
                groups.append(
                    DuplicateGroup(
                        keeper=keeper,
                        duplicates=duplicates,
                        reason="Stripped transient header text match",
                        size=keeper.stat().st_size,
                        content_hash=thash,
                    )
                )
                processed.update(paths)

    def _dedup_archive_cluster(
        self,
        cluster: list[FileMeta],
        groups: list[DuplicateGroup],
        processed: set[Path],
    ) -> None:
        """Detect incomplete and corrupted archives paired with complete archives."""
        # Find candidates where one is complete and others are broken/truncated
        valid_archives: list[Path] = []
        broken_archives: list[Path] = []

        for item in cluster:
            if item.path in processed:
                continue
            is_valid, _ = test_archive_validity(item.path)
            if is_valid:
                valid_archives.append(item.path)
            else:
                broken_archives.append(item.path)

        if valid_archives and broken_archives:
            keeper, _ = pick_canonical_keeper(valid_archives)
            groups.append(
                DuplicateGroup(
                    keeper=keeper,
                    duplicates=broken_archives,
                    reason="Incomplete / aborted archive download paired with intact archive",
                    size=sum(p.stat().st_size for p in broken_archives),
                )
            )
            processed.update(broken_archives)

    def execute_moves(
        self, groups: list[DuplicateGroup]
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Move redundant duplicate files to staged_duplicates directory.

        Returns (manifest_items, empty_dirs_pruned).
        """
        manifest_items: list[dict[str, Any]] = []
        now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")

        self.staged_duplicates_dir.mkdir(parents=True, exist_ok=True)

        counter = 0
        for grp in groups:
            for dup_path in grp.duplicates:
                if not dup_path.exists():
                    continue

                try:
                    rel_path = dup_path.relative_to(self.target_dir)
                    dest_path = self.staged_duplicates_dir / rel_path
                except ValueError:
                    dest_path = self.staged_duplicates_dir / dup_path.name

                # Avoid collisions in destination
                if dest_path.exists():
                    counter += 1
                    stem = dest_path.stem
                    suffix = dest_path.suffix
                    dest_path = (
                        dest_path.parent / f"{stem}_dup_{now_str}_{counter}{suffix}"
                    )

                dest_path.parent.mkdir(parents=True, exist_ok=True)

                if not self.dry_run:
                    shutil.move(str(dup_path), str(dest_path))

                manifest_items.append(
                    {
                        "original_path": str(dup_path),
                        "staged_path": str(dest_path),
                        "keeper_path": str(grp.keeper),
                        "reason": grp.reason,
                        "size": dup_path.stat().st_size if self.dry_run else dest_path.stat().st_size,
                        "hash": grp.content_hash,
                    }
                )

        empty_dirs_pruned: list[str] = []
        if self.clean_empty_dirs and not self.dry_run:
            empty_dirs_pruned = self._prune_empty_dirs()

        return manifest_items, empty_dirs_pruned

    def _prune_empty_dirs(self) -> list[str]:
        """Prune empty directories bottom-up up to target directory."""
        pruned: list[str] = []
        for root, dirs, files in os.walk(self.target_dir, topdown=False):
            root_path = Path(root)
            if root_path == self.target_dir:
                continue
            if self.is_excluded(root_path):
                continue
            try:
                # If directory is completely empty
                if not any(root_path.iterdir()):
                    root_path.rmdir()
                    pruned.append(str(root_path))
            except OSError as exc:
                logger.debug("Failed to remove dir %s: %s", root_path, exc)
        return pruned

    def run(self) -> RunSummary:
        """Run deduplication workflow."""
        summary = RunSummary()

        # Step 1: Scan
        all_files = list(self.scan_files())
        summary.total_scanned = len(all_files)
        summary.total_bytes_scanned = sum(f.size for f in all_files)

        all_groups: list[DuplicateGroup] = []
        handled_binary_paths: set[Path] = set()

        # Step 2: Binary deduplication
        if self.enable_binary:
            bin_groups, handled_binary_paths = self.find_binary_duplicates(all_files)
            all_groups.extend(bin_groups)
            summary.binary_groups = len(bin_groups)
            summary.binary_duplicates = sum(len(g.duplicates) for g in bin_groups)
            summary.binary_bytes = sum(g.size * len(g.duplicates) for g in bin_groups)

        # Step 3: Semantic deduplication
        if self.enable_semantic:
            sem_groups = self.find_semantic_duplicates(
                all_files, exclude_paths=handled_binary_paths
            )
            all_groups.extend(sem_groups)
            summary.semantic_groups = len(sem_groups)
            summary.semantic_duplicates = sum(len(g.duplicates) for g in sem_groups)
            summary.semantic_bytes = sum(
                sum(p.stat().st_size for p in g.duplicates) for g in sem_groups
            )

        # Step 4: Execute or simulate moves
        manifest_items, empty_dirs = self.execute_moves(all_groups)
        summary.moved_files = len(manifest_items)
        summary.moved_bytes = sum(item["size"] for item in manifest_items)
        summary.empty_dirs_removed = len(empty_dirs)

        # Step 5: Save manifest if executing
        if not self.dry_run and manifest_items:
            now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
            manifest_file = self.recycle_bin / f".dedup_manifest_{now_str}.json"
            manifest_data = {
                "manifest_version": 1,
                "timestamp": now_str,
                "target_dir": str(self.target_dir),
                "recycle_bin": str(self.recycle_bin),
                "staged_duplicates_dir": str(self.staged_duplicates_dir),
                "total_moved": summary.moved_files,
                "total_bytes": summary.moved_bytes,
                "items": manifest_items,
                "empty_dirs_removed": empty_dirs,
            }
            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)
            summary.manifest_path = manifest_file

        return summary


# -----------------------------------------------------------------------------
# Undo Workflow
# -----------------------------------------------------------------------------


def run_undo(manifest_path: Path) -> None:
    """Restore staged files to their original locations using the manifest."""
    manifest_path = manifest_path.resolve()
    if not manifest_path.is_file():
        sys.exit(f"Error: Manifest file not found: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", [])
    empty_dirs = data.get("empty_dirs_removed", [])
    print(f"Loaded manifest from {manifest_path}")
    print(f"Files to restore: {len(items)}")

    # 1. Recreate empty directories if needed
    for d_str in reversed(empty_dirs):
        Path(d_str).mkdir(parents=True, exist_ok=True)

    restored_count = 0
    missing_count = 0

    for item in items:
        orig = Path(item["original_path"])
        staged = Path(item["staged_path"])

        if not staged.exists():
            print(f"Warning: Staged file not found: {staged}")
            missing_count += 1
            continue

        orig.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staged), str(orig))
        restored_count += 1

    # Cleanup empty directories inside staged_duplicates
    staged_dir_str = data.get("staged_duplicates_dir")
    if staged_dir_str:
        staged_dir = Path(staged_dir_str)
        if staged_dir.exists():
            for root, dirs, files in os.walk(staged_dir, topdown=False):
                r = Path(root)
                if not any(r.iterdir()):
                    try:
                        r.rmdir()
                    except OSError:
                        pass

    # Mark manifest as undone
    undone_path = manifest_path.with_name(
        manifest_path.stem + ".undone" + manifest_path.suffix
    )
    manifest_path.rename(undone_path)

    print(
        f"Restoration complete: {restored_count} files restored, {missing_count} missing."
    )
    print(f"Manifest archived to: {undone_path}")


# -----------------------------------------------------------------------------
# Formatting & CLI Entrypoint
# -----------------------------------------------------------------------------


def format_bytes(size: float) -> str:
    """Format bytes into human-readable representation."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Intelligent Content & Binary Deduplication Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage:
  1. Simulation (Dry-Run):
     uv run ~/.gemini/config/skills/deduplicator/scripts/dedup.py /path/to/target

  2. Live Execution:
     uv run ~/.gemini/config/skills/deduplicator/scripts/dedup.py /path/to/target --execute

  3. Pure Binary Mode (Skip Semantic Normalization):
     uv run ~/.gemini/config/skills/deduplicator/scripts/dedup.py /path/to/target --execute --no-semantic

  4. Undo / Rollback:
     uv run ~/.gemini/config/skills/deduplicator/scripts/dedup.py --undo /path/to/target/_recycle_bin/.dedup_manifest_YYYYMMDD_HHMMSS.json
        """,
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Target directory to inspect and deduplicate (default: current directory)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute file moves. If omitted, runs in simulation/dry-run mode.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Force simulation mode (default behavior).",
    )
    parser.add_argument(
        "--recycle-bin",
        help="Custom recycle bin path (default: <target>/_recycle_bin)",
    )
    parser.add_argument(
        "--no-semantic",
        action="store_true",
        help="Disable intelligent semantic deduplication (PDF, image dHash, markdown).",
    )
    parser.add_argument(
        "--no-binary",
        action="store_true",
        help="Disable exact binary deduplication.",
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=0,
        help="Minimum file size in bytes to consider (default: 0).",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Substring or pattern to exclude from scanning.",
    )
    parser.add_argument(
        "--undo",
        help="Path to manifest JSON file to reverse a previous run.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable detailed debug logging.",
    )

    args = parser.parse_args()

    # Logging setup
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

    # Undo mode
    if args.undo:
        run_undo(Path(args.undo))
        return

    target_path = Path(args.target).resolve()
    if not target_path.is_dir():
        sys.exit(f"Error: Target directory does not exist: {target_path}")

    # Recycle bin resolution
    if args.recycle_bin:
        recycle_path = Path(args.recycle_bin).resolve()
    else:
        recycle_path = target_path / "_recycle_bin"

    dry_run = not args.execute or args.dry_run

    print("=" * 70)
    print(f"Target:       {target_path}")
    print(f"Recycle bin:  {recycle_path}")
    print(f"Mode:         {'SIMULATION (DRY-RUN)' if dry_run else 'LIVE EXECUTION'}")
    print(f"Binary dedup: {'Enabled' if not args.no_binary else 'Disabled'}")
    print(
        f"Semantic:     {'Enabled' if not args.no_semantic else 'Disabled'} (Pillow: {HAS_PILLOW}, pdftotext: {shutil.which('pdftotext') is not None})"
    )
    print("=" * 70)

    engine = DeduplicationEngine(
        target_dir=target_path,
        recycle_bin=recycle_path,
        dry_run=dry_run,
        enable_binary=not args.no_binary,
        enable_semantic=not args.no_semantic,
        exclude_patterns=args.exclude,
        min_size=args.min_size,
    )

    start_time = time.time()
    summary = engine.run()
    elapsed = time.time() - start_time

    print("\nScan Results:")
    print(f"  Files scanned:         {summary.total_scanned:,} ({format_bytes(summary.total_bytes_scanned)})")
    print(f"  Binary duplicate sets: {summary.binary_groups:,} ({summary.binary_duplicates:,} redundant files, {format_bytes(summary.binary_bytes)})")
    print(f"  Semantic sets:         {summary.semantic_groups:,} ({summary.semantic_duplicates:,} redundant files, {format_bytes(summary.semantic_bytes)})")
    print(f"  Total duplicate files: {summary.moved_files:,} ({format_bytes(summary.moved_bytes)})")
    print(f"  Time elapsed:          {elapsed:.2f}s")

    if dry_run:
        print("\nNote: Simulation mode. No files were modified on disk.")
        print("To execute these moves, re-run with --execute.")
    else:
        print("\nExecution Complete:")
        print(f"  Moved files:           {summary.moved_files:,}")
        print(f"  Empty dirs pruned:     {summary.empty_dirs_removed:,}")
        if summary.manifest_path:
            print(f"  Transaction manifest:  {summary.manifest_path}")
            print(f"  Rollback command:      uv run {Path(__file__).resolve()} --undo {summary.manifest_path}")


if __name__ == "__main__":
    main()
