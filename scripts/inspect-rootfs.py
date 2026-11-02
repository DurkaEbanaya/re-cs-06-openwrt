#!/usr/bin/env python3
"""Inspect a locally extracted image without executing its ARM binaries."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat


def inspect(root, deny=()):
    root = root.resolve()
    assert root.is_dir()
    for name in ("etc/shadow", "etc/passwd", "etc/uci-defaults/90-minimal-defaults",
                 "usr/sbin/re-cs-06-provision-macs", "etc/opkg.conf"):
        assert (root / name).is_file() and not (root / name).is_symlink(), name
    for name in ("etc/passwd", "etc/group"):
        path = root / name
        assert path.is_file() and not path.is_symlink()
        assert stat.S_IMODE(path.stat().st_mode) == 0o644, f"Account database must be readable by unprivileged services: {name}"
    assert stat.S_IMODE((root / "etc/shadow").stat().st_mode) == 0o600, "Shadow must remain private"
    shadow = (root / "etc/shadow").read_text()
    entries = [line.split(":") for line in shadow.splitlines() if line.startswith("root:")]
    assert len(entries) == 1 and entries[0][1] in ("", "!", "*", "!!"), "Embedded root password"
    assert "option check_signature" in (root / "etc/opkg.conf").read_text(), "Signature checking disabled"
    defaults = (root / "etc/uci-defaults/90-minimal-defaults").read_text()
    for setting in ("network.lan.ipaddr='192.168.76.1'", "network.wan.auto='0'",
                    "network.wan6.auto='0'", "firewall.@defaults[0].fullcone='0'",
                    "firewall.@defaults[0].fullcone6='0'",
                    "firewall.@defaults[0].flow_offloading_hw='0'"):
        assert setting in defaults, f"Missing initial default: {setting}"
    assert not (root / "etc/uci-defaults/zzz-default-settings").exists()
    blocked = []
    for pattern in ("etc/dropbear/*host_key*", "etc/ssh/ssh_host_*", "etc/uhttpd.key",
                    "etc/ssl/private/*", "root/.ssh/*", "etc/config/openclash", "etc/config/passwall*",
                    "etc/config/nikki", "etc/config/samba*", "etc/config/vsftpd"):
        blocked.extend(str(p.relative_to(root)) for p in root.glob(pattern) if p.is_file())
    assert not blocked, f"Unexpected keys or optional service configuration: {blocked}"
    wireless = root / "lib/wifi/mac80211.sh"
    assert wireless.is_file() and not wireless.is_symlink()
    generator = wireless.read_text()
    assert "set wireless.${section}.disabled='1'" in generator, "Wi-Fi not disabled by generator"
    assert "set wireless.${iface}.disabled='1'" in generator, "Wi-Fi interface not disabled by generator"
    assert 'country="00"' in generator, "Unexpected regulatory default"
    files, total = 0, 0
    digests = {}
    for path in sorted(root.rglob("*")):
        # Absolute image symlinks must never be followed into the build host.
        if path.is_symlink() or not path.is_file():
            continue
        data = path.read_bytes()
        assert not any(value and value.lower().encode() in data.lower() for value in deny), \
            f"Private device literal found in {path.relative_to(root)}"
        if path.parent == root / "etc/uci-defaults":
            assert not re.search(rb"(?:wget|curl)\s+https?://", data), "Remote first-boot script download"
        files += 1
        total += len(data)
        if path.relative_to(root).as_posix() in ("etc/shadow", "etc/opkg.conf",
                                                "etc/uci-defaults/90-minimal-defaults",
                                                "usr/sbin/re-cs-06-provision-macs"):
            digests[path.relative_to(root).as_posix()] = hashlib.sha256(data).hexdigest()
    return {"regular_files_checked": files, "regular_bytes_checked": total,
            "default_file_sha256": digests, "embedded_root_password": False,
            "embedded_host_private_keys": False, "private_literals_checked": bool(deny),
            "image_defaults_are_first_boot_instructions_not_runtime_test": True,
            "rootfs_offline_policy_passed": True, "hardware_boot_tested": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--deny-file", type=Path, help="Local-only JSON list; never copy into public output")
    args = parser.parse_args()
    deny = json.loads(args.deny_file.read_text()) if args.deny_file else []
    print(json.dumps(inspect(args.root, deny), indent=2))
