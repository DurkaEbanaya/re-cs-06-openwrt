# Publication and licensing

The build recipes, original scripts and patches are public. Their licenses
do not make all downloaded chipset firmware open source, and do not grant
additional redistribution rights to third-party binaries.

## Radio firmware review

The pinned tree packages `ath-firmware-ddwrt` from DD-WRT commit
`bd7c0abd4575446a514c5f109de3c317ca26819a` as
`LicenseRef-Qualcomm-Proprietary`. IPQ5332 files originate from the
`ath12k/IPQ5332/5332.wlanfw.eval/` directory; the board's PCI radio also
uses `ath12k/QCN9274/hw2.0/` files.

The repository's top-level `LICENSE.qca_firmware` permits binary
redistribution subject to conditions, but its README describes the older
ath10k firmware collection. A QCN9274 `Notice.txt` explicitly says that the
notice is not itself a license grant and that use is subject to a separate
Qualcomm agreement. Applicability of the older top-level grant to every
newer evaluation/ath12k file has **not been established**.

References at the exact downloaded revision:

- [Firmware package](https://github.com/coolsnowwolf/lede/blob/667a1afd89eb6955d29796f7979c1c77d999616c/package/firmware/ath-firmware-ddwrt/Makefile)
- [Top-level Qualcomm firmware license](https://github.com/mirror/dd-wrt/blob/bd7c0abd4575446a514c5f109de3c317ca26819a/src/router/firmwares/wireless/LICENSE.qca_firmware)
- [Firmware repository README](https://github.com/mirror/dd-wrt/blob/bd7c0abd4575446a514c5f109de3c317ca26819a/src/router/firmwares/wireless/README.md)
- [QCN9274 notice](https://github.com/mirror/dd-wrt/blob/bd7c0abd4575446a514c5f109de3c317ca26819a/src/router/firmwares/wireless/ath12k/QCN9274/hw1.0/Notice.txt)

Until that is resolved, full locally generated images containing those
files are not automatically rehosted as public GitHub release assets.
Hashes, structural test reports and source recipes can still be public.
This is a conservative publication decision, not a legal determination
that distribution is forbidden. A useful alternative is an explicitly
separate firmware-free build with no claim of working Wi-Fi.

## Source availability for binary releases

Before distributing GPL-covered binaries, provide the applicable complete
corresponding source, build/install scripts, patches and configuration in
the manner required by their licenses. Pinned upstream references help
reproduce the build, but are not described here as a complete archived
source distribution or a written source offer. A future public binary
release needs a separately reviewed source/notice bundle.

Package-signing private keys, SSH host keys, HTTPS private keys, device
calibration, factory blocks and backups are never release assets.
