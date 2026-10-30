from pathlib import Path
from unittest.mock import patch
import copy,json,unittest
from world_catalog import build,tsv

class Fixture:
 def __init__(self):
  self.data=dict(teams=[dict(teamid=i,teamname='Team '+str(i),latitude=0,longitude=0,overallrating=70) for i in (1,2,3,4)],nations=[dict(nationid=54,nationname='Brasil',isocountrycode='BR',confederation=4)],leagues=[dict(leagueid=9876,leaguename='Nova liga',countryid=54,level=1)],teamnationlinks=[dict(teamid=3,nationid=54)],teamplayerlinks=[dict(teamid=1),dict(teamid=2)],leagueteamlinks=[dict(teamid=i,leagueid=9876,secondarytable=0) for i in (1,2)])
  self.tables={name:dict(rows=len(rows)) for name,rows in self.data.items()}
 def rows(self,name,fields):return [{f:r.get(f) for f in fields} for r in self.data[name]]

class Catalog(unittest.TestCase):
 def test_national_divisions_precede_federations_for_existing_and_added_countries(self):
  from tempfile import TemporaryDirectory
  fixture=Fixture()
  fixture.data['nations'].append(dict(nationid=77,nationname='País novo',isocountrycode='XX',confederation=2))
  fixture.data['teamnationlinks']=[]
  leagues=[(601,54,1,'Brasileirão Betano'),(29,54,2,'Brasileirão Série B'),(903,54,3,'Brasileirão Série C'),(17,54,4,'Brasileirão Série D'),(2,54,1,'Federação Paulista [OFF]'),(3,54,2,'Federação Acreana [OFF]'),(710,77,1,'Primeira divisão'),(708,77,2,'Segunda divisão'),(709,77,3,'Terceira divisão'),(6,77,1,'Regional League')]
  fixture.data['leagues']=[dict(leagueid=i,countryid=country,level=level,leaguename=name) for i,country,level,name in leagues]
  fixture.data['teams']=[dict(teamid=100+i,teamname='Time '+str(i)) for i in range(len(leagues))]
  fixture.data['leagueteamlinks']=[dict(teamid=100+i,leagueid=league[0],secondarytable=0) for i,league in enumerate(leagues)]
  fixture.tables={name:dict(rows=len(rows)) for name,rows in fixture.data.items()}
  with TemporaryDirectory() as temp:
   game=Path(temp);folder=game/'ModCarrerMode/data/club_browser';folder.mkdir(parents=True);(folder/'catalog.tsv').write_text('');(folder/'world_geography.json').write_text('{}')
   rows,audit=build(game,fixture)
   brazil=[r for r in rows if r['nation']==54];other=[r for r in rows if r['nation']==77]
   self.assertEqual([r['league'] for r in brazil],[601,29,903,17,3,2])
   self.assertEqual([r['leagueName'] for r in brazil[:4]],['Brasileirão Série '+s for s in 'ABCD'])
   self.assertEqual([r['league'] for r in other],[710,708,709,6])
   self.assertEqual([r['leagueOrder'] for r in brazil],list(range(1,7)))
   self.assertEqual(audit['missingTeams'],[]);self.assertEqual(audit['missingLeagues'],[])
   self.assertEqual(len(rows),len(leagues))

 def test_added_league_and_selection_come_from_database_and_zero_survives_tsv(self):
  from tempfile import TemporaryDirectory
  with TemporaryDirectory() as t:
   game=Path(t);path=game/'ModCarrerMode/data/club_browser';path.mkdir(parents=True);(path/'world_geography.json').write_text(json.dumps(dict(BR=dict(world=0,lat=0,lon=0))));(path/'catalog.tsv').write_text('')
   rows,audit=build(game,Fixture());self.assertEqual(audit['clubs'],2);self.assertEqual(audit['nations'],1);self.assertEqual(audit['missingLeagues'],[]);self.assertEqual(audit['missingTeams'],[]);self.assertEqual(audit['excluded'][0]['id'],4)
   fields=tsv(rows,'nations').decode().strip().split('\t');self.assertEqual(len(fields),18);self.assertEqual(fields[3],'0');self.assertEqual(fields[12],'0')
   self.assertEqual({r['league'] for r in rows if r['kind']=='clubs'},{9876})

if __name__=='__main__':unittest.main(verbosity=2)
