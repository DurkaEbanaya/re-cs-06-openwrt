# Acceleration in this particular build

This is a pinned LEDE-derived IPQ53xx port, not an official generic OpenWrt
release and not QWRT. "Open source" does not mean "CPU-only", and a driver
being proprietary does not by itself establish which traffic it accelerates.

## Implemented paths versus enabled and measured paths

- The installed `qcom_ppe` module drives the Qualcomm Packet Processing
  Engine and EDMA; QCA8K/DSA drives the external QCA8386 switch. These are
  compiled C drivers in this source tree, not a userspace routing shortcut.
- The compiled PPE source includes `ppe_flowtable.c` and the netdevice
  `TC_SETUP_FT` callback. It translates supported netfilter flowtable rules
  into hardware next-hop/flow entries, including address/port translation
  and a supported PPPoE path. Unsupported rules fall back to software.
  Source support is not proof that a particular topology/protocol offloads.
- This driver also implements a PPE direct-switch interface for ath12k.
  Runtime debugfs shows registered PCI-radio rings. Ring registration is
  not proof that arbitrary Wi-Fi, bridge or routed traffic bypasses CPU.
- ath12k and mac80211/hostapd are source-built host software; the radios
  still run separately downloaded proprietary Qualcomm firmware. Removing
  vendor UI/proxy packages does not remove the radio's firmware requirement.
- The installed package set does not include the vendor QSDK NSS/ECM
  acceleration stack. Its absence must not be confused with absence of the
  separate native PPE implementation above, or a claim of feature parity.

For reproducible correctness tests, the current firewall configuration has
**both software and hardware flow offloading disabled**. At the initial
inspection PPE flowtable counters reported `bound:0 replace:0` and zero
active flow entries. This was the initial state, before the routed tests below.
Earlier iperf tests terminated on the router, not through it; these normally
exercise the CPU endpoint and cannot measure routed flowtable acceleration.
RPS/packet steering moves CPU processing between cores; it is not hardware
NAT or an NSS substitute.

## Acceptance before enabling acceleration by default

Use separate LAN and WAN endpoints and compare off/software/hardware modes
at identical rates and packet sizes. Require successful hardware bind and
packet/byte counter growth, not merely an enabled LuCI checkbox. Compare
throughput, CPU load, retransmissions and firewall behavior; test IPv4 NAT,
IPv6, reconnects and any required PPPoE/VLAN topology independently. Unsupported
tunnels, VPN encryption, SQM, helpers and local endpoints can remain CPU paths
even when ordinary routed flows offload. Do not promise line-rate VPN or all
QWRT features from the presence of PPE.

Enabling an untested fast path globally just to improve a benchmark can hide
correctness problems or change accounting/QoS behavior. It is a separate
acceptance step, not a reason to replace the bootloader or calibration.

## Routed hardware result

The later [resource audit](RESOURCE-AUDIT.md) verified IPv4 NAT through
JDCloud, rather than terminating traffic on it: valid PPE entries, increasing
packet/byte counters and conntrack `HW_OFFLOAD`, with 2.17/2.33 Gbit/s and
about 0.3% aggregate CPU busy during the sampled runs. This establishes a
working tested native hardware path, not NSS feature parity or acceptance
of every tunnel/protocol. Software-only ingress selection needed a separate
board-scoped fix. Both offload settings and WAN were returned to disabled
after diagnostics; see the audit for retransmissions and remaining gates.

## Current scoped completion

Subsequent r6 tests confirmed IPv6 PPE forwarding, actual PPPoE IPv4, tagged
LAN VLAN NAT and routed HE80 with PCI-radio Direct Switch. ARMv8 CryptoAPI
CE drivers are installed and kernel selftests report success. See the
[conditional-completion matrix](CONDITIONAL-COMPLETION.md) for accepted paths,
evidence and exclusions. This supersedes the earlier pending protocol gates
above without changing the historical measurements. The accepted scope is
not “every hardware feature”, NSS parity, VPN line rate or EHT/MLO support.
