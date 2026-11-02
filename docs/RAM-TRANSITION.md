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

**Runtime transition was attempted and failed; do not rely on it.** The
original test plan was to validate image loading/unloading before a
controlled RAM-to-RAM transition with serial capture, no eMMC devices and
no radio drivers loaded. Preserve the
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

## First load-only hardware check

The first guarded diagnostic booted and exposed the syscall and userspace
tool. Loading an inspected raw Image failed with `Resource busy` and kernel
message `Can't kexec: CPUs are stuck in the kernel.` No transition was
executed, `kexec_loaded` remained zero and SSH stayed available. The source
guard requires an available CPU `cpu_die` operation; with `HOTPLUG_CPU`
disabled that check always fails on a multicore ARM64 machine. The optional
build setting now selects CPU hotplug as well. This is a prerequisite fix,
not a bypass of the safety check.

## Hotplug-enabled hardware check (RAM v10)

The revised diagnostic booted from the guarded HTTP script. Kernel loading
and unloading both succeeded (`kexec_loaded`: 0 → 1 → 0), with SSH still
available. The checked raw Image was loaded again and `kexec -e` executed
with no radio drivers loaded and no eMMC block devices present.

The old kernel reported `Starting new kernel`, stopped CPUs 1–3 via PSCI,
and printed `Bye!`. No new-kernel startup was observed. Instead the boot
chain restarted and reported `System Reset Reason : NOC Error [0x6]`, then
booted the installed QWRT. This establishes a failed handoff, not its exact
hardware/driver cause. Do not bypass guards or repeatedly attempt the same
jump, and do not treat successful load/unload as proof of a usable restart.

Read-only checks after return found APPSBL, ART, HLOS, the primary GPT head
and all stored U-Boot environment values equal to the backup. Normal QWRT
boot can change its writable overlay; full rootfs equality is not claimed.
The host's normal internet route remained on its original Ethernet link.

The experiment has not provided automated recovery. Without a voltage-safe
UART transmit path, manual Reset-held entry into the existing HTTP recovery
remains the tested way to start another guarded RAM diagnostic from QWRT.
