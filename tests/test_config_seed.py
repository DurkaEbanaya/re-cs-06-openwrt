import gzip
import importlib.util
import io
from pathlib import Path
import tarfile
import unittest

spec = importlib.util.spec_from_file_location('seed', Path(__file__).resolve().parents[1] / 'scripts/make-config-seed.py')
seed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed)


class ConfigSeedTests(unittest.TestCase):
    def archive(self, name, kind=tarfile.REGTYPE):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w') as archive:
            member = tarfile.TarInfo(name)
            member.type = kind
            archive.addfile(member, io.BytesIO())
        return stream.getvalue()

    def test_exact_fstools_header_and_roundtrip(self):
        tar = self.archive('etc/rc.local')
        encoded = seed.encode(tar)
        self.assertEqual(encoded[:4], bytes.fromhex('1f8b0800'))
        self.assertEqual(gzip.decompress(encoded), tar)

    def test_default_gzip_filename_is_not_compatible(self):
        output = io.BytesIO()
        with gzip.GzipFile(filename='config.tgz', fileobj=output, mode='wb') as f:
            f.write(self.archive('etc/shadow'))
        self.assertNotEqual(output.getvalue()[:4], bytes.fromhex('1f8b0800'))

    def test_reject_unsafe_members(self):
        for name, kind in [('../etc/shadow', tarfile.REGTYPE),
                           ('/etc/shadow', tarfile.REGTYPE),
                           ('etc/link', tarfile.SYMTYPE)]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                seed.encode(self.archive(name, kind))
