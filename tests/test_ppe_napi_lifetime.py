"""Pinned-kernel NAPI setup regression; hardware unbind is tested separately."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class PpeNapiLifetimeTests(unittest.TestCase):
    def test_nested_patch_and_preserved_allocator_state(self):
        text = (REPO / 'patches/0019-ppe-ds-napi-netdev-lifetime.patch').read_text()
        match = re.search(r'@@ -0,0 \+1,(\d+) @@\n', text)
        self.assertIsNotNone(match)
        lines = text[match.end():].splitlines()
        self.assertEqual(len(lines), int(match[1]))
        self.assertTrue(all(line.startswith('+') for line in lines))
        patch = '\n'.join(line[1:] for line in lines) + '\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'kernel.patch'
            path.write_text(patch)
            result = subprocess.run(['git', 'apply', '--numstat', str(path)],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        additions = '\n'.join(line[1:] for line in patch.splitlines()
                              if line.startswith('+') and not line.startswith('+++'))
        self.assertIn('static void setup_allocated_dummy_netdev', additions)
        self.assertIn('setup_allocated_dummy_netdev);', additions)
        self.assertIn('dev->reg_state = NETREG_DUMMY;', additions)
        self.assertIn('set_bit(__LINK_STATE_PRESENT', additions)
        self.assertIn('set_bit(__LINK_STATE_START', additions)
        self.assertNotIn('memset(', additions)
        self.assertNotIn('alloc_netdev_dummy(', additions)
        self.assertNotIn('kfree(', additions)
        self.assertIn('--- a/net/core/dev.c', patch)
