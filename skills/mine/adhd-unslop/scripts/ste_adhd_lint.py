#!/usr/bin/env python3
"""
ste_adhd_lint.py - Deterministic linter for ASD-STE100, Unslop, and ADHD formatting.

Checks:
- Mandatory response beacon (optional flag --check-beacon)
- Sentence word limits (<=20 words for instructions/steps, <=25 words for descriptions)
- Semicolons (banned)
- Em dashes (banned)
- Banned AI vocabulary and marketing superlatives
- Banned abstract jargon metaphors
- Banned soft phrasal verbs
- Banned chatbot formulas
"""

import sys
import re
import argparse
from typing import List, Tuple

BANNED_AI_WORDS = {
    "additionally", "crucial", "delve", "enduring", "enhance", "foster",
    "garner", "intricate", "landscape", "pivotal", "showcase", "tapestry",
    "testament", "underscore", "vibrant", "utilize", "leverage"
}

BANNED_SUPERLATIVES = {
    "seamless", "robust", "flawless", "comprehensive", "cutting-edge",
    "blazing-fast", "effortless", "elegant", "groundbreaking", "breathtaking",
    "renowned", "stunning"
}

BANNED_METAPHORS = {
    "substrate", "wedge", "vector", "nexus", "locus", "vantage",
    "bedrock", "scaffolding", "flywheel", "north star", "gold-plating"
}

BANNED_PHRASAL_VERBS = [
    r"\bspin\s+up\b", r"\bdive\s+into\b", r"\bwind\s+down\b",
    r"\blook\s+into\b", r"\btake\s+off\b", r"\bkick\s+off\b",
    r"\bdrill\s+down\b", r"\bwrap\s+up\b"
]

BANNED_CHATBOT_PHRASES = [
    r"\bcertainly\b", r"\bgreat\s+question\b", r"\bi\s+hope\s+this\s+helps\b",
    r"\blet\s+me\s+know\s+if\b", r"\bfeel\s+free\s+to\b", r"\bof\s+course\b",
    r"\bi'd\s+be\s+(happy|glad)\s+to\b"
]

BEACON_HEADER = "───────── ౨ৎ ─────────"


def split_sentences(text: str) -> List[str]:
    """Split text into sentences while ignoring markdown code blocks."""
    lines = text.splitlines()
    in_code_block = False
    cleaned_lines = []
    in_frontmatter = False
    for i, line in enumerate(lines):
        if i == 0 and line.strip() == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if line.strip() == "---":
                in_frontmatter = False
            continue

        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        
        # Skip markdown headers entirely
        if re.match(r"^#+\s+", line.strip()):
            continue
            
        # Skip horizontal rules
        if re.match(r"^[-*_]{3,}$", line.strip()):
            continue
            
        # Skip markdown tables and lists to prevent them from merging into giant sentences
        if re.match(r"^\|.*\|$", line.strip()) or re.match(r"^\s*[-*]\s", line):
            continue
            
        # Skip blockquotes
        if line.strip().startswith(">"):
            continue

        cleaned_lines.append(line)
    
    cleaned_text = "\n".join(cleaned_lines)
    # Split by periods, exclamation marks, question marks followed by space or newline
    raw_sentences = re.split(r'(?<=[.!?])\s+', cleaned_text)
    return [s.strip() for s in raw_sentences if s.strip()]


def check_text(text: str, check_beacon: bool = False) -> List[str]:
    violations = []
    lines = text.splitlines()

    # 1. Beacon Check
    if check_beacon:
        stripped = text.strip().lstrip('\u200b').strip()
        if not stripped.startswith(BEACON_HEADER):
            violations.append(f"BEACON: Missing mandatory response beacon delimiter ('{BEACON_HEADER}') at start.")

    in_code = False
    in_frontmatter = False
    for line_idx, line in enumerate(lines, 1):
        if line_idx == 1 and line.strip() == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if line.strip() == "---":
                in_frontmatter = False
            continue

        stripped_line = line.strip()
        if stripped_line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
            
        # Skip markdown tables and blockquotes
        if re.match(r"^\|.*\|$", stripped_line) or stripped_line.startswith(">"):
            continue

        # Strip inline code snippets (`...`) and double quotes ("...") for word and punctuation checks
        line_no_inline = re.sub(r"`[^`]+`", "", line)
        line_no_inline = re.sub(r'"[^"]+"', "", line_no_inline)

        # 2. Semicolon check
        if ";" in line_no_inline:
            violations.append(f"Line {line_idx} (SEMICOLON): Semicolons are banned under ASD-STE100 Rule 8.1.")

        # 3. Em-dash check
        if "—" in line_no_inline or "--" in line_no_inline:
            # Allow horizontal rule lines (---) and markdown table lines (| --- |)
            if not re.match(r"^[-| :]+$", stripped_line):
                violations.append(f"Line {line_idx} (EM-DASH): Em dashes ('—' or '--') are banned AI punctuation tells.")

        line_lower = line_no_inline.lower()

        # 4. Banned AI Vocabulary
        words = re.findall(r"\b[a-zA-Z-]+\b", line_lower)
        for w in words:
            if w in BANNED_AI_WORDS:
                violations.append(f"Line {line_idx} (AI_VOCAB): Banned word '{w}'. Use plain equivalent.")
            if w in BANNED_SUPERLATIVES:
                violations.append(f"Line {line_idx} (SUPERLATIVE): Banned marketing superlative '{w}'. State facts or measurements.")
            if w in BANNED_METAPHORS:
                violations.append(f"Line {line_idx} (METAPHOR): Banned jargon metaphor '{w}'. Use concrete term.")

        # 5. Phrasal Verbs
        for pattern in BANNED_PHRASAL_VERBS:
            if re.search(pattern, line_lower):
                matched = re.search(pattern, line_lower).group(0)
                violations.append(f"Line {line_idx} (PHRASAL_VERB): Banned phrasal verb '{matched}'. Use single direct verb.")

        # 6. Chatbot Chatter
        for pattern in BANNED_CHATBOT_PHRASES:
            if re.search(pattern, line_lower):
                matched = re.search(pattern, line_lower).group(0)
                violations.append(f"Line {line_idx} (CHATBOT): Banned chatbot filler '{matched}'. Strip pleasantry.")

        # 7. Step word count
        is_step = bool(re.match(r"^\d+\.\s+", stripped_line))
        if is_step:
            step_words = stripped_line.split()
            if len(step_words) > 20:
                violations.append(f"Line {line_idx} (STEP_LENGTH): Step exceeds 20 words ({len(step_words)} words).")

    # 8. Prose sentence length
    sentences = split_sentences(text)
    for s in sentences:
        # Ignore markdown headers or list item markers
        cleaned = re.sub(r"^(#+|\d+\.|\*|-)\s+", "", s).strip()
        word_count = len(cleaned.split())
        if word_count > 25:
            # Check if this sentence has URL or file path inflating word count
            if not ("http://" in s or "https://" in s or "file:///" in s):
                violations.append(f"PROSE_LENGTH: Sentence exceeds 25 words ({word_count} words): \"{cleaned[:50]}...\"")

    return violations


def selftest() -> bool:
    bad_sample = """\u200b
───────── ౨ৎ ─────────
Certainly! I will delve into this intricate problem to leverage a seamless solution;
1. First you must spin up the server and then configure the settings and then check the database output to verify everything works properly without issues.
"""
    violations = check_text(bad_sample, check_beacon=True)
    expected_categories = ["SEMICOLON", "AI_VOCAB", "SUPERLATIVE", "PHRASAL_VERB", "CHATBOT", "STEP_LENGTH"]
    for cat in expected_categories:
        if not any(cat in v for v in violations):
            print(f"Self-test failed: Missing expected violation category {cat}")
            return False

    good_sample = """\u200b
───────── ౨ৎ ─────────

`pytest tests/test_core.py` passes cleanly.

1. Open `config.py`.
2. Set `DEBUG = False`.
3. Save the file.

Next: run `pytest` to confirm all tests pass.
"""
    good_violations = check_text(good_sample, check_beacon=True)
    if good_violations:
        print(f"Self-test failed: Good sample generated false positives: {good_violations}")
        return False

    print("Self-test passed successfully.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Lint text against ADHD + ASD-STE100 + Unslop rules.")
    parser.add_argument("files", nargs="*", help="Files to lint (reads from stdin if none provided)")
    parser.add_argument("--check-beacon", action="store_true", help="Enforce starting response beacon delimiter")
    parser.add_argument("--selftest", action="store_true", help="Run internal self-tests")

    args = parser.parse_args()

    if args.selftest:
        success = selftest()
        sys.exit(0 if success else 1)

    all_violations = []

    if not args.files:
        content = sys.stdin.read()
        violations = check_text(content, check_beacon=args.check_beacon)
        all_violations.extend(violations)
    else:
        for file_path in args.files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                file_violations = check_text(content, check_beacon=args.check_beacon)
                for v in file_violations:
                    all_violations.append(f"{file_path}: {v}")
            except Exception as e:
                print(f"Error reading {file_path}: {e}", file=sys.stderr)
                sys.exit(2)

    if all_violations:
        print(f"Found {len(all_violations)} violation(s):")
        for v in all_violations:
            print(f"  - {v}")
        sys.exit(1)
    else:
        print("Lint passed: No violations found.")
        sys.exit(0)


if __name__ == "__main__":
    main()
