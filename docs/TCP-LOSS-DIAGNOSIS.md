# TCP loss diagnosis after the two-router r12 tests

This is an investigation record, not a claim that every TCP retransmission
is a firmware defect or that all observed retries have been eliminated.
The PC's internet stayed on Wi-Fi; router management and test routes used
isolated Ethernet. Raw captures, identities and test credentials are private.

## Distinct loss locations

1. **Wired traffic terminating on the second router:** at unrestricted
   2.5G TCP receive rates, the LAN-port `Filtered` counter grew almost
   one-for-one with TCP retransmissions. There was no simultaneous CRC,
   EDMA-drop, softnet-drop or TCP receive-backlog-drop growth in the initial
   unidirectional controls. The first router's local receiver control did
   not show the same loss. This is not an independent forwarding benchmark.
2. **Software-routed wireless traffic with offload disabled:** AP softnet
   backlog drops matched retransmissions exactly in four HE80/EHT80 runs
   (606/150 and 467/98, forward/reverse). Hardware-offloaded runs avoided
   that specific CPU backlog loss. Increasing the backlog temporarily
   removed those drops in one EHT comparison, but did not eliminate every
   retry; this is not yet accepted as a persistent queue/latency policy.

## QCA8386 PAUSE reaction reserve

The MHT queue-manager control register at `0x808` read `0x007f004e`:
`FLOW_DROP_EN` was set and the six-bit `FLOW_DROP_CNT` field was 14.
Qualcomm SSDK's MHT initialization uses a reaction count of **60**.
The field and policy were checked against `isisc_reg.h`, `isisc_qos.c` and
the `CHIP_MHT` branch of `ssdk_init.c` in
[OpenWrt's qca-ssdk tree](https://github.com/openwrt/qca-ssdk/tree/openwrt).
Do not confuse MHT HOL queue fields with the older QCA8337 layout.

A reversible, board/ID-scoped RAM module changed only the reaction field
to 60 (`0x007f007c`) and restored it on unload. In isolated 15-second,
four-stream receive comparisons:

| State | Receive Mbit/s | TCP retries | LAN Filtered delta |
| --- | ---: | ---: | ---: |
| Original, repeat 1 | 2332.80 | 1101 | 1101 |
| Original, repeat 2 | 2314.13 | 744 | 744 |
| Reaction count 60, repeat 1 | 2347.12 | 1 | 0 |
| Reaction count 60, repeat 2 | 2347.11 | 1 | 0 |
| Restored, repeat 1 | 2316.98 | 797 | 795 |
| Restored, repeat 2 | 2346.86 | 1792 | 1791 |

Repeated isolated 30-second comparisons also removed `Filtered` growth,
but residual TCP retries varied (3, 522, 7 in the changed setting), including
reordering/duplicate-segment indications. Therefore the switch-drop
correction must **not** be described as solving all observed TCP retries.
Separate CPU-WRED-disable and ingress-buffer-only experiments did not
resolve the original loss and were fully reverted.

One longer wired run and one 4096-backlog wireless run accidentally
overlapped. They are explicitly excluded from isolated performance and
backlog-policy acceptance; their private directories carry limitation
notes. Subsequent experiments are serialized.

Patch `0021` applies the MHT reaction reserve during QCA8386 initialization,
preserves unrelated QM bits, propagates MDIO/register errors and leaves
other switch models unchanged. It does not disable PAUSE, WRED or AER,
change calibration, pace the sender or enlarge arbitrary HOL queues.
The full r13 candidate was installed on the second router. Kernel/rootfs,
protected partitions, same-device access files, both radio PHYs, PCIe Gen3 x2
and zero AER totals were verified. Six serialized 30-second four-stream
receive runs reached 2346.39–2347.41 Mbit/s with **zero Filtered growth**.
Default steering produced 11/10 retries, a temporary single-ring control
0/2, and restored default steering 7/2. The steering control was reverted:
this does not establish a persistent single-ring fix or zero-retry guarantee.

## Upgrade configuration regression found during r13 verification

The checked configuration archive restored the password, authorized key,
SSH host keys, wireless/firewall configuration and test markers, but the
image's `90-minimal-defaults` script subsequently replaced the owner's LAN
address with the initial `192.168.76.1`. SSH remained accessible with the
same private key at that address. The exact saved same-device network file
was restored, returning management to the lab subnet; no reset/reflash was
used to repair access. All saved configuration hashes then matched again.

The public defaults script now recognizes a restored archive containing
`etc/config/network` and does not overwrite it. Fresh installation and
access-only seeds still get conservative initial defaults. Tests cover
both preinit archive forms and optional `./` paths. This source correction
was added after the r13 image build. A subsequent full **loss-fixes-r14**
upgrade on the second router passed: the management address and all nine
checked configuration/access files retained their exact saved hashes without
manual repair. Kernel/rootfs readback, protected stock/bootloader/calibration
partitions, persistent ext4, both PHYs, Gen3 x2, zero AER totals and boot
counter zero were checked. The first router remains on r12; no r14 load
benchmark or first-router r14 installation is implied by that upgrade check.

## Residual Wi-Fi software-path retries

With a temporary backlog of 16384, a serialized EHT80 test eliminated the
previous softnet backlog drops. Its reverse software-forwarded run still
had eight TCP retransmissions. A filtered trace with zero buffer overruns
captured **eight `QDISC_CONGESTED` drops at `__fq_codel_dequeue` on the AP**;
the AP's switch-output qdisc counters also increased by eight (four on
each of two output queues). The station sender recorded eight TCP retries.
The forward software run had zero retries, and the earlier hardware-path
comparison had zero retries in both directions.

This distinguishes intentional active queue management from switch-buffer
overflow and software receive-backlog exhaustion. Disabling fq_codel or
inflating its target merely to obtain a zero-retry number is not accepted
as a fix. ECN negotiation was tested below as a way to signal congestion
without dropping eligible packets; non-ECN peers must still be handled.
The temporary receive-backlog setting is not yet a permanent image policy.

The first broad radio drop trace filled its buffers with unspecified frees
and lost events. It is not used as evidence that other losses were absent.
The narrower repeat excluded those frees and reported no buffer overruns.

An ECN control initially changed only the routers, which did not negotiate
ECN on PC-initiated connections; it still produced eight AQM drops/retries.
After temporarily enabling ECN requests on the PC too, all four EHT80
software/hardware forward/reverse runs had zero TCP retries. The software
reverse run recorded seven ECN marks instead of qdisc drops. No qdisc was
disabled or its latency target enlarged. The setting was a controlled
endpoint experiment, not a way for a router to force arbitrary clients to
use ECN or a universal zero-loss claim. Temporary settings are restored
after testing; congestion loss remains expected for non-ECN flows.

## Wired residuals: sender Tail Loss Probes

After the hardware correction, two additional 45-second receive runs
reached 2346.99/2346.94 Mbit/s with 15 retries each, without qdisc-drop
growth on either router. An independent privileged trace on the PC was
filtered to the lab TCP port and included kernel stacks. In its two runs
(2347.14/2346.80 Mbit/s, 5/2 iperf retries), all eight traced retransmit
events came through `tcp_send_loss_probe`; no trace events were lost.
The trace spans setup/teardown as well as iperf's measured intervals, so
its event total is not substituted for the reported 5+2 retries.

Receiver DSACK counters and sender socket samples recorded duplicate
acknowledgements; one retransmitted tail was only 96 bytes. These are
consistent with premature Tail Loss Probes rather than a recurrence of
the earlier switch-buffer drops. This does not prove that every retry in
every earlier run had the same cause. Disabling TCP loss recovery to force
a zero counter is not a firmware correction and is not applied.

A follow-up changed only iperf's userspace write size to an MSS multiple
(130320 bytes). The two runs still had 84 and 9 retries at 2341.37 and
2346.93 Mbit/s. Aligned writes are therefore not an accepted remedy; the
earlier 96-byte observation is not proof that write alignment caused all
residual probes.

## Final state and acceptance boundary

The switch-buffer loss has a tested source correction, and the upgrade
configuration regression has a successful full-image carryover test. The
software receive-backlog and fq_codel losses are separately localized;
temporary larger queues/ECN controls are not silently installed as generic
firmware defaults. Non-ECN congestion drops and sender loss probes are not
suppressed just to produce a zero number. A universal zero-retransmission
claim is therefore **not** made.

Cleanup verified RU with both radios disabled, WAN/WAN6 and persistent
offloading disabled, no pending UCI changes, original router backlog 1000,
ECN 2, EDMA bitmap 15 and RX RPS mask 2. Temporary test binaries, kernel
modules, tracing, NAT and host test routes were removed. The PC's temporary
ECN request setting was restored from 1 to its original 2; wired management
and Wi-Fi internet remained available before the owner-requested PC shutdown.
Private evidence and images have independently verified SSD copies. The
public binary release remains **r12-external**, not a newly tested r14 asset.
