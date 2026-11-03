# Stock-layout installation boundaries

The tested stock unit has January 2024 U-Boot, 29 GPT partitions, 7 MiB HLOS
slots and 122 MiB rootfs slots. Its existing loader can boot this ARM64 FIT;
replacing U-Boot or cloning a modified 23-partition GPT is not a prerequisite.
See [the actual migration and failures](SECOND-DEVICE.md). This document is
not a one-command installer for unknown firmware, geometry or boot policy.

## Why older local builds failed on this unit

1. Ethernet initialization relied on inherited switch state. Enable the
   switch reference before external reset and both UNIPHY LDO-ready outputs
   at `0x7a00610` / `0x7a10610` before reset. Patches 0016 and 0017 implement
   the ordering without skipping clock or switch-ID checks.
2. A configuration seed with gzip FNAME was valid gzip/tar, but fstools
   recognizes only header `1f8b0800`. The password, key and success hook were
   silently not restored. Use `scripts/make-config-seed.py` on a private
   uncompressed tar, not `tarfile.open(filename, 'w:gz')`.
3. Stock U-Boot counts boot attempts. The board-scoped public success hook
   clears its expected nonzero counter after userspace initialization,
   preserving stock successful-boot behavior. It never switches OS slots.
   This is not a comprehensive health check or a recovery guarantee.

UART was used to diagnose these defects. A corrected configuration seed must
provide network administration on its own; no secret is embedded in the
generic firmware. Router UART is 1.8 V if recovery diagnosis is necessary.

## First migration from stock

- Keep WAN disconnected and use isolated Ethernet. If host Wi-Fi provides
  internet, validate both the source-specific router route and the normal
  internet route after each carrier drop; an IP address alone is insufficient.
- Obtain authorized local shell access for the exact stock version. Record
  actual model, firmware, boot selections, geometry and eMMC health. The
  authenticated access method tested on JDCOS 4.5.3.r4530 can execute despite
  returning inner API `status:1`; do not infer execution from status alone.
- Capture and verify this unit's GPT, boot areas, ART, factory, LICENSE,
  bootloader, environment, bootconfig and OS partitions. Keep a verified
  second physical copy before writes. Live full-disk reads are not atomic
  filesystem snapshots. Never substitute another unit's private partitions.
- Validate both GPT headers and entry arrays. Repair missing alternate GPT
  only as a separate reviewed, backed-up operation; preserve every entry,
  GUID and boundary. A migration does not normally require repartitioning.
- Inspect the candidate FIT and squashfs independently. Kernel must fit
  7340032 bytes, root must be 64 KiB aligned and leave overlay space. Verify
  the actual FIT configuration and loader boot support, not just file sizes.
- Build a private seed containing a unique root credential, an administration
  public key and this unit's validated wired MAC provisioning. Keep private
  keys and passwords outside the source/build tree. Use restrictive modes
  and the filename-free seed encoder; inspect its members and header.
- Determine the **inactive** HLOS/rootfs pair from actual runtime boot policy.
  Write and readback-verify that pair and the seed at the aligned future
  overlay boundary. Keep the active stock pair intact. Activate only after
  both image and seed readbacks pass, preserving all unrelated selectors.
  Bootconfig format/age and its runtime-versus-disk differences must be
  reviewed for the actual loader; do not blindly copy this unit's bytes.
- One controlled reboot is followed by network, persistence and hardware
  acceptance. Stop if unreachable; do not repeatedly cycle power or assume
  a Reset/HTTP recovery implementation exists in the stock bootloader.

The recorded migration used a one-device, separately guarded tool. It is not
published as a universally safe stock installer. In particular, a factory
image filename does not make the stock vendor updater compatible.

## Subsequent upgrades from this custom primary OS

The r9 helper accepts only named primary HLOS/rootfs with exact HLOS size
14336 sectors and root size **249856 or 4194304 sectors**. The running root
PARTUUID must match that primary root; a stock/secondary boot is rejected.
At least 16 MiB is reserved for overlay. Unknown geometry is rejected.

After local image inspection, use the normal image-test path first. A
private configuration archive may be supplied with `sysupgrade -f`; the
stage2 helper rejects an incompatible gzip header before any block writes.
Normal retained settings use the ordinary generated backup. Do not use
`--force` to bypass a board, geometry or format failure.

The helper writes rootfs, initializes its overlay boundary, writes kernel and
places the staged backup, with readback hashes. It never writes GPT,
bootconfig, APPSBL, ART or factory. This is **not atomic A/B upgrading**;
power loss during writes can still require recovery.

## Required acceptance

Confirm build/kernel and correct root PARTUUID; ext4 overlay; the seed's
password/key and unique marker; own wired MACs; zero stock boot counter;
disabled WAN/radios until provisioned; preserved GPT/bootloader/calibration;
exact installed image readbacks; network-only reboots with unchanged host
keys and persistent markers. Physical cold start and all-port/forwarding
tests remain distinct from a successful warm boot. Full local images also
retain the [radio-firmware redistribution restrictions](LICENSING.md).
