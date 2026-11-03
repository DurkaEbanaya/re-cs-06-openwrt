"""Check patch scope; real fw4 execution is recorded in hardware reports."""
from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[1]


class FlowtableIngressTests(unittest.TestCase):
    def test_only_board_software_path_is_extended(self):
        text = (REPO / 'patches/0015-re-cs-06-software-flowtable-ingress.patch').read_text()
        self.assertIn("'jdcloud,re-cs-06'", text)
        self.assertIn('resolve_lower_devices(dsa_status, device)', text)
        self.assertIn("bus.call('network.device', 'status')", text)
        self.assertIn('push(devices, device)', text)
        additions = '\n'.join(line for line in text.splitlines() if line.startswith('++'))
        self.assertNotIn('flow_offloading_hw =', additions)
        self.assertNotIn('flags offload', additions)
