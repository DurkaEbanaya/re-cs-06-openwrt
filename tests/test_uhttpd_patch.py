"""Validate the nested package patch and allocation cleanup ordering."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class UhttpdPatchTests(unittest.TestCase):
    def test_inner_patch_lengths_and_cleanup(self):
        outer = (ROOT / 'patches/0023-uhttpd-cgi-size-t.patch').read_text()
        self.assertIn('+PKG_RELEASE:=2', outer)
        lines = outer.splitlines()
        header = next(i for i, line in enumerate(lines) if line.startswith('@@ -0,0 +1,'))
        count = int(re.search(r'\+1,(\d+)', lines[header])[1])
        inner_lines = lines[header + 1:]
        self.assertEqual(len(inner_lines), count)
        self.assertTrue(all(line.startswith('+') for line in inner_lines))
        inner = '\n'.join(line[1:] for line in inner_lines)
        self.assertIn('+static size_t field_len(', inner)
        self.assertIn('-\tcl->dispatch.req_free = uh_free_pending_request;', inner)
        self.assertIn('+\tcl->dispatch.req_free = uh_free_pending_request;', inner)
        self.assertEqual(inner.count('+\t\tif (!dr) {'), 2)
        self.assertIn('+\tif (!in) {', inner)
        # Check all embedded unified hunk counts, including context-only spaces.
        chunks = re.split(r'(?m)^@@ ', inner)[1:]
        for chunk in chunks:
            hunk_header, body = chunk.split('\n', 1)
            match = re.match(r'-(\d+),(\d+) \+(\d+),(\d+) @@', hunk_header)
            self.assertIsNotNone(match)
            hunk = []
            for line in body.splitlines():
                if line.startswith(('--- ', '+++ ')):
                    break
                hunk.append(line)
            self.assertEqual(sum(line.startswith((' ', '-')) for line in hunk), int(match[2]))
            self.assertEqual(sum(line.startswith((' ', '+')) for line in hunk), int(match[4]))


if __name__ == '__main__':
    unittest.main()
