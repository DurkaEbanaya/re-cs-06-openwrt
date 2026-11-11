"""Read-only preflight accepts both proven geometries, never guesses a slot."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class PreflightTests(unittest.TestCase):
    def run_fixture(self, sectors='249856', root='PARTUUID=ABCDEF-1234'):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            files = {
                '/tmp/sysinfo/board_name': 'jdcloud,re-cs-06\n',
                '/etc/openwrt_release': 'fixture\n',
                '/proc/cmdline': 'console=tty root=' + root + '\n',
                '/sys/class/block/mmcblk0p23/uevent': 'PARTUUID=abcdef-1234\nPARTNAME=rootfs\n',
                '/sys/class/block/mmcblk0p21/uevent': 'PARTNAME=0:HLOS\n',
                '/sys/class/block/mmcblk0p21/size': '14336\n',
                '/sys/class/block/mmcblk0p23/size': sectors + '\n',
                '/sys/block/loop0/loop/backing_file': '/mmcblk0p23\n',
                '/proc/mounts': 'fixture mounts\n',
                '/etc/sysupgrade.conf': '# fixture preservation\n',
            }
            text = (REPO / 'overlay/usr/sbin/re-cs-06-upgrade-preflight').read_text()
            for i, (name, data) in enumerate(files.items()):
                path = base / f'file{i}'
                path.write_text(data)
                text = text.replace(name, str(path))
            for name in ['ubus', 'opkg', 'df']:
                path = base / name
                path.write_text('#!/bin/sh\nexit 0\n')
                path.chmod(0o755)
            # Any accidental update command is a failure; no image is supplied.
            path = base / 'sysupgrade'
            path.write_text('#!/bin/sh\nexit 99\n')
            path.chmod(0o755)
            script = base / 'preflight'
            script.write_text(text)
            return subprocess.run(['sh', str(script)], env=dict(os.environ, PATH=str(base)+':'+os.environ['PATH']), capture_output=True, text=True)

    def test_primary_both_geometries_and_case(self):
        for sectors in ['249856', '4194304']:
            for root in ['PARTUUID=ABCDEF-1234', 'PARTUUID=abcdef-1234']:
                with self.subTest(sectors=sectors, root=root):
                    result = self.run_fixture(sectors, root)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn('No writes performed', result.stdout)

    def test_secondary_unknown_and_duplicate_root_refused(self):
        for sectors, root in [('250000', 'PARTUUID=abcdef-1234'), ('249856', 'PARTUUID=other'),
                              ('249856', '/dev/mmcblk0p23'), ('249856', 'PARTUUID=abcdef-1234 root=PARTUUID=abcdef-1234')]:
            with self.subTest(sectors=sectors, root=root):
                result = self.run_fixture(sectors, root)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Preflight refused', result.stderr)
