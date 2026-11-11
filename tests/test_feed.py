"""Offline parser fixtures use synthetic IPKs, no real signing keys or devices."""
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('feed', REPO / 'scripts/package-compatible-feed.py')
feed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feed)


class FeedTests(unittest.TestCase):
    @staticmethod
    def write_ipk(path, text):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w:gz') as archive:
            data = text.encode()
            member = tarfile.TarInfo('./control')
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
        with tarfile.open(path, 'w:gz') as archive:
            member = tarfile.TarInfo('./control.tar.gz')
            member.size = len(stream.getvalue())
            archive.addfile(member, io.BytesIO(stream.getvalue()))

    def test_collect_skips_stale_kmods_and_rejects_ambiguous_or_wrong_arch(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            selected = {'kmod-example', 'app'}
            stale = base / 'stale.ipk'
            self.write_ipk(stale, 'Package: kmod-example\nVersion: 1\nArchitecture: aarch64_cortex-a53\nDepends: kernel (=old-abi)\n')
            current = base / 'current.ipk'
            self.write_ipk(current, 'Package: kmod-example\nVersion: 1\nArchitecture: aarch64_cortex-a53\nDepends: kernel (=new-abi)\n')
            records = feed.collect_records([stale, current], selected, 'new-abi')
            self.assertEqual(records['kmod-example']['path'], current)
            wrong = base / 'wrong.ipk'
            self.write_ipk(wrong, 'Package: app\nVersion: 1\nArchitecture: x86_64\n')
            with self.assertRaisesRegex(SystemExit, 'Wrong architecture'):
                feed.collect_records([wrong], selected, 'new-abi')
            one, two = base / 'one.ipk', base / 'two.ipk'
            for path, version in [(one, '1'), (two, '2')]:
                self.write_ipk(path, f'Package: app\nVersion: {version}\nArchitecture: all\n')
            with self.assertRaisesRegex(SystemExit, 'Ambiguous package'):
                feed.collect_records([one, two], selected, 'new-abi')

    @staticmethod
    def record(name, depends='', **extra):
        return dict(control=dict(Package=name, Version='1-r1', Depends=depends, **extra))

    def test_dependency_closure_cycles_aliases_and_exact_package_precedence(self):
        records = {
            'app': self.record('app', 'nftables, libalias, kmod-example'),
            'nftables-json': self.record('nftables-json', SourceName='nftables', Provides='nftables'),
            'nftables-nojson': self.record('nftables-nojson', SourceName='nftables', Provides='nftables'),
            'nftables': self.record('nftables'),
            'libalias1': self.record('libalias1', 'app', Provides='libalias'),
            'kmod-example': self.record('kmod-example', 'kernel (=6.18.60-1-fixture)'),
            'kernel': self.record('kernel'),
        }
        closure, kernel = feed.dependency_closure(records, ['app'], '6.18.60-1-fixture')
        self.assertTrue(kernel)
        self.assertEqual(closure, {'app', 'nftables', 'libalias1', 'kmod-example'})
        self.assertNotIn('kernel', closure)
        del records['nftables']
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            feed.dependency_closure(records, ['app'], '6.18.60-1-fixture')

    def test_missing_wrong_kernel_and_version_constraints_fail_closed(self):
        for dependency in ['missing', 'kernel (=wrong)', 'kernel', 'kernel (>=6.18.60-1-fixture)', 'lib (>=2-r1)']:
            records = {'app': self.record('app', dependency), 'lib': self.record('lib')}
            with self.subTest(dependency=dependency), self.assertRaises(ValueError):
                feed.dependency_closure(records, ['app'], '6.18.60-1-fixture', lambda *_: False)
        records = {'app': self.record('app', 'missing | lib (>=1-r1)'), 'lib': self.record('lib')}
        observed = []
        def compare(*args):
            observed.append(args)
            return True
        self.assertEqual(feed.dependency_closure(records, ['app'], 'fixture', compare), ({'app', 'lib'}, False))
        self.assertEqual(observed, [('1-r1', '>=', '1-r1')])

    def test_control_parser_and_continuation(self):
        text = ('Package: example\nVersion: 1-r1\nArchitecture: all\n'
                'Depends: libc, kernel (= 6.18.60-1-fixture)\n'
                'Description: test\n continuation\n')
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w:gz') as archive:
            data = text.encode()
            member = tarfile.TarInfo('./control')
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'example.ipk'
            with tarfile.open(path, 'w:gz') as archive:
                member = tarfile.TarInfo('./control.tar.gz')
                member.size = len(stream.getvalue())
                archive.addfile(member, io.BytesIO(stream.getvalue()))
            parsed = feed.control(path)
        self.assertEqual(parsed['Package'], 'example')
        self.assertIn('kernel (= 6.18.60-1-fixture)', parsed['Depends'])
        self.assertEqual(parsed['Description'], 'test\n continuation')
        with self.assertRaises(ValueError):
            feed.fields('Package: first\nPackage: second\n')

    def test_full_tc_selected_for_sqm_virtual_dependency(self):
        records = {'sqm-scripts': self.record('sqm-scripts', 'tc'),
                   'tc-tiny': self.record('tc-tiny', Provides='tc'),
                   'tc-full': self.record('tc-full', Provides='tc')}
        self.assertEqual(feed.dependency_closure(records, ['sqm-scripts'], 'fixture')[0],
                         {'sqm-scripts', 'tc-full'})

    def test_public_payload_rejects_firmware_and_traversal(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'test.ipk'
            for name in ['./usr/bin/example', './lib/firmware/radio.bin', '../etc/shadow', '/etc/shadow']:
                data = io.BytesIO()
                with tarfile.open(fileobj=data, mode='w:gz') as archive:
                    entry = tarfile.TarInfo(name); entry.size = 4
                    archive.addfile(entry, io.BytesIO(b'test'))
                with tarfile.open(path, mode='w:gz') as archive:
                    entry = tarfile.TarInfo('./data.tar.gz'); entry.size = len(data.getvalue())
                    archive.addfile(entry, io.BytesIO(data.getvalue()))
                if name == './usr/bin/example':
                    feed.check_public_payload(path)
                else:
                    with self.subTest(name=name), self.assertRaises(ValueError):
                        feed.check_public_payload(path)

    def test_new_source_recipe_does_not_copy_whole_kernel(self):
        text = (REPO / 'scripts/prepare-extra-packages.py').read_text()
        lock = __import__('json').loads((REPO / 'extra-packages.lock.json').read_text())
        for key in ['kernel_source_commit', 'tools_source_commit', 'commit']:
            self.assertRegex(lock['amneziawg'][key], r'^[0-9a-f]{40}$')
        self.assertIn("text.replace(block, '')", text)
