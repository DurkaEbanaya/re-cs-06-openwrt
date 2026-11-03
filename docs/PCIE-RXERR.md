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
