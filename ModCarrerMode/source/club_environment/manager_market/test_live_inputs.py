import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import test_screen
from inputs import Inputs


class LiveInputs(unittest.TestCase):
 def test_all_primary_leagues_use_live_counters_instead_of_old_disk_rows(self):
  with tempfile.TemporaryDirectory() as tmp:
   game=Path(tmp);save=game/'DATA';save.write_bytes(b'unchanged')
   calendar=[dict(currdate=20260101,startdate=20260101)]
   stored=[dict(teamid=club,leagueid=league,secondarytable=0,nummatchesplayed=0,points=0,homewins=0,homedraws=0,homelosses=0,awaywins=0,awaydraws=0,awaylosses=0,homegf=0,homega=0,awaygf=0,awayga=0) for club,league in ((10,7),(20,7),(100,987),(200,987))]
   tables=dict(career_calendar=calendar,career_users=[dict(userid=1,clubteamid=10,firstname='A',surname='B')],leagueteamlinks=stored,leagues=[dict(leagueid=i,leaguename=str(i),countryid=1,level=1) for i in (7,987)],teams=[dict(teamid=r['teamid'],teamname=str(r['teamid']),domesticprestige=10,transferbudget=1000000) for r in stored],career_managerinfo=[])
   class DB:
    def __init__(self):self.tables={k:dict(fields={f:None for f in rows[0]}) for k,rows in tables.items() if rows}
    def rows(self,name,fields):return [{f:r[f] for f in fields if f in r} for r in tables.get(name,[])]
   db=DB();obj=object.__new__(Inputs);obj.game=game;obj.cache=SimpleNamespace(load=lambda *_:(b'unchanged',[db],db))
   snapshot=dict(date=20261201,nodes=[],fixtures=[],standings=[],source='save_bound_native')
   live=[dict(r,nummatchesplayed=8,points=24,homewins=4,awaywins=4) for r in stored]
   observed=dict(save=dict(path=str(save),pid=1,process_created_100ns=2),date=20261201,profile=dict(club_id=10,context_epoch=3))
   with patch('competition_schedule.read_schedule',return_value=[]),patch('competition_formats.read_formats',return_value={}),patch('saved_competitions.read',return_value=dict(snapshot,date=20260101)),patch('derived_campaigns.augment',return_value=snapshot),patch('catalog_meta.populate'),patch('catalog_meta.Labels',return_value=SimpleNamespace(leagues={},countries={})):
    c=obj.read(observed,object(),live_leagues=dict(rows=live))
    background=obj.read(observed,object(),live_leagues=dict(rows=live,date=20261201),league_only=True)
   self.assertEqual({7,987},{r['asset'] for r in c['performance']});self.assertTrue(c['coverage']['live_database'])
   self.assertTrue(all(r['played']==8 and r['date']==20261201 and r['source']=='live_league' for r in c['performance']))
   self.assertEqual(b'unchanged',save.read_bytes())
   self.assertEqual({7,987},{r['asset'] for r in background['performance']})
   self.assertTrue(background['coverage']['league_only']);self.assertFalse(background['coverage']['native_bound'])
   self.assertEqual([],background['fixtures']);self.assertTrue(all(r['date']==20261201 for r in background['performance']))

if __name__=='__main__':unittest.main()
