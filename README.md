# RE-CS-06 minimal OpenWrt-family build

Experimental, source-based build for **JDCloud RE-CS-06 / BE6500** with
Qualcomm IPQ5322/IPQ5332. This is **not an official OpenWrt release**.

**Status: local resources-r6 boots Linux 6.18.60 from eMMC with automatically
created ext4. Its checked upgrade retained settings and the original SSH key;
kernel/root readback passed. The earlier r4 TX/RX fixes yielded 2.346–2.348
Gbit/s RX and 1.961–2.034 Gbit/s TX, with zero retransmissions in four
30-second direct 2.5G runs. r5 includes the corrected RX scripts and USB
storage/UAS. Independent phone tests confirmed 5 GHz HE/802.11ax traffic;
an external UAS SSD passed direct-I/O verification and remount/fsck checks.
r6 adds ARMv8 CryptoAPI AES/GCM and fixes software-flowtable DSA ingress.
Routed IPv4 hardware NAT reached 2.19/2.31 Gbit/s with ~0.3% aggregate CPU;
PPE counters and HW_OFFLOAD confirmed the hardware path. This is not full
acceptance of IPv6, VPNs, EHT/MLO or broader upgrade/power-loss scenarios;
the current PHYs advertise no 6 GHz band.
Do not flash the older published images with the account-permissions defect.**

See [persistent installation results and follow-up fixes](docs/INSTALL-CANDIDATE.md).
Latest: [queuefix-r3 installation and hardware comparison](docs/QUEUEFIX-R3.md).
Current: [acceptance tracker](docs/KNOWN-ISSUES.md),
[r5 hardware report](reports/peripherals-r5-hardware.json),
[phone HE test](docs/PHONE-HE-TEST.md), [USB storage test](docs/USB-SSD-TEST.md)
and [acceleration implementation versus validation](docs/ACCELERATION.md).
Latest: [resource audit and r6 results](docs/RESOURCE-AUDIT.md).

## Goals

- Minimal router services, SSH and standard LuCI in English/Russian.
- No optional proxy/cloud/download/file-server bundles or vendor UI themes.
- Preserve the existing eMMC GPT, ART calibration and bootloader.
- Support an already-modified 23-partition layout without a `factory` partition.
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

Compilation is not hardware acceptance. In particular, all four Ethernet
ports, both radios, MAC fallback/provisioning, firmware compatibility and
recovery still need testing. Do not force this image through an older QWRT's
different board-ID check or assume an untested U-Boot recovery page works.

This public repository contains build recipes and tests, not private backups
or vendored chipset firmware. Generated binary redistribution additionally
requires review of the applicable third-party notices; source availability
does not by itself grant rights to redistribute every firmware blob.

The follow-up `external-radio` prerelease provides binary images without the
disputed radio files and a pinned, SHA256-verified downloader for those external
dependencies. Wi-Fi needs these files; this is not an all-in-one Wi-Fi image.
Earlier reports describe the original full local build, while
`reports/external-radio.json` describes the separately built public candidate.
