# First build results — 2026-11-02

The complete rootless-container cross-build finished successfully, including
package indexes, image metadata and checksums. It produced three local,
device-generic experimental images. **None has been booted or installed on
a router. Successful compilation is not hardware acceptance.**

## Generated images

Common prefix:
`re-cs-06-minimal-lede-experimental-2026.11.02-qualcommbe-ipq53xx-jdcloud_re-cs-06-`

| Suffix | Bytes | Intended role, not installation approval |
| --- | ---: | --- |
| `initramfs-uImage.itb` | 30467276 | Candidate for a separately verified RAM boot |
| `squashfs-factory.bin` | 26875723 | Kernel + aligned rootfs + metadata container |
| `squashfs-sysupgrade.bin` | 26461009 | Persistent kernel/rootfs tar + metadata |

Persistent kernel FIT: **6857104 bytes**, leaving **482928 bytes** in the
existing 7340032-byte HLOS slot. Squashfs: 19534842 bytes. No GPT expansion
or bootloader replacement is part of this build.

The resolved configuration selects 212 package symbols; the installed
manifest contains 206 packages (virtual/dependency selections differ from
installed package entries). The package list is public in
[`reports/packages.json`](../reports/packages.json). This is a practical
router/LuCI build, not an absolute smallest possible firmware.

## Offline checks passed

- Source/config policy: no forbidden optional proxy, torrent, cloud,
  file-server or vendor-theme bundles. English/Russian LuCI with Bootstrap.
- All eight files listed by the generated `sha256sums` matched.
- FIT kernel and DTB CRC32/SHA1 hashes verified; kernel gzip decompressed to
  an ARM64 Linux Image; DTB identifies RE-CS-06 and preserves two legitimate
  SoC efuse consumers without a storage-backed MAC NVMEM dependency.
- Sysupgrade tar contains exactly CONTROL, kernel and root under the board
  directory. Root bytes match the independently extracted squashfs, with
  only expected zero alignment padding. Factory container uses the same
  kernel/rootfs. Board metadata was extracted using the build's `fwtool`.
- Extracted squashfs: 1467 regular files inspected; no embedded root password,
  SSH/HTTPS private host keys or known private device literals. Initial WAN,
  Wi-Fi, full-cone NAT and flow offloading are disabled by the image's
  first-boot configuration/generator. These are not runtime test results.
- Embedded RAM archive: 1851 entries parsed; `/init` exports `INITRAMFS=1`
  and switches to tmpfs; selected defaults match the extracted squashfs.
  A completely write-free boot is **not** proven.

Machine-readable results are in [`reports/`](../reports/). Artifact SHA256
values are in [`reports/artifacts.json`](../reports/artifacts.json). Local
build paths and private identity values are deliberately absent from those
reports. Fast tool tests also run in the public GitHub Actions workflow.

## Not established

Bootloader compatibility, RAM loading method, cold boot, Ethernet port
mapping and 2.5G negotiation, MAC stability, both radios/BDF/calibration,
DFS/MLO, forwarding performance and physical recovery have not been tested.
The active QWRT installation, GPT, ART, bootloader, passwords and network
settings have not been changed by this build.

Full binary images remain local while [radio firmware redistribution and
corresponding-source packaging](LICENSING.md) are unresolved. The public
release is a source/inspection-results milestone, **not a downloadable
validated firmware release**. Keep per-device calibration and provisioning
private even if later generic binary redistribution is approved.
