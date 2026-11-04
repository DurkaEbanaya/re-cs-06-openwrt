# Building without touching the router

Requirements: Linux x86_64, rootless Podman, Python 3, Git; roughly 100 GiB
free disk, 24–32 GiB RAM recommended. Keep this checkout separate from any
private router backup directory. Scripts never connect to a router.

```sh
podman build -t localhost/re-cs-06-builder:ubuntu24.04 -f Containerfile .
python3 scripts/prepare.py "$PWD/work/lede"
scripts/container-run "$PWD/work/lede" bash -lc \
  './scripts/feeds update -i && ./scripts/feeds install -a'
cp config/minimal.config work/lede/.config
scripts/container-run "$PWD/work/lede" make defconfig
python3 scripts/check-config.py work/lede/.config
scripts/container-run "$PWD/work/lede" make download -j8
scripts/container-run "$PWD/work/lede" make -j12
```

First build downloads and compiles a full cross-toolchain. It can take hours.
Do not automatically replace failures with `IGNORE_ERRORS` or skip required
packages. Diagnose a failed step using a serial `make -j1 V=s` invocation.
Feed revision checks are pinned; `feeds update -i` only indexes local feeds.
`prepare.py` refuses to overwrite a config or merge an unreviewed overlay.
To resume a prepared tree, rerun make rather than rerunning preparation.
`config/resolved.config` records the current public release configuration;
`minimal.config` is the smaller seed used to derive it.

Follow-up: `resolved.config` records the public `r15-external` build.
Original complete-build hashes remain in the historical first-build reports.
The public seed excludes the radio firmware/BDF packages and keeps ath12k;
see [external dependencies](EXTERNAL-RADIO.md) for full local reconstruction.

Use a moderate parallelism limit so the desktop remains usable. The container
is non-root and only the source tree is mounted into it: no SSH agent,
GitHub credentials, home directory, backups, router block devices or private
identity inputs are exposed. Image files and package-signing keys created
inside `work/` are not tracked in this repository.

## Outputs and limits

Expected output directory: `work/lede/bin/targets/qualcommbe/ipq53xx/`.
The initramfs FIT is for a separately verified RAM boot method, not eMMC.
The sysupgrade tar is a persistent-install candidate, **not validated for
direct use from an older QWRT with a different board identifier**. A
`factory.bin` filename means an image format, not a unique factory partition.

Persistent kernels must fit 7340032 bytes. Public images must contain no
private device identity, password hashes or SSH/HTTPS host keys. Keep root
password unset only for the isolated initial LAN setup, set a new password
before connecting uplinks; Wi-Fi and WAN are disabled by default.

Official OpenWrt package repositories are deliberately disabled because
their kernel ABI does not match this custom source build. Build extra
packages from the pinned tree; do not disable package-signature checking.

## Offline acceptance

`scripts/inspect-fit.py` checks FIT hashes, ARM64 kernel structure, board DTB,
SoC-only NVMEM dependencies and the persistent kernel's size limit. Use its
`--initramfs` flag only for a RAM image; that flag deliberately removes the
persistent storage limit.

After extracting a newly built squashfs into a fresh local directory,
`scripts/inspect-rootfs.py DIRECTORY` checks first-boot defaults, signature
verification, missing embedded passwords/host keys and optional local
private-literal exclusions. It does not run any image binaries and does not
claim runtime isolation or a comprehensive security audit. The private deny
list, if used, must remain local, outside this repository.

`scripts/inspect-initramfs.py IMAGE ROOT_DIRECTORY` independently parses the
embedded newc archive, checks the RAM `/init` and compares selected files
with the inspected rootfs. It does not assert that booting cannot write to
flash. Bootloader/kernel behavior and runtime mounts remain hardware gates.

`scripts/inspect-sysupgrade.py IMAGE ROOT_SQUASHFS` checks the expected tar
members, board CONTROL file, persistent FIT and exact rootfs bytes/padding.
Appended fwtool metadata is inspected separately using the build's `fwtool`;
neither check approves a direct upgrade from older QWRT.

The GitHub workflow runs fast offline tool/policy tests, not a complete
firmware cross-build and not hardware tests. Source audit checks both index
and working copies of allowlisted tracked files; it is not an audit of
arbitrary Git history or untracked release assets.

## Private first-boot configuration seed

Keep per-device configuration outside this repository and the mounted build
tree. `scripts/make-config-seed.py INPUT.tar OUTPUT.tgz` creates a new mode-0600
filename-free gzip archive with the exact `1f8b0800` signature expected by
fstools. It rejects absolute/traversing/duplicate paths and non-regular,
non-directory members. It does not generate passwords, provision identities
or install anything. Validate the private tar contents and permissions before
use. A gzip/tar roundtrip alone does not prove first-boot recognition or restore;
see [stock installation boundaries](STOCK-INSTALLATION.md).

The current full-local build identifies as
`experimental-2026.11.04-usb-clocks-r15`. The public seed/resolved config
selects `experimental-2026.11.04-usb-clocks-r15-external`, excludes the
three radio firmware/BDF packages and contains no local firmware overlay.
The r15 recipe uses patches 0001–0022, including board USB clock
initialization tested with the full local image on both units. The historical
r14 recipe uses patches 0001–0021; to reproduce those assets, use their
corresponding-source archive or pinned release commit, not current patches
with an old version label. Current builds require the public overlay. Do not mix an
old resolved configuration/source archive with a new binary's provenance.
Full local radio dependencies remain subject to the separate workflow and
licensing restrictions above. See [r15 notes](RELEASE-R15.md).

The binary release includes its patched source tree/feed snapshots, downloaded
source archives, exact configuration and recipe as `corresponding-source.tar.zst`.
`scripts/package-source.py` includes new files introduced by the public patches,
not only paths already tracked in upstream Git; unrelated untracked diagnostics
are not part of that archive. Extract into a new directory and build in the
documented container, without reapplying prepare.py to the already patched tree.
