import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('source_package', ROOT/'scripts/package-source.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SourcePackageTests(unittest.TestCase):
    def test_new_nested_patch_sources_are_included(self):
        names = module.patched_paths(ROOT)
        self.assertIn('target/linux/qualcommbe/patches-6.18/0678-pci-re-cs-06-radio-sequence.patch', names)
        self.assertIn('target/linux/qualcommbe/patches-6.18/0677-net-preserve-allocated-dummy-netdev-state.patch', names)
        self.assertNotIn('net/core/dev.c', names)  # Nested payload is not a top-level file.

    def test_unsafe_patch_paths_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'patches').mkdir()
            for name in ('../private', '/private', 'tmp/private', 'files/lib/firmware/blob'):
                (root/'patches/test.patch').write_text('+++ b/'+name+'\n')
                with self.assertRaises(AssertionError):
                    module.patched_paths(root)
