import subprocess
import unittest
from pathlib import Path


class UsbClockTests(unittest.TestCase):
    def test_board_scoped_rates_are_assigned_before_probe(self):
        root = Path(__file__).resolve().parents[1]
        patch = (root / 'patches/0022-re-cs-06-usb-clock-rates.patch').read_text()
        subprocess.run(['git', 'apply', '--numstat', '-'], input=patch,
                       text=True, capture_output=True, check=True)
        self.assertEqual(patch.count('diff --git '), 1)
        self.assertIn('dts/ipq5322-re-cs-06.dts', patch)
        added = '\n'.join(line[1:] for line in patch.splitlines()
                          if line.startswith('+') and not line.startswith('+++'))
        clocks = ['GCC_USB0_MASTER_CLK', 'GCC_USB0_MOCK_UTMI_CLK',
                  'GCC_USB0_AUX_CLK', 'GCC_USB0_LFPS_CLK']
        self.assertEqual(sorted(added.count(clock) for clock in clocks), [1]*4)
        self.assertEqual([added.index(clock) for clock in clocks],
                         sorted(added.index(clock) for clock in clocks))
        self.assertIn('<200000000>, <60000000>, <2000000>, <25000000>', added)
        self.assertNotRegex(added, r'gpio|reset|sleep|quirk|maximum-speed|regulator')


if __name__ == '__main__':
    unittest.main()
