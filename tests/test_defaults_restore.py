"""First-install defaults must not reset a restored owner network."""
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class DefaultsRestoreTests(unittest.TestCase):
    def run_defaults(self, member=None, compressed=False):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'board').write_text('jdcloud,re-cs-06\n')
            (root / 'bin').mkdir()
            uci = root / 'bin/uci'
            uci.write_text('#!/bin/sh\necho called >> "$UCI_LOG"\ncat >/dev/null\n')
            uci.chmod(0o755)
            if member:
                archive = root / ('sysupgrade.tgz' if compressed else 'sysupgrade.tar')
                with tarfile.open(archive, 'w:gz' if compressed else 'w') as t:
                    m = tarfile.TarInfo(member)
                    m.size = 4
                    t.addfile(m, io.BytesIO(b'test'))
            script = (REPO / 'overlay/etc/uci-defaults/90-minimal-defaults').read_text()
            for old, new in [('/tmp/sysinfo/board_name', root / 'board'),
                             ('/tmp/sysupgrade.tar', root / 'sysupgrade.tar'),
                             ('/sysupgrade.tgz', root / 'sysupgrade.tgz'),
                             ('/etc/opkg/distfeeds.conf', root / 'feeds')]:
                script = script.replace(old, str(new))
            p = subprocess.run(['sh', '-c', script], capture_output=True,
                               env={**os.environ, 'PATH': str(root / 'bin') + ':' + os.environ['PATH'],
                                    'UCI_LOG': str(root / 'uci-log')})
            self.assertEqual(p.returncode, 0, p.stderr)
            return (root / 'uci-log').exists()

    def test_restored_network_preserved_in_both_archive_forms(self):
        for compressed in (False, True):
            for path in ('etc/config/network', './etc/config/network'):
                self.assertFalse(self.run_defaults(path, compressed))

    def test_fresh_install_and_access_only_seed_receive_defaults(self):
        self.assertTrue(self.run_defaults())
        self.assertTrue(self.run_defaults('etc/dropbear/authorized_keys'))
