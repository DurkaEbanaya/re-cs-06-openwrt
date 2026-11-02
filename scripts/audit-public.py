#!/usr/bin/env python3
"""Fail closed on unexpected tracked files or common secret/identity patterns."""
import argparse
import json
from pathlib import Path
import re
import subprocess

ALLOWED = re.compile(
    r"^(?:\.gitignore|\.gitattributes|\.github/workflows/tests\.yml|README\.md|LICENSE|Containerfile|sources\.lock\.json|radio-files\.lock\.json|"
    r"config/[a-z0-9._-]+\.config|patches/[a-z0-9._-]+\.patch|"
    r"docs/[A-Z0-9._-]+\.md|scripts/[a-z0-9._-]+|"
    r"tests/test_[a-z0-9_]+\.py|reports/[a-z0-9._-]+\.json|"
    r"overlay/etc/uci-defaults/[a-z0-9._-]+|overlay/lib/upgrade/re-cs-06\.sh|"
    r"overlay/usr/sbin/re-cs-06-provision-macs)$"
)
PATTERNS = {
    "private_key": re.compile(rb"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"),
    "github_token": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    "password_hash": re.compile(rb"\$(?:1|5|6|y)\$[A-Za-z0-9./]+\$[A-Za-z0-9./]{10,}"),
    "mac_address": re.compile(rb"(?i)(?<![a-z0-9])(?:[0-9a-f]{2}:){5}[0-9a-f]{2}(?![a-z0-9])"),
    "host_path": re.compile(rb"/(?:home|Users)/[A-Za-z0-9_.-]+/"),
}


def inspect_file(name, data, deny=()):
    errors = []
    if not ALLOWED.fullmatch(name):
        errors.append({"file": name, "reason": "unexpected_path"})
    if len(data) > 2 * 1024 * 1024 or b"\0" in data:
        errors.append({"file": name, "reason": "oversized_or_binary"})
    for label, pattern in PATTERNS.items():
        matches = list(pattern.finditer(data))
        if label == "mac_address":
            matches = [m for m in matches if m.group().lower() != b"00:00:00:00:00:00"]
        if matches:
            errors.append({"file": name, "reason": label})
    if any(literal and literal.lower().encode() in data.lower() for literal in deny):
        errors.append({"file": name, "reason": "private_literal"})
    return errors


def inspect_repo(repo, deny=()):
    entries = subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=repo).split(b"\0")
    entries = [entry for entry in entries if entry]
    assert entries, "No staged/tracked files to audit"
    errors = []
    for entry in entries:
        meta, name_bytes = entry.split(b"\t", 1)
        mode, object_id, stage = meta.decode().split()
        name = name_bytes.decode()
        if mode not in ("100644", "100755") or stage != "0":
            errors.append({"file": name, "reason": "unexpected_index_mode_or_conflict"})
            continue
        path = repo / name
        if path.is_symlink() or not path.is_file():
            errors.append({"file": name, "reason": "unexpected_path"})
            continue
        errors.extend(inspect_file(name, path.read_bytes(), deny))
        # An innocent working copy must not hide an older secret staged for commit.
        staged = subprocess.check_output(["git", "cat-file", "blob", object_id], cwd=repo)
        errors.extend(inspect_file(name, staged, deny))
    return {"files_checked": len(entries), "working_tree_and_index_checked": True,
            "errors": errors, "public_source_audit_passed": not errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deny-file", type=Path, help="Optional local-only JSON list of private literal strings")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    deny = json.loads(args.deny_file.read_text()) if args.deny_file else []
    result = inspect_repo(repo, deny)
    print(json.dumps(result, indent=2))
    if result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
