# Ethernet comparison through a Keenetic switch

The owner connected JDCloud LAN2 to the Keenetic's 2.5G port, replacing the
host USB Ethernet path. Read-only ethtool inspection on JDCloud reported
**2500 Mbit/s, full duplex, link up**. The host's onboard Ethernet link to
Keenetic remained **1000 Mbit/s**, so this topology cannot establish 2.5G
end-to-end throughput.

JDCloud's DHCP and IPv6 RA/DHCP services were stopped for this test because
LAN-to-LAN attachment otherwise exposes two configuration servers to the
same network. Saved configuration and service enablement were not changed;
a reboot can restart those services. Do not leave this arrangement across
reboots without a separately agreed LAN/DHCP configuration.

The endpoint test uses IPv6 link-local addressing across the switch, with
the existing SSH host key pinned. No Keenetic management login or router
configuration change is needed for this switched-host phase. Two TCP streams run for 15 seconds in each
direction. Forward/reverse refer to computer-to-JDCloud/JDCloud-to-computer,
not WAN/NAT forwarding.

The earlier USB tests used IPv4. This comparison changes the receiver NIC,
path, switch ingress/egress rates and IP version; it can identify a better
working path but cannot alone prove an RTL8153 driver defect or rule out
all JDCloud transmit/queueing issues.

## Unpaced results

| Direction/run | Receiver Mbit/s | Sender TCP retransmits |
| --- | ---: | ---: |
| Computer → JDCloud, 1 | 927.01 | 1 |
| JDCloud → computer, 1 | 914.97 | 40856 |
| JDCloud → computer, 2 | 904.61 | 40686 |
| Computer → JDCloud, 2 | 927.70 | 0 |

The reverse-direction problem therefore also occurs without the USB NIC.
The 2.5G-to-1G rate transition makes switch buffering, burstiness and flow
control additional variables; packet loss has not been localized. JDCloud
LAN2 FCS/alignment/overflow/underrun counters remained zero, and its pause
counters did not grow between the collected snapshots. This does not show
the Keenetic's egress-drop counters or prove the absence of queue drops.
Host onboard-NIC CRC, missed/error and per-RX-queue drop/checksum counters
also showed zero increase over the collected interval.

## Socket-paced reverse tests

With two streams paced at 400 Mbit/s each, the receiver reached 799.94 Mbit/s
with zero retransmits. At 450 Mbit/s per stream it reached 899.82 Mbit/s,
also with zero retransmits (15 seconds each). This supports sensitivity to
offered load/burstiness along this path, without localizing the loss or
establishing a full-rate fix. No persistent pacing setting was installed.

## Direct-router method

Authenticated Entware SSH access exposed an already available system binary,
`/usr/bin/iperf3` version 3.19, even though the web diagnostics did not offer
the iPerf component. It was unnecessary to run `opkg update`, install new
packages, change VPN routing or reboot Keenetic. Web component availability
alone was therefore insufficient to establish binary availability.

The direct comparison runs that binary as the client on Keenetic, targeting
the temporary JDCloud IPv6 server through the LAN bridge. This removes the
computer's Gigabit link from the traffic path. The SSH session only carries
commands/results; bulk test traffic stays between the two routers. Endpoint
CPU/software limits still apply, so a 2.5G physical link does not guarantee
2.5G application throughput.

| Direct direction/run | Receiver Mbit/s | Sender TCP retransmits |
| --- | ---: | ---: |
| Keenetic → JDCloud, 1 | 1607.11 | 218 |
| JDCloud → Keenetic, 1 | 1127.41 | 433 |
| Keenetic → JDCloud, 2 | 1618.68 | 244 |
| JDCloud → Keenetic, 2 | 1113.84 | 952 |

Both directions exceed Gigabit throughput, but neither reaches the physical
link's application ceiling. Retransmissions remain without the computer or
USB NIC in the data path. This is not a NAT/forwarding benchmark and does not
localize the loss to a specific router, queue or driver.

With a requested socket pacing rate of 500 Mbit/s per stream, JDCloud →
Keenetic delivered **996.06 Mbit/s with zero retransmits**. The opposite
direction delivered 1705.41 Mbit/s with 108 retransmits, exceeding the
requested aggregate rate. Therefore that pacing request was not effective
on the Keenetic sender and must not be described as a controlled 1G test
in that direction. No persistent pacing or queue settings were changed.

JDCloud LAN2 FCS/alignment/overflow/underrun counters remained zero. The
temporary JDCloud server was stopped and its executable/PID file removed.
No Entware package, VPN policy or Keenetic startup configuration was changed.
