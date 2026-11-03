# Acceptance tracker — do not equate compilation with normal operation

This is the current working checklist. Historical reports describe older
builds; an item is not resolved merely because a candidate patch exists.

**First-device development is conditionally complete for the tested scope.**
The [completion matrix](CONDITIONAL-COMPLETION.md) defines that scope and
the second-device acceptance plan. The open items below remain visible;
they are not silently marked fixed by this milestone. Historical r3/r4
overlay implementation notes do not describe the newer r6 squashfs.

**Second-device r9:** stock-loader Ethernet initialization and automatic
private configuration restore now pass on the 29-partition unit, with two
SSH-only persistence reboots and local LAN endpoint traffic. See
[the detailed record](SECOND-DEVICE.md) and
[stock installation boundaries](STOCK-INSTALLATION.md). Physical cold start,
all-port traffic and second-device routed offload remain pending. The table
below primarily records historical first-device acceptance, not those gates.

| Area | Latest established result | Remaining acceptance |
| --- | --- | --- |
| TX queue ordering | r3: seven reverse-direction tests without retransmissions | Longer mixed traffic and forwarding, not just endpoints |
| RX CPU contention | r3 plus RX CPU1: repeated 2.34G RX, 2.05G TX, zero retransmissions in 30-second runs; corrected r4 overlay policy survives reboot and packet-steering restart | All ports and routing; original r4 squashfs still has first guard implementation |
| Upgrade configuration | r4 automatically restored network, wireless and original SSH host key; hashes match pre-upgrade backup | More upgrade cycles; original r3 carryover failure not fully traced |
| ext4 initialization | r3 and r4 automatically created persistent ext4; r4 survives subsequent reboot | Cold power-cycle and longer storage checks |
| FDB deletion | Idempotent missing-entry patch installed in r3; no errors in collected boot | Repeated bridge/AP changes and sustained traffic |
| PCIe AER | Earlier single corrected boot RxErr; latest r3 boot counter zero | More boot/load samples; do not hide AER |
| HE | Independent Android phone negotiated 11ax/HE80 on 5 GHz; 441/559 Mbit/s actual traffic | 2.4 GHz HE, 160 MHz and extended stability; Intel client still reports NO-HE |
| EHT / MLO | Current firmware regulatory bitmap reports NO-EHT; grouped radio path previously crashed; owner has no Wi-Fi 7 client | Not accepted or fully testable with current clients; no regulatory bypass |
| WAN / NAT / IPv6 routing | r6: IPv4/IPv6 PPE counters and HW_OFFLOAD confirmed; real PPPoE session/reconnect/1492 MTU, tagged LAN VLAN NAT and routed HE80 Direct Switch tested | Remaining outbound TCP retransmits; WAN-tag insertion/QinQ, PPPoE IPv6 and provider interoperability not accepted |
| Crypto resources | r6 installed: ARMv8 CE AES/GCM registered, reported selftests pass; AF_ALG AES-CTR known-answer sample, 487 vs 51.5 MiB/s generic | VPN-specific tests; limited known-answer sample is not full crypto validation |
| USB / LEDs / buttons | r5: external UAS SSD at USB 5G; 512 MiB direct-I/O pattern and remount/fsck passed | Extended storage/power tests; physical LEDs/buttons, no destructive reset test |
| Security / time | WAN/radios off; root password unset; no router uplink/NTP | Owner password before uplink; verify time once routing is configured |
| Recovery | Existing HTTP recovery and original backups verified | New builds still experimental; do not replace bootloader/GPT |

## Additional routed protocol tests

[RECEIVER-LOSS-CONTROLS.md](RECEIVER-LOSS-CONTROLS.md) adds receiver-local
controls: UDP losses reproduced entirely within Keenetic and matched its
socket receive-buffer error increments. This localizes those particular
UDP drops independently of JDCloud. A separately supplied 48-run investigation
also reports receive-only buffer controls, CPU1 softirq saturation and a TCP
backlog-drop episode localized to Keenetic receive processing. Its raw report
and CSV have not been independently inspected here. These receiver limits
must not be treated as evidence that JDCloud forwarding requires a speculative
fix. The cause of reordering between software capture points and of every
earlier TCP retransmission remains unproven. No permanent tuning is applied.

[PROTOCOL-OFFLOAD-TESTS.md](PROTOCOL-OFFLOAD-TESTS.md) records actual IPv6,
PPPoE, tagged LAN VLAN and routed wireless traffic, including negative
results. Direct Switch's short-refill counter is not a packet-drop counter;
remaining outbound retransmission is not claimed fixed by receiver CPU
affinity or pacing. The ordinary PHY/flow counters cannot localize every
loss or reordering event in the complete PC–JDCloud–Keenetic path.

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
