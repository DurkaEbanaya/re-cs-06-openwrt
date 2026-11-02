#!/usr/bin/env python3
"""Prepare pinned sources and public-only overlay; never reads device backups."""
import argparse
import json
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


def main():
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
    # Feed indexing (-i only) and package selection happen in the container.
    (source / "feeds.conf").write_text("".join(feed_lines))
    if (source / "files").exists():
        raise SystemExit("Refusing to merge an existing files/ overlay; inspect it first")
    shutil.copytree(REPO / "overlay", source / "files")
    for path in (source / "files").rglob("*"):
        if path.is_file() and ("uci-defaults" in path.parts or "sbin" in path.parts):
            path.chmod(0o755)
    config = source / ".config"
    if config.exists():
        raise SystemExit("Refusing to overwrite existing .config")
    shutil.copyfile(REPO / "config/minimal.config", config)
    print("Prepared pinned sources. Run feeds indexing/install and make defconfig in the container.")


if __name__ == "__main__":
    main()
