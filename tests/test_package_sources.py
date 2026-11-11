"""Package sources migration must not be skipped by restored network defaults."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class SourcesTests(unittest.TestCase):
    def test_disables_wrong_official_target_and_preserves_custom_feed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'board').write_text('jdcloud,re-cs-06\n')
            feeds = root / 'feeds'
            custom = root / 'custom'
            custom.write_text('src/gz recs06_release https://old.example.org/old\nsrc/gz owner https://owner.example.org/feed\n')
            feeds.write_text(
                'src/gz old_core https://downloads.openwrt.org/releases/24.10.5/targets/qualcommbe/ipq53xx/packages\n'
                'src/gz old_base http://downloads.openwrt.org/releases/24.10.5/packages/aarch64_cortex-a53/base\n'
                'src/gz owner https://packages.example.org/verified\n'
                '# keep this comment\n')
            script = (REPO / 'overlay/etc/uci-defaults/89-re-cs-06-package-sources').read_text()
            script = script.replace('/tmp/sysinfo/board_name', str(root / 'board'))
            script = script.replace('/etc/opkg/distfeeds.conf', str(feeds))
            script = script.replace('/etc/opkg/customfeeds.conf', str(custom))
            script = script.replace('/usr/share/re-cs-06/release-feed', str(root/'absent-binding'))
            script = script.replace('mkdir -p /etc/opkg', ':')
            for _ in range(2):
                subprocess.run(['sh', '-c', script], env=os.environ, check=True)
            lines = feeds.read_text().splitlines()
            self.assertTrue(lines[0].startswith('# Disabled for custom build: src/gz old_core'))
            self.assertTrue(lines[1].startswith('# Disabled for custom build: src/gz old_base'))
            self.assertEqual(lines[2], 'src/gz owner https://packages.example.org/verified')
            self.assertEqual(lines[3], '# keep this comment')
            self.assertEqual(custom.read_text(), 'src/gz owner https://owner.example.org/feed\n')

    def test_provision_callback_returns_success_on_nonmatching_section(self):
        script = (REPO / 'overlay/usr/sbin/re-cs-06-provision-macs').read_text()
        callback = script.split('find_device() {', 1)[1].split('\n}', 1)[0]
        subprocess.run(['sh', '-c', 'set -e; wanted=br-lan; config_get() { name=unrelated; }; '
                        'find_device() {' + callback + '\n}; find_device test; echo survived'],
                       check=True, capture_output=True)
