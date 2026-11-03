# Queue-selection candidate r3

This locally built candidate is identified as
`experimental-2026.11.03-queuefix-r3`. It includes patches 0011 (available
overlay formatter), 0012 (idempotent QCA8K FDB deletion) and 0013 (PPE socket
TX queue selection), along with the earlier board/radio adaptations.

The persistent FIT is 6856772 bytes, within the existing 7340032-byte HLOS
slot. The sysupgrade tar is 26071901 bytes, SHA256:

`1670700563bef5cc202111af98fbe576d52b6cbbd88163cf0e3af32025f3f2a4`

These sizes/hash identify the **first, blocked build**, not the installed
stage2-fixed revision described below.

Before installation, FIT kernel/DTB hashes and board identity, rootfs bytes,
tar contents, account permissions and absence of known device-private
literals were checked offline. The patched kernel source and fstools source
were inspected in the actual rebuilt tree. The installed device accepted
`sysupgrade -T` without force. That validation is not a runtime TX-queue test.

A fresh private configuration/SSH-key backup was verified and copied onto
a second physical SSD. It is deliberately not included in this repository.
The board-specific upgrade path writes rootfs and HLOS, attempts configuration
carryover through the sysupgrade backup mechanism and does not change GPT, ART
or boot firmware. This is not atomic A/B rollback.

Full-radio local images still contain downloaded third-party firmware whose
redistribution review is unresolved. They are not automatically public release
assets. This candidate does not change regulatory policy or enable kexec.

Post-install boot, configuration persistence and repeated direct 2.5G tests
are required before calling the candidate a hardware-validated improvement.

## First upgrade attempt blocked

The installed r2 stage2 RAM filesystem included `sha256sum` and `head`, but
not `mktemp`, which the checked helper requires before any partition write.
After the sysupgrade handoff, SSH/HTTP were unavailable while the network
still responded. No stage2 serial log was available. Static inspection found
the missing dependency and the helper's fail-closed wait before writes; the
actual flash state still needs readback after restarting the installed OS.
The platform dependency list now explicitly includes `mktemp`, with a
regression test. This attempt must not be reported as a completed r3 install.

## Stage2-fixed revision installed

After an ordinary restart, readback confirmed the first attempt had left the
r2 kernel/rootfs intact. The currently running r2 stage2 dependency list was
corrected as well as the new image's list; a temporary RAM-root test confirmed
that `mktemp` executed there before retrying installation.

The final installed sysupgrade tar is 26071901 bytes, SHA256:

`0a7edf63e5d50fb05ea6a0e324d4375cc0070f483f687fcf82799bb10be2a48a`

Its persistent kernel is 6856704 bytes. Kernel and padded rootfs readback
matched the corresponding tar members. The device boots r3 with a writable
ext4 overlay created **automatically**, without the manual formatting needed
for r2. APPSBL, ART, primary GPT head and stored U-Boot environment matched
their backups.

**Automatic configuration carryover failed.** The first boot used defaults
and a newly generated SSH key. The independently verified pre-upgrade backup
was restored manually using `sysupgrade -r`, followed by reboot. The original
network/wireless configuration and SSH key then matched the backup and
persisted. The exact carryover failure is not established; no stage2 serial
capture was available. Thus this is a successful firmware install plus manual
configuration recovery, **not a fully validated unattended sysupgrade**.

## Direct 2.5G hardware comparison

Same direct Intel I225-V host ↔ JDCloud LAN3 topology, 2500 Mbit/s full duplex.
Host internet remains on Wi-Fi. Tests use local endpoint TCP traffic, not
WAN/NAT forwarding. Test destination TCP metrics were deleted on JDCloud
before each run. RPS, offloading and global congestion settings were not
tuned; process affinity below is an iperf-only control, not installed policy.

| Test | r2 baseline | r3 result |
| --- | --- | --- |
| Two streams, JDCloud → host | 1104–1142 Mbit/s, 810–949 retransmits | 1211–1225 Mbit/s, **0 retransmits** |
| One stream, sender CPU1 | 1752–1758 Mbit/s, 362–462 retransmits | 1787–1810 Mbit/s, **0 retransmits** |
| One stream, sender CPU0 | 1272–1281 Mbit/s, 0 retransmits | 1267 Mbit/s, 0 retransmits |
| Two streams, JDCloud → host IPv6 | 1094 Mbit/s, 609 retransmits | 1185 Mbit/s, **0 retransmits** |

An additional two-stream CPU1-bound reverse run reached 1190 Mbit/s with no
retransmits. All seven reverse runs were clean. This supports the TX queue
selection change as a practical fix for the reproduced JDCloud-sender
problem, without proving wire-level ordering or excluding every other change
in the rebuilt image. It is not a claim of full 2.5G throughput.

The opposite direction is **not completely resolved**: two-stream host →
JDCloud runs reached 1684–1721 Mbit/s with 255–350 retransmits, whereas a
single-stream run reached 1981 Mbit/s with zero. The earlier r2 IPv4
two-stream forward tests were nearly clean, so this is a possible regression
or changed load/ACK-path interaction requiring follow-up. Do not describe
the patch as eliminating all retransmissions in both directions.

LAN3 FCS/alignment/overflow/underrun counters remained zero. In the observed
post-restore boot, PCIe corrected RxErr and total corrected errors were zero,
and no FDB deletion errors appeared in collected dmesg. This single boot and
wired workload do not establish permanent PCIe/FDB resolution or validate
repeated AP teardown. WAN/Wi-Fi remain disabled. Temporary iperf files and
server were removed after testing.
