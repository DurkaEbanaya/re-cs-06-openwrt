"""Upgrade logic tests use regular temporary files, never real block devices."""
import hashlib
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class UpgradeTests(unittest.TestCase):
    def test_stage2_includes_temporary_directory_tool(self):
        patch = (REPO / 'patches/0010-re-cs-06-checked-upgrade.patch').read_text()
        copy_line = next(line for line in patch.splitlines() if line.startswith('+RAMFS_COPY_BIN='))
        for binary in ('sha256sum', 'head', 'mktemp'):
            self.assertIn(binary, copy_line.split("'")[1].split())

    def fixture(self, directory, extra=False):
        root = Path(directory)
        prefix = 'sysupgrade-jdcloud_re-cs-06'
        image = root / 'image.tar'
        kernel = bytes.fromhex('d00dfeed') + b'K' * 4092
        filesystem = b'hsqs' + b'R' * 65532
        with tarfile.open(image, 'w') as archive:
            entry = tarfile.TarInfo(prefix + '/')
            entry.type = tarfile.DIRTYPE
            archive.addfile(entry)
            files = {'CONTROL': b'BOARD=jdcloud_re-cs-06\n', 'kernel': kernel, 'root': filesystem}
            if extra:
                files['unexpected'] = b'no'
            for name, data in files.items():
                entry = tarfile.TarInfo(prefix + '/' + name)
                entry.size = len(data)
                archive.addfile(entry, io.BytesIO(data))
        for name, size in (('hlos', 7340032), ('rootfs', 196608)):
            (root / name).write_bytes(b'X' * size)
            sizepath = root / 'sys' / name
            sizepath.mkdir(parents=True, exist_ok=True)
            (sizepath / 'size').write_text('14336' if name == 'hlos' else '4194304')
        # Only replace device-test and sysfs path strings. Original write/hash
        # logic runs unchanged against fixture files.
        script = (REPO / 'overlay/lib/upgrade/re-cs-06.sh').read_text()
        script = script.replace('[ -b "$kernel_dev" ]', '[ -f "$kernel_dev" ]')
        script = script.replace('[ -b "$root_dev" ]', '[ -f "$root_dev" ]')
        script = script.replace('/sys/class/block/', str(root / 'sys') + '/')
        script = script.replace('/tmp/recs06-upgrade.', str(root / 'scratch.'))
        (root / 'script').write_text(script)
        return root, image, kernel, filesystem

    def run_script(self, root, image, operation):
        command = '''. "$FIXTURE/script"
find_mmc_part() { case "$1" in 0:HLOS) echo "$FIXTURE/hlos";; rootfs) echo "$FIXTURE/rootfs";; esac; }
OPERATION "$FIXTURE/image.tar"
'''.replace('OPERATION', operation)
        return subprocess.run(['sh', '-c', command], env={**os.environ, 'FIXTURE': str(root)},
                              capture_output=True, text=True)

    def test_check_has_no_writes_and_upgrade_readback(self):
        with tempfile.TemporaryDirectory() as temp:
            root, image, kernel, filesystem = self.fixture(temp)
            before = hashlib.sha256((root / 'hlos').read_bytes()).digest()
            result = self.run_script(root, image, 'recs06_check_image')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(hashlib.sha256((root / 'hlos').read_bytes()).digest(), before)
            result = self.run_script(root, image, 'recs06_do_upgrade')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / 'hlos').read_bytes()[:len(kernel)], kernel)
            data = (root / 'rootfs').read_bytes()
            self.assertEqual(data[:len(filesystem)], filesystem)
            self.assertEqual(data[len(filesystem):len(filesystem)+4096], bytes(4096))

    def test_bad_tar_and_geometry_rejected_without_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            root, image, _, _ = self.fixture(temp, extra=True)
            before = (root / 'hlos').read_bytes(), (root / 'rootfs').read_bytes()
            self.assertNotEqual(self.run_script(root, image, 'recs06_do_upgrade').returncode, 0)
            self.assertEqual(before, ((root / 'hlos').read_bytes(), (root / 'rootfs').read_bytes()))
            self.fixture(temp)
            (root / 'sys/hlos/size').write_text('1')
            self.assertNotEqual(self.run_script(root, image, 'recs06_check_image').returncode, 0)

    def test_backup_roundtrip_at_overlay_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            root, image, _, filesystem = self.fixture(temp)
            backup = root / 'config.tgz'
            with tarfile.open(backup, 'w:gz') as archive:
                entry = tarfile.TarInfo('etc/config/test')
                data = b'synthetic-private-settings\n'
                entry.size = len(data)
                archive.addfile(entry, io.BytesIO(data))
            operation = f'UPGRADE_BACKUP="{backup}"; recs06_do_upgrade'
            result = self.run_script(root, image, operation)
            self.assertEqual(result.returncode, 0, result.stderr)
            output = (root / 'rootfs').read_bytes()
            self.assertEqual(output[len(filesystem):len(filesystem)+backup.stat().st_size], backup.read_bytes())
            recovered = tarfile.open(fileobj=io.BytesIO(output[len(filesystem):]), mode='r:gz')
            self.assertEqual(recovered.extractfile('etc/config/test').read(), data)
            # Bad or missing backups fail before modifying kernel or rootfs.
            for content in (b'not gzip', b''):
                self.fixture(temp)
                backup.write_bytes(content)
                before = (root / 'rootfs').read_bytes(), (root / 'hlos').read_bytes()
                self.assertNotEqual(self.run_script(root, image, operation).returncode, 0)
                self.assertEqual(before, ((root / 'rootfs').read_bytes(), (root / 'hlos').read_bytes()))


if __name__ == '__main__':
    unittest.main()
