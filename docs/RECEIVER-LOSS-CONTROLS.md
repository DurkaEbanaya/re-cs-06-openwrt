# Routed retransmission follow-up: receiver-side loss evidence

## Updated conclusion and independently supplied investigation

The owner supplied a summary of a separate **48-run Keenetic investigation**.
Its `REPORT.md` and `results.csv` were not present in this workspace at review
time, so the following additional measurements are attributed to that supplied
summary, not independently reanalysed raw evidence. They must not be merged
with the different local-control measurements below as if they were one run.

- At an actual 280 Mbit/s, changing **only the test server's receive buffer**
  to 2 MiB eliminated UDP socket drops in alternating local-loopback and
  external runs. Reported loopback loss: 431 → 0 → 1621 → 0; external loss:
  473 → 0 → 5341 → 0. The sender and its send buffer were unchanged. This is
  a stronger receive-only control than our earlier two-endpoint `-w` tests.
- At an actual 500 Mbit/s external UDP rate, Keenetic CPU1 reached 97–99%
  utilization, approximately 93–95% in softirq. Its receive RPS targets CPU1.
  Receive-buffer overflow persisted even at 2 MiB. This supports a processing
  ceiling under this specific packet-rate/load, not just insufficient buffer
  space or defective physical hardware.
- In a reported instrumented TCP episode, original bytes appeared at Keenetic
  `eth2.1`, but were not acknowledged until retransmission while
  `TCPBacklogDrop` grew. That episode was localized after that receive
  observation point to Keenetic's receive processing. This is a busy TCP
  socket's backlog, not the SYN backlog or `netdev_max_backlog`.
- Separate paired captures reportedly showed no sequence gaps at JDCloud's
  WAN capture point, reordering at Keenetic's receive point, and DSACKs for
  some already received bytes. The reordering cause remains open: JDCloud
  TX/NIC, the physical path, aggregation and Keenetic's driver/queues are
  between those software observation points. LRO/RPS interaction is a
  hypothesis, not an identified bug or permission to disable offloads.

Selected externally reported results (actual sender → receiver rates):

| Scenario | Mbit/s | UDP lost / TCP retransmitted |
| --- | ---: | ---: |
| Local TCP through loopback | 3785.8 → 3784.9 | — / 0 |
| External UDP, default receive buffer | 280.0 → 274.9 | 5341 / — |
| External UDP, receive buffer 2 MiB | 280.0 → 280.0 | 0 / — |
| External UDP, default receive buffer | 500.0 → 426.5 | 75294 / — |
| External UDP, receive buffer 2 MiB | 500.0 → 493.2 | 6978 / — |
| PC → JDCloud NAT → Keenetic TCP | 1733.3 → 1731.5 | — / 8 |

Practical verdict: **Keenetic receiver queue/processing limits explain
specific reproduced losses; these runs are not a reliable sole reference
for declaring JDCloud forwarding broken.** Increasing buffering absorbs
bursts but does not add CPU capacity. This does not clear JDCloud's entire
TX path or explain every TCP retransmission. Reordering still needs an
independent receiver or separately agreed, reversible aggregation controls.
No VPN, ordinary-forwarding or total Keenetic hardware limit follows from
local iperf reception, and no HincyRay/Mihomo fault was established.

The installed JDCloud firmware was not changed in response. No permanent
receiver tuning was applied. Further tests must be coordinated with the
owner's parallel investigation rather than launching overlapping traffic.

The installed r6 firmware is unchanged in these tests. The PC sends through
JDCloud's hardware-offloaded IPv4 NAT to Keenetic's system iperf3 receiver.
Both JDCloud Ethernet links negotiate 2500 Mbit/s full duplex. No VPN routes,
global receive-buffer settings or persistent CPU/queue tuning are changed.
This document does not claim that every earlier TCP retransmission has the
same cause as an overloaded UDP receiver.

## Repeated TCP segmentation controls

Six two-stream, 15-second outbound runs alternated default writes, 16 KiB
writes and MSS 1200. Throughput ranged from 2110 to 2317 Mbit/s and TCP
retransmissions from 8 to 904. The identical default test gave 483 and 8
retransmissions at different points in the sequence. Neither smaller MSS nor
write size established a repeatable fix.

Keenetic's `TCPBacklogDrop` increased by 135, 31, 154, 17, 2 and 2 over
those intervals, respectively. These are system-wide counters, which also
include unrelated traffic; they demonstrate receive-path pressure but do
not map one-to-one onto the test's TCP retransmission count. DSACKs and
receive-queue collapsing were also observed. `TCPPrequeueDropped` remains
unsuitable as a literal discarded-packet count on this older kernel.

## UDP sequence and kernel counters

Single-stream UDP uses 1200-byte datagrams and 12-second runs. The initial
outbound 500 Mbit/s, 1 Gbit/s and 2 Gbit/s runs reported losses of 37.8%,
50.1% and 74.7%, while Keenetic's UDP receive-buffer errors grew. Its softnet
backlog-drop deltas were 439, 596943 and 1833116; JDCloud's corresponding
softnet-drop deltas were zero. Counters observe different processing stages,
so these totals must not be added or treated as a per-packet attribution.

A later 500 Mbit/s run lost exactly **10629 datagrams**, matching the
**10629 increase in Keenetic `Udp:RcvbufErrors`** over that interval, with
zero softnet-drop growth on either router. No out-of-order datagrams were
reported. This is strong evidence of actual receiver socket drops in that
specific test, not just TCP's interpretation of delayed/reordered delivery.
It is not proof that all loss at higher rates occurred at that same stage.

Reverse UDP requested 1 Gbit/s but the sender achieved only about
729 Mbit/s, with zero reported loss. Do not describe this as a successful
1 Gbit/s loss-free test.

## Per-test controls, not permanent workarounds

At 500 Mbit/s, alternating the sender's pacing timer between 1000 and
100 microseconds produced loss percentages 4.60, 3.32, 3.39 and 3.28.
Smoother timer pacing did not eliminate the problem.

Alternating default socket buffers and `iperf3 -w 1M` at the same rate
produced 2.78%, 0.50%, 3.62% and 0% loss. Only that test's sockets are
changed; the option can affect both endpoints. This supports sensitivity
to buffering/scheduling, not a verified global tuning prescription.

The corresponding TCP socket-buffer A/B produced 29, 7, 48 and 60
retransmissions at 2276–2317 Mbit/s (autotuned, 1 MiB, autotuned, 1 MiB).
The last larger-buffer run was worse than the preceding default run. This
is evidence against calling a larger buffer a general TCP fix.

Removing PC forwarding/NAT from the data path and sending directly from a
temporary JDCloud WAN-side client to the same receiver still produced UDP
loss: 28560, 1357, 53844 and 58280 datagrams at 500 Mbit/s (default, 1 MiB,
default, 1 MiB buffers). Keenetic receive-buffer errors grew by 28560, 1357,
53731 and 46002, respectively. Most or all loss in those intervals therefore
has receiver-side evidence even without traversing JDCloud's NAT path.
The final larger-buffer run did not fix it; load and scheduling still vary.

## Local receiver control, excluding JDCloud entirely

The same system iperf3 client and server then communicated locally on
Keenetic, both bound to its own LAN address. Neither JDCloud nor an external
Ethernet path forwards those data. The default-buffer runs lost **4538** and
**4072** datagrams; the receiver's `Udp:RcvbufErrors` increased by exactly
**4538** and **4072**. Alternating 1 MiB socket-buffer runs both reported zero
loss and zero receive-buffer errors. The sender did not achieve the requested
500 Mbit/s: actual receive rates were approximately 320–344 Mbit/s, so this
is not a controlled equal-throughput comparison to the external tests.

This proves that a local receiving/socket/scheduling limitation on Keenetic
can produce the observed UDP loss independently of JDCloud. It does not
establish every contributing condition in the external path or causally
explain all TCP retransmissions. The receiver has existing services and an
older kernel; those services were not stopped to manufacture a clean result.

Two local TCP controls on Keenetic delivered 4406.5 and 4444.0 Mbit/s with
2 and 1 retransmissions, respectively. This shows that a small nonzero
iperf retransmission count can occur without the external path, but is
not an explanation for the hundreds of retransmissions in some routed runs.

Keenetic's inspected limits were 229376-byte default receive buffers,
2097152-byte maximum receive buffers and a 1000-packet softnet backlog.
Those values were not modified. There is no justification here to reflash
JDCloud, suppress errors, mask AER or permanently cap bandwidth.

Raw captures and counter snapshots remain private. Machine-readable
sanitized results are recorded separately. The earlier Ethernet outage and
unused eMMC space are separate issues; this investigation neither modifies
GPT nor establishes the cause of the outage.
