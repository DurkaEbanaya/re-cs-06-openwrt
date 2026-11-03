"""Scoped RPS policy; writes only regular temporary fixture files."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class RpsTests(unittest.TestCase):
    def test_scope_and_online_cpu(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            board = root / 'board'
            cpu = root / 'cpu1'
            cpu.mkdir()
            online = cpu / 'online'
            uci = root / 'uci'
            uci.write_text('#!/bin/sh\nprintf "%s" "${STEERING:-}"\n')
            uci.chmod(0o755)
            queues = root / 'queues'
            for index in range(4):
                path = queues / f'rx-{index}/rps_cpus'
                path.parent.mkdir(parents=True)
                path.write_text('1\n')
            text = (REPO / 'overlay/etc/hotplug.d/net/90-re-cs-06-rps').read_text()
            text = text.replace('/tmp/sysinfo/board_name', str(board))
            text = text.replace('/sys/devices/system/cpu/cpu1', str(cpu))
            text = text.replace('/sys/class/net/switch/queues', str(queues))
            for action, device, model, cpu_state, expected in (
                ('remove', 'switch', 'jdcloud,re-cs-06', '1', '1'),
                ('add', 'wlan0', 'jdcloud,re-cs-06', '1', '1'),
                ('add', 'switch', 'other', '1', '1'),
                ('add', 'switch', 'jdcloud,re-cs-06', '0', '1'),
                ('add', 'switch', 'jdcloud,re-cs-06', '1', '2'),
                ('add', 'switch', 'jdcloud,re-cs-06', None, '2'),
            ):
                board.write_text(model)
                for path in queues.glob('*/rps_cpus'):
                    path.write_text('1\n')
                if cpu_state is None:
                    online.unlink()
                else:
                    online.write_text(cpu_state)
                subprocess.run(['sh', '-c', text], env={**os.environ, 'PATH': str(root) + ':' + os.environ['PATH'], 'ACTION': action,
                                                      'DEVICENAME': device}, check=True)
                self.assertTrue(all(path.read_text().strip() == expected
                                    for path in queues.glob('*/rps_cpus')))
            for path in queues.glob('*/rps_cpus'):
                path.write_text('1\n')
            subprocess.run(['sh', '-c', text], env={**os.environ, 'PATH': str(root) + ':' + os.environ['PATH'],
                           'ACTION': 'add', 'DEVICENAME': 'switch', 'STEERING': '0'}, check=True)
            self.assertTrue(all(path.read_text().strip() == '1' for path in queues.glob('*/rps_cpus')))

    def test_platform_wrapper_preserves_generic_arguments_and_failures(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            log = root / 'calls'
            generic = root / 'generic'
            generic.write_text('#!/bin/sh\necho "generic:$*" >> "$LOG"\nexit "${FAIL:-0}"\n')
            generic.chmod(0o755)
            override = root / 'override'
            override.write_text('#!/bin/sh\necho "override:$ACTION:$DEVICENAME" >> "$LOG"\n')
            uci = root / 'uci'
            uci.write_text('#!/bin/sh\nprintf "%s" "$FLOWS"\n')
            uci.chmod(0o755)
            text = (REPO / 'overlay/usr/libexec/platform/packet-steering.sh').read_text()
            text = text.replace('/usr/libexec/network/packet-steering.uc', str(generic))
            text = text.replace('/etc/hotplug.d/net/90-re-cs-06-rps', str(override))
            env = {**os.environ, 'PATH': str(root) + ':' + os.environ['PATH'], 'LOG': str(log)}
            for flows, expected in [('128', 'generic:-l 128 2'), ('', 'generic:2'), ('invalid', 'generic:2')]:
                log.write_text('')
                subprocess.run(['sh', '-c', text, 'script', '2'], env={**env, 'FLOWS': flows}, check=True)
                self.assertEqual(log.read_text().splitlines(), [expected, 'override:add:switch'])
            log.write_text('')
            result = subprocess.run(['sh', '-c', text], env={**env, 'FLOWS': '', 'FAIL': '7'})
            self.assertEqual(result.returncode, 7)
            self.assertEqual(log.read_text().splitlines(), ['generic:'])
            log.write_text('')
            subprocess.run(['sh', '-c', text, 'script', '0'], env={**env, 'FLOWS': ''}, check=True)
            self.assertEqual(log.read_text().splitlines(), ['generic:0'])
