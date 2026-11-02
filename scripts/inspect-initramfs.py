#!/usr/bin/env python3
"""Inspect the uncompressed embedded newc archive in this build's RAM FIT."""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import stat


spec = importlib.util.spec_from_file_location("fit_inspector", Path(__file__).with_name("inspect-fit.py"))
fit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fit)


def newc(data, offset):
    files = {}
    start = offset
    while True:
        assert data[offset:offset + 6] == b"070701", "Not an uncompressed newc archive"
        values = [int(data[offset + 6 + 8 * i:offset + 14 + 8 * i], 16) for i in range(13)]
        _, mode, uid, gid, _, _, size, _, _, _, _, namesize, checksum = values
        assert uid == gid == checksum == 0
        assert 1 <= namesize <= 4096 and offset + 110 + namesize <= len(data)
        name_bytes = data[offset + 110:offset + 110 + namesize]
        assert name_bytes[-1:] == b"\0" and b"\0" not in name_bytes[:-1]
        name = name_bytes[:-1].decode()
        offset = (offset + 110 + namesize + 3) & ~3
        assert offset + size <= len(data)
        content = data[offset:offset + size]
        offset = (offset + size + 3) & ~3
        if name == "TRAILER!!!":
            assert size == 0
            return files, offset - start
        while name.startswith("./"):
            name = name[2:]
        assert not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts
        assert name not in files
        files[name] = (mode, content)


def inspect(image, root, deny=()):
    fit_report = fit.inspect(image, persistent=False)
    _, nodes = fit.fdt(image)
    config = nodes["/configurations/" + fit_report["default_config"]]
    props = nodes["/images/" + fit.string(config["kernel"])]
    assert fit.string(props["compression"]) == "gzip"
    raw = gzip.decompress(props["data"])
    candidates = []
    offset = 0
    while True:
        offset = raw.find(b"070701", offset)
        if offset < 0:
            break
        try:
            files, length = newc(raw, offset)
            if "init" in files and "etc/shadow" in files:
                candidates.append((offset, length, files))
                # Each later member also starts with the newc magic. Do not
                # mistake suffixes of the same archive for additional archives.
                offset += length
                continue
        except (AssertionError, ValueError, UnicodeDecodeError):
            pass
        offset += 6
    assert len(candidates) == 1, "Expected one complete embedded initramfs"
    offset, length, files = candidates[0]
    init_mode, init = files["init"]
    assert stat.S_ISREG(init_mode) and init_mode & 0o111
    for line in (b"export INITRAMFS=1", b"mount -t tmpfs tmpfs", b"switch_root $NEW_ROOT /sbin/init"):
        assert line in init, "Unexpected RAM boot init"
    checked = {}
    for name in ("etc/shadow", "etc/opkg.conf", "etc/uci-defaults/90-minimal-defaults",
                 "usr/sbin/re-cs-06-provision-macs", "lib/wifi/mac80211.sh"):
        mode, data = files[name]
        assert stat.S_ISREG(mode)
        source = root / name
        assert not source.is_symlink() and source.is_file()
        assert data == source.read_bytes(), f"RAM archive differs from inspected rootfs: {name}"
        checked[name] = hashlib.sha256(data).hexdigest()
    for name, (mode, data) in files.items():
        if not stat.S_ISREG(mode):
            continue
        assert not (name.startswith("etc/dropbear/") and "host_key" in name)
        assert name != "etc/uhttpd.key" and not name.startswith("etc/ssl/private/")
        assert not any(value and value.lower().encode() in data.lower() for value in deny), \
            f"Private literal in RAM archive: {name}"
    return {"embedded_cpio_offset": offset, "embedded_cpio_bytes": length,
            "embedded_entries_checked": len(files), "default_file_sha256": checked,
            "ram_init_exports_initramfs_and_switches_to_tmpfs": True,
            "private_literals_checked": bool(deny), "initramfs_offline_check_passed": True,
            "write_free_boot_proven": False, "hardware_boot_tested": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("root", type=Path, help="Already inspected local build rootfs")
    parser.add_argument("--deny-file", type=Path)
    args = parser.parse_args()
    deny = json.loads(args.deny_file.read_text()) if args.deny_file else []
    print(json.dumps(inspect(args.image.read_bytes(), args.root, deny), indent=2))
