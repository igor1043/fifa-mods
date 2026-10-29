from pathlib import Path
import unittest,xml.etree.ElementTree as ET
import test_screen
import package

class PackageTest(unittest.TestCase):
 def test_card_and_navigation_preserve_existing_entries_and_are_idempotent(self):
  game=Path(__file__).resolve().parents[4];raw=(game/package.XML).read_bytes();new=package.layout(raw);before=ET.fromstring(raw);after=ET.fromstring(new)
  old_events=[n.get('DESTINATION') for n in before.iter() if n.get('DESTINATION')];new_events=[n.get('DESTINATION') for n in after.iter() if n.get('DESTINATION')]
  for e in old_events:self.assertEqual(old_events.count(e),new_events.count(e))
  self.assertEqual(1,new_events.count(package.EVENT));self.assertEqual(new,package.layout(new))
  nav=package.navigation((game/package.NAV).read_bytes());self.assertEqual(nav,package.navigation(nav));data=package.read_nav(nav.decode('utf8'));self.assertEqual(1,sum(t.get('event')==package.EVENT for n in package.walk(data) for t in n.get('transitions',[])))

if __name__=='__main__':unittest.main()
