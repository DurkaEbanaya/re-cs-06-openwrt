#!/usr/bin/env python3
"""Reject extra services or missing essentials after make defconfig."""
import argparse
import json
from pathlib import Path
import re

FORBIDDEN = re.compile(
    r"^(?:default-settings(?:-.*)?|autocore(?:-.*)?|automount|coremark|"
    r"(?:luci-app-)?(?:ssr-plus|passwall.*|nikki|openclash|mihomo|"
    r"adguardhome|daed.*|easytier|honk|lucky|openlist|qmodem.*|"
    r"vlmcsd|vsftpd|samba.*|qbittorrent.*|transmission.*|aria2.*|"
    r"autoreboot|turboacc|upnp|ddns|filetransfer|arpbind|accesscontrol|nlbwmon)|"
    r"(?:xray|v2ray|sing-box|shadowsocks).*|ttyd|miniupnpd.*|"
    r"ddns-scripts.*|luci-theme-(?!bootstrap$).*)$", re.I
)
REQUIRED = {
    "base-files", "busybox", "dropbear", "dnsmasq", "firewall4", "netifd",
    "luci", "luci-theme-bootstrap", "luci-ssl-openssl", "wpad-openssl",
    "kmod-qcom-ppe", "kmod-dsa-qca8k", "kmod-phy-qca83xx", "kmod-ath12k",
    "kmod-fs-ext4", "e2fsprogs", "opkg",
}


def check_version_name(text):
    value = re.search(r'^CONFIG_VERSION_DIST="([^"]+)"$', text, re.M)
    assert value and re.fullmatch(r"[A-Za-z0-9._-]+", value[1]), \
        "VERSION_DIST is used in unquoted image paths: use letters/digits/dot/underscore/hyphen only"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    text = args.config.read_text()
    check_version_name(text)
    packages = set(re.findall(r"^CONFIG_PACKAGE_([^=]+)=y$", text, re.M))
    bad = sorted(x for x in packages if FORBIDDEN.fullmatch(x))
    missing = sorted(REQUIRED - packages)
    assert not bad, f"Forbidden packages selected: {bad}"
    assert not missing, f"Required packages missing: {missing}"
    assert not packages.intersection({"ath12k-firmware-ipq5332-ddwrt",
                                     "ath12k-firmware-qcn9274-ddwrt", "ipq-wifi-jdcloud_re-cs-06"}), \
        "Public build must use separately downloaded radio firmware"
    for line in ("CONFIG_TARGET_qualcommbe_ipq53xx_DEVICE_jdcloud_re-cs-06=y",
                 "CONFIG_TARGET_ROOTFS_INITRAMFS=y", "CONFIG_TARGET_ROOTFS_SQUASHFS=y",
                 "CONFIG_SIGNED_PACKAGES=y", "CONFIG_LUCI_LANG_ru=y"):
        assert line in text.splitlines(), f"Missing setting: {line}"
    assert not re.search(r"^CONFIG_LUCI_LANG_zh[^=]*=y$", text, re.M)
    print(json.dumps({"selected_packages": len(packages), "forbidden": bad,
                      "missing": missing, "config_policy_valid": True}, indent=2))


if __name__ == "__main__":
    main()
