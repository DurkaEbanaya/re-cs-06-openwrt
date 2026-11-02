#!/usr/bin/env python3
"""Fail closed on unexpected tracked files or common secret/identity patterns."""
import argparse
import json
from pathlib import Path
import re
import subprocess

ALLOWED = re.compile(
    r"^(?:\.gitignore|\.gitattributes|README\.md|LICENSE|Containerfile|sources\.lock\.json|"
    r"config/[a-z0-9._-]+\.config|patches/[a-z0-9._-]+\.patch|"
    r"docs/[A-Z0-9._-]+\.md|scripts/[a-z0-9._-]+|"
    r"tests/test_[a-z0-9_]+\.py|reports/[a-z0-9._-]+\.json|"
    r"overlay/etc/uci-defaults/[a-z0-9._-]+|"
    r"overlay/usr/sbin/re-cs-06-provision-macs)$"
)
PATTERNS = {
    "private_key": re.compile(rb"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"),
    "github_token": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    "password_hash": re.compile(rb"\$(?:1|5|6|y)\$[A-Za-z0-9./]+\$[A-Za-z0-9./]{10,}"),
    "mac_address": re.compile(rb"(?i)(?<![a-z0-9])(?:[0-9a-f]{2}:){5}[0-9a-f]{2}(?![a-z0-9])"),
    "host_path": re.compile(rb"/(?:home|Users)/[A-Za-z0-9_.-]+/"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deny-file", type=Path, help="Optional local-only JSON list of private literal strings")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=repo).decode().split("\0")
    names = [n for n in names if n]
    assert names, "No staged/tracked files to audit"
    deny = json.loads(args.deny_file.read_text()) if args.deny_file else []
    errors = []
    for name in names:
        path = repo / name
        if not ALLOWED.fullmatch(name) or path.is_symlink() or not path.is_file():
            errors.append({"file": name, "reason": "unexpected_path"})
            continue
        data = path.read_bytes()
        if len(data) > 2 * 1024 * 1024 or b"\0" in data:
            errors.append({"file": name, "reason": "oversized_or_binary"})
        for label, pattern in PATTERNS.items():
            matches = list(pattern.finditer(data))
            if label == "mac_address":
                matches = [m for m in matches if m.group().lower() != b"00:00:00:00:00:00"]
            if matches:
                errors.append({"file": name, "reason": label})
        for literal in deny:
            if literal and literal.lower().encode() in data.lower():
                errors.append({"file": name, "reason": "private_literal"})
                break
    print(json.dumps({"files_checked": len(names), "errors": errors,
                      "public_source_audit_passed": not errors}, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
