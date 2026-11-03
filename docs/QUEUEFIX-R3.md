# Queue-selection candidate r3

This locally built candidate is identified as
`experimental-2026.11.03-queuefix-r3`. It includes patches 0011 (available
overlay formatter), 0012 (idempotent QCA8K FDB deletion) and 0013 (PPE socket
TX queue selection), along with the earlier board/radio adaptations.

The persistent FIT is 6856772 bytes, within the existing 7340032-byte HLOS
slot. The sysupgrade tar is 26071901 bytes, SHA256:

`1670700563bef5cc202111af98fbe576d52b6cbbd88163cf0e3af32025f3f2a4`

Before installation, FIT kernel/DTB hashes and board identity, rootfs bytes,
tar contents, account permissions and absence of known device-private
literals were checked offline. The patched kernel source and fstools source
were inspected in the actual rebuilt tree. The installed device accepted
`sysupgrade -T` without force. That validation is not a runtime TX-queue test.

A fresh private configuration/SSH-key backup was verified and copied onto
a second physical SSD. It is deliberately not included in this repository.
The board-specific upgrade path writes rootfs and HLOS, preserves configuration
through the usual sysupgrade backup mechanism and does not change GPT, ART
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
