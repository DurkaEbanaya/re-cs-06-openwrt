# Extended full-local r14 validation

This follow-up targets the second RE-CS-06 running the **full local r14**,
with the first r14 device as an isolated peer. The owner excluded repeating
the already-checked physical-port inventory. These tests do not constitute
a hardware boot test of the separate public `r14-external` images.

## Scope and reporting

Results cover management/authentication, persistence and storage,
cryptographic primitives, radio AP/STA roles, DHCP/DNS, physical
WAN/NAT/firewall, PPPoE and IPv6 routing. Destructive reset, bootloader
replacement, recovery writes and power interruption during writes are not
part of this validation. No calibration or identity is copied between units.

Full software-path saturation can legitimately cause queue/congestion drops;
an active offload flag is not evidence of zero loss. Results retain TCP
retransmissions alongside measured throughput. Endpoint CPU limits remain
part of this two-router/one-PC setup.

## Service and storage checks

| Area | Established result | Boundary |
| --- | --- | --- |
| Installed firmware and identity | Kernel/rootfs, protected partitions, GPT and private configuration readbacks matched | Not atomic A/B or power-loss safety |
| Management | HTTP/HTTPS LuCI login pages; unauthenticated system API rejected; authenticated HTTPS board query and session destruction passed | Local self-signed certificate, not public trust |
| Persistent ext4 | Exclusive 4 MiB write, sync and direct-read SHA256 comparison; persistence marker survived one graceful reboot | No mounted-filesystem repair or destructive reset |
| ARM crypto | AES-CTR known-answer sample passed through generic and ARM CE implementations | Limited sample, not VPN performance or comprehensive cryptographic validation |
| DNS | Local positive/negative answers and forwarding through an isolated controlled upstream passed | Not a public Internet DNS availability test |
| Time | Isolated NTP peer corrected the initially unsynchronized clock to within one second of the test reference | No battery-backed RTC or public Internet NTP acceptance |
| WAN DHCP | Real lease and reconnect on ordinary and VLAN-tagged WAN passed | Isolated peer; no provider interoperability claim |
| WAN firewall | Dedicated TCP client connected to LAN management ports 22/80/443, while the tested WAN addresses refused those ports | Not an exhaustive firewall/security audit |
| DHCPv6 / RA | Client IA_NA lease independently matched the server record; SLAAC address and IPv6 ping passed | Prefix delegation and PPPoE IPv6 not tested |

The graceful reboot initially spent tens of seconds in USB storage timeouts.
This was a real negative result, not a normal boot-time guarantee. The USB
investigation below separated a bootloader-inherited clock dependency from
filesystem integrity. No claim that every subsystem worked on full r14 is
made.

## Routed traffic and hardware offload

The first router's dedicated LAN port was temporarily separated from its
management bridge and connected to the second router's physical WAN. The
PC's ordinary Internet path remained Wi-Fi. Tests used two TCP streams,
20 seconds per direction, with off/software/hardware modes where listed.
"Out/in" below means LAN→WAN / WAN→LAN; these are receiver rates, not PHY
negotiation speeds.

| Path | Hardware out/in (Mbit/s) | TCP retransmissions out/in |
| --- | --- | --- |
| DHCP IPv4 NAT | 2338.87 / 1465.31 | 0 / 0 |
| 802.1Q-tagged WAN DHCP / NAT | 2315.90 / 1490.26 | 0 / 0 |
| PPPoE IPv4 | 2323.34 / 1928.11 | 0 / 0 |
| Routed IPv6, without NAT | 2304.06 / 2024.96 | 0 / 0 |

Hardware samples showed conntrack `HW_OFFLOAD`, valid PPE entries and
packet/byte growth; collected bind/resource/index/readback failure counters
were zero. IPv4 software-flowtable controls showed `OFFLOAD` without hardware
binding. Off/software runs and their nonzero retransmission counts remain in
the [machine-readable report](../reports/full-r14-validation.json), rather
than being averaged away. PPPoE reconnect and actual MTU 1492 passed; the
1464-byte ICMP payload check was not a complete DF/PMTU boundary test.

A separate **180-second-per-direction** hardware NAT run reached
2339.54 / 2041.89 Mbit/s, with **173 / 0 TCP retransmissions**. The outgoing
retransmissions were not individually traced and are not declared fixed or
explained by clean accelerator counters. The checked `Filtered`, FCS,
oversize, overflow and underrun counters and softnet drop counts did not
increase. PCIe AER remained zero; maximum sampled temperatures were
62.2 / 62.8 °C. This six-minute traffic sample is not long-term stability
or thermal-limit certification.

## Both radio roles and basic network services

Actual HE association and traffic were tested with **RU**, channel 1 / HE20
on 2.4 GHz and channel 36 / HE80 on 5 GHz. Each case tested a real DHCP lease,
local DNS, IPv4 and manually assigned ULA IPv6 pings (ten packets per family,
zero loss), then two 20-second, two-stream TCP directions. The radio network
was separate from the wired management network, not bridged over the cable.

| Band / security | AP / station | Station→AP / AP→station (Mbit/s) | TCP retransmissions |
| --- | --- | --- | --- |
| 2.4 GHz HE20, WPA3-SAE / required PMF | second / first | 169.41 / 170.86 | 120 / 81 |
| 2.4 GHz HE20, WPA2-PSK / optional PMF | first / second | 184.05 / 160.06 | 0 / 86 |
| 5 GHz HE80, WPA3-SAE / required PMF | second / first | 1099.62 / 1383.78 | 340 / 0 |
| 5 GHz HE80, WPA2-PSK / optional PMF | first / second | 1084.36 / 1394.11 | 268 / 0 |

Very close placement produced unusually strong received signals. These are
endpoint/service checks with default backlog, not loss-free wireless,
wireless-routing offload or range tests. Both PHYs returned and collected
logs had no panic, Oops, CPU warning or AER growth. The earlier actual
[US-location EHT80 forwarding tests](US-EHT-TEST.md) remain a separate scope;
this matrix does not add 6 GHz, MLO, DFS/radar, roaming or extended wireless
stability acceptance.

## USB: defect found, not hidden by the successful service tests

The same direct-connected RTL9210B bridge/SSD worked at 5000 Mbit/s/UAS on
the workstation and first full-r14 unit, but only 480 Mbit/s/usb-storage on
the second unit. Repeated direct reads, filesystem checking and an exclusive
64 MiB write/remount/read comparison passed; formatting was unnecessary.
Some earlier second-unit boots had USB command timeouts and slow startup.

The [USB clock diagnosis](USB-CLOCK-DIAGNOSIS.md) found AUX/LFPS/mock-UTMI
rates left at 24 MHz on the stock-loader unit. Board-scoped explicit rate
assignment in the **r15 candidate kernel** restored 5000 Mbit/s/UAS on that
unit, including an owner-confirmed power-off/on cycle, matching consecutive
256 MiB reads and read-only ext4 checking. Those r15 results do not retroactively
accept full r14's USB3 initialization. A live rebind of the outer USB wrapper
also caused an unexplained restart; it is not a recommended recovery method.

## Cleanup and remaining gates

After the full-r14 sequence and again after the USB investigation, independent
checks verified original network/wireless/firewall/DHCP bytes, private access,
image/protected-partition readbacks, disabled WAN/radios/persistent offloading,
RU selection, original backlog/ECN/EDMA/RPS policy, no pending UCI changes,
removed test processes/tools/routes and the PC's preserved Wi-Fi Internet
route. The later r15 kernel experiment and same-full-image upgrades on both
units are recorded separately in the [USB/r15 investigation](USB-CLOCK-DIAGNOSIS.md).

Physical LEDs/buttons still need owner observation; factory reset and recovery
writes were deliberately not exercised. USB hotplug repetitions, other USB
devices and power delivery, VPNs, prefix delegation, PPPoE IPv6, QinQ,
provider-specific services, MLO/6 GHz, power-loss safety and long-duration
stability remain outside acceptance. The request to test the firmware is
not a claim of exhaustive proof that every possible feature works.
