# Retransmission capture investigation — 2026-11-03

## Verdict

**The exact underlying hardware/driver cause is not established.** Do not
describe a pacing workaround, a zero hardware-error counter, or the results
below as a verified firmware fix. The evidence distinguishes duplicate
delivery from missing first copies, but does not identify every loss point.

## Method and evidence

A temporary statically linked libpcap collector captured only IPv6 TCP port
5201, with 160-byte snapshots and no promiscuous mode, on JDCloud LAN2 and
Keenetic's LAN bridge. Raw captures contain private network metadata and
remain local. They were not published. Both collectors reported zero capture
drops. Capturing consumes CPU and changes the workload; results are not
interchangeable with the earlier uncaptured throughput runs.

Keenetic GRO combines segments, making direct packet-count comparisons
misleading. A second paired capture temporarily disabled GRO on Keenetic's
physical interface and bridge and used one stream with fixed process CPU
affinity. This allowed matching exact TCP sequence/length pairs:

- 194 distinct sequence/length pairs were transmitted again by JDCloud.
- For 134 of those pairs, both copies appeared in Keenetic's receive capture.
- For 60, only one copy appeared in the receive capture.
- All 134844 receiver ACK records matched records in the sender capture
  (sequence, ACK, flags and options); no missing reverse ACK record was found.
- For the 134 duplicate-delivery cases, the cumulative ACK covering the data
  was emitted after the duplicate arrived. First-copy-to-cumulative-ACK
  intervals were approximately 13–38 ms in that captured workload. This can
  include waiting for earlier gaps; it is not proof of a delayed-ACK bug.

The first GRO-enabled capture also contained DSACKs. These establish that
some retransmissions duplicated already received data, not that every
retransmission was spurious. Software capture before/after NIC processing
cannot prove where an original copy was lost or delayed. Driver/offload
behavior and capture-start timing remain limitations. A later physical/bridge
capture also demonstrated VLAN/GRO representation differences; raw record
counts were not treated as wire packet counts.

## Controlled comparisons, all reverted

Reverse direct-router tests used two streams, 12–15 seconds each. Results
vary with CPU scheduling and load; each comparison is evidence against a
simple proposed fix, not exhaustive elimination of a subsystem.

| Temporary change | Result |
| --- | --- |
| Disable JDCloud RACK | 756 retransmits, versus 693 before and 734 after |
| Disable Keenetic GRO | Throughput fell to about 435 Mbit/s; 293 retransmits remained |
| Disable Keenetic TCP prequeue using `tcp_low_latency` | 936 retransmits, versus 688 before and 597 after |
| Disable Keenetic receive RPS | 486 retransmits, versus 880 before and 596 after |
| Raise Keenetic backlog 1000 → 10000 | 779 retransmits, versus 626 before and 727 after; softnet drops did not grow in these runs |
| Raise JDCloud TCP reordering threshold 3 → 300 | 672 retransmits, versus 638 before and 690 after |

`TCPPrequeueDropped` is **not reliable evidence of discarded packets** here:
the Linux 4.9 implementation increments it while flushing the prequeue into
normal processing. Its growth stopped when prequeue was disabled, but TCP
retransmits did not. No persistent tuning was applied.

JDCloud EDMA error/descriptor-exhaustion counters and PPE queue-drop counters
were zero in the collected snapshots. PPE drop reason 122 was identified as
pause-frame accounting, not proof of discarded TCP data. These counters do
not rule out all hardware, switch or receiver losses.

## Cleanup and next boundary

All tested runtime settings were restored: Keenetic GRO enabled, receive RPS
mask 2, backlog 1000, `tcp_low_latency=0`; JDCloud `tcp_recovery=1` and
`tcp_reordering=3`. Temporary collectors, packet files and iperf server were
removed from both routers after copying evidence locally. VPN routes,
startup configuration and firmware were not changed.

The owner requested shutting down the workstation after the investigation.
The unresolved conclusion is retained explicitly rather than claiming an
exact diagnosis. Further localization needs a wire-side capture or independent
receiver/firmware comparison with controlled NIC/offload conditions. The
LAN-to-LAN DHCP/RA precaution from `KEENETIC-TEST.md` still applies: JDCloud's
services were stopped only at runtime and can restart on router reboot.
