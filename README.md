# RE-CS-06 minimal OpenWrt-family build

Experimental, source-based build for **JDCloud RE-CS-06 / BE6500** with
Qualcomm IPQ5322/IPQ5332. This is **not an official OpenWrt release**.

**Latest full local candidate: usb-clocks-r15, Linux 6.18.60.** The same full
image is installed on both inspected RE-CS-06 units: one with a modified
bootloader/2 GiB primary root and the other with its stock bootloader/122 MiB
primary root. Each retains its own persistent settings, identity and keys;
GPT, bootloader and calibration are not normalized or copied between units.
The [USB investigation](docs/USB-CLOCK-DIAGNOSIS.md) found an inherited
clock-state dependency in r14. Explicit board clock rates restored 5G/UAS
on the stock-loader unit, including an owner-confirmed kernel-only power
cycle and subsequent full-image upgrade/file checks. Post-upgrade HE service
and isolated hardware-NAT tests also completed; their nonzero TCP retries
remain visible in the report. This is not a complete USB hotplug/device/power
acceptance matrix or universal loss-free traffic claim.
The [TCP loss investigation](docs/TCP-LOSS-DIAGNOSIS.md) distinguishes the
corrected QCA8386 switch drops, software backlog/AQM congestion and residual
sender Tail Loss Probes. It does not promise zero TCP retries in all traffic.
The separately built public **r15-external** recipe omits
radio firmware/BDF blobs: see [release notes](docs/RELEASE-R15.md) and
[external dependencies](docs/EXTERNAL-RADIO.md). It is not the byte-identical
hardware-tested full image, and is not a universal stock installer.

**Download: [r15-external prerelease](https://github.com/DurkaEbanaya/re-cs-06-openwrt/releases/tag/experimental-2026.11.04-usb-clocks-r15-external)** —
images, corresponding source, inspection results and SHA256SUMS. Radio files
are external dependencies; read the release notes before installing.

First-device resources-r6 is conditionally complete for its tested scope.
Linux 6.18.60
boots from eMMC with persistent ext4 and checked upgrade/configuration
carryover. Hardware IPv4 NAT, IPv6 forwarding, PPPoE IPv4, tagged LAN VLAN
NAT, routed 5 GHz HE80 PCI-radio Direct Switch and ARMv8 CryptoAPI CE paths
have been exercised. Software-flowtable ingress and TX/RX queue fixes are
included. See the [acceptance matrix and second-device plan](docs/CONDITIONAL-COMPLETION.md).
The [second device's stock migration](docs/SECOND-DEVICE.md) exposed and
isolated Ethernet-reset/LDO and first-boot seed defects. The r9 candidate
boots with its existing stock U-Boot and restores private setup automatically;
see [stock installation boundaries](docs/STOCK-INSTALLATION.md). No bootloader
replacement or copied first-device calibration is required. One owner-performed
cold power start with UART disconnected also passed network/persistence checks.
The [PCIe investigation](docs/PCIE-RXERR.md) fixed a separate NAPI teardown
panic in r10 and localized cold RxErr to integrated-radio startup. r12
sequences PCI host initialization after AHB PHY registration, without AER
masking or reducing Gen3 x2. Its missing-helper 60-second kernel fallback
was tested. Two r11 diagnostic cold starts were clean; full r12 results and
the pending physical-cycle confirmation are recorded separately. The owner
accepted the physical ports. [Extended full-r14 validation](docs/FULL-R14-VALIDATION.md)
checked actual WAN NAT, WAN VLAN, PPPoE IPv4, routed IPv6 and both radio
roles; untested provider combinations and broader wireless acceptance remain
separate gates. Actual US-location 5 GHz EHT80 AP/STA with four spatial streams (NSS4) and measured
AP PPE/Direct Switch traffic is documented in the [EHT control](docs/US-EHT-TEST.md);
this is not 6 GHz, MLO, or arbitrary STA forwarding acceptance.

**По-русски: [как перейти со стока на нашу систему](docs/INSTALL-STOCK-RU.md)** —
пошаговая подготовка, доступ, бэкапы, первый вход и честные ограничения текущего
установочного процесса. Это пока не универсальный установщик «в один клик».

**[Что нового в r15](docs/RELEASE-R15.md)** ·
**[Стенд из двух роутеров, включая Wi-Fi 7](docs/TWO-ROUTER-LAB-RU.md)**

This is not universal hardware certification: broader EHT/MLO, provider WAN VLANs,
PPPoE IPv6, VPN throughput and power-loss safety remain outside acceptance.
The earlier unexplained Ethernet outage and remaining inter-capture-point
reordering are not claimed fixed. Current PHYs advertise no 6 GHz band.
WAN/radios and persistent flow offloading remain disabled after test cleanup;
owner provisioning is still required before ordinary use.
**Do not flash the older published images with the account-permissions defect.**

See [persistent installation results and follow-up fixes](docs/INSTALL-CANDIDATE.md).
Historical: [queuefix-r3 installation and hardware comparison](docs/QUEUEFIX-R3.md).
Current: [acceptance tracker](docs/KNOWN-ISSUES.md),
[r5 hardware report](reports/peripherals-r5-hardware.json),
[phone HE test](docs/PHONE-HE-TEST.md), [USB storage test](docs/USB-SSD-TEST.md)
and [acceleration implementation versus validation](docs/ACCELERATION.md).
Evidence: [resource audit and r6 results](docs/RESOURCE-AUDIT.md),
[protocol offload tests](docs/PROTOCOL-OFFLOAD-TESTS.md),
[receiver-loss controls](docs/RECEIVER-LOSS-CONTROLS.md).

## Goals

- Minimal router services, SSH and standard LuCI in English/Russian.
- No optional proxy/cloud/download/file-server bundles or vendor UI themes.
- Preserve the existing eMMC GPT, ART calibration and bootloader.
- Support the inspected stock 29-partition and modified 23-partition layouts,
  without treating their first-install or recovery procedures as interchangeable.
- Keep all per-device identity, keys and backups out of the public repository
  and out of any public firmware images.

The current source base is `coolsnowwolf/lede`, pinned to a full commit.
Its recently imported IPQ53xx support has not completed physical acceptance.
Compiling successfully does not establish working Ethernet, Wi-Fi or recovery.

## Safety and privacy

This repository does not contain and must never receive eMMC/ART/factory
dumps, stock configuration exports, private MAC/SN/CID, SSH keys, passwords
or recovery archives. Local work, private inputs and binary outputs live
outside version control. Publication uses an explicit file allowlist.

No flashing commands are part of the build procedure. Images require
independent inspection and a verified recovery/RAM-boot path first.
Hardware backup and a second physical copy remain prerequisites for writing.

## Build and review

- [Build instructions](docs/BUILD.md)
- [Adaptations and hardware acceptance gates](docs/ADAPTATION.md)
- [Firmware licensing and publication](docs/LICENSING.md)
- [External radio download workflow](docs/EXTERNAL-RADIO.md)
- [Recovery and USB preflight](docs/RECOVERY.md)
- [Pinned source/feed commits](sources.lock.json)
- [Minimal configuration](config/minimal.config)
- [Local tests](tests/test_tools.py): `python3 -m unittest discover -s tests -v`
- [Build and image inspection results](docs/RESULTS.md)

The build produces a persistent kernel/rootfs candidate and an initramfs FIT
for a separately verified RAM-boot method. No preconfigured private identity
is embedded. WAN and Wi-Fi stay disabled for isolated first setup; LAN is
`192.168.76.1/24`. Set a new root password and configure proper owner-specific
MACs, country and Wi-Fi encryption before connecting uplinks.

Compilation is not hardware acceptance. The documented first-device tests
do not replace checking a second unit's bootloader, geometry, calibration
and provisioning. Do not force an image through an older QWRT's different
board-ID check or assume a different U-Boot recovery page behaves identically.

This public repository contains build recipes and tests, not private backups
or vendored chipset firmware. Generated binary redistribution additionally
requires review of the applicable third-party notices; source availability
does not by itself grant rights to redistribute every firmware blob.

The current `r12-external` prerelease provides binary images without the
disputed radio files and a pinned, SHA256-verified downloader for those external
dependencies. Wi-Fi needs these files; this is not an all-in-one Wi-Fi image.
Earlier reports describe the original full local build, while
`reports/external-radio-r12.json` describes the current public candidate.
The November 2 releases remain explicitly marked **DO NOT FLASH** historical
prototypes; their binaries are not silently replaced under the same names.
