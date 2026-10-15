#!/usr/bin/env python3
"""
organize_library.py - Johnny.Decimal Master Library Organizer Engine

An immutable, safe execution engine for digital library organization,
exact binary deduplication, metadata extraction, and Johnny.Decimal classification.

Configuration is fully decoupled into an external taxonomy schema (taxonomy.json).
"""

import os
import sys
import json
import argparse
import hashlib
import re
import shutil
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

DEFAULT_TAXONOMY_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "taxonomy.json")

def load_taxonomy(taxonomy_path, target_dir):
    """Loads taxonomy configuration with local workspace override support."""
    # Check for local workspace manifest first
    local_manifest = os.path.join(target_dir, "library_manifest.json")
    if os.path.isfile(local_manifest):
        with open(local_manifest, 'r', encoding='utf-8') as f:
            return json.load(f), local_manifest

    if taxonomy_path and os.path.isfile(taxonomy_path):
        with open(taxonomy_path, 'r', encoding='utf-8') as f:
            return json.load(f), taxonomy_path

    if os.path.isfile(DEFAULT_TAXONOMY_PATH):
        with open(DEFAULT_TAXONOMY_PATH, 'r', encoding='utf-8') as f:
            return json.load(f), DEFAULT_TAXONOMY_PATH

    raise FileNotFoundError(f"Taxonomy configuration not found. Checked: {local_manifest}, {taxonomy_path}, {DEFAULT_TAXONOMY_PATH}")

def compute_sha256(filepath):
    """Computes SHA-256 hash using 64KB streaming chunks."""
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (OSError, PermissionError):
        return None

def clean_text(s):
    if not s:
        return ""
    return ' '.join(str(s).split()).strip()

def sanitize_basename(base):
    """Clean unwanted tokens, tracking tags, and duplicates suffixes from base filename."""
    # Strip tracking tags
    base = re.sub(r'\[(?:z-lib\.org|oceanofpdf\.com|b-ok\.cc|annas-archive)\]', '', base, flags=re.IGNORECASE)
    # Strip numeric dupe indicators like (1), [2], _v2
    base = re.sub(r'\s*[\(\[]\d+[\)\]]\s*$', '', base)
    base = re.sub(r'\s*[-_]v\d+\s*$', '', base, flags=re.IGNORECASE)
    # Strip year tags like (2024)
    base = re.sub(r'\s*\(\d{4}\)\s*$', '', base)
    # Replace illegal filesystem characters
    base = re.sub(r'[<>:"/\\|?*]', ' - ', base)
    base = re.sub(r'\s+', ' ', base).strip(' -_')
    return base

def extract_metadata(filepath, ext):
    """Extracts title, author/creator, and text sample safely from EPUB and PDF files."""
    meta = {'title': '', 'author': '', 'sample': ''}
    ext_lower = ext.lower()

    if ext_lower == '.epub':
        try:
            with zipfile.ZipFile(filepath, 'r') as z:
                opf_candidates = [n for n in z.namelist() if n.lower().endswith('.opf')]
                if opf_candidates:
                    root = ET.fromstring(z.read(opf_candidates[0]))
                    title_elem = root.find('.//{*}title')
                    if title_elem is not None and title_elem.text:
                        meta['title'] = clean_text(title_elem.text)
                    creator_elem = root.find('.//{*}creator')
                    if creator_elem is not None and creator_elem.text:
                        meta['author'] = clean_text(creator_elem.text)
        except Exception:
            pass

    elif ext_lower == '.pdf':
        try:
            res = subprocess.run(
                ['pdftotext', '-f', '1', '-l', '3', filepath, '-'],
                capture_output=True,
                text=True,
                errors='ignore',
                timeout=8
            )
            if res.returncode == 0 and res.stdout:
                meta['sample'] = clean_text(res.stdout)[:2000]
        except Exception:
            pass

    return meta

def matches_token(pattern, text):
    """Matches a keyword using word boundaries to prevent substring collisions."""
    regex = r'\b' + re.escape(pattern.lower()) + r'\b'
    return bool(re.search(regex, text.lower()))

def check_gatekeeper_exclusion(filename, sample, exclusions):
    """Returns True if the file contains administrative/PII tokens that disqualify it from the library."""
    combined = f"{filename} {sample}".lower()
    for kw in exclusions.get('keywords', []):
        if matches_token(kw, combined):
            return True, kw
    return False, None

def classify_document(filename, metadata, categories):
    """Scores candidate categories using weighted title, sample, and regex matching."""
    title = metadata.get('title', '')
    author = metadata.get('author', '')
    sample = metadata.get('sample', '')
    
    title_text = f"{filename} {title} {author}".lower()
    sample_text = sample.lower()

    best_category = None
    best_score = 0

    for cat in categories:
        rules = cat.get('rules', {})
        score = 0

        # Title keyword matches (weight 10)
        for kw in rules.get('title_keywords', []):
            if matches_token(kw, title_text):
                score += 10

        # Content keyword matches (weight 3)
        for kw in rules.get('content_keywords', []):
            if matches_token(kw, sample_text):
                score += 3

        # Regex matches (weight 12)
        for pattern in rules.get('regex_patterns', []):
            try:
                if re.search(pattern, title_text, flags=re.IGNORECASE):
                    score += 12
                elif re.search(pattern, sample_text, flags=re.IGNORECASE):
                    score += 6
            except re.error:
                continue

        min_score = rules.get('min_score', 10)
        if score >= min_score and score > best_score:
            best_score = score
            best_category = cat

    return best_category, best_score

def format_canonical_name(filename, metadata, ext):
    """Constructs a clean canonical filename based on sanitized base and metadata."""
    base = os.path.splitext(filename)[0]
    clean_base = sanitize_basename(base)
    
    title = clean_text(metadata.get('title', ''))
    author = clean_text(metadata.get('author', ''))

    # If the file base is completely numeric or opaque (e.g. 9780132350884 or download), use metadata
    if re.match(r'^\d+$', clean_base) or clean_base.lower() in ('download', 'document', 'file', 'book'):
        if title and author:
            return f"{author} - {title}{ext}"
        elif title:
            return f"{title}{ext}"

    # If base already has "Author - Title", preserve the sanitized form
    return f"{clean_base}{ext}"

def run_undo(manifest_path):
    """Rolls back operations recorded in a transaction manifest."""
    if not os.path.isfile(manifest_path):
        print(f"Error: Manifest file {manifest_path} not found.")
        sys.exit(1)

    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    operations = manifest.get('operations', [])
    print(f"Reversing {len(operations)} operations from {manifest.get('timestamp', 'unknown')}...")

    reverted = 0
    for op in reversed(operations):
        src = op['src']
        dest = op['dest']
        if os.path.exists(dest):
            os.makedirs(os.path.dirname(src), exist_ok=True)
            shutil.move(dest, src)
            reverted += 1
            print(f"Restored: {dest} -> {src}")
        else:
            print(f"Skipped (target missing): {dest}")

    print(f"\nRollback complete. Restored {reverted}/{len(operations)} files.")

def resolve_system_dir(target_dir, rel_path):
    """Resolves inbox or duplicates directory intelligently relative to target or parent."""
    direct = os.path.join(target_dir, rel_path)
    if os.path.exists(direct):
        return direct
    parent = os.path.abspath(os.path.join(target_dir, ".."))
    parent_candidate = os.path.join(parent, rel_path)
    if os.path.exists(parent_candidate):
        return parent_candidate
    return direct

def resolve_category_dest(target_dir, cat_path):
    """Resolves category destination handling root vs sub-area targets without duplicate nesting."""
    target_name = os.path.basename(os.path.abspath(target_dir))
    parts = Path(cat_path).parts
    if parts and parts[0] == target_name:
        subpath = os.path.join(*parts[1:]) if len(parts) > 1 else ""
        return os.path.join(target_dir, subpath)
    return os.path.join(target_dir, cat_path)

def main():
    parser = argparse.ArgumentParser(description="Johnny.Decimal Master Library Organizer Engine")
    parser.add_argument('--dir', help="Target directory to organize")
    parser.add_argument('--taxonomy', help="Path to custom taxonomy JSON configuration")
    parser.add_argument('--dry-run', action='store_true', help="Simulate moves and report planned changes without touching disk")
    parser.add_argument('--json-report', help="Output machine-readable report to specified JSON file")
    parser.add_argument('--format-policy', choices=['co_locate', 'exact_only'], default='co_locate',
                        help="Policy for multi-format works (co_locate keeps both EPUB and PDF)")
    parser.add_argument('--undo', help="Undo operations recorded in the specified manifest file")
    args = parser.parse_args()

    if args.undo:
        run_undo(args.undo)
        return

    if not args.dir:
        parser.error("--dir is required unless --undo is specified.")

    target_dir = os.path.abspath(args.dir)
    if not os.path.exists(target_dir):
        print(f"Error: Directory {target_dir} not found.")
        sys.exit(1)

    taxonomy, config_src = load_taxonomy(args.taxonomy, target_dir)
    print(f"Loaded Taxonomy Configuration from: {config_src}")

    system_folders = taxonomy.get('system_folders', {})
    inbox_rel = system_folders.get('inbox', '00-09 System & Inbox/01 Intake & Inbox')
    dupe_rel = system_folders.get('duplicates', '_recycle_bin/staged_duplicates')
    
    inbox_dir = resolve_system_dir(target_dir, inbox_rel)
    dupe_dir = resolve_system_dir(target_dir, dupe_rel)

    supported_exts = set(taxonomy.get('format_policy', {}).get('supported_extensions', ['.pdf', '.epub', '.mobi']))
    exclusions = taxonomy.get('gatekeeper_exclusions', {})
    categories = taxonomy.get('categories', [])

    # Discover candidate files
    all_files = []
    for root, dirs, files in os.walk(target_dir):
        rel_root = os.path.relpath(root, target_dir)
        # Skip recycle bin and hidden directories
        if rel_root.startswith('_recycle_bin') or rel_root.startswith('.'):
            continue
        for f in files:
            if f.startswith('.'):
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext in supported_exts:
                all_files.append(os.path.join(root, f))

    print(f"Discovered {len(all_files)} supported documents across target directory.")

    # Phase 1: Fast Exact Binary Deduplication (Size grouping + SHA-256)
    size_dict = defaultdict(list)
    for p in all_files:
        try:
            size_dict[os.path.getsize(p)].append(p)
        except OSError:
            pass

    exact_duplicates = []
    unique_files = []

    for size, paths in size_dict.items():
        if len(paths) == 1:
            unique_files.append(paths[0])
        else:
            hash_dict = defaultdict(list)
            for p in paths:
                h = compute_sha256(p)
                if h:
                    hash_dict[h].append(p)
                else:
                    unique_files.append(p)
            for h, hpaths in hash_dict.items():
                if len(hpaths) == 1:
                    unique_files.append(hpaths[0])
                else:
                    # Sort so canonical/cleanest path is kept
                    hpaths.sort(key=lambda x: (len(os.path.basename(x)), x))
                    unique_files.append(hpaths[0])
                    for redundant in hpaths[1:]:
                        exact_duplicates.append(redundant)

    print(f"Exact binary duplicates identified: {len(exact_duplicates)}")

    # Phase 2: Classification and Planning
    planned_moves = []
    disqualified_files = []
    unclassified_files = []

    for p in unique_files:
        filename = os.path.basename(p)
        ext = os.path.splitext(filename)[1]
        metadata = extract_metadata(p, ext)
        # Check if file is already inside a recognized category folder
        parent_rel = os.path.relpath(os.path.dirname(p), target_dir)
        parent_base = os.path.basename(os.path.dirname(p))
        is_already_categorized = any(
            parent_rel.startswith(cat['path']) or
            parent_base.startswith(cat['jd_code'])
            for cat in categories
        )

        # Admissions Gatekeeper check
        disqualified, reason_kw = check_gatekeeper_exclusion(filename, metadata.get('sample', ''), exclusions)
        if disqualified:
            disqualified_files.append({'src': p, 'reason': f"Matched exclusion token '{reason_kw}'"})
            dest_folder = inbox_dir
            new_name = filename
        else:
            cat, score = classify_document(filename, metadata, categories)
            if cat:
                dest_folder = resolve_category_dest(target_dir, cat['path'])
                new_name = format_canonical_name(filename, metadata, ext)
            elif is_already_categorized:
                # File is already inside an appropriate category folder, preserve its location
                dest_folder = os.path.dirname(p)
                new_name = format_canonical_name(filename, metadata, ext)
            else:
                unclassified_files.append(p)
                dest_folder = inbox_dir
                new_name = format_canonical_name(filename, metadata, ext)

        dest_path = os.path.join(dest_folder, new_name)
        if os.path.abspath(p) != os.path.abspath(dest_path):
            planned_moves.append({
                'src': p,
                'dest': dest_path,
                'dest_folder': dest_folder,
                'new_name': new_name,
                'action': 'move'
            })

    for d in exact_duplicates:
        dest_path = os.path.join(dupe_dir, os.path.basename(d))
        planned_moves.append({
            'src': d,
            'dest': dest_path,
            'dest_folder': dupe_dir,
            'new_name': os.path.basename(d),
            'action': 'stage_duplicate'
        })

    # Report Summary
    report = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'target_dir': target_dir,
        'dry_run': args.dry_run,
        'total_scanned': len(all_files),
        'exact_duplicates_found': len(exact_duplicates),
        'disqualified_gatekeeper_files': len(disqualified_files),
        'unclassified_routed_to_inbox': len(unclassified_files),
        'planned_moves_count': len(planned_moves),
        'operations': planned_moves
    }

    print("\n" + "="*50)
    print(f"JOHNNY.DECIMAL EXECUTION PLAN SUMMARY ({'DRY RUN' if args.dry_run else 'LIVE RUN'})")
    print("="*50)
    print(f"Total documents scanned:       {report['total_scanned']}")
    print(f"Exact binary duplicates:       {report['exact_duplicates_found']}")
    print(f"Gatekeeper exclusions:         {report['disqualified_gatekeeper_files']}")
    print(f"Unclassified (routed to inbox):{report['unclassified_routed_to_inbox']}")
    print(f"Files to move / reorganize:    {report['planned_moves_count']}")

    if args.json_report:
        with open(args.json_report, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to: {args.json_report}")

    if args.dry_run:
        print("\nDry-run completed. No files were modified on disk.")
        return

    # Phase 3: Live Execution with Transaction Journal
    timestamp_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    manifest_path = os.path.join(target_dir, f".jd_manifest_{timestamp_slug}.json")
    
    executed_operations = []
    print(f"\nExecuting {len(planned_moves)} file movements...")

    for move in planned_moves:
        src = move['src']
        dest_folder = move['dest_folder']
        new_name = move['new_name']

        if not os.path.exists(src):
            continue

        os.makedirs(dest_folder, exist_ok=True)
        dest_path = os.path.join(dest_folder, new_name)

        # Collision avoidance: append counter if target already exists with different contents
        if os.path.exists(dest_path) and os.path.abspath(src) != os.path.abspath(dest_path):
            base, ext = os.path.splitext(new_name)
            counter = 1
            while os.path.exists(dest_path) and os.path.abspath(src) != os.path.abspath(dest_path):
                dest_path = os.path.join(dest_folder, f"{base} ({counter}){ext}")
                counter += 1

        if os.path.abspath(src) != os.path.abspath(dest_path):
            shutil.move(src, dest_path)
            executed_operations.append({
                'src': src,
                'dest': dest_path,
                'action': move['action'],
                'sha256': compute_sha256(dest_path)
            })

    # Save transaction manifest
    manifest_data = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'manifest_id': timestamp_slug,
        'target_dir': target_dir,
        'operations': executed_operations
    }
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest_data, f, indent=2)

    print(f"Execution complete. Manifest written to: {manifest_path}")
    print(f"You can undo this execution anytime with: python {__file__} --undo {manifest_path}")

if __name__ == "__main__":
    main()
