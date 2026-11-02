import unittest
from unittest.mock import patch
import engine as e

class RehireRarity(unittest.TestCase):
 def test_recent_return_is_one_percent_and_older_return_five_percent(self):
  with patch.object(e,'draw',return_value=99):self.assertTrue(e.rehire_allowed('s','c',1,20260401,20260301,e.DEFAULTS))
  with patch.object(e,'draw',return_value=100):self.assertFalse(e.rehire_allowed('s','c',1,20260401,20260301,e.DEFAULTS))
  with patch.object(e,'draw',return_value=499):self.assertTrue(e.rehire_allowed('s','c',1,20261201,20260301,e.DEFAULTS))
  with patch.object(e,'draw',return_value=500):self.assertFalse(e.rehire_allowed('s','c',1,20261201,20260301,e.DEFAULTS))
 def test_new_club_or_never_dismissed_does_not_consume_rarity_draw(self):
  with patch.object(e,'draw') as draw:self.assertTrue(e.rehire_allowed('s','c',2,20261201,None,e.DEFAULTS));draw.assert_not_called()
 def test_decision_is_repeatable_for_the_same_vacancy(self):
  self.assertEqual(e.rehire_allowed('s','c',1,20261201,20260301,e.DEFAULTS),e.rehire_allowed('s','c',1,20261201,20260301,e.DEFAULTS))

if __name__=='__main__':unittest.main()
