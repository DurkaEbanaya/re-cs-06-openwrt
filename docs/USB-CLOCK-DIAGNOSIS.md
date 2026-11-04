# r14 USB3 difference between the two units

This investigation follows the [extended full-local r14 validation](FULL-R14-VALIDATION.md).
It includes a successful kernel-only r15 candidate test followed by full-r15
upgrades on both units. It is not a hardware test of r14-external.

## Controlled observations

The same RTL9210B bridge/SSD was connected directly, without a cable:

| Host | Negotiated link | Storage transport | Read-only checks |
| --- | --- | --- | --- |
| Workstation | 5000 Mbit/s | UAS | Two 256 MiB direct reads agreed; ext4 check passed |
| First RE-CS-06, full r14 | 5000 Mbit/s | UAS | 256 MiB direct read agreed with the second unit's latest read; ext4 check passed |
| Second RE-CS-06, full r14 | 480 Mbit/s | usb-storage | Consecutive 256 MiB direct reads agreed; ext4 check passed |

The second unit also wrote a new 64 MiB regular file, synchronized and
unmounted it, then verified its SHA256 with a direct read after a read-only
remount. The test file was removed and read-only e2fsck passed. There was no
formatting. Raw hashes obtained before and after these authorized filesystem
writes are not expected to agree, because filesystem metadata changed.

The first unit's earlier r5 UAS/write-pattern result is historical; the r14
USB3 read above is a fresh control with the same current device. The first
unit has a modified bootloader and the second retains its stock bootloader.
This difference is relevant to inherited state, but does not alone prove
which component initialized the clocks or that the connector is faulty.

## Clock-state difference

Read-only clock-framework queries and GCC register snapshots agree:

| USB clock | First unit, USB3 working | Second unit |
| --- | --- | --- |
| AUX | 2 MHz | 24 MHz |
| LFPS | approximately 25 MHz | 24 MHz |
| mock UTMI / DWC3 reference | 60 MHz | 24 MHz |
| PIPE | 250 MHz | 250 MHz |
| Master | approximately 200 MHz | approximately 200 MHz |

The second unit's AUX, LFPS and mock-UTMI RCG configuration words are zero,
consistent with the XO reset configuration. The board DT lists these clock
inputs but assigns no rates. The legacy Qualcomm wrapper enables them
without setting rates. DWC3 calculates reference timing using the current
reference-clock rate, explaining corresponding differences in its timing
registers; that is not independently proof of the USB3 failure's cause.

A temporary read-only diagnostic queried the three clocks with
`clk_get_rate()` and `clk_round_rate()`. On both units the provider supports
the requested 2/25/60 MHz rates. It made no rate/reset changes and left no
resident module. No arbitrary MMIO writes or bootloader changes were made.

## Kernel-only candidate: first warm-start result

Patch `0022` assigns master/mock-UTMI/AUX/LFPS rates of 200/60/2/25 MHz in
the RE-CS-06 USB wrapper node, before driver probing. It does not change
USB speed limits, PHY tuning, GPIOs, regulators, UAS quirks or another board.
The full `usb-clocks-r15` build passed offline FIT/hash/compiled-DT checks;
all 94 module files were byte-identical to r14. The owner authorized a
kernel-only test and one reboot of the second unit. Before writing, its
whole current HLOS partition, private configuration and environment were
saved, along with the checked candidate and rollback, on two physical disks.

Only the primary kernel FIT was replaced. Immediate readback matched;
the whole root partition, protected partitions (including the boot
environment before reboot), GPT head/tail and configuration were unchanged.
The r14 root filesystem and its access settings were retained. After the
single reboot, candidate kernel/rootfs-prefix/protected-partition/GPT and
saved configuration checks passed. Boot counter returned to zero.

The three USB clocks now read 2 MHz AUX, approximately 25 MHz LFPS and
60 MHz mock UTMI. The same attached bridge enumerated at **5000 Mbit/s
with UAS**, at kernel time 3.176 seconds, and its disk appeared by 3.548
seconds. Two 256 MiB direct reads matched the latest first-unit control;
read-only ext4 checking passed. No USB reset, I/O error or kernel fault was
present in the captured boot/read log; PCIe AER totals were zero.

This intervention strongly supports missing clock-rate initialization as
the cause of the observed second-unit SuperSpeed failure. It does not prove
the stock bootloader is corrupt. Repeated hotplug and longer storage/power
checks remain separate gates. The tested system at this stage is
**an r15 candidate kernel with an unchanged r14 root**, not a tested full-r15
upgrade or a new public binary release.

The same warm-start session also passed a 64 MiB exclusive regular-file
write, fsync/unmount, read-only remount and direct-read SHA256 comparison.
The test file was removed, the filesystem unmounted, and read-only e2fsck
passed afterward. The bridge remained at 5000 Mbit/s/UAS without recorded
USB resets or I/O errors. This does not replace a physical cold-start test.

The owner subsequently confirmed manually switching the second router off
and on. The observer issued no reboot itself. On that new boot, the bridge
enumerated as SuperSpeed at 3.146 seconds and UAS at 3.253 seconds. Two
consecutive 256 MiB direct reads matched each other, read-only ext4 checking
passed, the expected 2/25/60 MHz rates were retained, both radio PHYs and
Gen3 x2 returned, and all six PCIe AER totals were zero. Kernel/rootfs-prefix,
protected partition and saved configuration hashes matched. The precise
power-off duration was not independently recorded. This is one confirmed
power-cycle sample, not universal cold-start or power-loss acceptance.

## One image for both inspected units

The correction belongs in the common RE-CS-06 DT, not in per-device
bootloader patches or a first-boot script. Clock assignments are applied
before USB driver probing, including the reference used by DWC3 timing.
The first unit already has approximately these rates; requesting them
explicitly removes reliance on that inherited setting. The subsequent
full-image checks on both units are recorded below; broader USB acceptance
still requires additional devices and power/hotplug testing.

Available nonunique identification fields match on both devices:
`soc_id=593`, SoC revision `1.1`, machine `IPQ5322`, and the RE-CS-06 DT
compatibility. This is not a PCB revision identifier. Different PCB
revisions are neither established nor ruled out by these fields, and are
not a reason to create two images without additional evidence.

The existing updater already accepts the two inspected primary-root sizes
(122 MiB and 2 GiB) while rejecting unknown geometry or a booted secondary
root. The identical generic kernel/rootfs can be used for both sizes;
configuration archives, identities and keys remain separate for each unit.
No GPT normalization, shared calibration or bootloader replacement is
needed for that workflow. This is not a universal stock first-installer.

The **identical full-local r15 sysupgrade image** was subsequently installed
on both units, sequentially, after fresh per-device configuration, protected
partition, GPT and live-root backups were verified on a second physical
disk. The running version and kernel/rootfs readbacks matched on both.
Each unit retained all saved regular configuration/access files, its own
environment variables and management address; protected partitions and GPT
matched their independent pre-upgrade records. Both radio PHYs, Gen3 x2,
zero AER totals and the assigned USB clock rates passed. The first unit's
existing persistent logging service remained enabled.

On the second unit, the attached bridge remained at 5000 Mbit/s/UAS after
the full upgrade. A new exclusive 64 MiB file passed write/fsync/unmount,
read-only remount/direct-read SHA256 comparison, removal and read-only
filesystem checking. The disk was left unmounted. There is not yet an
attached-device USB3 test of the first unit's full r15, nor a new
owner-confirmed power-cycle test of the full-image pair. The earlier
kernel-only cold-start evidence remains explicitly separate.

Two initial post-upgrade WAN-load attempts stopped before iperf. The first
had no dedicated WAN link; after the cable was added, the old harness still
mistakenly separated the first unit's LAN1, which actually carried management,
instead of LAN2, which carried the new WAN test cable. Restoring the first
bridge recovered access without rebooting; both original configurations and
temporary-tool cleanup were verified. These are topology/preflight failures,
not forwarding measurements. The revised harness checks the learned bridge
forwarding entry for the management peer and refuses to detach that port.
It also allows time for link negotiation after administratively enabling WAN;
an administratively disabled port is not diagnosed as a cable failure.

With the mapped dedicated link, a fresh full-r15 DHCP/NAT test completed
two 30-second, two-stream directions: **2337.76 / 1482.19 Mbit/s**, with
**1056 / 0 TCP retransmissions** (LAN→WAN / WAN→LAN). Both samples showed
HW_OFFLOAD, valid PPE entries and zero collected bind/index/readback/resource
failures. Checked Ethernet MIB and softnet-drop counts did not increase;
PCIe AER stayed zero. The outbound retries were not individually traced
and are **not** declared explained or fixed by those clean counters.
LAN management listeners were positive controls for blocked WAN TCP
22/80/443, and DHCP reconnect passed. Original configurations were restored;
subsequent full-image, private configuration, GPT/environment and protected
partition checks passed on both units. Test tools/routes were removed,
WAN/radios/persistent offloading disabled again, and PC Wi-Fi Internet retained.

### Cable replacement and observation controls

After the owner reported replacing a flat cable, the PC link initially
negotiated at 1 Gbit/s and then returned to 2.5 Gbit/s. The first two repeats
measured 2338.54/2027.23 and 2337.13/2012.12 Mbit/s, with zero TCP retries
in all four directions, but lack complete before/after link snapshots.
Their directory label is historical, not evidence of 1 Gbit/s during traffic.
Subsequent controls required a 2.5G/full-duplex PC link before and after
each repeat, and waited for both ends of the dedicated WAN link:

| Control, repeat | Out/in (Mbit/s) | TCP retransmissions out/in |
| --- | --- | --- |
| Normal active diagnostic snapshot, 1 | 2340.91 / 2030.18 | 79 / 0 |
| Normal active diagnostic snapshot, 2 | 2338.62 / 1465.34 | 0 / 0 |
| No diagnostic reads during load, 1 | 2338.79 / 1467.52 | 0 / 0 |
| No diagnostic reads during load, 2 | 2340.68 / 2029.71 | 0 / 0 |

These remain two-stream, 30-second-per-direction endpoint/NAT tests. In the
79-retry sample, the peer/receiver's CPU1 softnet drop counter increased by
exactly 79 while the target's softnet drops stayed zero. This is consistent
with receiver backlog loss in that run, not proof of a target PPE or cable
fault. Checked FCS and `Filtered` counts did not increase. Some peer
`RxBadByte` increments were exactly 64 times received PAUSE frames, without
FCS growth; they are not independently treated as damaged payload frames.

Normal samples showed active HW_OFFLOAD and valid PPE entries. Quiet controls
used the same hardware-mode configuration but intentionally omitted active
flow snapshots; their report's false observation flag means **not sampled**,
not that hardware support disappeared. Before/after failure counters and
target AER remained zero; no configuration or sysctl tuning was introduced.
All six repeat sessions restored the original settings and passed final
firmware, protected-partition, private-config, cleanup and Internet-route checks.

The earlier 1056 retries were all in the 7–8-second interval, coinciding
with an active diagnostic snapshot; that coincidence alone does not prove
observer causality. The receiver rate also varied in reverse even without
diagnostic reads. Neither a faulty old cable nor a complete observer-effect
explanation is established by these controls, and earlier nonzero results
are retained rather than replaced with the best repeats.

Machine-readable evidence: [USB/r15 report](../reports/usb-clocks-r15.json).

Post-upgrade HE service checks on both full-r15 units also passed actual
AP/STA association, DHCP, DNS and IPv4/IPv6 pings in both 2.4 GHz HE20 and
5 GHz HE80 roles with WPA3-SAE/required PMF and WPA2-PSK/optional PMF.
Four 2.4 GHz endpoint runs measured 146.32–173.26 Mbit/s with zero TCP
retransmissions. The four 5 GHz runs measured 1098.20–1408.53 Mbit/s, with
150/0 retransmissions for first-station→second-AP / reverse and 1234/0 for
second-station→first-AP / reverse. These two-stream, 20-second runs retained
default backlog; they do not establish loss-free wireless or a new USB-related
network-performance improvement. All eight per-case device logs had zero
AER totals and no captured panic, Oops or CPU warning. Original configurations
were restored afterward.

## Negative findings that remain visible

- Some earlier second-unit boots failed to enumerate the disk reliably or
  spent tens of seconds on storage timeouts. Those timeouts delayed module
  loading and could reach the PCI/AHB sequence's 60-second fallback.
- Live unbind/rebind of the outer legacy USB wrapper was followed by an
  unexpected whole-system restart. No pre-restart UART/pstore record was
  available, so panic versus watchdog or another cause remains unproven.
  Do not repeat that operation as a routine recovery procedure.
- A successful 480 Mbit/s file test does not accept SuperSpeed, hotplug
  reliability, all USB devices, power delivery or power-loss behavior.

All per-device raw logs and configuration remain private. The candidate
does not overwrite ART, factory, bootloader, GPT or stock OS slots.
