# Routed protocol and Wi-Fi acceptance on resources-r6

These tests use the installed r6 image, not a new firmware installation.
The PC reaches the test receiver on Keenetic through JDCloud. Two TCP
streams run for 15 seconds per protocol/direction (20 seconds for Wi-Fi).
They benchmark the complete endpoints and forwarding path, not the isolated
PPE ceiling. All addresses, routes, test servers and firewall changes are
temporary; production VPN policy on Keenetic is not modified.

## Hardware path evidence

| Path | Outbound Mbit/s / retransmits | Inbound Mbit/s / retransmits |
| --- | ---: | ---: |
| IPv6 routing, no NAT | 1876.65 / 834 | 2103.51 / 0 |
| IPv4 over PPPoE WAN | 755.25 / 773 | 914.65 / 0 |
| Tagged LAN VLAN → IPv4 NAT WAN | 2311.18 / 7 | 2333.20 / 0 |
| Phone HE80 → IPv4 NAT WAN | 752.67 / 43 | 894.98 / 0 |

Active conntrack entries report `HW_OFFLOAD`; corresponding PPE entries
and byte/packet counters grow. IPv6 uses valid IPv6 forwarding entries.
PPPoE uses an actual kernel PPP session to a temporary local access
concentrator, with a PPE PPPoE slot and no PPPoE rejection recorded. The
VLAN test carries real 802.1Q tags between the PC and JDCloud's LAN bridge;
it does **not** establish WAN VLAN insertion, QinQ or PPPoE-over-VLAN.

PPPoE reconnected after an explicit session down/up. With MTU 1492, an IPv4
packet of 1492 bytes passed without fragmentation; a 1493-byte packet with
DF returned an error. The test receiver had narrowly scoped temporary
firewall exceptions only for the test traffic.

The phone negotiates 11ax/HE. Hardware Wi-Fi NAT flows use the wireless
virtual port and Direct Switch, which remains running and not faulted.
Without offload, the corresponding Wi-Fi measurements were 508.67/831.27
Mbit/s, versus 752.67/894.98 with hardware enabled. This is actual routed
traffic, not the earlier phone-to-router endpoint benchmark.

## Direct Switch refill counter

`refill_fail` grew during traffic. Source inspection shows that it counts
polls where the client supplied fewer free buffers than the requested batch.
The ath12k callback removes buffers from its preallocated free list; it is
not a per-packet allocation/error count. The PPE driver records a short
refill and provides retry/wakeup paths. This counter must not be relabelled
as a packet-drop count, nor hidden simply to make diagnostics look clean.
It also does not prove that pool pressure can never affect performance.

## Remaining transmit/retransmission limitation

Repeated hardware IPv4 runs delivered 2317–2320 Mbit/s with 5, 32 and 5 TCP
retransmissions. Receiver-CPU A/B runs at a requested aggregate 2.2 Gbit/s
delivered 2180–2193 Mbit/s with 2, 29, 2 and 3 retransmissions. The CPU
change did not establish a deterministic cure. A receiver backlog-drop
counter grew in one run, but not sufficiently to attribute all duplicates
to it. The older Linux `TCPPrequeueDropped` counter can count packets
flushed into normal processing; it is not direct proof of packet loss.

The exact remaining LAN→WAN loss/reordering cause is **not established**.
Do not install a bandwidth cap, pin the receiving application, suppress
diagnostic counters or claim an untested driver change as the solution.
IPv6 and PPPoE outbound retransmissions remain acceptance limitations.

## Not covered

No Wi-Fi 7 client is available; EHT/MLO are not accepted. These tests do not
prove PPPoE IPv6, provider-specific VLAN service, every MTU combination,
arbitrary VPN acceleration, power-loss safety or indefinite stability.
Root password provisioning still requires the owner. WAN and radio service
must remain disabled after diagnostic cleanup until proper configuration.

## Repeated traffic and final cleanup

Two rounds of all four wired paths, 30 seconds per direction, completed
16 runs and 480 seconds of traffic. Inbound retransmissions were zero in
every run. Outbound retransmissions remained (IPv4 414/766, IPv6 653/645,
tagged VLAN 387/740, PPPoE 1477/551). This is a bounded repeated-traffic
check, not simultaneous mixed traffic or an overnight endurance test.
The same boot ID persisted; sampled temperatures were 50.6–59.8 °C, with
no observed panic, radio crash or storage I/O error. The test runner's final
telemetry collection initially failed because it used a nonexistent debugfs
`resources` name; all traffic results had already completed. The actual
`resource_stats` node was subsequently captured. No new source/firmware fix
is claimed from that diagnostic-script correction.

A fresh four-core, 192 MiB, 90-second userspace memory-pattern check passed.
The unmounted USB test filesystem passed read-only `e2fsck -f -n` again.
Bootloader, ART and primary GPT hashes still match the original backup.
IPv6 WAN-side TCP connection attempts to management ports 22/80/443 were
rejected while LAN management remained available.

All owned PPPoE sessions/server processes, iperf servers, temporary firewall
exceptions, IPv6 return routes, PC VLAN profile and diagnostic host routes
were removed. Uncommitted JDCloud network/firewall/wireless changes were
reverted; `fw4 check` passes, WAN/radios are disabled and PPE resource failure
stage counters are zero. Keenetic's existing VPN/startup configuration and
the PC's normal Wi-Fi internet route were not changed.

The phone's temporary test network and executable were removed before this
stage. Its saved post-test status was disconnected, and it was no longer
available over ADB at final verification. Automatic reconnection to its
original Wi-Fi is **not** claimed for this later run.

The owner requested PC shutdown after completion. Reports and private logs
are saved before requesting normal operating-system power-off; this does
not turn the unresolved acceptance limitations into a claim of perfection.
