# Optional RAM-to-RAM transition diagnostic

The currently installed QWRT kernel and the earlier RAM diagnostics have no
usable kexec support. A userspace executable alone cannot add that syscall.
UART receive-only capture cannot interrupt autoboot, and a 3.3 V adapter TX
must not drive a 1.8 V router RX directly.

Patch `0008` adds an optional `KERNEL_KEXEC_FILE` build setting and allows
the kexec package with that setting. ARM64 in this pinned tree supports the
kernel-managed file loader even when the legacy kexec syscall is unavailable.
Append `config/ram-transition.config` after the usual minimal seed before
`make defconfig` to select this diagnostic variant. The normal minimal seed
does not enable it automatically.

The first diagnostic build succeeded with `CONFIG_KEXEC_CORE=y`,
`CONFIG_KEXEC_FILE=y` and the userspace kexec utility included. Its persistent
kernel still passed the HLOS size gate. The local guarded RAM wrapper keeps
the eMMC compatible unbound, removes the WSI group and disables radio
autoload. No private firmware/calibration is embedded.

**Runtime transition is not yet tested.** One more ordinary recovery entry
is needed to start that new kernel. First validate image loading/unloading
without executing it, then attempt a controlled RAM-to-RAM transition with
serial capture, no eMMC devices and no radio drivers loaded. Preserve the
runtime DTB's memory and reserved-memory properties; the kernel file loader
derives its next DTB from the running tree rather than accepting an arbitrary
FIT as a bootloader would. Load an inspected raw ARM64 Image, not the HTTP
wrapper or an eMMC install container.

This may reduce repetitive recovery entry during development. It does not
provide power control, recovery from a hang or a way to enter U-Boot from
QWRT. A successful first jump also would not prove safe quiescence/restart
of already running radio firmware. Do not unbind the radios as a shortcut:
the partial-state cleanup path has already panicked on this device.

No saved boot environment, bootloader or installed firmware needs to be
changed to perform this experiment. Do not write `bootcmd=httpd`, erase HLOS
or replace U-Boot just to avoid holding Reset.
