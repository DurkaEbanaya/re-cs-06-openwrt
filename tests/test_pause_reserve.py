import re
import subprocess
import unittest
from pathlib import Path


class PauseReserveTests(unittest.TestCase):
    def test_nested_patch_scope_and_fields(self):
        path = Path(__file__).resolve().parents[1] / 'patches/0021-qca8386-pause-reaction-reserve.patch'
        text = path.read_text()
        body = text.split('@@ -0,0 +1,', 1)[1].split('\n', 1)[1]
        nested = '\n'.join(line[1:] for line in body.splitlines()) + '\n'
        subprocess.run(['git', 'apply', '--numstat', '-'], input=nested,
                       text=True, capture_output=True, check=True)
        self.assertIn('if (qca8k_is_qca8386(priv))', nested)
        self.assertIn('FIELD_PREP(QCA8386_QM_FLOW_DROP_CNT, 60)', nested)
        self.assertIn('QCA8386_QM_FLOW_DROP_EN | QCA8386_QM_FLOW_DROP_CNT', nested)
        self.assertIn('GENMASK(5, 0)', nested)
        self.assertIn('BIT(6)', nested)
        self.assertIn('return dev_err_probe', nested)
        added = '\n'.join(line for line in nested.splitlines()
                          if line.startswith('+') and not line.startswith('+++'))
        self.assertNotRegex(added, r'WRED|HOL_CTRL|msleep|udelay|netdev_max_backlog')


if __name__ == '__main__':
    unittest.main()
