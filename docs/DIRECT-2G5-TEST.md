# Direct workstation ↔ JDCloud comparison

The workstation's internet connection was moved to Wi-Fi by the owner.
Its Intel I225-V rev 03 Ethernet interface (`igc`) was connected directly
to JDCloud's logical LAN3. Both ends reported **2500 Mbit/s, full duplex**.
Keenetic and the USB Ethernet adapter are absent from this test data path.

An active-only NetworkManager change assigned a separate test subnet with
no Ethernet gateway or DNS. The internet default route remained on Wi-Fi.
The installed router image was not changed and no reboot was needed.

## Initial endpoint tests

Two TCP streams, 15 seconds per run; receiver goodput:

| Direction / transport | Mbit/s | Sender retransmits |
| --- | ---: | ---: |
| Workstation → JDCloud IPv4, 1 | 1696.59 | 1 |
| JDCloud → workstation IPv4, 1 | 1142.03 | 949 |
| Workstation → JDCloud IPv4, 2 | 1869.24 | 1 |
| JDCloud → workstation IPv4, 2 | 1103.59 | 810 |
| Workstation → JDCloud IPv6 | 1613.44 | 273 |
| JDCloud → workstation IPv6 | 1093.66 | 609 |

The reverse-direction symptom is reproducible without Keenetic. This
excludes Keenetic as a necessary cause of this reproduction; it does not
prove that every earlier retransmission had the same cause or exclude
both endpoint drivers. PHY/error/drop counter deltas collected on the
active JDCloud port and workstation NIC were zero during these baseline
runs. These counters do not measure every queueing or ordering failure.

## CPU affinity and offered-load controls

Single-stream reverse tests with the sender pinned to JDCloud CPU0 returned
1271.99, 1281.04 and 1278.86 Mbit/s with **zero retransmits**; an IPv6 run
returned 1235.50 Mbit/s with zero retransmits. Pinning to CPU1 returned
1758.37 Mbit/s with 462 retransmits and 1752.09 Mbit/s with 362 retransmits.
CPU1 paced at 1200 Mbit/s returned 1199.17 Mbit/s with 13 retransmits.

Other reverse controls: zero-copy 1105.68 Mbit/s / 65 retransmits; 16 KiB
writes 1434.16 Mbit/s / 727; two streams paced at 500 Mbit/s each,
999.76 Mbit/s / zero. These change burstiness, speed and scheduling as well
as the selected CPU; they are not standalone proof of a driver defect.

The pinned EDMA driver implements `edma_port_select_queue()` by returning
the current CPU. `edma_port_xmit()` then uses the queue mapping to select
one of the transmit rings. ACK-driven sends and process-driven sends on
different CPUs are therefore a candidate source of cross-ring ordering
changes. The initial receive RPS mask on all four conduit RX queues was 1
(CPU0). This source observation is a hypothesis to test, not evidence that
cross-ring reordering was directly traced in the running driver.

Changing RPS initially produced zero-retransmit CPU1 runs, but restoring
the original mask also produced a zero-retransmit run. That comparison is
inconclusive and must not be reported as a fix. Subsequent comparisons
delete only the test destination's cached TCP metrics before each run to
reduce learned-state carry-over, then alternate original and test masks.

These are local endpoint tests, not routing/NAT benchmarks or proof of
full 2.5G forwarding throughput.

## Alternating RPS tests with per-destination TCP metrics reset

The sender's cached TCP metrics for the test destination were deleted
before each run. No global TCP metrics cache was flushed. Each run lasted
12 seconds; affinity refers to the JDCloud sending process.

| RPS CPU | Sender CPU / streams | Mbit/s | Retransmits |
| --- | --- | ---: | ---: |
| 0 | CPU1 / 1 | 1753.47 | 795 |
| 1 | CPU1 / 1 | 1650.14 | 0 |
| 0 | CPU1 / 1 | 1735.50 | 350 |
| 1 | CPU1 / 1 | 1630.23 | 0 |
| 0 | unpinned / 2 | 1135.54 | 720 |
| 1 | unpinned / 2 | 1780.34 | 3033 |
| 0 | unpinned / 2 | 1135.42 | 662 |

Thus the single-flow same-CPU improvement reproduced under alternating
conditions, but setting RPS to CPU1 is **not a general fix**: the unpinned
two-stream test still had many retransmissions.

## Equal-rate ring counter comparison

One sending process was pinned to CPU1; one IPv4 stream was socket-paced at
1600 Mbit/s for 15 seconds. RPS alternated CPU0/CPU1/CPU0/CPU1:

| RPS CPU | Mbit/s | Retransmits | TX completion ring 4 delta | Ring 5 delta |
| --- | ---: | ---: | ---: | ---: |
| 0 | 1594.78 | 79 | 94398 | 2062213 |
| 1 | 1595.83 | 7 | 14020 | 2142295 |
| 0 | 1591.38 | 69 | 109100 | 2042817 |
| 1 | 1596.18 | 10 | 8660 | 2148510 |

These are the driver's `desc_with_more_bit` completion counters, not a
per-flow wire capture or exact TCP-packet counts. They include background
management traffic. Nevertheless, changing the ACK processing CPU reduces
both use of the additional ring and retransmissions at almost equal
receiver goodput. This strengthens the cross-ring ordering hypothesis;
it does not directly demonstrate a particular packet overtaking another.

## Candidate source change — not installed

Patch `0013-qcom-ppe-preserve-socket-tx-queue.patch` replaces the per-packet
current-CPU selection with `netdev_pick_tx()`, the core socket-cached,
XPS/flow-hashed selector. The core permits queue changes when safe, rather
than unconditionally following the current execution CPU. Multiple queues
remain available; no global CPU pinning or speed limit is introduced.

The inner patch applies in a dry run against the prepared kernel source.
A small C regression test extracts the added selector body and checks its
delegation, arguments and returned queue with a mocked core selector.
It does **not** test real kernel socket state, ordering, performance or
hardware. The modified driver has not been built/booted in this stage;
there is no verified firmware fix yet. A controlled before/after image
test is required before attributing the full problem to this code.

## Cleanup

All four conduit RPS masks were restored to 1. TCP recovery/reordering
settings remained 1/3. No NIC offload, global affinity, firmware or router
startup setting was changed. The temporary iperf server was stopped and
its executable/PID file removed. WAN and Wi-Fi remain disabled. Internet
remained on the workstation's Wi-Fi, and the Ethernet test address has no
default gateway or DNS.

JDCloud DHCP/RA services remain runtime-stopped from the earlier LAN-to-LAN
test. Direct isolated attachment no longer puts them on Keenetic's LAN;
their saved enablement was left unchanged. Do not reconnect LAN-to-LAN and
reboot without addressing the two-DHCP/RA-server conflict.
