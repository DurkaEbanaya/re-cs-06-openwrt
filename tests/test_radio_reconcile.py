"""Only retry a failed enabled radio once, after its matching PHY exists."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class ReconcileTests(unittest.TestCase):
    def run_fixture(self, disabled='0', up='false', pending='false', failed='true', present=True):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root/'board').write_text('jdcloud,re-cs-06\n')
            if present: (root/'phys/phy1').mkdir(parents=True)
            (root/'functions').write_text('config_load() { :; }\nconfig_foreach() { "$1" radio1; }\nconfig_get_bool() { disabled="$DISABLED"; }\n')
            commands = {
                'ubus': '#!/bin/sh\ncase "$*" in *phyname*) echo phy1 ;; *) echo status ;; esac\n',
                'jsonfilter': '#!/bin/sh\ncase "$*" in *.up*) echo "$UP" ;; *.pending*) echo "$PENDING" ;; *.retry_setup_failed*) echo "$FAILED" ;; *phyname*) echo phy1 ;; esac\n',
                'sleep': '#!/bin/sh\n: \n',
                'logger': '#!/bin/sh\n: \n',
                'wifi': '#!/bin/sh\necho "$*" >> "$RECORD"\n',
            }
            for name, text in commands.items():
                path = root/name; path.write_text(text); path.chmod(0o755)
            text = (REPO/'overlay/usr/libexec/re-cs-06-radio-reconcile').read_text()
            for old,new in [('/tmp/sysinfo/board_name',str(root/'board')),('/lib/functions.sh',str(root/'functions')),('/sys/class/ieee80211',str(root/'phys')),('/sbin/wifi',str(root/'wifi'))]:
                text=text.replace(old,new)
            env=dict(os.environ, PATH=str(root)+':'+os.environ['PATH'], DISABLED=disabled,
                     UP=up, PENDING=pending, FAILED=failed, RECORD=str(root/'calls'))
            result=subprocess.run(['sh','-c',text],env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            return (root/'calls').read_text() if (root/'calls').exists() else ''

    def test_failed_ready_radio_retried_only_once(self):
        self.assertEqual(self.run_fixture(),'up radio1\n')

    def test_disabled_up_pending_missing_phy_or_no_failure_not_restarted(self):
        for args in [dict(disabled='1'),dict(up='true'),dict(pending='true'),dict(failed='false'),dict(present=False)]:
            with self.subTest(args=args):self.assertEqual(self.run_fixture(**args),'')
