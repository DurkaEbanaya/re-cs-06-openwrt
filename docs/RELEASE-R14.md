# r14 release: switch loss and upgrade configuration fixes

Full local version: `experimental-2026.11.04-loss-fixes-r14`.
Public binary variant: `experimental-2026.11.04-loss-fixes-r14-external`.
Linux **6.18.60**, pinned LEDE-derived IPQ53xx port; not official OpenWrt.

## Changes since r12

- **QCA8386 PAUSE reaction reserve:** patch `0021` sets the MHT reaction
  count to 60, matching Qualcomm SSDK, instead of the inherited 14. It
  preserves unrelated queue-manager bits and propagates register errors.
  Reversible A/B/A tests localized the original wired loss; subsequent
  installed-image tests showed no growth of the earlier LAN `Filtered`
  drops. This does not disable PAUSE/WRED or promise zero TCP retries.
- **Preserve restored owner settings:** `90-minimal-defaults` recognizes a
  checked restored archive containing `etc/config/network` and no longer
  resets the owner's LAN address on upgrade. Fresh installation/access-only
  seeds retain conservative defaults. Real full-image upgrades retained
  each unit's own configuration, password, SSH keys and management address.
- Includes r12's PCI/AHB startup sequence, r10's common dummy-NAPI lifetime
  correction, earlier stock-loader switch reference/LDO startup fixes,
  checked ext4/configuration restore, queue/RPS/flowtable changes and other
  accumulated adaptations. See [r12 notes](RELEASE-R12.md) for history.

## What was tested

Both routers run the same **full local r14**, with separate identities and
keys. Firmware/protected-partition/GPT readbacks and configuration checks
passed. Both radio PHYs, PCIe Gen3 x2, boot counter zero and zero AER totals
were verified; these are observations, not universal power-loss/recovery
acceptance.

Four serialized 30-second wired endpoint runs measured approximately
2.346 Gbit/s PC→router, and 1.975 Gbit/s router2→PC. TCP retries were 0 to
router1, 4/9 to router2, and 0 in reverse; no `Filtered` or softnet-drop
growth. The remaining retries were not freshly stack-traced in these runs.

Actual **US-location 5 GHz EHT80/NSS4** AP/STA tests used two streams for
25 seconds. Hardware mode measured 1.284/1.644 Gbit/s with zero TCP retries
and AP HW_OFFLOAD/PPE/Direct Switch evidence. Software mode measured
1.338/0.823 Gbit/s with 0/6 retries; the reverse retries matched six AP
fq_codel congestion drops, with no trace overruns. These controls used a
**temporary** backlog of 16384, not a new firmware default. Separate ECN
controls showed congestion marks replacing eligible drops; ECN cannot be
forced on arbitrary clients. A zero TCP count is not zero Wi-Fi MAC retries.

Neither PHY exposed 6 GHz. This is not Wi-Fi 6E, MLO, arbitrary STA
forwarding, long-term wireless stability or all-port/provider acceptance.
The US selection followed the owner's physical-location confirmation;
cleanup restored requested RU with radios disabled. Before enabling radio,
select the country matching the actual installation location.

Evidence: [TCP diagnosis](TCP-LOSS-DIAGNOSIS.md), [US EHT test](US-EHT-TEST.md),
[r14 recheck report](../reports/r14-recheck.json),
[r14 corrections report](../reports/loss-fixes-r14.json).

## Public external-radio variant

Public **r14-external** is a separate build without Qualcomm radio
firmware/BDF payloads. It contains the drivers, fixes and readiness service,
but **is not a standalone Wi-Fi image**. Its image/source inspection is
offline; do not describe the installed full-local tests as a hardware boot
test of these byte-different public images. Use the pinned
[external dependency workflow](EXTERNAL-RADIO.md) under applicable upstream
terms. The full local image is not included in this release.

Without AHB firmware, the readiness signal may never arrive; the tested
60-second kernel deadline permits PCI host probing but cannot supply missing
firmware. External dependency installation/reprobe still has its own
hardware-validation boundary. Do not assume live module unloading is safe.

Assets include persistent sysupgrade and factory images, an initramfs FIT,
corresponding sources and recipe, resolved configuration/package manifest,
inspection results, pinned external-radio downloader/lock and SHA256SUMS.

## Installation and safety

- Use **sysupgrade** only on the reviewed compatible installed-system path
  with verified per-device backups and a second physical copy. Inspected
  primary root sizes are stock 122 MiB and modified 2 GiB. Secondary-root
  execution/unknown geometry is rejected. Upgrades are not atomic A/B.
- `factory.bin` is **not** permission to feed it to the stock JDCloud
  updater; initramfs requires a separately verified RAM-boot method. This
  release is not a universal stock installer. See the
  [Russian stock migration guide](INSTALL-STOCK-RU.md).
- Never substitute another device's ART/factory/MAC/private keys. Keep
  calibration, credentials and recovery archives private. The public images
  embed no owner password, private host key or device calibration.
- Fresh defaults keep WAN/radios and persistent offloading disabled, with
  LAN `192.168.76.1`. A configuration-preserving upgrade keeps owner settings;
  inspect those settings before connecting an uplink.
- Keep signature verification enabled; these custom source/ABI builds are
  not compatible with arbitrary official binary feeds. The older November 2
  account-permission-defective prototypes remain **DO NOT FLASH**.
