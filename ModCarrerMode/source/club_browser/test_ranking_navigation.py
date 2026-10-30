from pathlib import Path
import os,tempfile,unittest,xml.etree.ElementTree as ET
from collections import Counter
import build_ranking_apt as screen
import ranking_package as package
from native_review_vm import open_native

class RankingNavigation(unittest.TestCase):
 def test_two_pages_have_original_help_and_separate_back(self):
  for kind in ('clubs','nations'):
   with self.subTest(kind=kind),tempfile.TemporaryDirectory() as t:
    path=Path(t)/'ranking.big';screen.build(Path(os.environ['SERVER16_GAME_ROOT']),path,kind);vm,view,apt,calls=open_native(path,screen.full(kind))
    if not view.get('screenReady'):vm.invoke(view.get('Ready'),view)
    self.assertTrue(view.get('screenReady'));help=vm.invoke(view.get('getHelpContext'),view)
    self.assertEqual([v[0] for v in help],['ADVANCE','BACK','LAS_UD','L1R1','L2R2','OPTION_LEFT','OPTION_TOP','RAS_UD'])
    for code,command in ((2,'rank_filter'),(10,'rank_mine'),(17,'rank_top')):
     vm.invoke(view.get('LocalEventHandler'),view,(code,True));self.assertTrue(any(n=='SendSystemEvent' and list(args)==['Calendar','Server16ClubBrowser',command] for n,args in calls))
    vm.invoke(view.get('LocalEventHandler'),view,(1,True));self.assertTrue(any(n=='SendEvent' and list(args)==['Calendar','Back',''] for n,args in calls))
    vm.invoke(view.get('OnExitScreen'),view);self.assertTrue(view.get('exiting'))
 def test_layout_keeps_every_destination_and_calendar_competition_ids(self):
  game=Path(os.environ['SERVER16_GAME_ROOT']);raw=(game/package.XML).read_bytes();out=package.layout(raw);self.assertEqual(package.layout(out),out)
  before=ET.fromstring(raw);after=ET.fromstring(out)
  events=lambda tree:Counter(n.get('DESTINATION') for n in tree.iter() if n.get('DESTINATION'))
  expected=events(before)
  for entry in package.ENTRIES:expected['Server16Enter'+entry[3]]=1
  self.assertEqual(events(after),expected)
  calendar=lambda r:next(t for t in r.find('panel_4').findall('tile') if t.find('tileid').get('NAME')=='CALENDAR')
  self.assertEqual(ET.tostring(calendar(before)),ET.tostring(calendar(after)))
  for name in ('panel_0','panel_1','panel_2','panel_3','panel_5','panel_7'):self.assertEqual(ET.tostring(before.find(name)),ET.tostring(after.find(name)))
 def test_navigation_is_idempotent_and_only_adds_two_routes(self):
  game=Path(os.environ['SERVER16_GAME_ROOT']);raw=(game/package.NAV).read_bytes();out=package.navigation(raw);self.assertEqual(package.navigation(out),out)
  old,new=package.read_nav(raw),package.read_nav(out)
  for tree in (old,new):
   for node in package.walk(tree):
    if 'transitions' in node:node['transitions']=[t for t in node['transitions'] if t.get('event') not in ('Server16EnterWorldClubRanking','Server16EnterWorldNationRanking')]
    if 'states' in node:node['states']=[s for s in node['states'] if s.get('name') not in ('Server16WorldClubRanking','Server16WorldNationRanking')]
  self.assertEqual(old,new)

if __name__=='__main__':unittest.main(verbosity=2)
