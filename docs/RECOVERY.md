# Recovery preflight — not hardware boot acceptance

Read-only inspection of the currently installed QWRT found:

- Linux 5.4.213; `CONFIG_KEXEC` and `CONFIG_KEXEC_FILE` are disabled.
  Installing a userspace kexec executable cannot add the missing kernel support.
- USB DWC3 is configured as `host` in the running device tree and kernel.
  `CONFIG_USB_GADGET` is disabled and no UDC/device-role interface was found.
  A normal USB-A to USB-A cable is not a serial console and must not be used
  to connect two powered host ports. Cable wiring and power handling matter;
  do not assume every A-to-A cable is safe or suitable for recovery.
- The saved installed U-Boot has `bootm`, `tftpboot` and HTTP firmware-recovery
  strings. Its embedded UI identifies a July 2024 modification. Strings do
  not prove a working recovery path or a RAM-upload feature.

Prefer investigating Ethernet/Reset-triggered recovery before opening the
case. A controlled recovery-mode entry needs physical assistance and a
router-specific button/power sequence: holding Reset on a running firmware
may factory-reset it. Do not upload a test image through a generic firmware
update page under the assumption it will only run in RAM.

The current README of a different/newer third-party U-Boot tree advertises
web RAM boot and a web console. This does not establish those features in
the older bootloader actually installed here. Do not replace the bootloader
merely to make the test convenient.

UART is not an agreed prerequisite. If Ethernet recovery cannot be verified
without writing, stop and discuss alternatives rather than silently flashing
or requiring disassembly. Qualcomm USB emergency-download/EDL is a separate
mode with hardware, cable and loader requirements; no working external USB
entry sequence or compatible loader has been established for this unit.

No reboot, flash write, USB-role change or recovery upload was performed
during these checks. Main Internet connectivity remained on the other router.

## Follow-up: Ethernet recovery actually entered

With the owner's physical assistance, powering up while holding Reset
successfully entered the installed recovery. Read-only HTTP GET over the
isolated USB-Ethernet interface returned:

- `/` and `/index.html`: HTTP 200, uIP/0.9, `FIRMWARE UPDATE`, version
  `uboot2.0 version:24.07.25`.
- `/initramfs.html`, `/ram.html`, `/console.html`: HTTP 404.
- The saved bootloader's page strings contain firmware, U-Boot, ART and
  MIBIB update pages, but no advertised initramfs or console page.

This validates recovery **entry and HTTP access**, not the correctness of
its flash writer, restoration, or compatibility with the new kernel.
No POST/upload, flash write, environment change or firmware test was done.
No network RAM-boot method is established for this installed version.
Do not upload initramfs through the generic firmware-update form.

Power cycling with Reset released should leave recovery and boot the
unchanged installed QWRT. Verify that before considering further changes.
UART is declined by the owner. Replacing U-Boot merely to obtain a web
RAM loader would itself be a high-risk flash operation and has not been
performed or proposed as a risk-free prerequisite.

Recovery shares the primary router's IPv4 address. Host access used a
source-specific routing table on the dedicated USB adapter; normal Internet
traffic remained on the primary Ethernet interface. NetworkManager's temporary
device settings can disappear after link loss. Always recheck the interface,
source address and route before accessing or uploading to a recovery server.

## Follow-up: controlled RAM test attempted

The owner subsequently authorized firmware testing, with UART as a fallback.
Static inspection of the saved July 2024 bootloader found a distinct script
container path, not an advertised web RAM-loader page:

- A marker at offset 0x5c selects a special image type before the ordinary
  FIT case. The special recovery branch initializes SPI and invokes the
  FIT image's `script` from the upload buffer.
- The ordinary FIT branch instead writes HLOS/rootfs, so **uploading an
  ordinary initramfs to this page is still unsafe**. This discovery is not
  permission to treat other bootloaders or recovery forms the same way.
- A no-op script wrapper was accepted; the router rebooted to QWRT and
  APPSBL, ART and HLOS hashes matched the original backup. No serial script
  output was captured; that test alone does not directly prove execution.

A separate local wrapper was then uploaded. It embedded the external-radio
initramfs with only its RAM DTB's eMMC controller disabled. Its script used
guarded extraction to a separate RAM address, volatile boot arguments and
`bootm`. No `flash`, `saveenv`, raw-storage write or persistent installation
was requested. The disabled eMMC controller is an additional safeguard in
the test kernel, not a property of the normal published firmware images.

**Result: Linux boot was not confirmed.** Recovery accepted the complete
upload and Ethernet dropped. The router subsequently returned to its
original QWRT, reachable over SSH; the new test LAN was not reachable.
After return, APPSBL, ART, HLOS, the primary GPT-head backup range and saved
bootloader environment values matched the original backup. The live QWRT
overlay was not claimed byte-identical: normal boots write runtime settings.

Static analysis found a 64 MiB bootloader kernel decompression bound, while
the test kernel including initramfs expands to 55402504 bytes. This does not
establish why the attempt failed. Script/extraction errors, bootloader FIT
handling and an early kernel failure cannot be distinguished without console
logs. Do not claim a successful RAM boot or flash the persistent image as a
workaround. UART capture is the next diagnostic step. No bootloader/GPT/ART
replacement is proposed.

## UART follow-up: wrapper format failure identified

A CP2102 with router TX connected to adapter RX and a common GND produced
readable receive-only logs at 115200 8N1. The initial missing GND caused
corrupted reception; this was not evidence of an unsupported baud rate.
Adapter TX and VCC remained disconnected. Raw logs contain hardware identity
and remain private.

Repeating the identical first RAM wrapper with serial capture established:

```text
Executing: sf probe; imgaddr=0x44000000 && source $imgaddr:script
Failed to initialize SPI flash at 0:0
## Executing script at 44000000
Bad FIT image format
HTTP ugrade is done! Rebooting...
```

The special script branch is now directly observed. Its `source` command
rejected the wrapper before the first script echo and before any kernel
launch. The UI's success/reboot message is therefore not script success.
The SPI probe failure did not prevent reaching `source`.

The hand-built outer FIT omitted root `description` and `timestamp`.
Upstream U-Boot v2016.01 `fit_check_format()` requires `description` and,
when timestamps are enabled, `timestamp`. The inner kernel FIT already had
these fields; this failure concerns the outer recovery wrapper, not a
demonstrated kernel/Ethernet bug. The earlier no-op wrapper omitted the same
fields, so its reboot must not be cited as proof that its echo executed.

Replacement local wrappers add the mandatory root metadata while retaining
the recovery marker, identical scripts/payloads, hash verification and the
disabled-eMMC test DTB. Host `mkimage -l` accepts the corrected no-op FIT.
The corrected no-op wrapper was subsequently tested on the same bootloader.
UART directly showed:

```text
crc32+ sha1+ JD_RAM_SCRIPT_PREFLIGHT_NO_FLASH
HTTP ugrade is done! Rebooting...
```

This confirms hash verification and execution of the no-op script, not
Linux boot. Recovery automatically reboots after the script returns. The
corrected initramfs wrapper still needs a separate recovery entry/test.

## Corrected initramfs: kernel boot confirmed, acceptance incomplete

The corrected wrapper was subsequently uploaded with receive-only UART
capture. U-Boot verified script/payload/kernel/DTB hashes, decompressed the
kernel, and transferred control to AArch64 Linux. The serial log confirms
Linux **6.18.60**, model RE-CS-06, all four CPUs, `/init`, preinit and procd
reaching `- ubus -`. PCIe Gen3 x2 and the radio PCI endpoint enumerated;
that is not a radio functionality test. No persistent install was requested.

The test exposed two blockers:

1. **eMMC isolation failed.** The uploaded nested DTB was checked to have
   `status = "disabled"` at `/soc@0/mmc@7804000`, but Linux nevertheless
   probed the controller and enumerated the card and partitions. The saved
   bootloader contains the literal fixup string
   `/soc@0/mmc@7804000/%status%?okay`, consistent with re-enabling this node.
   The runtime DTB has not been retrieved, so that explanation remains
   strongly indicated rather than independently verified. Do not repeat
   claims of disabled storage or proven write-free boot for this wrapper.
   No mount/storage write is shown in the captured excerpt, but absence of
   such log messages does not establish absence of writes.
2. LAN HTTP access timed out after reapplying the isolated host address.
   Kernel diagnostics show deferred probing at MDIO `:10` and pending clock
   sync for Ethernet/PPE, PCS and Wi-Fi. The last userspace stage observed
   was procd `- ubus -`; no normal shell/login prompt was observed. The
   exact userspace/Ethernet root cause is not established. Do not equate
   an Ethernet carrier indication with a working LAN or successful boot.

Next: return to the saved QWRT installation and recheck critical hashes;
prepare stronger test-only storage isolation and early runtime diagnostics
before further RAM tests. A persistent flash is not a remedy for these
blockers. Raw serial logs remain private because they contain identifiers.

### Return verification and Ethernet-cable correction

After an owner power cycle, the original QWRT kernel 5.4.213 booted again.
The host initially reported no carrier; the owner found the Ethernet cable
was not fully inserted. Reseating it restored carrier and SSH. Read-only
checks then confirmed APPSBL, ART, HLOS, the primary GPT-head range and all
saved bootloader environment values match the original backup. This is not
a full-disk or live-overlay equality claim.

The cable's exact condition during the RAM boot is unknown. Accordingly,
the RAM test's HTTP timeout alone cannot establish a firmware Ethernet
failure. The deferred-probe messages remain genuine observations, but
their effect on eventual connectivity is unproven. Repeat network testing
with a confirmed seated cable after strengthening storage isolation.

## Diagnostic RAM v3: storage guard confirmed at runtime

The next local-only test changed the MMC controller `compatible` to an
unmatched diagnostic identifier, in addition to disabling its status.
It also replaced `/init` and an unused Wi-Fi detection script body inside
the embedded archive, keeping their lengths and kernel section offsets
unchanged, to emit four rounds of early runtime diagnostics. No such
modifications were applied to the published persistent images. Wireless
configuration is deliberately unavailable in this diagnostic image.

All four rounds showed an empty `/proc/partitions`, root on tmpfs, no eMMC
card and no storage mounts. The runtime DT exposed the unmatched MMC
compatible but **status `okay`**, directly confirming that the bootloader
overrode the uploaded `disabled` property. The unmatched compatible
prevented its SDHCI driver from binding despite this override.

The diagnostics narrow the userspace blocker: PID 1 is procd, `ubusd` is
running and its Unix socket exists, but procd has not advanced past its
UBUS startup stage. Only loopback exists and the normal service/module
loading stage has not been reached. This means the lack of Ethernet is
not yet an isolated Ethernet-driver diagnosis. Further test-only procd
debug output and bounded ubus/process queries are prepared; the exact
cause remains unproven. See `reports/ram-v3-diagnostics.json`.

## Diagnostic RAM v4: account database permissions blocker

With procd debug enabled, both procd and the standalone `ubus` client
repeatedly failed to connect despite a listening `ubusd` socket. Procd and
ubusd remained in epoll waits; only boot-stage modules were loaded. Storage
isolation remained active (no block partitions; root on tmpfs).

Offline inspection then found both `/etc/passwd` and `/etc/group` have mode
0600 in the generated squashfs **and** initramfs. `ubusd` runs as user ubus
and its ACL setup uses `getpwuid()`/`getgrgid()` for incoming clients. These
public account databases must be readable by that service (0644), unlike
`/etc/shadow`, which must remain 0600. This is a concrete build defect and
a strong explanation of the observed connection failure, pending the next
RAM confirmation. Existing published images are not installation-ready.

A test-only v5 wrapper changes those two permissions in its tmpfs root
before procd starts; shadow stays private and the unmatched MMC compatible
guard remains unchanged. It is prepared but not hardware-tested yet. The
rootfs inspector now rejects 0600 passwd/group and non-0600 shadow, with a
regression test. Earlier content-only inspection passes did not check this
functional permissions requirement and must not be interpreted as such.

## Diagnostic RAM v5: successful wired userspace boot

Changing only public passwd/group modes to 0644 in tmpfs before procd
confirmed the diagnosis: procd connected to ubus and entered normal init;
normal modules, network services, dropbear and uhttpd started. The connected
port appeared as `lan3`, negotiated 1000/full and provided SSH and HTTP on
192.168.76.1. LuCI returned its expected unauthenticated login-required page.
This does not mean authenticated LuCI configuration or other ports were
tested. WAN remains disabled. There is no Wi-Fi validation: radio blobs and
per-device ART are deliberately unavailable in this isolated diagnostic.

SSH independently confirmed an empty partition list, root on tmpfs and no
storage mounts. `/etc/shadow` remained 0600. The persistent installation has
not been changed. The unmatched MMC-compatible guard is only in this RAM
test and is not a substitute for persistent firmware's MMC support.

The public source checkout had been created under a restrictive host umask:
many Git 0644/0755 tracked files were actually 0600/0700. Source preparation
now explicitly uses umask 022 and restores Git modes for tracked regular
files; a base-files patch additionally enforces passwd/group 0644 and shadow
0600. Local source/feed modes were restored and a clean package rebuild was
started as `external-radio-r1` to avoid reusing mode-defective packages.
Earlier release images remain defective and must not be flashed.

The next physical cable move tested logical `lan1`: SSH and HTTP remained
available and ethtool reported 1000/full. Together with the earlier `lan3`
test, two LAN connectors now have basic wired access confirmed. Physical
printed-label mapping, `lan2`, WAN, 2.5G and routed throughput remain untested.

The clean r1 rebuild completed. Its actual squashfs and embedded initramfs
both contain passwd/group mode 0644 and shadow 0600; all rootfs/FIT/cpio/
sysupgrade checks passed and external radio blobs remain absent. This is an
offline check of the corrected images, not a claim that those exact images
were booted (the current router still runs diagnostic v5). Results are in
`reports/external-radio-r1.json` and `reports/ethernet-ram-tests.json`.
