"""Static safety checks for opt-in local beta launcher."""
import unittest
from pathlib import Path

class LocalBetaSafety(unittest.TestCase):
    def test_localhost_only_and_private_state(self):
        source = (Path(__file__).resolve().parents[1] / 'versionary_local_beta.py').read_text()
        self.assertIn("host='127.0.0.1'", source)
        self.assertIn('0o600', source)
        self.assertIn('0o700', source)
        self.assertIn("'ARBY_AGENT_REPORTING_ENABLED'] = 'false'", source)
        self.assertNotIn('systemctl', source)

if __name__ == '__main__':
    unittest.main()
