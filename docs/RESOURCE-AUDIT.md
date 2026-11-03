# Hardware resource audit

## CPU and cryptography

The installed r5 reports four CPUs, a `cpufreq-dt` policy with 1.1 and
1.5 GHz frequencies, `schedutil`, and a sampled current frequency of 1.5 GHz.
No overclock or forced performance governor is needed to expose that maximum.
CPU features include AES, PMULL, SHA1 and SHA2.

OpenSSL 3.6.4 already uses CPU acceleration directly. A two-second-per-size
AES-128-GCM comparison reached 691773.44 kB/s at 16 KiB blocks with normal
capability detection, versus 35717.12 kB/s with `OPENSSL_armcap=0` for that
process only. This is an EVP benchmark, not VPN or routed throughput; the
environment override was not saved globally.

Kernel CryptoAPI is a separate path: r5 registered generic AES/GHASH rather
than the ARMv8 CE AES/GCM implementations. Patch `0014` introduces an explicit
IPQ53xx-scoped package for `aes-ce-cipher`, `aes-ce-blk`, `aes-ce-ccm` and
`ghash-ce`. The r6 candidate compiled successfully, passed offline FIT/rootfs
inspection and includes autoload entries. It was not installed or validated
at that build checkpoint; the subsequent installation result is below.
Its changed kernel package ABI must not be bypassed with forced module
installation on r5.

SHA1/SHA2 library architecture support is already enabled in this Linux
version; old assumptions about separate sha*-ce modules do not transfer
automatically to its new library implementation. The generic target's QCE
config symbols do not prove a bound device: no IPQ5332 QCE device was found
in the compiled board tree/runtime driver bindings. Do not invent a crypto
engine DT node, or claim NSS/ECM compatibility, from a generic config option.
The Qualcomm hardware random-number generator is registered separately.

## Routed acceleration acceptance

The owner added a physical Keenetic-LAN to JDCloud-WAN link. The isolated
test enables WAN DHCP without accepting a default route or peer DNS. PC
source routing sends only the test destination through JDCloud; the PC's
ordinary internet connection remains on Wi-Fi. WAN input filtering is not
opened. The Keenetic system iperf server is a separate WAN-side endpoint;
the test does not terminate on JDCloud.

The first run was limited by an unexpectedly renegotiated 100 Mbit/s PC LAN
link. Its ~94 Mbit/s results are not 2.5G performance evidence. Nevertheless,
hardware mode produced valid PPE NAT entries with growing packet/byte
counters and conntrack `HW_OFFLOAD`; software mode had no PPE flow entries.
The owner reseated the LAN cable and both PC LAN and WAN then negotiated
2.5G full duplex. Repeat results must be recorded separately.

The corrected-link repeat (two TCP streams, 15 seconds per direction) gave:

| Mode | LAN → WAN Mbit/s | WAN → LAN Mbit/s | JDCloud CPU busy, directions |
| --- | ---: | ---: | --- |
| Off | 1699.72 | 1755.18 | 42.16% / 40.86% |
| Software, existing fw4 device selection | 1526.73 | 1658.44 | 40.61% / 37.91% |
| Hardware | 2173.72 | 2327.05 | 0.29% / 0.30% |

CPU percentages are aggregate `/proc/stat` busy deltas across the test
interval, not isolated packet-processing cycle counts. Hardware mode had
537 sender retransmits LAN → WAN and zero in reverse. PPE reported valid
NAT entries, increasing hardware packet/byte counters, conntrack
`HW_OFFLOAD`, and no replacement/resource/readback failures. This is positive
hardware-forwarding evidence, not proof of every protocol or saturation
condition. The CPU-based Keenetic endpoint may also constrain throughput.

The existing software-only flowtable selected `br-lan` and `wan`, while the
hardware path selected physical DSA ports. No `OFFLOAD` marker appeared for
the sampled active software-only connections. That run must not be presented
as an accepted, functioning software fast path; a physical-port comparison
is a separate diagnostic. WAN-side connection attempts to TCP 22/80/443
were rejected with the tested firewall; LAN management remained reachable.

Adding physical ports experimentally produced conntrack `OFFLOAD` with no
PPE entries. Patch `0015` applies this selection only to RE-CS-06's software
path, retaining the original bridge and resolving its lower devices. Live
`fw4 check` and a firewall restart passed. Its repeat reached 1551.50 /
1604.72 Mbit/s, CPU 30.94% / 29.92%, with 405 / 367 retransmits. This confirms
the software fast path, not a throughput win over ordinary routing or a
general cure for packet loss. Hardware acceleration remains a distinct mode.

Remaining independent gates include IPv6 routing, PPPoE/VLAN if required,
Wi-Fi routed direct-switch traffic, firewall rejection, reconnect behavior,
VPN-specific crypto and sustained mixed traffic. EHT/MLO are not accepted;
the current owner-provided client only establishes HE, and the grouped MLO
firmware path previously crashed. Enabling every optional feature is not
equivalent to maximizing useful, correct hardware utilization.

## r6 installation and CryptoAPI runtime

The completed r6, including patches `0014` and `0015`, was installed through
the checked sysupgrade path. The configuration archive was copied to a
second physical SSD beforehand. Network/wireless settings and the original
SSH host key restored automatically; ext4 remained writable. Kernel/rootfs
image ranges matched their generated hashes after installation. APPSBL,
ART, primary GPT head and saved U-Boot environment matched the original
backups. This was not a forced module installation.

Runtime `/proc/crypto` now registers `gcm-aes-ce`, `rfc4106-gcm-aes-ce`,
`ccm-aes-ce` and AES CE mode implementations with reported selftests passed.
A temporary AF_ALG AES-CTR benchmark explicitly selected generic and CE
drivers, encrypted 16 KiB messages for three seconds each, and checked the
first 16-byte result against the published NIST SP800-38A CTR example on
every iteration. It measured **51.50 MiB/s generic versus 487.19 MiB/s CE**.
That limited known-answer check is not a complete algorithm validation or
an IPsec/OpenVPN benchmark. Kernel-reported selftests and this independent
sample are recorded separately from application/VPN acceptance.

After r6 installation, the routed two-stream tests were repeated:

| Mode | LAN → WAN Mbit/s | WAN → LAN Mbit/s | CPU busy | TCP retransmits |
| --- | ---: | ---: | --- | --- |
| Software | 1663.94 | 1646.79 | 32.16% / 29.90% | 434 / 314 |
| Hardware | 2187.27 | 2314.96 | 0.27% / 0.32% | 442 / 0 |

Both software `OFFLOAD` and hardware `HW_OFFLOAD` were observed in their
respective modes; PPE NAT flow counters grew only in hardware mode. The
remaining LAN → WAN retransmissions have not been localized and must not
be called fixed. WAN and offloading were restored to disabled, test-server
processes stopped, and the PC's normal Wi-Fi internet route preserved.
The owner still needs to set an administrator password before operational
uplink use; diagnostic WAN input rules remained rejecting management.
