# r15 release: deterministic USB clock initialization

Full local version: `experimental-2026.11.04-usb-clocks-r15`.
Public binary variant: `experimental-2026.11.04-usb-clocks-r15-external`.
Linux **6.18.60**, pinned LEDE-derived IPQ53xx port; not official OpenWrt.

## Change since r14

Patch `0022` assigns the RE-CS-06 USB controller's supported clock rates
before probing: master 200 MHz, mock UTMI 60 MHz, AUX 2 MHz and LFPS 25 MHz.
Previously the stock-loader unit inherited 24 MHz for the latter three,
while the modified-loader unit inherited working rates. The same bridge/SSD
therefore enumerated at USB2/usb-storage on one unit and USB3/UAS on the other.
The correction removes that initialization dependency without replacing a
bootloader, changing GPIOs/PHY tuning, adding a storage quirk or formatting
the disk. Different PCB revisions were not established by this observation.

All earlier r14 fixes remain, including the PAUSE reaction reserve,
configuration-preserving upgrades, PCI/AHB sequencing, common dummy-NAPI
allocation fix, Ethernet startup and checked persistent ext4 restoration.

## Hardware evidence: full local image

- The **same full r15 image** is installed on both inspected units, with
  separate identities, keys and settings. One has a modified bootloader and
  2 GiB primary root; the other retains its stock bootloader and 122 MiB root.
  Kernel/rootfs, protected partitions, GPT, configuration and environment
  checks passed. No partition normalization or calibration copying was needed.
- The second unit passed warm and owner-confirmed cold USB3 checks with an
  r15 kernel/r14 root, followed by a full-r15 upgrade and exclusive 64 MiB
  file write/fsync/unmount/remount/direct-read SHA256 verification. USB stayed
  at **5000 Mbit/s/UAS**; read-only filesystem checking passed.
- The first unit was independently checked on the full r15 before this
  release: installed kernel/rootfs hashes matched, the same bridge enumerated
  at **5000 Mbit/s/UAS**, two direct 256 MiB reads agreed, and read-only ext4
  checking passed. No USB reset, I/O error or kernel fault was recorded in
  that collected log; PCIe AER totals were zero. The disk was left unmounted.
  Reflashing an already verified r15 was unnecessary.
- Post-upgrade HE20/HE80 AP/STA, WPA2/WPA3, DHCP/DNS and IPv4/IPv6 checks
  passed. Hardware-NAT controls reached approximately 2.34 Gbit/s outward;
  reverse endpoint rates varied from about 1.47 to 2.03 Gbit/s. Retries and
  receiver-backlog limits are retained in the reports, not declared all fixed.

The full-r14 WAN VLAN, PPPoE IPv4, routed IPv6, management, NTP and crypto
matrix remains separately identified; it is not silently relabeled r15.
Earlier US-location 5 GHz EHT80/NSS4 tests are also separate: no 6 GHz or MLO
acceptance follows from them. This release does not establish all USB devices,
repeated hotplug, power delivery, whole-system cold-start combinations,
power-loss safety, VPN performance or long-term stability.

Evidence: [USB diagnosis and cable controls](USB-CLOCK-DIAGNOSIS.md),
[r15 report](../reports/usb-clocks-r15.json),
[extended r14 validation](FULL-R14-VALIDATION.md),
[TCP loss diagnosis](TCP-LOSS-DIAGNOSIS.md).

## Public external-radio images

Public **r15-external** is a separate build without Qualcomm radio
firmware/BDF payloads. Drivers and fixes are included, but it is **not a
standalone Wi-Fi image**. Full-local hardware tests are not a boot test of
these byte-different public images. Their FIT/rootfs/initramfs and source
inspection is offline; see the attached inspection and source-verification
records. Radio dependencies remain pinned by the
[external workflow](EXTERNAL-RADIO.md), subject to upstream terms.

Without AHB firmware, PCI readiness may use the tested 60-second kernel
deadline; that does not supply missing firmware. Do not assume live driver
unloading/reprobe is a safe dependency-installation method.

Assets include sysupgrade/factory images, an initramfs FIT, corresponding
sources and recipe, resolved configuration, package manifest, external-radio
downloader/lock, inspection records and SHA256SUMS. The full local image is
not a public asset.

## Installation boundaries

- Use sysupgrade only on the reviewed compatible installed-system path with
  verified per-device backups on a second physical disk. The inspected
  primary roots are 122 MiB and 2 GiB; unknown or booted-secondary layouts
  are rejected. Upgrades are not atomic A/B.
- `factory.bin` is **not permission to use the stock JDCloud updater**.
  Initramfs needs a separately verified RAM-boot method. See the
  [Russian stock migration guide](INSTALL-STOCK-RU.md); this is not a
  universal stock installer.
- Never substitute another unit's ART/factory/MAC/private keys. Public
  images contain no owner password, private host key or calibration.
- Fresh defaults use LAN `192.168.76.1`, with WAN/radios/persistent offload
  disabled. Configuration-preserving upgrades retain owner settings; verify
  credentials, identity and the actual installation country before use.
- Preserve package signature checking; arbitrary official binary feeds do
  not match this custom ABI. Older November 2 defective prototypes remain
  **DO NOT FLASH**. r12/r14 releases remain historical.
