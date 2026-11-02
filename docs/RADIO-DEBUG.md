# Radio bring-up: current evidence

These are experimental RAM tests, not permission to install a persistent
image. Known private device calibration is never published with these logs.

## Fresh first load (RAM v6)

Suppressing ath12k module autoload allowed all generic firmware files and
the owner's two calibration slices to be placed in tmpfs before the first
driver load. eMMC block devices remained absent. First AHB initialization
still failed at `qcom_scm_pas_init_image` with error -5. The PCI driver found
its 7786496-byte firmware container, but no wireless PHY appeared. SSH
remained available; no PCI unbind or module removal was attempted.

This distinguishes the AHB failure from the earlier missing-file startup
and from the separate partial-state PCI unbind panic. It does not establish
that the packaged radio firmware or reserved-memory contract is correct.

## PAS INIT v2 candidate

Qualcomm's original patch by Manikanta Mylavarapu, dated 2023-05-02, explains
that IPQ5332 security software expects the metadata buffer size in PAS init:

- Original patch ID: `de95dbf665d742604997705d62c9ec6e320005b6`
- [TIP downstream copy](https://github.com/Telecominfraproject/wlan-ap/blob/a85083bce7a01c571c54fc65ceeba517fea0682c/feeds/qca-wifi-7/ipq53xx/patches-6.6/0250-drivers-firmware-scm-ipq5332-add-v2-pas-init-scm-cal.patch)
- [Independent QSDK-based port implementation](https://github.com/sx-ui2/immortalwrt-be6500-port/blob/69deaa2026fff1447cbb3d25c8cc1812f1bf2387/native-6.6/kernel-overrides/drivers/firmware/qcom_scm.c)

The pinned 6.18 source only invokes the legacy two-argument call. Patch
`0007` adapts the original change to the new source paths, retaining its
author/sign-off. It queries command availability and uses command `0x1a`
with the metadata size only when advertised; otherwise it retains the
legacy path. No authentication checks are bypassed and no TrustZone image
is replaced. This is a **candidate fix pending hardware validation**, not
proof that Wi-Fi will work after compilation.

Continue using a freshly booted guarded RAM image, install firmware and
calibration before loading drivers, and retain serial capture. Never
repeat PCI unbind in the known failing partial initialization state.

## PAS v2 hardware result (RAM v7)

The patched kernel successfully started Q6 using the same firmware and
calibration as v6. Both AHB and PCI radios reported firmware versions:
IPQ5332 WBE 1.7-01733 and QCN9274 WBE 1.6-01270. Thus the earlier PAS
initialization failure was cleared; this is not yet Wi-Fi acceptance.

The two-device WSI/MLO group then crashed with firmware assertion
`platform_mlo.c:2038 Assertion !partner_chip_crash_ind failed`. During
automatic recovery Linux panicked in `dev_addr_check` via `free_netdev`,
`qcom_ppe_ds_unregister`, `ath12k_wifi7_ds_cleanup` and
`ath12k_core_qmi_firmware_ready`. No user-triggered PCI unbind was involved.
Different firmware versions are observed, not proven to cause the crash.

The machine automatically returned to QWRT. Read-only verification found
APPSBL, ART, HLOS, primary GPT head and stored U-Boot environment equal to
their backups. This does not claim equality of the live writable overlay.

The next local diagnostic removes the WSI graph from both radio DT nodes,
letting the driver's documented single-device grouping fallback isolate
the radios from inter-device MLO. Kernel, firmware files and calibration
are otherwise unchanged. This is an untested diagnostic, not a published
claim of working independent radios or a persistent firmware change.

## Independent-radio result (RAM v8)

With only that DTB change, both `phy0` and `phy1` registered, Q6 remained
running, and SSH was available. eMMC block devices were still absent and
root was tmpfs. No wireless interface was created; AP/client traffic,
regulatory configuration, long-term stability and MLO were not tested.
This isolates the initial crash to the grouped-radio path sufficiently to
continue independent-radio diagnostics; it does not prove its ultimate
firmware/driver cause or that persistent images are ready to install.
