"""Ordering/scope checks, not a substitute for stock-bootloader hardware tests."""
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class MdioReferenceTests(unittest.TestCase):
    def test_both_ldo_ready_resources_are_declared_and_initialized(self):
        text = (REPO / 'patches/0017-re-cs-06-uniphy-ldo-ready.patch').read_text()
        self.assertIn('<0x7a00610 0x4>, <0x7a10610 0x4>', text)
        self.assertIn('eth_ldo_rdy[3]', text)
        self.assertIn('ARRAY_SIZE(priv->eth_ldo_rdy)', text)
        self.assertIn('devm_ioremap(', text)
        self.assertNotIn('BRANCH_HALT_SKIP', text)

    def test_ldo_nested_patch_is_parseable(self):
        text = (REPO / 'patches/0017-re-cs-06-uniphy-ldo-ready.patch').read_text()
        section = text.split('@@ -0,0 +1,44 @@\n', 1)[1]
        lines = section.splitlines()
        self.assertEqual(len(lines), 44)
        self.assertTrue(all(line.startswith('+') for line in lines))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'kernel.patch'
            path.write_text('\n'.join(line[1:] for line in lines) + '\n')
            result = subprocess.run(['git', 'apply', '--numstat', str(path)],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_outer_patch_contains_a_parseable_kernel_patch(self):
        text = (REPO / 'patches/0016-re-cs-06-switch-reference-before-reset.patch').read_text()
        nested = text.split('@@ -0,0 +1,35 @@\n', 1)[1]
        lines = nested.splitlines()
        self.assertEqual(len(lines), 35)
        self.assertTrue(all(x.startswith('+') for x in lines))
        patch = '\n'.join(x[1:] for x in lines) + '\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'kernel.patch'
            path.write_text(patch)
            result = subprocess.run(['git', 'apply', '--numstat', str(path)],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_reference_is_enabled_before_gpio_acquisition(self):
        patch = (REPO / 'patches/0016-re-cs-06-switch-reference-before-reset.patch').read_text()
        self.assertIn('IPQ5332_ETH_50MHZ_CLK', patch)
        self.assertIn('devm_clk_get_optional_enabled', patch)
        self.assertLess(patch.index('switch_ref = devm_clk_get_optional_enabled'),
                        patch.index('priv->reset_gpios ='))
        self.assertIn('return dev_err_probe', patch)

    def test_board_opt_in_does_not_change_mdc_or_skip_clock_checks(self):
        patch = (REPO / 'patches/0016-re-cs-06-switch-reference-before-reset.patch').read_text()
        additions = '\n'.join(x for x in patch.splitlines() if x.startswith('+'))
        self.assertIn('ipq5322-re-cs-06.dts', patch)
        self.assertNotIn('BRANCH_HALT_SKIP', additions)
        self.assertNotIn('clock-frequency =', additions)
        self.assertNotIn('mdc_rate =', additions)
