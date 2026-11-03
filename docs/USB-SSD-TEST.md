# USB storage acceptance — peripherals r5

The external RTL9210B USB bridge initially enumerated at 5000 Mbit/s but
provided no block disk: the minimal r4 image omitted USB-storage/UAS modules.
The source kernel had SCSI/disk support, but that alone was insufficient.
USB-storage and UAS are now selected in the seed and peripherals candidate.

Newly built modules required a different kernel package ABI. No forced
dependency override or incompatible module insertion was attempted. Instead
the checked r5 image was installed with fresh configuration backups on two
physical drives. Network/wireless settings and the original SSH host key
carried over automatically; kernel/root readback matched the image. Boot
firmware, ART, GPT head and stored boot environment remained unchanged.

After upgrade, the bridge bound to **UAS** on a **5 Gbit/s USB link**. It
reported 28131328 sectors of 512 bytes (14403239936 bytes, about 13.4 GiB).
This is the capacity reported by this attached device, not an assumption
about the owner's expected SSD capacity or the actual NAND geometry.

## Destructive scope authorized by owner

Only the first partition of the USB-backed disk was reformatted to ext4.
USB ancestry, UAS binding, exact disk/partition sizes and absence of mounts
were checked before formatting. The disk partition table and second
partition were not rewritten. Internal eMMC and workstation drives were
not test targets. Previous data on that first partition is not preserved.

## Measured test

A private test executable created one new 512 MiB regular file using
`O_DIRECT`, 4096-byte-aligned memory and 1 MiB blocks. It generated a
deterministic per-word mixed pattern, synchronized writes with `fsync`,
reopened using `O_DIRECT`, and verified every 64-bit word.

- Write: **123.27 MiB/s**, including pattern generation and fsync.
- Read: **196.41 MiB/s**, including full pattern verification.
- All 536870912 bytes verified.
- SHA256 before unmount and after remount matched.
- Offline read-only `e2fsck -fn` completed with exit status 0.

These are end-to-end filesystem/test-program results, not raw USB bus
bandwidth or a complete SSD benchmark. No whole-surface, power-loss,
long-duration endurance or discard/TRIM acceptance is claimed.

The test file and executable were removed, and the filesystem was cleanly
unmounted. No automount or file-sharing service was enabled. The formatted
first partition remains available for subsequent owner use.
