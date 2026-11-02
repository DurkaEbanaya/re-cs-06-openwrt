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
