# Binary release with external radio dependencies

The `external-radio` images contain ath12k drivers, but no IPQ5332/QCN9274
radio firmware/BDF package. They are not standalone Wi-Fi firmware, nor are
they hardware-validated. See [licensing](LICENSING.md) and [recovery](RECOVERY.md).

On the build PC, from this repository:

```sh
python3 scripts/fetch-radio.py ./radio-files
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
The exact runtime driver/reprobe procedure still needs hardware testing.

For an optional complete local rebuild, copy the verified `lib/firmware/`
subtree into the prepared build's `files/lib/firmware/` overlay, then rebuild.
Keep that downloaded overlay local and do not commit it or publish the full
image until the relevant redistribution rights have been established. Building
the image does not itself prove bootloader, Ethernet or Wi-Fi compatibility.
