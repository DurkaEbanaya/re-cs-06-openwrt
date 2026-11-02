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
