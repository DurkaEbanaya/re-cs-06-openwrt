#!/usr/bin/env python3
"""Download pinned original radio files to a NEW local directory; never install or reboot."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import urllib.request


def fetch(lock, output):
    records = json.loads(lock.read_text())["files"]
    for record in records:
        path = PurePosixPath(record["path"])
        assert str(path).startswith("lib/firmware/ath12k/") and ".." not in path.parts
        assert record["url"].startswith("https://raw.githubusercontent.com/")
    output.mkdir(parents=True, exist_ok=False)
    for record in records:
        with urllib.request.urlopen(record["url"], timeout=60) as response:
            data = response.read(64 * 1024 * 1024)
        assert hashlib.sha256(data).hexdigest() == record["sha256"], record["path"]
        target = output / record["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return {"downloaded_files": len(records), "all_sha256_verified": True,
            "installed_on_router": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New local directory, NOT a running router root")
    args = parser.parse_args()
    print(json.dumps(fetch(Path(__file__).resolve().parents[1] / "radio-files.lock.json", args.output), indent=2))
