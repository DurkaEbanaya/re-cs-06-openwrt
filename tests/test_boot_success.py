"""Counter policy tests use synthetic files and mocked tools, never firmware."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class BootSuccessTests(unittest.TestCase):
    def run_hook(self, counter, partname='0:APPSBLENV', sectors='512'):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'board').write_text('jdcloud,re-cs-06\n')
            (root / 'env.config').write_text('/dev/synthetic 0x0 0x40000\n')
            (root / 'size').write_text(sectors)
            (root / 'uevent').write_text('PARTNAME=' + partname + '\n')
            (root / 'fw_printenv').write_text('#!/bin/sh\nprintf "%s\\n" "$COUNTER"\n')
            (root / 'fw_setenv').write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$RECORD"\n')
            (root / 'logger').write_text('#!/bin/sh\nexit 0\n')
            for binary in ('fw_printenv', 'fw_setenv', 'logger'):
                (root / binary).chmod(0o755)
            text = (REPO / 'overlay/usr/libexec/re-cs-06-boot-success').read_text()
            text = text.replace('/tmp/sysinfo/board_name', str(root / 'board'))
            text = text.replace('/etc/fw_env.config', str(root / 'env.config'))
            text = text.replace('[ -b "$device" ]', '[ "$device" = /dev/synthetic ]')
            text = text.replace('/sys/class/block/${device##*/}/size', str(root / 'size'))
            text = text.replace('/sys/class/block/${device##*/}/uevent', str(root / 'uevent'))
            (root / 'hook').write_text(text)
            record = root / 'writes'
            result = subprocess.run(['sh', str(root / 'hook')], capture_output=True,
                                    env={**os.environ, 'PATH': str(root) + ':' + os.environ['PATH'],
                                         'COUNTER': counter, 'RECORD': str(record)})
            return result.returncode, record.read_text() if record.exists() else ''

    def test_only_expected_nonzero_counters_are_cleared(self):
        for counter in ('1', '2', '3', '4', '5'):
            rc, writes = self.run_hook(counter)
            self.assertEqual(rc, 0)
            self.assertIn('jd_failsafe_counter 0', writes)
        for counter in ('0', '6', '-1', '', 'garbage'):
            rc, writes = self.run_hook(counter)
            self.assertEqual(writes, '')

    def test_wrong_partition_or_geometry_never_writes(self):
        for part, size in [('factory', '512'), ('0:APPSBLENV', '1024')]:
            rc, writes = self.run_hook('1', part, size)
            self.assertEqual(writes, '')

    def test_hook_registration_preserves_local_script_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'board').write_text('jdcloud,re-cs-06\n')
            (root / 'hook').write_text('#!/bin/sh\nexit 0\n')
            (root / 'hook').chmod(0o755)
            local = root / 'rc.local'
            original = '#!/bin/sh\necho owner-marker\nexit 0\n'
            local.write_text(original)
            text = (REPO / 'overlay/etc/uci-defaults/91-re-cs-06-boot-success').read_text()
            text = text.replace('/tmp/sysinfo/board_name', str(root / 'board'))
            text = text.replace('/usr/libexec/re-cs-06-boot-success', str(root / 'hook'))
            text = text.replace('/etc/rc.local', str(local))
            for _ in range(2):
                result = subprocess.run(['sh', '-c', text], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(local.read_text().count(str(root / 'hook')), 1)
            self.assertIn('echo owner-marker\n', local.read_text())
            self.assertTrue(local.read_text().endswith('exit 0\n'))
