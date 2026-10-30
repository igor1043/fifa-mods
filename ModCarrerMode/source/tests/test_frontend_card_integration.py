from collections import Counter
from pathlib import Path
import sys,unittest
import xml.etree.ElementTree as E

SOURCE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SOURCE/'tools'))
import integrate_frontend_cards as mod

class FrontendCardIntegration(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  fixtures=Path(__file__).parent/'fixtures'
  cls.career=(SOURCE.parents[1]/mod.CAREER).read_bytes()
  cls.donor=(fixtures/'robson_transfer_cards.xml').read_bytes()
  cls.front=(fixtures/'frontend_personalize_before.xml').read_bytes()
 def test_visual_merge_preserves_all_career_routes_and_calendar_ids(self):
  old=E.fromstring(self.career);new=E.fromstring(mod.merge_career(self.career,self.donor))
  self.assertEqual(mod.events(old),mod.events(new))
  for panel in ('panel_0','panel_1','panel_3','panel_4','panel_5','panel_6','panel_7'):
   self.assertEqual(E.tostring(old.find(panel)),E.tostring(new.find(panel)))
  ids=lambda root:Counter((n.tag,n.get('tileid'),n.get('ID')) for n in root.iter() if n.get('tileid') or n.get('ID'))
  self.assertEqual(ids(old),ids(new))
  for route in ('Server16EnterWorldClubRanking','Server16EnterWorldNationRanking'):
   self.assertEqual(mod.events(new)[route],1)
 def test_compact_titles_are_literal_single_line_and_text_stays_inside_card(self):
  root=E.fromstring(mod.merge_career(self.career,self.donor))
  for name in ('SHOPPING_LIST','SERVER16_MANAGER_MARKET'):
   tile=mod.card(root,name)
   for page,owner in mod.slides(tile):
    title=owner.find("data[@ID='TITLE']")
    self.assertEqual(title.get('TRANSLATE'),'FALSE');self.assertLessEqual(len(title.get('PARAM')),14)
    self.assertLessEqual(int(title.get('Y'))+int(title.get('HEIGHT')),72)
    for text in owner.findall('data'):
     if text.get('TYPE')=='text':
      self.assertLessEqual(int(text.get('Y'))+int(text.get('HEIGHT')),204)
      self.assertLessEqual(int(text.get('X'))+int(text.get('WIDTH')),278)
  actions=dict((p.get('DESTINATION'),p.get('BG_ICON')) for p,_ in mod.slides(mod.card(root,'SHOPPING_LIST')))
  self.assertEqual(actions['EnterSellPlayers'],'Contract_Sml')
  self.assertEqual(actions['EnterNegHistory'],'Contract_Sml')
 def test_transform_is_byte_idempotent(self):
  career=mod.merge_career(self.career,self.donor)
  self.assertEqual(mod.merge_career(career,self.donor),career)
  frontend=mod.personalize(self.front)
  self.assertEqual(mod.personalize(frontend),frontend)
 def test_personalize_keeps_functional_routes_once_and_removes_offline_entries(self):
  old=E.fromstring(self.front);new=E.fromstring(mod.personalize(self.front))
  expected=mod.events(old);expected.subtract({'powCatalogue':1})
  self.assertEqual(+expected,mod.events(new))
  tiles={t.find('tileid').get('tileid'):t for t in new.find('panel_4').findall('tile')}
  self.assertNotIn('304',tiles);self.assertNotIn('48',tiles)
  for route in ('CreatePlayerAdvance','EditPlayerAdvance','DeletePlayerAdvance','EditTeamManagement'):
   self.assertEqual(mod.events(new)[route],1)
  for ident in ('320','322','323'):
   self.assertEqual(tiles[ident].find('number_of_subtiles').get('LENGTH'),'0')
   self.assertEqual(tiles[ident].find('settings').get('FILE_PATH'),'TILE')
  self.assertEqual(int(new.find('panel_4/entries').get('numberoftiles')),len(tiles))
 def test_visible_pc_grid_has_no_overlapping_cards(self):
  root=E.fromstring(mod.personalize(self.front));tiles={t.find('tileid').get('tileid'):t for t in root.find('panel_4').findall('tile')}
  expected={'272':(109,278),'336':(537,278),'368':(965,278),'1216':(1393,278),
            '320':(109,598),'322':(537,598),'323':(965,598),'352':(1393,598)}
  for ident,(x,y) in expected.items():
   node=tiles[ident].find('settings')
   self.assertEqual(tuple(map(int,(node.get('X'),node.get('Y')))),(x,y))
   self.assertEqual(tuple(map(int,(node.get('WIDTH'),node.get('HEIGHT')))),(418,310))
 def test_donor_with_changed_route_is_rejected(self):
  bad=self.donor.replace(b'EnterPlayerSearch',b'WrongDestination')
  with self.assertRaises(ValueError):mod.merge_career(self.career,bad)

if __name__=='__main__':unittest.main(verbosity=2)
