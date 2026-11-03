# Second RE-CS-06: stock-device preflight

This unit is independent of the modified-layout first device. Its initial
inventory identifies RE-CS-06, JDCOS-4.5.3.r4530, Linux 5.4.213 and a
125057368064-byte eMMC user area (244252672 sectors of 512 bytes).
There are **29 stock GPT partitions**, not the 23-partition geometry
accepted by the existing upgrade helper. No first-device calibration,
identity or private keys have been copied to it.

## Local access and changes before backup

The stock UI advertised its initial administrator login, which worked.
The unit reported incomplete initialization. The owner authorized minimal
local setup; the exact stock completion API was inspected before setting a
unique administrator password. WAN setup, cloud binding, stock updates and
factory reset were not requested. Credentials remain private.

An authenticated console-enable request was tested locally rather than
executing third-party JavaScript. Launching `telnetd` alone did not open
the port. The reference two-step method, which requests a persistent
factory Telnet-enable flag and then starts the daemon, did open it.
The API returned inner `status:1` for both steps despite the observed
working root console. Thus neither transport success nor inner error is
sufficient proof of whether a command ran. The exact initial factory
Telnet value was not captured before this request; the backup is explicitly
**post-provisioning/access enablement**, not a pristine factory snapshot.

A temporary ordinary forwarding control was created and removed. A
subsequent read returned an empty forwarding list; deletion itself returned
inner `status:1`. No bootloader, firmware or GPT replacement was performed.
Telnet is an isolated-LAN migration transport, not the intended final
administration service. Do not expose it through an uplink.

## Recovery and bootloader findings

- Primary APPSBL contains an ELF32 ARM U-Boot image identifying itself as
  U-Boot 2016.01, built January 2024. Its default boot command is `bootipq`.
- The entire APPSBL_1 partition reads as zero. This means no second image
  was found there; it does not by itself prove corruption of the active one.
- The environment CRC matches. No trusted vendor APPSBL digest or UART
  capture is available, so active-code integrity is not fully established.
- Offline string inspection found no HTTP/web-recovery implementation
  resembling the first device's modified July 2024 U-Boot. Absence of
  strings is not a complete capability audit, but the first device's
  Reset/WebUI procedure must not be assumed applicable.
- Both bootconfig views select primary APPSBL and secondary HLOS/rootfs/
  WIFIFW. The running overlay loop device is backed by rootfs_1. Do not
  write one named kernel/root partition and assume it is the active pair.

The owner's report of slow startup and failed recovery entry remains an
observation, **not a proven damaged bootloader**. No recovery entry or
flashing experiment has been performed on this second device.

## GPT and storage findings

The kernel reported an invalid alternate GPT and used the primary.
Offline inspection of captured bytes confirms:

- Primary GPT header CRC and partition-entry CRC are correct.
- It declares alternate LBA 241663999 and last usable LBA 241663966,
  short of the actual 244252672-sector device end.
- No GPT header signature exists at either the declared alternate location
  or the physical last sector in the captured ranges.

This is a real partition-table redundancy problem, not evidence that U-Boot
code is corrupted. No automatic GPT repair or `fdisk` write was performed.
The actual layout and both tail locations have been preserved before any
future decision about repair or migration.

The card reports model SCA128, lifetime estimates `0x01 0x02` and PRE_EOL
`0x01` (normal reserve state). These coarse counters are not a full media
test. The saved boot log also shows ext4 overlay recovery with 12 orphan
inodes removed after an unclean shutdown and substantial radio cold-boot
initialization. These do not establish the complete cause of the owner's
startup delay or any delay before Linux started.

## Backups and installation gate

Completed first: raw partitions 1–25, including this unit's ART, LICENSE,
factory, both APPSBL slots, environment, early boot stages and both stock
kernel/rootfs slots; both 4 MiB hardware boot areas; primary GPT head,
physical tail and the declared alternate-GPT range. Every transfer is
hashed over the same source stream and independently rehashed offline.
Private persistent-file and runtime/device-tree archives were also captured.

A critical archive was copied to a separate physical SSD and independently
SHA256-verified. Neither archive nor private identity/diagnostic contents
are public release assets. A full-disk read is a separate operation;
completion is not implied by the critical backup's success. Live mounted
filesystems are not an atomic filesystem snapshot even when their captured
byte stream has verified transport integrity.

**Installation remains gated.** The current 23-partition upgrade helper is
not a stock installer. A compatible boot path, active-slot policy, partition
capacity and recovery plan must be established before writes. Do not clone
the first device's GPT, bootloader, factory block or ART as a shortcut.
