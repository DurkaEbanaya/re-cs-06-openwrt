"""Static service regression: rc.common must interpret its own entry point."""
from pathlib import Path
import subprocess
import unittest


class HealthLogTests(unittest.TestCase):
    def test_rc_common_entry_and_bounded_interval(self):
        path = Path(__file__).resolve().parents[1] / 'scripts/jd-health-log.init'
        text = path.read_text()
        subprocess.run(['sh', '-n', str(path)], check=True)
        self.assertTrue(text.startswith('#!/bin/sh /etc/rc.common\n'))
        self.assertIn('procd_set_param command /usr/libexec/jd-health-log', text)
        self.assertNotIn('command /bin/sh /etc/init.d/', text)
        worker = path.with_name('jd-health-log-worker').read_text()
        subprocess.run(['sh', '-n', str(path.with_name('jd-health-log-worker'))], check=True)
        self.assertIn('sleep 60', worker)
        self.assertIn('dmesg | logger -t jd-boot', worker)
        self.assertNotIn('. /etc/rc.common', worker)
        self.assertNotIn('uci ', text)
        self.assertNotIn('dd ', text)
        self.assertNotIn('reboot', text)


if __name__ == '__main__':
    unittest.main()
