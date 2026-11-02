# Adaptation and acceptance gates

## Source choice

The pinned LEDE tree already contains IPQ53xx, QCA8386 DSA/PPE and ath12k
support for this board. The importer explicitly states that physical device
acceptance is still outstanding. We reuse this work with attribution, rather
than presenting it as a new upstream OpenWrt port.

## Changes

1. Replace the `qualcommbe` router package defaults with a minimal set. Do not
   include `default-settings`: its startup script sets a shared root password,
   redirects package mirrors, removes `check_signature`, and forces regional
   UI defaults. The proxy feed is not fetched at all.
2. Remove this board's `factory` NVMEM provider and its MAC consumers. Some
   previously modified devices no longer have that GPT partition. Reading
   from ART offset 0/6 is not a universal substitute. Do not use hardcoded
   old-sector remnants inside an active filesystem as an NVMEM provider.
3. Reject persistent FIT kernels larger than the 7 MiB HLOS slot. Build an
   independent initramfs FIT without that storage-only limit. Use gzip,
   which the previous installed image used; that is still not a boot test.
4. Generate Wi-Fi disabled with world regulatory domain (`00`). Choose the
   actual operating country and encryption before enabling it. Full
   `wpad-openssl` is selected instead of assuming basic hostapd covers all
   new Wi-Fi 7/MLO requirements. MLO support is not claimed as tested.
5. Use LAN `192.168.76.1/24`, UTC, standard LuCI and English/Russian. WAN is
   administratively disabled initially. Disable software/hardware flow
   offloading during first acceptance. Do not silently consume official
   OpenWrt binary feeds with incompatible custom kernel/package ABIs.

No GPT, bootloader, ART or MAC values are written by the build process.
Public firmware is device-generic. Initially wired addresses depend on the
kernel/DSA fallback. The provided `re-cs-06-provision-macs` command validates
two owner-supplied addresses and saves only wired UCI settings; it does not
restart networking or touch raw storage. Wireless MAC setup and stability
must be inspected after the actual PHY devices appear. Multiple devices
must never use a hardcoded shared public identity.

## Required hardware acceptance — not yet performed

- Verify a working recovery/UART or suitable RAM boot method and a second
  physical backup copy. Merely finding HTTP recovery strings is not enough.
- RAM boot without writing rootfs/HLOS. Establish isolated wired access and
  capture serial/kernel logs without publishing unique identity or keys.
- Confirm eMMC geometry, ART extraction, both radios and their BDF/caldata
  requests; no assumptions based solely on successful compilation.
- Test all four physical Ethernet ports and actual LAN/WAN mapping at 1G
  and 2.5G; test basic forwarding/firewall before any offloading.
- Configure owner-specific MACs, a new password, correct country and Wi-Fi
  encryption. Verify address uniqueness, 2.4/5GHz AP/client operation,
  stability, DFS as appropriate, and recovery from firmware crashes.
- Only then consider a controlled persistent install. Old QWRT has a different
  board ID and a permissive image checker; do not force sysupgrade metadata.

## Binary packages and licensing

Wi-Fi uses chipset firmware distributed by the source project under its
respective notices. Minimal user services do not make radio firmware open
source. Preserve upstream copyright, firmware notices and all applicable
licenses. Reproducible-input claims mean pinned inputs and scripts; byte-for-
byte reproducibility is unproven until an independent second build matches.
