# Installed system component checks

These are bounded tests of install-r2 after the enclosure was reassembled,
not a declaration that every component and operating mode passed. UART was
disconnected by the owner; all tests used the existing wired SSH connection.
No reflash, reset or reboot was performed during this run.

## Passed checks

- Four CPU-affined workers tested 48 MiB each for 90 seconds, using six
  write/verify patterns with no mismatch. This is 192 MiB of allocated
  userspace RAM, not all physical memory or a long-duration burn-in.
- Existing ext4 overlay is writable. A temporary 64 MiB random file had the
  same SHA256 before/after sync; ordinary cached reads were used. A separate
  512 MiB sequential block read completed. No destructive/full-surface test
  was performed. Original bootloader, ART and both calibration slices matched
  their saved hashes. Zero wear fields are unspecified, not proof of no wear.
- SSH, HTTP, HTTPS, local authoritative DNS and DHCP responded. Procd daemons
  were running; the exited random-seed instance completed with status zero.
  `fw4 check` passed. WAN remains off; internet DNS/NTP were not tested.
- Both protected temporary APs associated with an Intel AX201 client and
  carried TCP traffic. Profile-specific routing kept traffic on the selected
  client interface and left the host's primary internet route unchanged.

| Router endpoint test | Client → router | Router → client |
| --- | ---: | ---: |
| Wired LAN, 1 Gb/s | 941 Mb/s | 867 Mb/s |
| 5 GHz, channel 36, configured HE80 | 507 Mb/s | 684 Mb/s |
| 2.4 GHz, channel 1, configured HE20 | 85 Mb/s | 88 Mb/s |

iperf3 3.19.1 used two TCP streams for 15 seconds in each direction. These
are endpoint tests, **not NAT, bridge forwarding or WAN throughput**. Reverse
wired traffic had 899 TCP retransmissions despite zero interface hardware
errors: the cause is unresolved. Only the currently connected LAN port was
throughput-tested; earlier four-port RAM link checks are separate evidence.

## Important limitations and warnings

The APs were configured for HE, but station snapshots reported HT on 2.4 GHz
and VHT on 5 GHz. Therefore these tests do **not** validate Wi-Fi 6 or 7
negotiation. With RU selected the self-managed regulatory report includes
`NO-EHT`; ath12k maps the firmware's `ATH12K_REG_PHY_BITMAP_NO11BE` flag to
that result. This is evidence about the installed driver/firmware combination,
not a determination that Wi-Fi 7 is generally unlawful in Russia. No country
spoofing or regulatory bypass was used.

Sampled temperatures were about 38–47 °C in the enclosure. There was no
continuous peak-temperature measurement or prolonged stress test. No panic,
firmware crash or storage I/O error appeared during this run. Boot logs did
contain a correctable PCIe receiver error; QCA8K FDB deletion returned -22 at
boot and when removing APs. These warnings must not be silently treated as
fully resolved because traffic works.

USB 2/3 root hubs and LED sysfs controls exist. Peripheral transfers, physical
buttons/visual LED behavior, 2.5 Gb/s copper negotiation, WAN/NAT/PPPoE,
upstream IPv6, HE/EHT negotiation, DFS and long-term stability remain untested.
Do not test Reset by casually pressing it: it can erase configuration.

## Cleanup and security

Temporary APs and host Wi-Fi profile were removed, original disabled radio
configuration restored, iperf server stopped, and uploaded test binaries and
test file removed. RU remains recorded in the disabled radio configuration
from the pre-AP test stage; it is **not** an owner-approved final radio setup.
The root password is still unset and must be set before enabling an uplink.
Raw logs, calibration, MACs and temporary credentials remain private.

Machine-readable results: [`reports/system-component-tests.json`](../reports/system-component-tests.json).
