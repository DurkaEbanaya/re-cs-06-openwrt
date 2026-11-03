# Second RE-CS-06: stock-device preflight and migration

This unit is independent of the modified-layout first device. Its initial
inventory identifies RE-CS-06, JDCOS-4.5.3.r4530, Linux 5.4.213 and a
125057368064-byte eMMC user area (244252672 sectors of 512 bytes).
There are **29 stock GPT partitions**, rather than the 23-partition geometry
accepted by the original upgrade helper. No first-device calibration,
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
inner `status:1`. No bootloader, firmware or GPT replacement was performed
during this access-enablement stage; the later authorized migration is below.
Telnet is an isolated-LAN migration transport, not the intended final
administration service. Do not expose it through an uplink.

## Recovery and bootloader findings

- Primary APPSBL contains an ELF32 ARM U-Boot image identifying itself as
  U-Boot 2016.01, built January 2024. Its default boot command is `bootipq`.
- The entire APPSBL_1 partition reads as zero. This means no second image
  was found there; it does not by itself prove corruption of the active one.
- The environment CRC matches. No trusted vendor APPSBL digest is available,
  so active-code integrity is not fully established. Later UART output does
  establish that this loader verifies the FIT and enters the custom kernel.
- Offline string inspection found no HTTP/web-recovery implementation
  resembling the first device's modified July 2024 U-Boot. Absence of
  strings is not a complete capability audit, but the first device's
  Reset/WebUI procedure must not be assumed applicable.
- At initial inventory, both bootconfig views selected primary APPSBL and
  secondary HLOS/rootfs/WIFIFW. The stock overlay loop device was backed by rootfs_1. Do not
  write one named kernel/root partition and assume it is the active pair.

The owner's report of slow startup and failed recovery entry remains an
observation, **not a proven damaged bootloader**. No additional recovery-entry
experiment was performed during this migration. The
later migration keeps its existing bootloader rather than assuming damage.

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
are public release assets. The subsequent full-disk read captured all
125057368064 bytes; the same source-stream hash matched at the receiver.
Full offline decompression and verification of all 35 backup entries passed,
and the compressed full image was independently SHA256-verified on a second
physical SSD before any GPT or OS write. Live mounted
filesystems are not an atomic filesystem snapshot even when their captured
byte stream has verified transport integrity.

The original 23-partition upgrade helper was **not a stock installer**. Its
2 GiB root-partition gate rejected this unit's 122 MiB root slots.
The later r9 candidate adds explicit 122 MiB support for an already booted
custom primary OS, not stock JDCloud's upgrade API. Do not clone the first device's GPT,
bootloader, factory block or ART as a shortcut.

## Authorized GPT repair and inactive-slot installation

After verified backups on two physical devices, the owner authorized GPT
repair and installation of the same resources-r6, accepting a first boot
without UART connected and UART diagnosis if it fails. This is a per-device
migration record, **not a generic flashing recipe**.

- Reconstructed the alternate GPT array/header at the real device end,
  updated the primary header's alternate pointer and the protective MBR's
  device length. Wrote backup first, then primary header, then protective MBR;
  every planned range passed exact readback. All 29 partition entries, GUIDs,
  boundaries and the existing last-usable-LBA policy remain unchanged.
- Wrote the unchanged **experimental-2026.11.03-resources-r6** kernel FIT
  (6856796 bytes) to inactive HLOS and squashfs (19267584 bytes) to inactive
  rootfs, within their 7 MiB / 122 MiB capacities. Verified payload hashes
  from the device. Existing active HLOS_1/rootfs_1 were not written.
- Supplied a local-only first-boot seed with this unit's wired identity,
  unique root credential and a new administration key. No first-unit keys,
  passwords, calibration or configuration were reused; public firmware
  payloads are unchanged. Secrets and device-specific scripts stay private.
- Stock U-Boot maintains `jd_failsafe_counter`; a successful stock boot clears
  it. A guarded local boot hook provides the same success-counter clearing
  on this unit. Disassembly suggests repeated unacknowledged attempts select
  the other OS pair; this is **not a tested recovery guarantee**.
- Activated only BOOTCONFIG0, with higher age and primary HLOS/rootfs selected,
  **after** both payload readbacks passed. BOOTCONFIG1, APPSBL/APPSBL_1,
  ART, factory, LICENSE and environment hashes were unchanged at installation.
  The success-counter hook may subsequently update the environment as intended.

One preflight attempt stopped before all writes because the stock interactive
console truncated a long command. The corrected transport stages bounded
chunks in RAM, verifies the full command SHA256 and executes it only after
verification. The complete gated repair/install then passed without a reboot
inside the installer. Firmware boot and hardware acceptance are separate gates.

An initial send-only reboot request did not actually restart the stock system:
its boot ID/runtime selections and uptime remained from the original boot,
while the on-disk activation was present. A subsequent request was kept open
until the stock shell acknowledged command execution. Boot observation is a
separate gate, not proof furnished by either request alone.

Do not equate successful flash readback with a successful boot,
ext4 persistence, radio operation or acceleration acceptance. Do not repeatedly
power-cycle an unreachable unit or overwrite its bootloader as a diagnostic.

## UART follow-up: kernel boots, Ethernet acceptance failed

After the acknowledged warm reboot, Ethernet carrier did not return within
the observation window. One owner-performed cold power cycle also did not
restore carrier. The owner then connected UART; a captured cold boot shows:

- Existing January 2024 U-Boot reads the primary HLOS slot, verifies both
  FIT subimages, decompresses the kernel and enters AArch64 through the monitor.
- Linux 6.18.60 starts all four CPUs, enumerates all 29 eMMC partitions and
  mounts primary rootfs (`179:23`) as squashfs. No invalid-alternate-GPT warning
  appears in this captured boot; exact post-boot GPT verification is still pending.
- An ext4 overlay mounts, and procd reaches its `init` stage. This is not yet
  an authenticated network shell, a persistence-reboot acceptance or a complete service test.
- `nss_cc_switch_core_clk` remains off and fails critical-clock registration
  with `-EBUSY`; QCA8K reads switch ID `ff` instead of `17`. All four QCA8084
  PHY probes later remain deferred because package clock `apb_bridge` is not ready.
  These are concrete Ethernet initialization failures consistent with no carrier,
  not evidence that replacing U-Boot is necessary. Their underlying cause remains
  under investigation, including initialization differences from the first unit.
- Radio firmware initialization proceeds; the PCI radio registers Direct Switch
  rings. This does not establish working wireless traffic or acceleration.

The captured output has no kernel panic/Oops and continues through about 20 seconds.
CR and CR/LF sent through the adapter produced no console response. Router-to-PC
UART reception works; the PC-to-router path and console responsiveness are not
established. Do not infer a system-wide hang or a bad solder joint from that alone.
The second unit is **not accepted as operational**. Bootloader replacement
is not a proposed remedy for this Ethernet-driver failure.

### UART voltage and transmit-path follow-up

The owner confirms the router UART is **1.8 V**, not 3.3 V. Never directly
drive its RX from a 3.3 V adapter TX; VCC must remain disconnected. A suitable
level interface is required. The earlier assistant advice calling this a
3.3 V router UART was incorrect.

After the owner added a TX voltage divider, the capture showed a real
`root@re-cs-06:/#` prompt and an ash error response. This establishes a live
userspace shell at that observation, not a reliable command channel: transmitted
text was received/echoed largely as repeated `0xEF` bytes, including on a slow
short probe. Further command transmission was stopped pending electrical-path
checks. No successful diagnostic-command capture or Ethernet repair is claimed.

### Stock fallback and kernel-only reference-clock experiment

After later owner-performed power/reconnection actions, the stock secondary
OS became reachable again. Its network console confirms secondary rootfs
and a cleared success counter. Both on-disk bootconfig copies now select the
stock pair. This is consistent with fallback, but the precise transition was
not captured and is not proof of a universally reliable recovery procedure.
Readback still matches the installed custom kernel/rootfs and all repaired
GPT ranges. These findings separate a working stock system from the custom
kernel's Ethernet initialization failure.

The CP2102 passed a direct adapter-only loopback test. Under stock Linux,
an explicit router UART transmit marker reached the PC exactly, whereas
PC-to-router CR/LF did not increment the router UART receive counter. That
narrows the UART problem to the inbound path or its configuration; it is
not an Ethernet/root-filesystem diagnosis. No state-changing UART command
is used while that direction remains unreliable.

The owner requested continuing software diagnosis without first fixing UART.
Source inspection found that the MDIO parent pulses the external switch
reset before the child NSSCC driver enables its reference clock, despite the
child's documented reference-before-reset requirement. Patch 0016 adds an
optional managed `switch_ref` acquisition **before GPIO acquisition** and
opts in only RE-CS-06 with its existing 50 MHz CMN PLL output. Probe errors
are propagated, and the clock remains acquired for the MDIO device lifetime.
This is a **candidate hypothesis**, not yet an established root cause or fix;
inherited MDIO rates, register state and hardware differences remain relevant.

The test plan changes only the custom kernel FIT and then BOOTCONFIG0 after
readback. The existing resources-r6 rootfs and its private persistent overlay
are retained, as are the complete active stock OS pair and current stock
BOOTCONFIG1. No bootloader, calibration, GPT or radio-firmware replacement
is part of this experiment. Kernel/rootfs ABI and payload checks precede any
write, and a successful network boot remains the acceptance gate.

### Live isolation: missing UNIPHY LDO-ready outputs

After the owner repaired the inbound UART wiring, exact command/response
testing and a Linux shell inventory succeeded. This supersedes the earlier
unreliable-transmit observations; the 1.8 V warning remains in force.

The reference-clock-only r7 candidate was insufficient: a warm observation
progressed further but timed out in PHY-package initialization, and a subsequent
start again returned all ones on MDIO. The common PLL registers matched stock.
Changing the inherited MDC divider alone and repeating external reset did not
restore access. A live parent-driver unbind/rebind experiment also exposed an
unsafe clock-registration reprobe path and caused an Oops/restart; that is not
an installation or recovery technique and is not used as an Ethernet workaround.

A small RAM-only diagnostic then isolated two missing **UNIPHY LDO-ready**
outputs: bit 0 at `0x7a00610` and `0x7a10610`. Both read `0x31c` before
enable and `0x31d` afterward. After enabling them before external reset,
the same MDIO bus read the correct switch register value `0x1700` (ID `0x17`)
instead of `0xffffffff`. This directly establishes a missing initialization
dependency; it does not by itself establish complete working Ethernet.

Patch 0017 supplies both resources on RE-CS-06 and initializes all optional
LDO-ready words before the existing external reset. Mapping is non-exclusive
because those words overlap the PCS windows. Clock-status checks are retained;
there is no hardcoded successful switch ID or ignored timeout. The r8 kernel
candidate includes this change; full port, traffic and repeated-boot acceptance
remain required. The custom rootfs and active stock pair are not overwritten
by the kernel-only isolation experiment.

### Independent first-boot provisioning defect

Offline inspection of the first custom overlay showed that the prepared
password, SSH authorized key and boot-counter hook had **not** been restored.
Readback of the compressed seed had passed, but the seed's gzip header was
`1f8b0808`: Python's filename-bearing gzip output sets the FNAME flag.
The installed fstools identifies gzip by exactly `1f8b0800`, including flags,
and therefore silently formatted a fresh overlay instead of restoring the seed.
Tar/gzip roundtrip tests alone did not exercise that recognition boundary.

`scripts/make-config-seed.py` creates filename-free gzip and validates the
archive member paths. Regression tests cover the exact fstools header and
the rejected filename-bearing case. The checked upgrade helper now rejects
an incompatible seed before any write. The existing private seed is retained
as evidence; a corrected one preserves its uncompressed tar bytes exactly.
The authorized unit's password/key and guarded boot-counter hook were restored
through the now-working UART for continued diagnosis, with counter zero
verified. That manual restoration is **not** acceptance of unattended setup.
A clean first-boot restore and subsequent SSH-only reboots must still pass
before claiming installation without mandatory UART.

### r8 network result and r9 installation candidate

The r8 kernel with both LDO-ready resources booted with the existing January
2024 loader. QCA8084 PCS initialization succeeded, all four external PHYs
registered, and the connected LAN port negotiated 2.5 Gbit/s full duplex.
SSH authentication with this unit's administration key succeeded. The earlier
switch-ID and critical-clock errors were absent. Exact repaired GPT ranges,
kernel readback, APPSBL/APPSBL_1, ART, LICENSE, factory and the preserved stock
kernel passed post-boot checks; the stock boot counter was zero.
This is one successful warm boot, not a cold-start or all-port traffic verdict.
The rootfs release still identified r6 because r8 was a kernel-only experiment.

The full r9 candidate combines the Ethernet changes with public, board-scoped
boot-counter handling and upgrade checks for exactly 7 MiB HLOS paired with
either 2 GiB or 122 MiB rootfs. At least 16 MiB remains for overlay. The
running root PARTUUID must match the named primary rootfs; secondary or
ambiguous boots are rejected without writes. GPT and boot-slot selection are
not modified by ordinary upgrade. Neither an arbitrary geometry nor a stock
vendor upgrade path is accepted by this gate.

The first r9 test uses a new filename-free private configuration seed, not
the manually repaired overlay: its own root password, administration key,
wired identity setup and a unique restoration marker. The old custom
root/overlay was captured first and hash-verified on a second physical SSD.
The image's FIT and extracted rootfs policy checks passed offline; unprivileged
extraction could not create `/dev/console`, which is not used by those offline
checks. A non-writing `sysupgrade -T` passed on the actual 122 MiB layout.
Clean restore, repeat network-only reboots and physical cold-start validation
remain separate hardware gates, not implications of that image check.

The clean r9 upgrade subsequently booted and printed `- config restore -`.
The unique marker, exact private shadow/key contents, own-unit wired MACs,
public boot-success hook and zero counter were verified after boot over SSH.
The 122 MiB primary slot mounted a persistent ext4 overlay. Kernel/rootfs
readbacks, repaired GPT ranges and protected partition hashes matched.
This test did not copy the old manually repaired overlay, and no UART command
was needed to complete or repair the installation.

The first post-upgrade network observer timed out because the PC lost its
source-policy rules on Ethernet reactivation while retaining its addresses
and table-110 routes. An independent UART **read-only** inventory showed a
working router network; correcting the PC's route restored SSH immediately.
The observer now verifies the actual interface/table selection, not just IP
presence. This host-side false negative is not concealed as an effortless
first connection or treated as a firmware Ethernet regression.

Two subsequent SSH-only reboot tests passed with changed boot IDs, retained
configuration markers and unchanged SSH host keys. Full post-boot acceptance
checks completed after approximately 44.4 and 46.4 seconds, respectively;
these times include the checks, not just boot-to-carrier time. Both runs
rechecked the image payloads, protected partitions and cleared boot counter.
An earlier observer attempt stopped on a transient NetworkManager reapply
error during carrier teardown; it was corrected to wait rather than abort.

A temporary local iperf3 endpoint test on the connected LAN port measured
2340.10 Mbit/s PC-to-router and 2026.77 Mbit/s router-to-PC, two TCP streams,
20 seconds per direction, zero retransmissions in both runs. The temporary
server and binary were removed. This is local endpoint traffic, **not** a
second-device routed NAT/PPE acceptance test. Both radio PHYs enumerate,
but radios and WAN remain disabled; no wireless-traffic verdict follows.
Physical cold-start, other physical ports and routed/accelerated traffic
remain open gates. No cold-start result is inferred from warm reboots.
