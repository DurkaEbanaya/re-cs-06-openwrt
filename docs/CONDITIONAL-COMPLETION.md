# Conditional completion: first RE-CS-06 device

The owner requested closing this development stage after verifying the
available acceleration paths, then testing a second RE-CS-06 independently.
The installed reference is **experimental-2026.11.03-resources-r6**, Linux
6.18.60. This is a conditional milestone for the tested configuration, not
official OpenWrt support, a universal hardware certification or a claim of
zero defects. No new image or speculative tuning is installed for closure.

## Acceleration acceptance matrix

| Path | Evidence | Verdict for this stage |
| --- | --- | --- |
| IPv4 NAT, native PPE | Valid hardware entries, packet/byte growth, conntrack HW_OFFLOAD, off/software/hardware comparison | Confirmed in tested topology |
| IPv6 routed PPE | Valid IPv6 forwarding entries and HW_OFFLOAD; bidirectional traffic | Confirmed without NAT |
| PPPoE IPv4 WAN | Real session, hardware PPPoE slot, NAT flow counters, reconnect, MTU 1492 boundary | Confirmed for untagged local test service |
| 802.1Q LAN ingress → ordinary WAN NAT | Actual tagged PC traffic, hardware entries/counters | Confirmed; not WAN VLAN/QinQ |
| Routed 5 GHz HE80 wireless | Phone 11ax, wireless VP NAT entries, running/non-faulted Direct Switch with increasing counters | Confirmed for tested PCI-radio path |
| Software flowtable | DSA physical ingress fix and conntrack OFFLOAD without hardware binding | Confirmed, distinct from PPE |
| ARMv8 cryptographic instructions | AES/GCM/CCM CE drivers registered with passed kernel selftests; AF_ALG AES-CTR known-answer sample and generic/CE comparison | Confirmed for tested algorithms, not VPN throughput |
| RX RPS / socket-stable TX queues | Direct 2.5G tests and persistent board-specific policy | Confirmed CPU-path fixes; not hardware NAT |

Earlier r6 IPv4 NAT tests reached approximately 2.19/2.31 Gbit/s with low
sampled aggregate CPU busy time. IPv6 reached 1.88/2.10 Gbit/s, tagged LAN
VLAN NAT 2.31/2.33 Gbit/s, PPPoE 0.76/0.91 Gbit/s, and routed HE80
0.75/0.89 Gbit/s. Receiver CPU/socket limits, radio conditions and test
duration matter; these are observations, not guaranteed product rates.

Sources: [resource audit](RESOURCE-AUDIT.md), [protocol tests](PROTOCOL-OFFLOAD-TESTS.md),
[receiver controls](RECEIVER-LOSS-CONTROLS.md). Final current-device checks
are recorded in `reports/conditional-completion.json`.

The final current-device repeat measured software flowtable at
1601.86/1607.14 Mbit/s and hardware PPE at 2317.13/2340.17 Mbit/s
(outbound/inbound, two TCP streams, 15 seconds each). Software mode showed
OFFLOAD without hardware binding; hardware mode showed HW_OFFLOAD and
valid PPE flows. PPE bind/replace/readback/resource failure counters were
zero in the collected snapshots. Hardware runs had 9 outbound and 0 inbound
TCP retransmissions; a zero-retransmission universal guarantee is not claimed.
Current AES/GCM/CCM CE registrations and passed kernel selftests were
rechecked. All 35 offline regression tests passed. No new acceleration
blocker was identified within the accepted scope.

The first attempt at this final repeat started before WAN DHCP was ready
and returned network-unreachable. Its cleanup ran; the successful repeat
explicitly waited for interface/address readiness. This test-harness race
is not reported as a forwarding failure or hidden in a performance average.

## Boundaries that remain open, without blocking this scoped milestone

- Some receiver losses and TCP backlog drops were localized to Keenetic.
  Reordering between software observation points is not fully localized;
  JDCloud's entire transmit/NIC path is not exonerated. The second device
  provides a better independent receiver than treating a loaded Keenetic
  local iperf endpoint as a universal firmware verdict.
- EHT/Wi-Fi 7 and MLO are not accepted. The grouped-radio path previously
  crashed; accepted operation uses independent radios. No Wi-Fi 7 client is
  available, and no regulatory restriction is bypassed. Current PHYs expose
  no 6 GHz band. No acceptance of AHB-radio Direct Switch follows from the
  PCI-radio test.
- PPPoE IPv6, provider WAN tagging, QinQ, VPN performance, SQM interaction,
  arbitrary tunnels and all NSS/ECM feature parity are not established.
- Native ARM crypto is not evidence of a functioning separate QCE engine.
  There is no verified bound QCE instance in this configuration.
- Earlier Ethernet outage remains unexplained. Persistent bounded logs are
  installed, but there is no registered ramoops backend and no guarantee of
  capturing the final message of a whole-system hang or power failure.
- Upgrades are checked but not atomic A/B. Backups/recovery remain necessary.
  Unallocated eMMC space is unchanged; this milestone does not authorize GPT
  modification. Per-device data and firmware licensing restrictions remain.

## Operational state is intentionally conservative

Successful temporary hardware-offload tests do not mean acceleration is
currently enabled permanently. Cleanup restores WAN and Wi-Fi disabled and
both flow-offloading settings to zero. The owner must set a root password,
configure actual uplink/regulatory/Wi-Fi credentials and choose offloading
policy before ordinary use. No passwords or private provisioning are put
in generic images or public reports.

## Second router workflow

1. Connect it isolated, without changing the first device or the PC's main
   internet route. Establish its actual model, firmware, GPT and bootloader;
   identical enclosure/model does not prove identical installed layout.
2. Back up **its own** eMMC geometry, boot/service partitions, ART/factory,
   configuration and identity, verify hashes, and keep an independent copy.
   Never copy the first unit's ART, factory block, MACs, SSH/HTTPS private
   keys or system configuration as a replacement for its own.
3. Inspect the chosen image and the second unit's installer/upgrade path.
   Do not run the modified-layout upgrade helper against an unverified stock
   layout, or distribute the obsolete defective prerelease as a final image.
4. Install only after those gates, then verify readback, ext4 persistence,
   automatic configuration carryover as applicable, ports and radio calibration.
5. Use the two devices for controlled endpoint and routed comparisons,
   matching protocol, packet size, offload mode, rate and CPU observations.
   Recheck hardware counters and loss without the Keenetic receiver bottleneck.

The first unit is a tested reference, not an identity or calibration template.
