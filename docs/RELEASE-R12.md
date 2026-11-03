# r12 release: radio sequencing and accumulated fixes

Current full local build: `experimental-2026.11.03-radio-sequence-r12`.
Public binary variant: `experimental-2026.11.03-radio-sequence-r12-external`.
Linux **6.18.60**, pinned LEDE-derived IPQ53xx port; not official OpenWrt.

## Changes since the obsolete public November 2 prototypes

- Correct account-file modes (`passwd`/`group` 0644; `shadow` 0600), isolated
  first boot and per-device identity provisioning, not embedded credentials.
- Persistent ext4 overlay, checked firmware writes/readback, bounded private
  configuration restore and a filename-free gzip seed matching fstools.
- Upgrade geometry checks for the inspected 122 MiB stock primary root slot
  and 2 GiB modified root slot; reject other sizes/secondary-root execution.
  This is not a generic stock web updater or an atomic A/B upgrade.
- Socket-stable TX queues, board-scoped RX RPS, software-flowtable DSA ingress,
  native PPE integration, ARMv8 CryptoAPI CE, USB storage/UAS and bounded logs.
  First-device acceleration measurements are historical evidence, not a
  rerun of every path on r12/second-device hardware.
- Stock-loader Ethernet startup: prepare switch reference before reset and
  assert both UNIPHY LDO-ready bits before resetting the external switch.
- Guarded stock boot-success counter handling; preserve the device's own
  bootloader, calibration and identity rather than cloning another unit.
- Common dummy-netdev setup fix prevents the reproducible PPE/ath12k NAPI
  teardown panic. Three r10 PCI unbind/rebind cycles passed; not universal
  acceptance of all driver unload/recovery scenarios.
- **r12:** board-scoped PCI host sequencing. Hold the declared endpoint reset
  before link initialization until the integrated AHB radio PHY is ready.
  A normal procd service signals readiness; a tested kernel 60-second deadline
  permits probe if userspace readiness is absent. No AER masking or Gen2 cap.

The sequence avoids exposing the PCIe link to the observed integrated-radio
startup interval. It does not identify or repair the exact analog/firmware
operation underlying the original receiver event. The r11 diagnostic passed
two owner-confirmed cold starts without RxErr. Full r12 passed normal boots,
the deliberately disabled-helper deadline test and subsequent network/readback
checks with both radios and Gen3 x2. Its latest network return had zero AER;
physical UART disconnection/power-off details remain owner-confirmation
pending in the report. Do not turn a boot observer label into physical proof.

## Publication and installation boundaries

Public images omit disputed radio firmware/BDF files. The drivers, fixes and
service are included; use the pinned external dependency workflow under the
applicable upstream terms. The full local image is not rehosted as a public
asset. The external variant is a **separate build**, not the byte-identical
image installed on the second router, and is not hardware-accepted merely
because the full local variant passed. With no AHB firmware, readiness may
not occur and the PCI host uses its bounded fallback.

Use the sysupgrade image only with the reviewed compatible installed-system
path and verified backups. A `factory.bin` filename is not permission to feed
it to the stock JDCloud updater. Initramfs is for a separately verified RAM
boot procedure. Keep original per-device ART/factory/keys private and retain
a second physical backup. See [the Russian stock guide](INSTALL-STOCK-RU.md).

WAN, Wi-Fi and persistent flow offloading default to disabled. No root
password, owner calibration or private SSH/HTTPS host keys are embedded.
Radio enum/probe is not radio traffic acceptance. EHT, MLO, 6 GHz, VPN line
rate, all-port/routed second-device performance and power-loss safety remain
outside acceptance. The r12 local LAN endpoint sample was 2347.32/1613.18
Mbit/s, zero TCP retransmits in both directions, not a PPE/NAT benchmark.

Evidence: [PCIe investigation](PCIE-RXERR.md),
[r12 report](../reports/radio-sequence-r12.json),
[stock migration](SECOND-DEVICE.md), [acceleration scope](CONDITIONAL-COMPLETION.md).
Next: [two-router / Wi-Fi 7 laboratory plan in Russian](TWO-ROUTER-LAB-RU.md).
