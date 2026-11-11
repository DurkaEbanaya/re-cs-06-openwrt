#!/usr/bin/env python3
"""Prepare pinned sources and public-only overlay; never reads device backups."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

REPO = Path(__file__).resolve().parents[1]


def run(args, cwd):
    subprocess.run(args, cwd=cwd, check=True)


def checkout(url, commit, destination):
    if not destination.exists():
        destination.mkdir(parents=True)
        run(["git", "init", "-q"], destination)
        run(["git", "remote", "add", "origin", url], destination)
        run(["git", "fetch", "--depth", "1", "origin", commit], destination)
        run(["git", "checkout", "--detach", "FETCH_HEAD"], destination)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=destination, text=True).strip()
    if actual != commit:
        raise SystemExit(f"Wrong source revision at {destination}: {actual}")
    # Existing checkouts may have been created with a restrictive umask too.
    # Restore Git file modes, without changing tracked file contents.
    for entry in subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=destination).split(b"\0"):
        if not entry:
            continue
        metadata, name = entry.split(b"\t", 1)
        mode, _, stage = metadata.decode().split()
        path = destination / name.decode()
        if stage == "0" and mode in ("100644", "100755") and path.is_file() and not path.is_symlink():
            path.chmod(0o755 if mode == "100755" else 0o644)


def main():
    # Git checkout honors umask; restrictive inherited masks can silently
    # produce unreadable configuration files in the final firmware.
    # Private keys/backups never enter this public-source preparation tree.
    os.umask(0o022)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    lock = json.loads((REPO / "sources.lock.json").read_text())
    checkout(lock["source"]["url"], lock["source"]["commit"], source)
    for patch in sorted((REPO / "patches").glob("*.patch")):
        applied = subprocess.run(["git", "apply", "--reverse", "--check", str(patch)], cwd=source, capture_output=True)
        if applied.returncode:
            run(["git", "apply", "--check", str(patch)], source)
            run(["git", "apply", str(patch)], source)
    feed_lines = []
    for feed in lock["feeds"]:
        checkout(feed["url"], feed["commit"], source / "feeds" / feed["name"])
        feed_lines.append(f"src-git {feed['name']} {feed['url']}^{feed['commit']}\n")
    run(["python3", str(REPO / "scripts/prepare-extra-packages.py"), str(source),
         str(source.parent / "awg-recipes")], REPO)
    # Feed indexing (-i only) and package selection happen in the container.
    (source / "feeds.conf").write_text("".join(feed_lines))
    if (source / "files").exists():
        raise SystemExit("Refusing to merge an existing files/ overlay; inspect it first")
    shutil.copytree(REPO / "overlay", source / "files")
    for path in (source / "files").rglob("*"):
        if path.is_file() and any(part in path.parts for part in ("uci-defaults", "sbin", "hotplug.d", "libexec", "init.d")):
            path.chmod(0o755)
    config = source / ".config"
    if config.exists():
        raise SystemExit("Refusing to overwrite existing .config")
    shutil.copyfile(REPO / "config/minimal.config", config)
    print("Prepared pinned sources. Run feeds indexing/install and make defconfig in the container.")


if __name__ == "__main__":
    main()
