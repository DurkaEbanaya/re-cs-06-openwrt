# Binary release with external radio dependencies

The `external-radio` images contain ath12k drivers, but no IPQ5332/QCN9274
radio firmware/BDF package. They are not standalone Wi-Fi firmware, nor are
they hardware-validated. See [licensing](LICENSING.md) and [recovery](RECOVERY.md).

Current public version: **radio-sequence-r12-external**. It includes all
source/overlay fixes through patch 0020; the complete local r12 has separate
hardware evidence. The November 2 assets are obsolete **DO NOT FLASH**
prototypes. See [r12 release notes](RELEASE-R12.md).

On the build PC, from this repository:

```sh
python3 scripts/fetch-radio.py ./radio-files
```

For the standalone release assets, keep the pinned manifest alongside the
downloaded script and explicitly select it:

```sh
python3 fetch-radio.py --lock radio-files.lock.json ./radio-files
```

This creates a **new** directory and downloads 52 files directly from pinned
upstream URLs, verifying each SHA256. It refuses an existing output directory
and does not connect to the router or change the host's firmware directory.
The resulting `radio-files/lib/firmware/ath12k/` tree includes the board-specific
BDF overrides from the original full build. It contains no ART, private MACs
or serial numbers. Do not blindly download from unpinned latest branches.

After a separately verified isolated RAM boot, transfer this tree into that
RAM environment's `/lib/firmware/ath12k/` before the radio driver loads. For a
persistent installation the same files need to be provided in the writable
overlay, but persistent copying/reloading is not performed by this repository.
The exact external-image provisioning/reprobe procedure still needs hardware
testing. The historical missing-firmware v5 session panicked during PCI
cleanup. r10 fixed the common dummy-NAPI allocator defect and passed three
unbind/rebind cycles with firmware present; that does not validate every
missing-firmware recovery path. Do not use live unbind/module unloading as an
assumed safe way to inject the files. Prefer preparing dependencies before a
fresh controlled driver startup or making a complete **local** image. The
earlier AHB SCM failure has subsequent full-image fixes, but is retained as
historical evidence, not represented as a current full-r12 failure.

r12 waits for the integrated radio PHY before probing PCIe. Without external
AHB firmware that signal may never arrive: the kernel's 60-second deadline
then permits normal PCI host probing. This prevents an indefinite readiness
wait, but does not make absent radio firmware work. Do not mistake driver
enumeration or a fallback log for functioning wireless service.

For an optional complete local rebuild, copy the verified `lib/firmware/`
subtree into the prepared build's `files/lib/firmware/` overlay, then rebuild.
Keep that downloaded overlay local and do not commit it or publish the full
image until the relevant redistribution rights have been established. Building
the image does not itself prove bootloader, Ethernet or Wi-Fi compatibility.
