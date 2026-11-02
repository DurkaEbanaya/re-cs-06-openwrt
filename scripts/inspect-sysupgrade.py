#!/usr/bin/env python3
"""Validate a candidate sysupgrade tar locally; never calls sysupgrade."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile


spec = importlib.util.spec_from_file_location("fit_inspector", Path(__file__).with_name("inspect-fit.py"))
fit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fit)


def inspect(data, expected_rootfs):
    prefix = "sysupgrade-jdcloud_re-cs-06"
    expected = {prefix, prefix + "/CONTROL", prefix + "/kernel", prefix + "/root"}
    blobs = {}
    seen = set()
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        for member in archive:
            assert member.name in expected and member.name not in seen, "Unexpected/duplicate tar member"
            seen.add(member.name)
            assert member.uid == member.gid == 0
            if member.name == prefix:
                assert member.isdir()
                continue
            assert member.isfile() and member.size <= 256 * 1024 * 1024
            blobs[member.name.rsplit("/", 1)[1]] = archive.extractfile(member).read()
    assert seen == expected
    assert blobs["CONTROL"] == b"BOARD=jdcloud_re-cs-06\n"
    kernel = fit.inspect(blobs["kernel"])
    root = blobs["root"]
    assert root.startswith(b"hsqs") and root.startswith(expected_rootfs)
    # The image pipeline aligns squashfs/rootfs_data to 64 KiB. No old overlay
    # or private configuration is allowed to be appended to the public root.
    padding = root[len(expected_rootfs):]
    assert len(padding) <= 65536 and not padding.strip(b"\0")
    return {"tar_members_verified": len(seen), "persistent_kernel": kernel,
            "rootfs_bytes": len(root), "rootfs_padding_bytes": len(padding),
            "rootfs_sha256": hashlib.sha256(root).hexdigest(),
            "sysupgrade_offline_check_passed": True,
            "hardware_boot_tested": False, "old_qwrt_direct_upgrade_approved": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("rootfs", type=Path, help="Independently inspected build root.squashfs")
    args = parser.parse_args()
    print(json.dumps(inspect(args.image.read_bytes(), args.rootfs.read_bytes()), indent=2))
