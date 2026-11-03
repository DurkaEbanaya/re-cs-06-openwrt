# Unreachable Ethernet before an owner reboot

The owner reported a green status LED but no accessible Ethernet port.
The workstation's physical carrier was zero. Targeted IPv6 probes from
Keenetic to the previously known JDCloud link-local addresses also failed;
stale neighbor-cache entries were not treated as live reachability.

Following the owner's reboot, the original pinned SSH host key was accepted
and resources-r6 booted normally. The active logical port was `lan2` and
negotiated 2500 Mbit/s full duplex approximately 16 seconds after kernel
startup. MDIO/QCA8386 preinitialization, the internal switch link and PPE
conduit all initialized. FCS, alignment, overflow and underrun counters were
zero in the initial snapshots. All four RX RPS masks were `2`; the ext4
overlay recovered its journal and mounted read/write. Journal recovery after
an unclean shutdown is not itself proof of filesystem corruption.

The new boot showed corrected PCIe physical-layer RxErr events at roughly
eight seconds, on both the radio root port and endpoint. Each corrected
counter was one. Both radios subsequently reported firmware versions. No
kernel panic or Ethernet initialization timeout was observed in this boot.
This does **not** establish a relationship between the corrected radio PCIe
event and the earlier absence of Ethernet carrier.

## Missing previous-boot evidence

`pstore` and `ramoops` modules are present, but the pstore backend is null,
ramoops memory address and size are zero, and no ramoops DT reservation is
present. The pstore directory is empty. The system log is a volatile 128 KiB
buffer with no configured persistent file or remote log destination.

Consequently, the earlier hang/link state cannot be reconstructed from the
fresh boot log. An empty pstore directory here is **not evidence that no
panic happened**: there was no registered persistence backend. A spontaneous
memory reservation must not be added to this board's sensitive radio/secure
memory map just to enable ramoops. Capture live logs and host link events
before another failure instead of resetting first when access remains.

The cause of the original outage is unresolved. A working reboot cannot
distinguish a switch/PHY stall, a whole-system hang, cable/peer state or host
NIC activation behavior. No bootloader, memory map, firmware, offload setting
or persistent network configuration was changed during this inspection.

## Bounded post-reboot traffic check

Two TCP streams for 15 seconds per direction, with the workstation connected
directly at 2.5G, delivered 2339.68 Mbit/s PC→router and 2006.09 Mbit/s
router→PC, both with zero retransmissions. A live system-log stream was saved
on the workstation during the test. No new panic, FDB error, timeout or
storage I/O error was observed. The temporary iperf server and its files were
removed. This short success does not reproduce or rule out the previous
outage, and it does not test the outstanding routed LAN→WAN retransmissions.
