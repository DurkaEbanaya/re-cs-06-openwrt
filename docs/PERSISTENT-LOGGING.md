# Installed diagnostic logging and unused eMMC space

The owner requested persistent logs after an Ethernet outage left no prior
boot evidence. Logging is now configured on the existing writable ext4
overlay, without modifying the GPT, bootloader, calibration or system image.

## Current storage geometry

The inherited layout has 23 GPT partitions and a 2 GiB `rootfs` partition.
The eMMC user area is about 116.47 GiB, not 128 GiB. Approximately 114.42 GiB
after the existing partitions remains unallocated. This was retained during
migration to avoid altering service/bootloader partition geometry. It is
unused space, not an occupied hidden filesystem or a RAM limitation.

A separate data partition in the tail is the proposed way to use it,
without moving ART, the bootloader or `rootfs`. Such a GPT operation needs
explicit approval, a fresh geometry/CRC backup, independent verification,
formatting of only the new partition and a tested mount/preservation policy.
No partition has been added by the logging setup. The proposed partition
has not been proven to survive every installer/recovery path.

## Active logging settings

- `system.@system[0].log_file=/overlay/jd-logs/system.log`
- `log_size=8192` (KiB in the installed ubox implementation)
- `log_buffer_size=256` (separate RAM buffer, KiB)
- Log directory mode 0700, files created mode 0600.
- The installed file writer rotates to `system.log.old` after the size
  threshold, retaining about 16 MiB total plus one-message overhead.
- The installed writer calls `fsync` after file messages. This improves
  durability but increases eMMC writes; it cannot guarantee the last message
  survives a power failure, whole-system lockup or storage failure.

`scripts/jd-health-log.init` is an optional on-device procd service, not
silently enabled in generic images. It records boot ID, a startup dmesg
snapshot, and once-per-minute uptime/load, available memory, port carrier,
error/drop counters and temperatures. It does not reset a stuck device,
dump packet contents, publish identity or change network/offload settings.
Kernel and ordinary system messages are captured by the normal log service.

The file writer and health service were checked running, and test messages
and health snapshots appeared in the persistent file. The service's init
file and enable/stop symlinks are listed for sysupgrade preservation.
The worker is a separate executable (`/usr/libexec/jd-health-log`) rather
than a long-running rc.common action: sourcing procd in the worker retained
the service lock and initially blocked restart. That implementation was
replaced, the owned old worker terminated, and repeated service restarts
were checked successfully. The worker is also listed for preservation.

Actual
post-upgrade/reboot persistence of this newly added service is not yet
hardware-tested. Log contents themselves live outside `/overlay/upper` and
are **not** promised to survive a rootfs-formatting sysupgrade; copy them
privately to the PC before upgrades. A future separate data volume can
separate diagnostic history from the system overlay.

This is not ramoops: the earlier lack of a registered pstore backend remains.
Arbitrary physical memory reservations are unsafe on this board's secure
and radio memory map. Persistent file logs can show the last successful
activity, but may not capture a final panic or explain a total Ethernet hang.

Raw logs contain private network/authentication metadata. They remain local
and must not be attached to public issues without sanitization.
