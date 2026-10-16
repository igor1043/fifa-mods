import unittest
from install import configuration_payload

class SavedChoiceTests(unittest.TestCase):
    source=b'[cloth_motion]\r\nenabled=0\r\nshorts_hem_lift_m=0.015\r\n'
    def test_new_installation_starts_off(self):
        self.assertEqual(configuration_payload(self.source),self.source)
    def test_upgrade_preserves_explicit_opt_in_and_updated_tuning(self):
        old=b'\xef\xbb\xbf[other]\nenabled=0\n[CLOTH_MOTION]\n enabled = 1 ; saved\nshorts_hem_lift_m=0.012\n'
        self.assertEqual(configuration_payload(self.source,old),self.source.replace(b'enabled=0',b'enabled=1'))
    def test_off_missing_invalid_stay_off(self):
        for old in (b'[cloth_motion]\nenabled=0\n',b'[other]\nenabled=1\n',b'[cloth_motion]\nenabled=bad\n'):
            self.assertEqual(configuration_payload(self.source,old),self.source)
    def test_requested_reset_turns_off_previous_opt_in(self):
        self.assertEqual(configuration_payload(self.source,b'[cloth_motion]\nenabled=1\n',True),self.source)

if __name__=='__main__':unittest.main()
