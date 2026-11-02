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

## Actual persistent installation

The owner entered HTTP recovery and the inspected install-r2 factory
container was uploaded. U-Boot reported successful writes to HLOS (14336
sectors) and rootfs (37487 sectors), erasing the existing whole rootfs
partition first. Linux 6.18.60 booted from eMMC, SSH became available and
both independent radio PHYs registered with ART-derived calibration.

First boot exposed a separate minimal-build issue: fstools automatically
chose F2FS for the roughly 2 GiB overlay, but `mkfs.f2fs` was absent. The
system used a temporary RAM overlay. An ext4 filesystem was created only
at the verified squashfs-aligned offset within rootfs (not on the whole
disk or whole rootfs partition). After reboot it mounted read-write as the
persistent overlay. A newly created test file and SSH host key survived
another controlled reboot. The first copied temporary-overlay marker did
not survive initialization; persistence was only declared after this
second, successful test.

Patch `0011` changes automatic fstools selection to prefer the available
ext4 formatter if F2FS formatting tools are absent. An explicitly requested
command-line filesystem remains respected. This source fix is for future
builds; the currently installed r2 was repaired by manual ext4 initialization,
not by silently replacing its image or claiming the patch was installed.

The MAC provisioning helper also needed `set -u` removed: the actual OpenWrt
shell library intentionally reads unset optional variables. The corrected
helper is deployed locally and saves owner-specific wired addresses only
in UCI, never raw ART or a fabricated factory partition. The test fixture
now exercises an unset optional library variable.

Readback checks found APPSBL, ART, primary GPT and all stored boot environment
values identical to the backup. HLOS and rootfs intentionally changed; live
rootfs equality with the old QWRT backup is not claimed. Normal sysupgrade,
AP/client traffic, MLO and long-term stability remain acceptance gates.
The radio firmware redistribution decision is unchanged: complete local
images are not automatically public assets.
