#!/usr/bin/env python3
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import tarfile
import unittest

REPO = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


fit = module("inspect-fit")
policy = module("check-config")
audit = module("audit-public")
rootfs = module("inspect-rootfs")
initramfs = module("inspect-initramfs")
sysupgrade = module("inspect-sysupgrade")


def make_fdt(node):
    strings = bytearray()
    offsets = {}

    def pad(data):
        return data + bytes(-len(data) % 4)

    def encode(name, fields, children):
        result = struct.pack(">I", 1) + pad(name.encode() + b"\0")
        for key, value in fields.items():
            if key not in offsets:
                offsets[key] = len(strings)
                strings.extend(key.encode() + b"\0")
            result += struct.pack(">3I", 3, len(value), offsets[key]) + pad(value)
        for name, fields, children in children:
            result += encode(name, fields, children)
        return result + struct.pack(">I", 2)

    body = encode("", *node) + struct.pack(">I", 9)
    start = 56
    total = start + len(body) + len(strings)
    return struct.pack(">10I", 0xD00DFEED, total, start, start + len(body), 40,
                       17, 16, 0, len(strings), len(body)) + bytes(16) + body + strings


def sample_fit(*, bad_hash=False, nvmem=False, config="config@mi01.6"):
    raw = bytearray(128)
    raw[56:60] = b"ARM\x64"
    kernel = gzip.compress(bytes(raw), mtime=0)
    fields = {"model": b"JDCloud RE-CS-06\0", "compatible": b"jdcloud,re-cs-06\0qcom,ipq5332\0"}
    if nvmem:
        fields["nvmem-cells"] = bytes(4)
    dtb = make_fdt((fields, []))

    def image(name, data, props):
        digest = hashlib.sha256(data).digest() if not bad_hash else bytes(32)
        return (name, {"data": data, **props}, [
            ("hash@1", {"algo": b"sha256\0", "value": digest}, [])])

    return make_fdt(({}, [
        ("images", {}, [image("kernel@1", kernel, {"arch": b"arm64\0", "os": b"linux\0",
                                                 "compression": b"gzip\0", "load": struct.pack(">I", 0x41000000),
                                                 "entry": struct.pack(">I", 0x41000000)}),
                         image("fdt@1", dtb, {})]),
        ("configurations", {"default": config.encode() + b"\0"}, [
            (config, {"kernel": b"kernel@1\0", "fdt": b"fdt@1\0"}, [])])]))


class FitTests(unittest.TestCase):
    def test_valid(self):
        result = fit.inspect(sample_fit())
        self.assertEqual(result["default_config"], "config@mi01.6")
        self.assertFalse(result["hardware_boot_tested"])
        self.assertTrue(result["images"][1]["no_nvmem_mac_dependency"])

    def test_corruption(self):
        with self.assertRaises(AssertionError):
            fit.inspect(sample_fit(bad_hash=True))

    def test_factory_dependency(self):
        with self.assertRaises(AssertionError):
            fit.inspect(sample_fit(nvmem=True))

    def test_soc_efuses_are_not_mac_factory_dependencies(self):
        tree = {
            "/": {},
            "/opp-table-cpu": {"compatible": b"operating-points-v2-kryo-cpu\0",
                               "nvmem-cells": struct.pack(">I", 1)},
            "/soc/efuse": {"compatible": b"qcom,ipq5332-qfprom\0qcom,qfprom\0"},
            "/soc/efuse/speed-bin": {"phandle": struct.pack(">I", 1)},
        }
        self.assertEqual(fit.inspect_nvmem(tree), 1)
        tree["/soc/efuse"]["compatible"] = b"block\0"
        with self.assertRaises(AssertionError):
            fit.inspect_nvmem(tree)

    def test_wrong_config(self):
        with self.assertRaises(AssertionError):
            fit.inspect(sample_fit(config="config@wrong"))

    def test_truncation(self):
        with self.assertRaises((AssertionError, ValueError, struct.error)):
            fit.inspect(sample_fit()[:-2])

    def test_storage_limit_not_applied_to_ram_image(self):
        data = sample_fit() + bytes(7 * 1024 * 1024)
        with self.assertRaises(AssertionError):
            fit.inspect(data)
        self.assertFalse(fit.inspect(data, persistent=False)["persistent_slot_limit_checked"])


class CpioTests(unittest.TestCase):
    def entry(self, name, content=b"", mode=0o100644):
        names = name.encode() + b"\0"
        fields = (1, mode, 0, 0, 1, 0, len(content), 0, 0, 0, 0, len(names), 0)
        header = b"070701" + b"".join(f"{value:08x}".encode() for value in fields)
        result = header + names
        result += bytes(-len(result) % 4)
        result += content
        return result + bytes(-len(result) % 4)

    def test_newc_valid_truncated_and_unsafe_path(self):
        archive = self.entry("init", b"#!/bin/sh\n", 0o100755) + self.entry("TRAILER!!!")
        files, size = initramfs.newc(archive, 0)
        self.assertEqual(files["init"], (0o100755, b"#!/bin/sh\n"))
        self.assertEqual(size, len(archive))
        for invalid in (archive[:-8], self.entry("../escape") + self.entry("TRAILER!!!"),
                        self.entry("/absolute") + self.entry("TRAILER!!!"),
                        self.entry("init") + archive):
            with self.assertRaises((AssertionError, ValueError)):
                initramfs.newc(invalid, 0)

    def test_embedded_archive_members_are_not_multiple_archives(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            RootfsTests().fixture(root)
            init = b"export INITRAMFS=1\nmount -t tmpfs tmpfs $NEW_ROOT\nswitch_root $NEW_ROOT /sbin/init\n"
            archive = self.entry("init", init, 0o100755)
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    archive += self.entry(path.relative_to(root).as_posix(), path.read_bytes())
            archive += self.entry("TRAILER!!!")
            # Replace only the compressed kernel data/hash in a synthetic valid FIT.
            _, tree = fit.fdt(sample_fit())
            raw = bytearray(128)
            raw[56:60] = b"ARM\x64"
            data = gzip.compress(bytes(raw) + archive, mtime=0)
            tree["/images/kernel@1"]["data"] = data
            tree["/images/kernel@1/hash@1"]["value"] = hashlib.sha256(data).digest()
            def node(path):
                children = [(name.rsplit("/", 1)[1], *node(name)) for name in tree
                            if name != "/" and name.rsplit("/", 1)[0] == path.rstrip("/")]
                return tree[path], children
            result = initramfs.inspect(make_fdt(node("/")), root)
            self.assertTrue(result["initramfs_offline_check_passed"])
            self.assertFalse(result["write_free_boot_proven"])


class SysupgradeTests(unittest.TestCase):
    def image(self, *, extra=False, corrupt=False):
        output = io.BytesIO()
        prefix = "sysupgrade-jdcloud_re-cs-06"
        with tarfile.open(fileobj=output, mode="w:") as archive:
            directory = tarfile.TarInfo(prefix)
            directory.type = tarfile.DIRTYPE
            archive.addfile(directory)
            objects = {"CONTROL": b"BOARD=jdcloud_re-cs-06\n", "kernel": sample_fit(bad_hash=corrupt),
                       "root": b"hsqs" + bytes(65532)}
            if extra:
                objects["private-settings"] = b"not-allowed"
            for name, data in objects.items():
                entry = tarfile.TarInfo(prefix + "/" + name)
                entry.size = len(data)
                archive.addfile(entry, io.BytesIO(data))
        return output.getvalue()

    def test_tar_kernel_root_and_no_extra_settings(self):
        result = sysupgrade.inspect(self.image(), b"hsqs")
        self.assertTrue(result["sysupgrade_offline_check_passed"])
        self.assertFalse(result["old_qwrt_direct_upgrade_approved"])
        for image in (self.image(extra=True), self.image(corrupt=True)):
            with self.assertRaises(AssertionError):
                sysupgrade.inspect(image, b"hsqs")


class PolicyTests(unittest.TestCase):
    def test_radio_manifest_matches_verified_local_download_policy(self):
        records = json.loads((REPO / "radio-files.lock.json").read_text())["files"]
        self.assertEqual(len(records), 52)
        paths = set()
        for record in records:
            self.assertNotIn(record["path"], paths)
            paths.add(record["path"])
            self.assertTrue(record["path"].startswith("lib/firmware/ath12k/"))
            self.assertNotIn("..", Path(record["path"]).parts)
            self.assertTrue(record["url"].startswith("https://raw.githubusercontent.com/"))
            self.assertRegex(record["sha256"], r"^[0-9a-f]{64}$")

    def test_image_recipe_defers_soc_and_dtb_expansion(self):
        patch = (REPO / "patches/0003-enforce-persistent-kernel-slot-size.patch").read_text()
        recipes = "\n".join(line[1:] for line in patch.splitlines()
                            if line.startswith("+\tKERNEL"))
        with tempfile.TemporaryDirectory() as temp:
            makefile = Path(temp) / "Makefile"
            makefile.write_text("""KDIR := /kernel
define Device/Test
DEVICE_DTS = $$(SOC)-re-cs-06
""" + recipes + """
SOC := ipq5322
KERNEL_SIZE := 7168k
endef
$(eval $(call Device/Test))
all:
\t@printf '%s\\n' '$(KERNEL)' '$(KERNEL_INITRAMFS)'
""")
            result = subprocess.check_output(["make", "--no-print-directory", "-f", str(makefile)], text=True)
            lines = result.splitlines()
            self.assertEqual(len(lines), 2)
            self.assertTrue(all("/kernel/image-ipq5322-re-cs-06.dtb" in line for line in lines))
            self.assertIn("check-size 7168k", lines[0])
            self.assertNotIn("check-size", lines[1])

    def test_image_version_name_is_shell_safe(self):
        policy.check_version_name('CONFIG_VERSION_DIST="RE-CS-06-Minimal-LEDE"\n')
        for value in ("Unsafe (fork)", "unsafe/name", "unsafe;name", "unsafe name"):
            with self.assertRaises(AssertionError):
                policy.check_version_name(f'CONFIG_VERSION_DIST="{value}"\n')

    def test_forbidden_services(self):
        for name in ("default-settings", "luci-app-nikki", "luci-app-passwall2", "vsftpd",
                     "ttyd", "mihomo", "xray-core", "samba4-server", "luci-theme-argon"):
            self.assertIsNotNone(policy.FORBIDDEN.fullmatch(name), name)

    def test_essentials_not_forbidden(self):
        for name in policy.REQUIRED:
            self.assertIsNone(policy.FORBIDDEN.fullmatch(name), name)

    def test_private_paths_not_allowed(self):
        for name in ("private/identity.json", "backup/ART.bin", "router-known_hosts",
                     "artifacts/firmware.bin", "scripts/../private.json"):
            self.assertIsNone(audit.ALLOWED.fullmatch(name), name)

    def test_secret_patterns(self):
        self.assertIsNotNone(audit.PATTERNS["private_key"].search(b"-----BEGIN " + b"OPENSSH PRIVATE KEY-----"))
        self.assertIsNotNone(audit.PATTERNS["github_token"].search(b"ghp_" + b"x" * 32))

    def test_staged_secret_cannot_hide_behind_clean_working_file(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            path = repo / "README.md"
            path.write_text("synthetic-private-marker")
            subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
            path.write_text("innocent working file")
            result = audit.inspect_repo(repo, ["synthetic-private-marker"])
            self.assertFalse(result["public_source_audit_passed"])
            self.assertEqual(result["errors"], [{"file": "README.md", "reason": "private_literal"}])


class ProvisionTests(unittest.TestCase):
    def run_fixture(self, lan, wan):
        # Replace only fixed filesystem locations; never source host /lib or touch networking.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "board").write_text("jdcloud,re-cs-06\n")
            for name in ("lan1", "lan2", "lan3", "wan"):
                (root / name).touch()
            (root / "functions").write_text('''config_load() { :; }
config_foreach() { "$1" existing_bridge; }
config_get() { eval "$1=br-lan"; }
''')
            (root / "id").write_text("#!/bin/sh\necho 0\n")
            (root / "id").chmod(0o755)
            (root / "uci").write_text('''#!/bin/sh
echo "$*" >> "$LOG"
if [ "$1" = add ]; then echo "cfg$PPID$RANDOM"; fi
''')
            (root / "uci").chmod(0o755)
            script = (REPO / "overlay/usr/sbin/re-cs-06-provision-macs").read_text()
            script = script.replace("/tmp/sysinfo/board_name", str(root / "board"))
            script = script.replace("/sys/class/net/$dev", str(root) + "/$dev")
            script = script.replace("/lib/functions.sh", str(root / "functions"))
            (root / "script").write_text(script)
            import os
            env = {**os.environ, "PATH": str(root) + ":/usr/bin:/bin", "LOG": str(root / "log")}
            result = subprocess.run(["sh", str(root / "script"), lan, wan], env=env, capture_output=True, text=True)
            log = (root / "log").read_text() if (root / "log").exists() else ""
            return result, log

    def test_valid_and_existing_bridge_reused(self):
        # Synthetic locally-administered addresses, generated without literal device identity.
        result, log = self.run_fixture(":".join(["02", "00", "00", "00", "00", "11"]),
                                       ":".join(["02", "00", "00", "00", "00", "12"]))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("network.existing_bridge.macaddr=", log)
        self.assertIn("commit network", log)
        self.assertIn("NOT restarted", result.stdout)

    def test_invalid_inputs_no_uci_writes(self):
        good = ":".join(["02", "00", "00", "00", "00", "11"])
        for bad in ("invalid", "$(touch /not-allowed)", ":".join(["01", "00", "00", "00", "00", "11"]), good):
            result, log = self.run_fixture(bad, good)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(log, "")


class RootfsTests(unittest.TestCase):
    def fixture(self, root):
        content = {
            "etc/shadow": "root:::0:99999:7:::\n",
            "etc/passwd": "root:x:0:0:root:/root:/bin/ash\n",
            "etc/group": "root:x:0:\n",
            "etc/opkg.conf": "option check_signature\n",
            "etc/uci-defaults/90-minimal-defaults": (REPO / "overlay/etc/uci-defaults/90-minimal-defaults").read_text(),
            "usr/sbin/re-cs-06-provision-macs": "#!/bin/sh\nexit 0\n",
            "lib/wifi/mac80211.sh": "set wireless.${section}.disabled='1'\nset wireless.${iface}.disabled='1'\ncountry=\"00\"\n",
        }
        for name, data in content.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(data)
            path.chmod(0o600 if name == "etc/shadow" else 0o644)

    def test_unreadable_account_database_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            for name in ("etc/passwd", "etc/group"):
                (root / name).chmod(0o600)
                with self.assertRaises(AssertionError):
                    rootfs.inspect(root)
                (root / name).chmod(0o644)

    def test_clean_and_private_literal_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            self.assertTrue(rootfs.inspect(root)["rootfs_offline_policy_passed"])
            (root / "private-marker").write_text("synthetic-private-identity-marker")
            with self.assertRaises(AssertionError):
                rootfs.inspect(root, ["synthetic-private-identity-marker"])

    def test_password_or_embedded_key_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            (root / "etc/shadow").write_text("root:embedded-secret:0:0:0:0:::\n")
            with self.assertRaises(AssertionError):
                rootfs.inspect(root)
            self.fixture(root)
            (root / "etc/uhttpd.key").write_text("synthetic-key-marker")
            with self.assertRaises(AssertionError):
                rootfs.inspect(root)


if __name__ == "__main__":
    unittest.main()
