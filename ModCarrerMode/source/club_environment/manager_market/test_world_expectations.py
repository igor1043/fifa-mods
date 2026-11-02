from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from test_engine import catalog,context
from engine import Market,DEFAULTS,dismissal_probability
from model import project
from catalog_meta import key

class WorldExpectationsTest(unittest.TestCase):
 def test_low_performance_at_big_club_has_real_pressure_in_any_country(self):
  with TemporaryDirectory() as folder:
   root=Path(folder);catalog(root/'cat.sqlite3');m=Market(root/'market.sqlite3',root/'cat.sqlite3')
   try:
    m.open_save('A','DATA',context());club=m.one('clubs','club_id',1)
    table=[dict(club=1,rank=2,played=20,points=18),dict(club=2,rank=1,played=20,points=35),dict(club=3,rank=3,played=20,points=12)]
    values=[]
    for country in ('Espanha','Uruguai','Japão','Alemanha','Nova liga adicionada'):
     pressure,_,_,reason=m.table_pressure(dict(club,country=country),table,20260701,DEFAULTS)
     self.assertGreaterEqual(pressure,60);self.assertLess(100-pressure,40);self.assertGreater(dismissal_probability(dict(club,country=country),pressure,DEFAULTS),0)
     self.assertIn('30%',reason);values.append(pressure)
    self.assertEqual(1,len(set(values)))
    weak=m.one('clubs','club_id',3);weak_table=[dict(club=2,rank=1,played=20,points=35),dict(club=1,rank=2,played=20,points=30),dict(club=3,rank=3,played=20,points=18)]
    self.assertLess(m.table_pressure(weak,weak_table,20260701,DEFAULTS)[0],30)
   finally:m.close()
 def test_country_sort_preserves_all_divisions_without_country_specific_ids(self):
  with TemporaryDirectory() as folder:
   root=Path(folder);catalog(root/'cat.sqlite3');m=Market(root/'market.sqlite3',root/'cat.sqlite3')
   try:
    m.open_save('A','DATA',context())
    additions=[]
    for i,country in enumerate(('África do Sul','Áustria','Bélgica','Brasil','Espanha','Uruguai')):
     for division in (1,2,3):
      ident=1000+i*10+division
      additions.append(dict(club_id=ident,name='Clube '+str(ident),league_id=ident,league_name=country+' '+str(division),country=country,region='',reputation=5,budget=10000000,level=division))
    with m.db:m.sync_clubs(dict(context(),clubs=additions))
    data=project(m);names=[r['name'] for r in data['countries']]
    self.assertEqual(sorted(names,key=key),names)
    for country in ('África do Sul','Áustria','Bélgica','Brasil','Espanha','Uruguai'):
     expected={c['league_id'] for c in additions if c['country']==country};actual={l['id'] for l in data['leagues'] if l['country']==country};self.assertTrue(expected<=actual)
   finally:m.close()

if __name__=='__main__':unittest.main()
