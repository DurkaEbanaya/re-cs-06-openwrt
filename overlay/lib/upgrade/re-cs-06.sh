# SPDX-License-Identifier: GPL-2.0-only
# Board-specific checked tar upgrade; never changes GPT, ART or boot firmware.
recs06_prepare_upgrade() {
	local image="$1" list kernel_dev root_dev kernel_size root_size
	RECS06_TMP=$(mktemp -d /tmp/recs06-upgrade.XXXXXX) || return 1
	list=$(tar tf "$image") || return 1
	[ "$list" = 'sysupgrade-jdcloud_re-cs-06/
sysupgrade-jdcloud_re-cs-06/CONTROL
sysupgrade-jdcloud_re-cs-06/kernel
sysupgrade-jdcloud_re-cs-06/root' ] || return 1
	RECS06_DIR="$RECS06_TMP/sysupgrade-jdcloud_re-cs-06"
	mkdir "$RECS06_DIR" || return 1
	# Never extract member paths/links from an untrusted tar onto the filesystem.
	local member
	for member in CONTROL kernel root; do
		tar xf "$image" -O "sysupgrade-jdcloud_re-cs-06/$member" > "$RECS06_DIR/$member" || return 1
	done
	[ "$(cat "$RECS06_DIR/CONTROL")" = 'BOARD=jdcloud_re-cs-06' ] || return 1
	[ -f "$RECS06_DIR/kernel" ] && [ ! -L "$RECS06_DIR/kernel" ] || return 1
	[ -f "$RECS06_DIR/root" ] && [ ! -L "$RECS06_DIR/root" ] || return 1
	[ "$(head -c 4 "$RECS06_DIR/kernel" | hexdump -v -e '1/1 "%02x"')" = d00dfeed ] || return 1
	[ "$(head -c 4 "$RECS06_DIR/root")" = hsqs ] || return 1
	# This is a format/geometry gate, not cryptographic image authentication.
	# Full FIT hash verification is performed offline before installation.
	kernel_dev=$(find_mmc_part '0:HLOS')
	root_dev=$(find_mmc_part rootfs)
	[ -b "$kernel_dev" ] && [ -b "$root_dev" ] && [ "$kernel_dev" != "$root_dev" ] || return 1
	[ "$(cat "/sys/class/block/${kernel_dev##*/}/size")" = 14336 ] || return 1
	[ "$(cat "/sys/class/block/${root_dev##*/}/size")" = 4194304 ] || return 1
	kernel_size=$(wc -c < "$RECS06_DIR/kernel")
	root_size=$(wc -c < "$RECS06_DIR/root")
	[ "$kernel_size" -gt 40 ] && [ "$kernel_size" -le 7340032 ] || return 1
	[ "$root_size" -gt 4096 ] && [ "$root_size" -lt 2147479552 ] || return 1
	[ $((root_size % 65536)) -eq 0 ] || return 1
	EMMC_KERN_DEV="$kernel_dev"
	EMMC_ROOT_DEV="$root_dev"
	EMMC_ROOTFS_BLOCKS=$((root_size / 512))
}

recs06_stage_backup() {
	RECS06_BACKUP=
	[ -n "$UPGRADE_BACKUP" ] || return 0
	[ -s "$UPGRADE_BACKUP" ] && [ ! -L "$UPGRADE_BACKUP" ] || return 1
	# Validate and preserve the actual stage2 input before touching either slot.
	gzip -t "$UPGRADE_BACKUP" && tar tzf "$UPGRADE_BACKUP" >/dev/null || return 1
	RECS06_BACKUP="$RECS06_TMP/config.tgz"
	cp "$UPGRADE_BACKUP" "$RECS06_BACKUP" || return 1
	local size available
	size=$(wc -c < "$RECS06_BACKUP")
	available=$((2147483648 - EMMC_ROOTFS_BLOCKS * 512))
	[ "$size" -gt 0 ] && [ "$size" -le "$available" ]
}

recs06_write_backup() {
	[ -n "$RECS06_BACKUP" ] || return 0
	local size expected actual
	size=$(wc -c < "$RECS06_BACKUP")
	expected=$(sha256sum "$RECS06_BACKUP")
	expected=${expected%% *}
	dd if="$RECS06_BACKUP" of="$EMMC_ROOT_DEV" bs=512 seek="$EMMC_ROOTFS_BLOCKS" conv=fsync || return 1
	# Read exactly the backup bytes back; never expose configuration contents.
	actual=$(dd if="$EMMC_ROOT_DEV" bs=512 skip="$EMMC_ROOTFS_BLOCKS" count=$(((size + 511) / 512)) 2>/dev/null | head -c "$size" | sha256sum)
	actual=${actual%% *}
	[ "$actual" = "$expected" ]
}

recs06_check_image() {
	local rc=0
	recs06_prepare_upgrade "$1" || rc=1
	[ -z "$RECS06_TMP" ] || rm -rf "$RECS06_TMP"
	[ "$rc" = 0 ] || echo 'RE-CS-06: invalid tar/FIT/rootfs or unsupported partition geometry' >&2
	return "$rc"
}

recs06_write_verify() {
	local source="$1" target="$2" size expected actual
	size=$(wc -c < "$source")
	expected=$(sha256sum "$source")
	expected=${expected%% *}
	dd if="$source" of="$target" bs=65536 conv=fsync || return 1
	actual=$(head -c "$size" "$target" | sha256sum)
	actual=${actual%% *}
	[ "$actual" = "$expected" ] || return 1
}

recs06_do_upgrade() {
	# Recheck inside stage2, after pivoting to RAM and unmounting the overlay.
	local rc=0
	if recs06_prepare_upgrade "$1" && recs06_stage_backup; then
		recs06_write_verify "$RECS06_DIR/root" "$EMMC_ROOT_DEV" &&
		dd if=/dev/zero of="$EMMC_ROOT_DEV" bs=512 seek="$EMMC_ROOTFS_BLOCKS" count=8 conv=fsync &&
		recs06_write_verify "$RECS06_DIR/kernel" "$EMMC_KERN_DEV" &&
		recs06_write_backup || rc=1
	else
		rc=1
	fi
	[ -z "$RECS06_TMP" ] || rm -rf "$RECS06_TMP"
	[ "$rc" = 0 ] || echo 'RE-CS-06: UPGRADE FAILED; recovery may be required' >&2
	return "$rc"
}
