# Two-router quick checks on full local r12

Both RE-CS-06 units run the same full local radio-sequence-r12 firmware.
Management remains wired: PC → first router LAN bridge → second router LAN.
No WAN or DHCP/RA server was enabled; the PC's ordinary internet stayed on
its separate Wi-Fi interface. This is a short functional/load check, not
long-duration product certification.

## Wired 2.5GbE control

Four TCP streams, 30 seconds per run, PC native iperf3 to an iperf3 endpoint
on the second router, through the first router's switch:

| Direction | Receiver Mbit/s | TCP retransmits |
| --- | ---: | ---: |
| PC → second router | 2343.74 | 2777 |
| Second router → PC | 1929.07 | 0 |
| Simultaneous PC → second router | 181.17 | 1442 |
| Simultaneous second router → PC | 1810.74 | 0 |

The asymmetric simultaneous result is **not a passed full-duplex line-rate
test**. It does not by itself localize the bottleneck to the switch, driver
or endpoint CPU. The second router runs the traffic endpoint rather than
forwarding to an independent receiving PC. Recorded Ethernet error/drop
fields on the active second-router LAN port remained zero; PCIe AER totals
were zero on both units. One test-script cleanup returned nonzero because
iperf3 had already removed its own PID file; all three traffic JSON results
and before/after counters were saved. Cleanup was made idempotent.

## Actual Wi-Fi capabilities and association

- Neither PHY on either unit exposes actual 6 GHz channels. A regulatory
  domain containing 6 GHz rules does not create a radio band. **Wi-Fi 6E is
  not available in the tested configuration.**
- PCI radios advertise EHT AP/STA capabilities, but the actual RU self-managed
  domain reports `NO-EHT`. Requesting EHT80 produced no working AP/STA link;
  `ieee80211be=1` in hostapd configuration is not an EHT association. The test
  returned to HE80. No false country, regulatory bypass or firmware flag
  modification was used. **Wi-Fi 7 is not accepted by this test.**
- The working control is 5 GHz channel 36, HE80, WPA3-SAE with required PMF,
  first router AP and second router STA. Sampled rates reached HE-MCS 11,
  NSS 4, 2401.9 Mbit/s PHY rate. That is not application throughput.
- Signal was exceptionally strong, approximately −9 to −14 dBm at 10 dBm
  configured transmit power. The close-range result is not representative
  of range or difficult propagation. Radio `tx failed` counters increased
  even in tests with zero TCP retransmits; no zero-radio-loss claim follows.

## Routed radio path and hardware acceleration

The PC uses an explicit route through the AP to a separate radio-only
subnet. A narrow temporary SNAT rule on the AP forces replies back over
radio rather than the shared wired management bridge. The STA's iperf3
server binds only its radio address. The radio is not bridged into management,
so there is no wired/wireless L2 loop.

Two TCP streams, 25 seconds per direction:

| AP forwarding mode | PC → STA Mbit/s | STA → PC Mbit/s | TCP retransmits out / back |
| --- | ---: | ---: | ---: |
| Offloading disabled | 1365.22 | 815.14 | 397 / 128 |
| Hardware flow offload enabled | 1398.03 | 1509.58 | 0 / 0 |

On the AP, active conntrack entries had `HW_OFFLOAD`; valid PPE NAT entries
had increasing packet/byte counters, and Direct Switch was running,
non-faulted, with increasing descriptor counters. Collected PPE bind,
readback, conflict and resource-error counters remained zero. Direct Switch
refill-failure/retry/deferred counters did increase under hardware load;
this report does not turn those into a claim of perfect radio delivery.
The offloading-disabled control had no hardware-bound flows, although the
radio's Direct Switch receive path can still run independently of NAT
offloading. The STA terminated traffic locally, with no bound PPE flows
and its Direct Switch node not running; **STA forwarding acceleration is
not established** by this topology.

No EHT, MLO, AHB-radio traffic or both-router forwarding acceptance is implied.
Both radio drivers probing successfully and AER staying zero are necessary
observations, not a substitute for those missing tests.

## Short stability and bounded duplex controls

A 60-second HE80 simultaneous TCP run with hardware offloading measured
699.97 Mbit/s PC → STA and 858.91 Mbit/s STA → PC, with 11 and 0 TCP
retransmits respectively. Concurrent ping delivered 200/200 replies, but
latency under load was **9.49 / 52.73 / 1062.71 ms min/average/max**. No
disconnect, kernel panic, Oops or CPU warning was found in the collected
post-load logs. This is a passed short connectivity check, **not low-latency
acceptance or a long-duration stability guarantee**.

A separate wired control paced at 1 Gbit/s each way delivered
999.98 / 999.92 Mbit/s simultaneously, with zero TCP retransmits. Therefore
the earlier unpaced asymmetry is not evidence that simultaneous Ethernet
exchange is entirely broken; its saturation behavior still needs isolation.
An unpaced repeat with two streams instead of four measured
1576.25 / 779.63 Mbit/s, with 84 / 0 retransmits. This substantial variation
also prevents attributing the first asymmetric result to a fixed line limit.
Sampled thermal sensors were approximately 49.9–53.9 °C. These samples do
not establish the maximum temperature or absence of throttling over time.
All collected post-load correctable/nonfatal/fatal PCIe totals remained zero
at both ends on both routers, and Direct Switch remained non-faulted.

## Cleanup and evidence

The original per-router network/wireless/firewall files were restored
byte-for-byte. Approved wired management addresses and disabled DHCP/RA
remain. Test radios, persistent flow offloading and WAN are off again;
temporary SNAT table, host radio route and RAM iperf binary/servers were
removed. Both management SSH paths and the PC's Wi-Fi internet remain.

Sanitized measurements: [`reports/two-router-r12.json`](../reports/two-router-r12.json).
Raw logs, station identity, unique test credentials and configuration copies
are private and are not public release assets.
