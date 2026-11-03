"""Packaging checks, not execution of the ARM64 algorithms."""
from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[1]


class CryptoPackageTests(unittest.TestCase):
    def test_ipq53xx_ce_is_explicit_and_scoped(self):
        patch = (REPO / 'patches/0014-ipq53xx-armv8-crypto-package.patch').read_text()
        self.assertIn('@TARGET_qualcommbe_ipq53xx', patch)
        for symbol, module in (
                ('AES_ARM64_CE', 'aes-ce-cipher'),
                ('AES_ARM64_CE_BLK', 'aes-ce-blk'),
                ('AES_ARM64_CE_CCM', 'aes-ce-ccm'),
                ('GHASH_ARM64_CE', 'ghash-ce')):
            self.assertIn('CONFIG_CRYPTO_' + symbol, patch)
            self.assertIn(module + '.ko', patch)
            self.assertIn(module, patch.split('AUTOLOAD:=')[1].splitlines()[0])
        self.assertIn('CONFIG_PACKAGE_kmod-crypto-armv8-ce-ipq53xx=y',
                      (REPO / 'config/resources-candidate.config').read_text())
        self.assertNotIn('CONFIG_CRYPTO_DEV_QCE', patch)
