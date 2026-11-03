# Second-device PCIe RxErr investigation

The r9 cold-start check recorded a correctable physical-layer Receiver Error
on the PCIe root port and QCN9274 endpoint. Each device had `RxErr 1` and
`TOTAL_ERR_COR 1`, with zero nonfatal and fatal AER totals. These are two
reporting locations on the same link, not proof of two independent failures.

## Established before any candidate change

- Link negotiation and the live sysfs state were **Gen3 x2, 8.0 GT/s**.
- Counts were unchanged at approximately 82, 280 and 450 seconds of that
  boot. This is an idle observation, not a wireless load/stability test.
- The error was logged around kernel time 8.19 seconds: after ath12k PCI
  probing/MSI setup, before the firmware-selection/MHI power-on messages.
- Both live Link Control registers had ASPM L0s/L1 disabled. This does not
  establish their state at the instant of the earlier error.
- Subsequent warm boots also produced zero RxErr without a PCIe fix. A
  single clean boot is therefore not evidence that a candidate solved it.
- No AER masks, `pci=noaer`, artificial link-speed cap or regulatory bypass
  are used to make the observation disappear.

The exact origin of the physical-layer event remains unproven. The timing
suggests examining the driver's initialization/reset path, but does not
exclude PHY/board/power behavior. Successful firmware loading and PHY
enumeration are not a wireless traffic acceptance test.

## A separate reproducible teardown defect

With radios administratively disabled, explicitly unbinding only the PCI
ath12k device caused a kernel panic. UART captured the first fault in
`dev_addr_check` → `dev_addr_flush` → `free_netdev`, called while freeing the
PPE Direct Switch NAPI netdev. A PPE-only allocation fix moved the fault to
ath12k's own NAPI netdev cleanup: the common allocator was the real scope.

The source cause is the pinned tree's generic compatibility patch
`generic/hack-6.18/991-revert-init_dummy_netdev.patch`. It restores a full
`memset` in `init_dummy_netdev()` for older embedded-netdev callers, while
`alloc_netdev_dummy()` still passes that function as the setup callback.
`alloc_netdev()` has already allocated its address list and reference state
before invoking setup; clearing the object loses that state and leaves
`dev_addr` null. Normal `free_netdev()` then dereferences it.

Public patch `0019` separates the allocated dummy setup from the destructive
embedded-device initialization. It preserves allocator-owned resources,
dummy state and ordinary cleanup rather than suppressing the null-pointer
check, leaking the netdev or disabling Direct Switch. The same distinction
is explained in the [original allocator discussion](https://lists.infradead.org/pipermail/ath11k/2024-April/005696.html).

The full **pcie-diag-r10** candidate containing the common fix is installed.
Kernel/rootfs readback and protected stock/bootloader/calibration partitions
matched expectations. The same-device password, authorized key, SSH host
keys and persistence markers survived the automatic upgrade. The temporary
PPE-only overlay module was not carried over.

Three consecutive instrumented PCI radio unbind/rebind cycles completed
without a panic, warning or timeout. Firmware initialized again, both radio
PHYs enumerated and Direct Switch rings registered. Targeted kprobes captured
2,698, 2,701 and 2,699 register accesses respectively, plus reset/power-up
events, with no reported trace loss. Both ends remained Gen3 x2 and reported
zero correctable, nonfatal and fatal AER totals in those warm-start samples.
This is not a wireless traffic or cold-start test.

A subsequent ordinary SSH-requested reboot also returned with the same
private access/markers, verified firmware and protected-partition readbacks,
boot counter zero and Gen3 x2. Both ends again reported zero AER totals.

The teardown panic is **not** the original correctable PCIe event. Successful
warm reinitialization must not be described as resolving the intermittent
cold-start RxErr.

## r10 physical cold start

An owner-performed 15–20-second power-off/on cycle reproduced the original
event: root port and radio endpoint each reported `RxErr 1`, with nonfatal
and fatal totals zero. UART and the kernel log agree on the event around
8.27 seconds, after MSI setup and before the MHI firmware-selection and
power-on messages. The device nevertheless returned with Gen3 x2, both
radio PHYs, unchanged private access, verified firmware/protected partitions
and boot counter zero. No UART commands were needed for that boot.

This establishes that r10's NAPI fix did **not** eliminate the cold-start
RxErr. A temporary early-boot trace is being used to narrow the interval;
no permanent PCIe behavior change has been made.

The next cold start with early kprobes reproduced it again. The AER handler
ran at about 8.435 seconds, during the PCI device's `ath12k_fw_map()` call
(8.120–9.466 seconds). The first traced `ath12k_pci_power_up()` was later,
at 9.468 seconds, and the MHI reset was at 9.508 seconds. Before AER, the
trace contained one tracked PCI register read for hardware identification
and no tracked register writes. Per-CPU trace buffers reported zero
overruns. This rules out the *later* reset sequence as the direct preceding
operation in that sample; it does not prove firmware file I/O causes a
physical-layer fault, or exclude untraced PCI configuration/power activity.

A subsequent separating experiment held only the PCI radio unbound from
early boot using a temporary `driver_override`. RxErr still occurred at
about 8.50 seconds, before any PCI ath12k probing. Before releasing the
driver at 16.22 seconds, both ends already had count 1; after successful
radio initialization, both remained at 1. Early Link Control snapshots
were `0x0008` at both ends (ASPM L0s/L1 off). This disproves an explanation
requiring the PCI driver's firmware-file read or reset to cause the event.
The earlier overlap with firmware mapping was timing, not established
causality. The integrated AHB radio was still starting in this experiment;
shared SoC/radio initialization is not excluded.

The next physical cold start held **both** radios unbound from early boot,
then released them separately. Both PCIe reporting locations stayed at
`RxErr 0` before release. The PCI radio was released at 16.239 seconds,
initialized successfully, and counts were still zero after a 15-second
observation. Releasing the integrated AHB radio at 33.851 seconds moved
the AER event to about 35.168 seconds. Its firmware-version message appeared
at 34.962 seconds; both PCIe locations then had `RxErr 1`.

This separates the triggering **stage**: the event follows AHB radio
bring-up, not a fixed eight-second boot timer or the PCI radio's own probe.
It does not establish which AHB firmware action, shared clock/power path or
physical interaction causes the receiver event. Host QMI and clock tracing
are the next checks; changing calibration data or suppressing AER is not a
substitute for that evidence.

After each completed isolation experiment, both radio drivers returned,
Gen3 x2 and the full firmware/protected-partition checks passed, and the
temporary hold/trace hook was removed. These hooks are not part of the
generic image. No wireless traffic acceptance follows from driver probing.

## QMI/WMI and host clock isolation

A further both-held cold start added request-ID-only QMI probes, WMI command
IDs and Linux clock-framework tracepoints. The PCI radio again initialized
first without RxErr. After the integrated radio was released, its timeline
was:

| Kernel time (seconds) | Integrated AHB initialization / PCIe observation |
| --- | --- |
| 33.931 | Controlled AHB driver release |
| 35.049 | Firmware-version message |
| 35.067–35.137 | Board-data download requests |
| 35.142 | M3 information request |
| 35.144 | Firmware-ready handler; WLAN INI request |
| 35.148 | WLAN configuration request |
| 35.150 | WLAN mode request |
| 35.228 | WMI command 1 (`WMI_INIT_CMDID`) |
| 35.255 / 35.264 | PCIe AER handler entries |
| 35.316 | Firmware-ready handler returns success |

The first AER handler followed WMI INIT by approximately **27.7 ms**.
This identifies a narrower initialization interval; temporal ordering alone
does **not** prove WMI INIT itself, calibration, a particular firmware
instruction or a defective component caused the physical receiver event.
All four trace buffers reported zero overruns. Between 35.13 and 35.32
seconds the raw trace contains CPU-frequency activity and eMMC clock
disable/unprepare events, but no recorded PCIe, Wi-Fi or CMN clock-framework
transition. This is narrower than saying there were no clock events at all:
the initial summary filtered out CPU/eMMC activity. It does not exclude
firmware- or secure-world-controlled changes, indirect effects of those
other host clocks, or analog supply/reference behavior.

An equivalent warm-start tracing rehearsal had zero RxErr. The cold sample
again ended at count 1 at each reporting location, with zero nonfatal/fatal
totals; a later idle check found no increase. Both drivers returned, Gen3 x2
was retained, all firmware/protected-partition checks passed, and temporary
trace/hold hooks and overrides were removed. This is still **not an RxErr
fix**. There is insufficient evidence for a permanent PCIe/clock/calibration
change, and no such change is included in r10.

## Hardware-sequencing experiment, not yet an accepted fix

Holding only the PCI radio driver does not hold the already trained PCIe
link in reset. A temporary board-scoped module therefore tested the standard
root-port Link Disable bit, after unbinding and removing the endpoint. It
successfully disabled the link, but clearing Link Disable and rescanning
did not rediscover the endpoint. A second warm rehearsal including the
standard secondary-bus reset also failed to rediscover it. Both tests were
reversed by ordinary reboots, restoring both radio PHYs and Gen3 x2; no
module, AER masking or speed cap was installed persistently. These failed
recovery sequences are **not candidates for deployment**.

The next local diagnostic instead defers the PCIe host's normal probe and
uses its declared, polarity-aware PERST descriptor to hold the endpoint
before host initialization. A bounded userspace diagnostic waits for the
integrated radio PHY and then requests the normal controller probe. A
timeout must also release it rather than leave PCIe disabled indefinitely.
This requires a separate opt-in diagnostic kernel/DT and is not part of
the published r10 source patch set. The first kernel-only warm rehearsal
passed: integrated-radio firmware initialized first, host probing was
requested at 10.65 seconds, the PCIe link trained Gen3 x2 at 11.02 seconds,
and both PHYs returned with RxErr zero. Kernel/module compatibility (94
module files byte-identical), kernel/rootfs and protected-partition readback,
private access carryover and boot counter zero were verified. The unchanged
r10 rootfs/release label remains, so it must not be confused with a full r11
release. A known-good r10 kernel and this diagnostic were independently
copied and verified before writing only the custom kernel partition.

The first owner-performed physical cold start with the same diagnostic
also passed: integrated-radio firmware was reported at 7.85 seconds, host
probing was requested at 10.64 seconds, and PCIe trained Gen3 x2 at 11.01
seconds. AER was enabled normally at 11.16 seconds; both radio PHYs returned
with correctable/nonfatal/fatal counts zero. Kernel/rootfs and protected
readbacks, private access, disabled WAN/radios/offloading and boot counter
zero passed. The rootfs remains the unchanged r10 root; only the diagnostic
kernel and local bounded release hook differ.

This is a **first positive cold sample**, not repeated acceptance or proof
of the exact analog/firmware cause. The link is intentionally not operating
while AHB initializes; this avoids exposing an active link to that stage
rather than masking an error on an active link. Cold repeatability, real
wireless traffic and robust integration/failure handling are still pending.
This remains a local diagnostic, not a production synchronization design or
an accepted RxErr fix. The bounded release hook is temporary and must be
removed on restoration or replaced by a reviewed implementation if the
hypothesis survives testing.

After that first cold boot, a bidirectional LAN endpoint regression measured
2345.55 Mbit/s PC→router and 1986.13 Mbit/s router→PC (two TCP streams,
20 seconds per direction, zero retransmits). A subsequent snapshot still
had zero correctable/nonfatal/fatal AER totals at both PCIe reporting
locations. The temporary server was removed. This is an Ethernet endpoint
regression, **not** routed PPE acceptance or a Wi-Fi traffic test. All 50
offline regression tests also passed. The sanitized diagnostic record is
[`reports/pcie-sequence-diagnostic.json`](../reports/pcie-sequence-diagnostic.json).
