import tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
import build_career_options as options
from native_review_vm import open_native


class CareerOptionsNavigationTest(unittest.TestCase):
 def test_office_entries_preserve_original_actions_and_are_idempotent(self):
  game=Path(__file__).resolve().parents[3];raw=(game/options.XML).read_bytes();updated=options.layout(raw);self.assertEqual(updated,options.layout(updated))
  before=ET.fromstring(raw);after=ET.fromstring(updated)
  old=[n.get('DESTINATION') for n in before.iter() if n.get('DESTINATION')]
  new=[n.get('DESTINATION') for n in after.iter() if n.get('DESTINATION')]
  for item in old:self.assertIn(item,new)
  for name,event,tile,*_ in options.PAGES:
   matches=[t for t in after.find('panel_3').findall('tile') if any(n.get('DESTINATION')==event for n in t)]
   self.assertEqual(1,len(matches));self.assertEqual(tile,matches[0].find('tileid').get('NAME'))
 def test_isolated_flows_are_added_once(self):
  game=Path(__file__).resolve().parents[3];raw=(game/options.NAV).read_bytes();updated=options.navigation(raw);self.assertEqual(updated,options.navigation(updated))
  for name,event,*_ in options.PAGES:self.assertIn(event.encode(),updated)
 def test_native_views_finish_loading_and_back_uses_original_calendar(self):
  game=Path(__file__).resolve().parents[3]
  with tempfile.TemporaryDirectory() as tmp:
   for name,*_ in options.PAGES:
    package=Path(tmp)/(name+'.big');options.build(game,package,name)
    vm,view,_,calls=open_native(package,full='game.screens.career.server16.'+name)
    self.assertTrue(view.get('screenReady'));self.assertEqual([],vm.errors)
    vm.invoke(view.get('LocalEventHandler'),view,(1,None))
    self.assertTrue(any(kind=='SendEvent' and 'Back' in values for kind,values in calls))
    vm.invoke(view.get('OnExitScreen'),view);self.assertTrue(view.get('exiting'));self.assertEqual([],vm.errors)


 def test_escape_listener_routes_back_and_is_removed_on_exit(self):
  from apt_vm import Object,Native
  game=Path(__file__).resolve().parents[3]
  with tempfile.TemporaryDirectory() as tmp:
   for name,*_ in options.PAGES:
    package=Path(tmp)/(name+'.big');options.build(game,package,name)
    def setup(vm,calls):vm.global_.set('Key',Object({k:Native(k) for k in ('addListener','removeListener','getCode')}))
    vm,view,_,calls=open_native(package,full='game.screens.career.server16.'+name,setup=setup,callbacks={'getCode':lambda owner,args:27})
    self.assertTrue(any(k=='addListener' for k,v in calls))
    calls.clear();vm.invoke(view.get('onKeyDown'),view)
    self.assertTrue(any(k=='SendEvent' and list(v)==['Calendar','Back',''] for k,v in calls))
    vm.invoke(view.get('OnExitScreen'),view)
    self.assertTrue(any(k=='removeListener' for k,v in calls));self.assertEqual([],vm.errors)

if __name__=='__main__':unittest.main()
