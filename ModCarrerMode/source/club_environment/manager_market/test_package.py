from pathlib import Path
import unittest,xml.etree.ElementTree as ET,importlib.util
import test_screen
# Other mod suites also contain package.py. Resolve this integration test's
# own module explicitly so discovery order cannot select another mod.
_spec=importlib.util.spec_from_file_location('manager_market_package_test',Path(__file__).with_name('package.py'))
package=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(package)

class PackageTest(unittest.TestCase):
 def test_card_and_navigation_preserve_existing_entries_and_are_idempotent(self):
  game=Path(__file__).resolve().parents[4];raw=(game/package.XML).read_bytes();new=package.layout(raw);before=ET.fromstring(raw);after=ET.fromstring(new)
  old_events=[n.get('DESTINATION') for n in before.iter() if n.get('DESTINATION')];new_events=[n.get('DESTINATION') for n in after.iter() if n.get('DESTINATION')]
  for e in old_events:self.assertEqual(old_events.count(e),new_events.count(e))
  self.assertEqual(1,new_events.count(package.EVENT));self.assertEqual(new,package.layout(new))
  nav=package.navigation((game/package.NAV).read_bytes());self.assertEqual(nav,package.navigation(nav));data=package.read_nav(nav.decode('utf8'));self.assertEqual(1,sum(t.get('event')==package.EVENT for n in package.walk(data) for t in n.get('transitions',[])))

if __name__=='__main__':unittest.main()
