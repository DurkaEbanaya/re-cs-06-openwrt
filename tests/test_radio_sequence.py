"""Board-scoped, bounded radio sequencing; no real devices used."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class RadioSequenceTests(unittest.TestCase):
    def run_helper(self, board='jdcloud,re-cs-06', ready=False, initial='N', path='c000000.wifi'):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'board').write_text(board+'\n')
            (root/'param').write_text(initial+'\n')
            (root/'phy').mkdir()
            if ready:
                (root/'phy/phy0').mkdir()
                (root/'phy/phy0/device').symlink_to(root/path)
            (root/'sleep').write_text('#!/bin/sh\necho sleep >> "$RECORD"\n')
            (root/'logger').write_text('#!/bin/sh\necho "$*" >> "$RECORD"\n')
            for name in ('sleep','logger'):
                (root/name).chmod(0o755)
            text = (REPO/'overlay/usr/libexec/re-cs-06-radio-ready').read_text()
            text = text.replace('/tmp/sysinfo/board_name',str(root/'board'))
            text = text.replace('/sys/module/pcie_qcom/parameters/recs06_radio_ready',str(root/'param'))
            text = text.replace('/sys/class/ieee80211/*',str(root/'phy/*'))
            result = subprocess.run(['sh','-c',text],capture_output=True,text=True,
                env={**os.environ,'PATH':str(root)+':'+os.environ['PATH'],'RECORD':str(root/'record')})
            return result.returncode,(root/'param').read_text(),(root/'record').read_text() if (root/'record').exists() else ''

    def test_only_integrated_phy_releases(self):
        rc,param,log=self.run_helper(ready=True)
        self.assertEqual(rc,0)
        self.assertEqual(param,'Y\n')
        self.assertNotIn('sleep',log)
        rc,param,log=self.run_helper(ready=True,path='18000000.pcie')
        self.assertEqual(param,'N\n')
        self.assertEqual(log.count('sleep'),65)

    def test_wrong_board_or_already_released_does_nothing(self):
        for board,initial in [('other,board','N'),('jdcloud,re-cs-06','Y')]:
            rc,param,log=self.run_helper(board=board,initial=initial,ready=True)
            self.assertEqual(rc,0)
            self.assertEqual(param,initial+'\n')
            self.assertEqual(log,'')

    def test_timeout_leaves_kernel_fail_open_authoritative(self):
        rc,param,log=self.run_helper()
        self.assertEqual(rc,0)
        self.assertEqual(param,'N\n')
        self.assertEqual(log.count('sleep'),65)
        self.assertIn('kernel fail-open',log)

    def test_kernel_gate_is_scoped_one_way_and_bounded(self):
        text=(REPO/'patches/0020-re-cs-06-radio-pcie-sequence.patch').read_text()
        nested='\n'.join(line[1:] for line in text.splitlines() if line.startswith('+') and not line.startswith('+++'))+'\n'
        self.assertIn('of_machine_is_compatible("jdcloud,re-cs-06")',nested)
        self.assertIn('jdcloud,wait-for-ahb-radio',nested)
        self.assertIn('GPIOD_OUT_HIGH',nested)
        self.assertIn('60 * HZ',nested)
        self.assertIn('device_attach(dev)',nested)
        self.assertIn('if (ret || !ready)',nested)
        self.assertNotIn('pci=noaer',nested)
        self.assertNotIn('max-link-speed',nested)
        self.assertNotIn('writel(',nested)

    def test_public_nested_patch_parses(self):
        text=(REPO/'patches/0020-re-cs-06-radio-pcie-sequence.patch').read_text()
        match=re.search(r'@@ -0,0 \+1,(\d+) @@\n',text)
        self.assertIsNotNone(match)
        lines=text[match.end():].splitlines()
        self.assertEqual(len(lines),int(match[1]))
        data='\n'.join(line[1:] for line in lines)+'\n'
        with tempfile.NamedTemporaryFile(mode='w') as f:
            f.write(data);f.flush()
            result=subprocess.run(['git','apply','--numstat',f.name],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_service_is_managed_and_enabled(self):
        service=(REPO/'overlay/etc/init.d/re-cs-06-radio-sequence').read_text()
        self.assertIn('USE_PROCD=1',service)
        self.assertIn('procd_set_param command /usr/libexec/re-cs-06-radio-ready',service)
        self.assertNotIn('respawn',service)
        defaults=(REPO/'overlay/etc/uci-defaults/92-re-cs-06-radio-sequence').read_text()
        self.assertIn('/etc/init.d/re-cs-06-radio-sequence enable',defaults)
