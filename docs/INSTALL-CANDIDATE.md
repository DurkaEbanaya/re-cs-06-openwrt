# Local persistent candidate r2

User authorized a controlled persistent installation after the guarded RAM
tests. The local `install-r2` variant adds PAS INIT v2, the tested independent
radio DT layout, account database permission fixes and generic hash-locked
radio files. It does not include the failing kexec experiment, private
calibration, device MACs or credentials. Wi-Fi and WAN remain disabled.

`0009` removes the two WSI graphs for RE-CS-06 only. `0010` replaces this
board's unconditional platform image check with the tar/format/size/geometry
gate in `overlay/lib/upgrade/re-cs-06.sh`. That helper supports the tested
23-partition geometry only: 7 MiB HLOS and 2 GiB rootfs. It stages tar member
contents into private temporary files without extracting untrusted paths,
writes rootfs then kernel with readback SHA256 comparison, and initializes
the new overlay boundary. It never changes GPT, ART or bootloader. This is
not cryptographic image authentication or a power-fail atomic A/B update.
FIT hashes are verified offline, and sysupgrade's metadata check still applies.

The stage2 error path waits instead of automatically rebooting and claiming
success. Preserved configuration uses the platform's existing
`emmc_copy_config` mechanism. First installation does not preserve QWRT's
network/settings because board IDs and interfaces differ. Future upgrades
must still be built from compatible pinned sources and inspected first.

The initial migration uses the already inspected installed U-Boot recovery
writer: a normal factory FIT/container splits at 7 MiB into named `0:HLOS`
and `rootfs` partitions. The script-mode marker used for prior RAM tests
must NOT be present at offset 0x5c of this installation image. Never upload
a normal initramfs as an install image. HTTP recovery is not transactional;
keep power stable and preserve the existing bootloader/recovery.

Before writing, the complete verified backup was copied to a separate
physical SSD and independently hash-checked. Private paths/logs stay local.
The built image and its embedded rootfs/FIT/DTB were inspected, including
enabled normal SDHCI, absent WSI graph, 52 matching generic radio files,
no private caldata/identity, account permissions and disabled kexec.

This document records preparation, not a claim of successful installation.
Persistent boot, overlay creation, settings persistence and normal sysupgrade
remain hardware acceptance gates. The radio firmware redistribution decision
is unchanged: complete local images are not automatically public assets.
