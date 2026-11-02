#!/usr/bin/env python3
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import tempfile
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


class PolicyTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
