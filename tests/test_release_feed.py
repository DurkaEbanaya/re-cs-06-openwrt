"""Exact release feeds must not follow a moving latest URL or a foreign ABI."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('binding', ROOT/'scripts/configure-release-feed.py')
binding = importlib.util.module_from_spec(spec)
spec.loader.exec_module(binding)


class ReleaseFeedTests(unittest.TestCase):
    def test_marker_rejects_credentials_and_moving_or_injected_urls(self):
        kernel = '6.18.60-1-fixture'
        key = '0123456789abcdef'
        for url in ['http://example.org/'+kernel, 'https://example.org/latest',
                    'https://user:password@example.org/'+kernel,
                    'https://example.org/'+kernel+'?token=secret',
                    'https://example.org/'+kernel+'\nreboot']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                binding.marker(kernel, url, key)
        self.assertIn(kernel, binding.marker(kernel, 'https://example.org/'+kernel, key))

    def test_registers_only_current_signed_feed_and_preserves_owner_sources(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root/'keys').mkdir()
            (root/'keys/0123456789abcdef').write_text('fixture public key')
            (root/'board').write_text('jdcloud,re-cs-06\n')
            (root/'custom').write_text('src/gz owner https://owner.example.org/feed\n')
            (root/'dist').write_text('')
            kernel = '6.18.60-1-fixture'
            url = 'https://example.org/packages-'+kernel
            (root/'binding').write_text(binding.marker(kernel, url, '0123456789abcdef'))
            script = (ROOT/'overlay/etc/uci-defaults/89-re-cs-06-package-sources').read_text()
            for old, new in [('/tmp/sysinfo/board_name', root/'board'),
                             ('/etc/opkg/distfeeds.conf', root/'dist'),
                             ('/etc/opkg/customfeeds.conf', root/'custom'),
                             ('/usr/share/re-cs-06/release-feed', root/'binding'),
                             ('/etc/opkg/keys/', str(root/'keys')+'/')]:
                script = script.replace(old, str(new))
            script = script.replace('mkdir -p /etc/opkg', ':')
            script = script.replace('opkg status kernel', "printf 'Version: "+kernel+"\\n'")
            for _ in range(2):
                subprocess.run(['sh', '-c', script], check=True, capture_output=True)
            self.assertEqual((root/'custom').read_text().splitlines(),
                             ['src/gz owner https://owner.example.org/feed', 'src/gz recs06_release '+url])
            bad = script.replace("printf 'Version: "+kernel, "printf 'Version: wrong")
            self.assertNotEqual(subprocess.run(['sh', '-c', bad], capture_output=True).returncode, 0)
            self.assertEqual((root/'custom').read_text(), 'src/gz owner https://owner.example.org/feed\n')
