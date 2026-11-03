# Acceptance tracker — do not equate compilation with normal operation

This is the current working checklist. Historical reports describe older
builds; an item is not resolved merely because a candidate patch exists.

| Area | Latest established result | Remaining acceptance |
| --- | --- | --- |
| TX queue ordering | r3: seven reverse-direction tests without retransmissions | Longer mixed traffic and forwarding, not just endpoints |
| RX CPU contention | r3 plus RX CPU1: repeated 2.34G RX, 2.05G TX, zero retransmissions in 30-second runs; corrected r4 overlay policy survives reboot and packet-steering restart | All ports and routing; original r4 squashfs still has first guard implementation |
| Upgrade configuration | r4 automatically restored network, wireless and original SSH host key; hashes match pre-upgrade backup | More upgrade cycles; original r3 carryover failure not fully traced |
| ext4 initialization | r3 and r4 automatically created persistent ext4; r4 survives subsequent reboot | Cold power-cycle and longer storage checks |
| FDB deletion | Idempotent missing-entry patch installed in r3; no errors in collected boot | Repeated bridge/AP changes and sustained traffic |
| PCIe AER | Earlier single corrected boot RxErr; latest r3 boot counter zero | More boot/load samples; do not hide AER |
| HE | AP advertises HE; current Intel client reports NO-HE | Compatible legal-channel HE client required for actual HE traffic |
| EHT / MLO | Current firmware regulatory bitmap reports NO-EHT; grouped radio path previously crashed | Compatible supported firmware/driver path, no regulatory bypass |
| WAN / NAT / IPv6 routing | Not yet accepted on current installed build | Isolated second endpoint/uplink and firewall tests |
| USB / LEDs / buttons | Controller/sysfs visible | Actual attached device and physical checks, no destructive reset test |
| Security / time | WAN/radios off; root password unset; no router uplink/NTP | Owner password before uplink; verify time once routing is configured |
| Recovery | Existing HTTP recovery and original backups verified | New builds still experimental; do not replace bootloader/GPT |

## RX policy and upgrade hardening

The board-scoped net hotplug script affects only the PPE conduit `switch`
when CPU1 is online. It sets RX RPS to CPU1, keeping IRQ/NAPI work on the
original CPU while moving protocol processing. It requires the r3
socket-stable TX queue patch; earlier experiments without that patch did
not provide a general improvement. This is not an application affinity or
bandwidth limit. RPS masks are checked independently after boot.

The first r4 hotplug guard incorrectly required `cpu1/online`, an attribute
absent when CPU hotplug is not compiled. The corrected guard allows an
enumerated non-hotpluggable CPU1 and still rejects an explicitly offline
CPU. The platform packet-steering wrapper first runs the generic policy,
then applies the scoped override; an explicit `packet_steering=0` is
respected. Corrected scripts currently live in the persistent overlay,
not the already installed original r4 squashfs. Both reboot and service
restart were checked for all four RX masks equal to `2`.

The new upgrade helper validates an existing backup archive, copies it to
private stage2 temporary storage before any block writes, writes it at the
64 KiB-aligned future overlay boundary and compares its SHA256 after readback.
The generic later copy hook becomes a no-op for this board only. Format and
geometry checks remain in place. Regular-file tests cover backup roundtrip
and invalid-backup rejection, and the same backup helper was exercised with
BusyBox on the router using only tmpfs regular files. These tests alone do
not prove first-boot restoration; the installation result must be recorded
separately. The underlying r3 carryover failure is not claimed to be proven.

Actual r4 installation succeeded with automatic carryover and no manual
restore. Readback of kernel/root image ranges matched the installed image;
APPSBL, ART, primary GPT head and stored U-Boot environment matched the
original backup. This is one successful hardware upgrade, not a guarantee
of every power-loss/recovery scenario.

The current upgrade path is not atomic A/B. Readback checks detect failure;
they cannot make a power loss during writes safe. Keep independent backups
and the tested recovery path.
