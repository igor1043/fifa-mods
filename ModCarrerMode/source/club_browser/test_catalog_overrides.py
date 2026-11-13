from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json,unittest
from catalog_overrides import load
from test_world_catalog import Fixture
from world_catalog import build,ensure,tsv

class Overrides(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.game=Path(self.temp.name);self.folder=self.game/'ModCarrerMode/data/club_browser';self.folder.mkdir(parents=True)
        (self.folder/'catalog.tsv').write_text('',encoding='utf8')
        (self.folder/'world_geography.json').write_text(json.dumps({'BR':{'world':30,'lat':-15.8,'lon':-47.9},'BE':{'world':130,'lat':50.85,'lon':4.35},'MA':{'world':163,'lat':31,'lon':-7},'AU':{'world':138,'lat':-25,'lon':134},'NZ':{'world':137,'lat':-41,'lon':175},'GB':{'world':144,'lat':52,'lon':-2}}),encoding='utf8')
        self.fixture=Fixture();self.fixture.data['teamnationlinks']=[]
    def ini(self,value):(self.folder/'catalog_overrides.ini').write_text(value,encoding='utf-8-sig')
    def table(self,name,rows):
        self.fixture.data[name]=rows;self.fixture.tables[name]={'rows':len(rows)}
    def nation(self,ident,name,iso):self.fixture.data['nations'].append(dict(nationid=ident,nationname=name,isocountrycode=iso,confederation=2))
    def test_stale_row_links_do_not_split_belgian_or_moroccan_domestic_leagues(self):
        for n,name,iso in [(7,'Belgium','BE'),(8,'Bosnia','BA'),(129,'Morocco','MA'),(210,'Free agents','')]:self.nation(n,name,iso)
        self.table('leagues',[dict(leagueid=200,countryid=7,level=2,leaguename='Belgium'),dict(leagueid=84,countryid=129,level=1,leaguename='Botola')])
        self.table('leagueteamlinks',[dict(teamid=1,leagueid=200,secondarytable=0),dict(teamid=2,leagueid=84,secondarytable=0)])
        self.table('rowteamnationlinks',[dict(teamid=1,nationid=8),dict(teamid=2,nationid=210)])
        rows,_=build(self.game,self.fixture);self.assertEqual([(r['id'],r['nation']) for r in rows],[(1,7),(2,129)])
    def test_club_geography_and_cross_border_division_are_independent(self):
        self.nation(195,'Australia','AU');self.nation(198,'New Zealand','NZ')
        self.table('leagues',[dict(leagueid=379,countryid=195,level=1,leaguename='A-League')])
        self.table('leagueteamlinks',[dict(teamid=i,leagueid=379,secondarytable=0) for i in [1,2]])
        self.ini('[club:1]\ncountry_id=198\ncity=Auckland\nlatitude=-36.85\nlongitude=174.76\n[country:198]\nname=Nova Zelândia\n')
        rows,_=build(self.game,self.fixture);club=next(r for r in rows if r['id']==1)
        self.assertEqual((club['nation'],club['countryName'],club['league'],club['lat'],club['lon']),(198,'Nova Zelândia',379,-36.85,174.76))
        self.assertEqual(club['leagueScope'],'national');self.assertEqual(club['divisionLabel'],'1ª divisão · Australia')
        self.assertEqual(len(tsv(rows,'clubs').decode().splitlines()[0].split('\t')),18)
        self.assertEqual(len(tsv(rows,'clubs',metadata=True).decode().splitlines()[0].split('\t')),19)
    def test_regional_federations_use_brazil_and_state_location_without_false_tier(self):
        self.nation(223,'Brasil Nordeste 2','BR')
        self.table('leagues',[dict(leagueid=2,countryid=223,level=4,leaguename='Federação Piauiense')])
        self.table('leagueteamlinks',[dict(teamid=1,leagueid=2,secondarytable=0)])
        self.fixture.data['teams'][0].update(latitude=51,longitude=0)
        self.ini('[league:2]\ncountry_id=54\nscope=regional\nstate=Piauí (PI)\ndivision_label=Federação estadual · PI\nlatitude=-5.0892\nlongitude=-42.8019\n')
        rows,_=build(self.game,self.fixture);club=next(r for r in rows if r['id']==1)
        self.assertEqual((club['nation'],club['leagueScope'],club['divisionLabel']),(54,'regional','Federação estadual · PI'))
        self.assertEqual((club['lat'],club['lon']),(-5.0892,-42.8019));self.assertIn('aproximada',club['city'])
    def test_country_labels_are_canonical_for_old_and_new_clubs(self):
        (self.folder/'catalog.tsv').write_text('54\tBrasil\t54\t30\t1\t9876\tLiga\t1\t0\t1\tTeam 1\tCidade\t-20\t-45\t70\t70\t70\t70\n',encoding='utf8')
        rows,_=build(self.game,self.fixture);self.assertEqual({r['countryName'] for r in rows},{'Brasil'})
    def test_invalid_section_is_reported_without_poisoning_other_clubs(self):
        self.ini('[club:1]\nlatitude=nan\nlongitude=10\n[club:2]\ncity=Brasília\nlatitude=-15.8\nlongitude=-47.9\n')
        values,warnings=load(self.game);self.assertNotIn(1,values['club']);self.assertEqual(values['club'][2]['city'],'Brasília');self.assertEqual(len(warnings),1)
        rows,audit=build(self.game,self.fixture);self.assertEqual(next(r for r in rows if r['id']==2)['city'],'Brasília');self.assertTrue(audit['overrideWarnings'])
    def test_unknown_ids_do_not_create_teams_or_leagues(self):
        self.ini('[club:99999]\ncity=Fantasma\n[club:1]\ncountry_id=9999\n')
        rows,audit=build(self.game,self.fixture);self.assertNotIn(99999,{r['id'] for r in rows});self.assertEqual(next(r for r in rows if r['id']==1)['nation'],54);self.assertEqual(len(audit['overrideWarnings']),2)
    def test_country_coordinates_fix_selection_without_moving_clubs(self):
        self.fixture.data['teamnationlinks']=[dict(teamid=3,nationid=54)]
        self.ini('[country:54]\nname=Brasil\nworld_id=30\nlatitude=-15.8\nlongitude=-47.9\n')
        rows,_=build(self.game,self.fixture);nation=next(r for r in rows if r['kind']=='nations');self.assertEqual((nation['lat'],nation['lon'],nation['city']),(-15.8,-47.9,'Brasil'))
    def test_ini_changes_invalidate_generated_catalog_and_unchanged_inputs_reuse_it(self):
        db=self.game/'data/db';db.mkdir(parents=True)
        for name in ['fifa_ng_db.db','fifa_ng_db-meta.xml']:(db/name).write_bytes(b'fixture')
        with patch('world_catalog.FifaDatabase',return_value=self.fixture) as factory:
            folder=ensure(self.game);before=(folder/'catalog.tsv').read_bytes();ensure(self.game);self.assertEqual(factory.call_count,1)
            self.ini('[club:1]\ncity=Brasília\nlatitude=-15.8\nlongitude=-47.9\n')
            ensure(self.game);self.assertEqual(factory.call_count,2);self.assertNotEqual(before,(folder/'catalog.tsv').read_bytes())
        self.assertEqual(len((folder/'catalog.tsv').read_text().splitlines()[0].split('\t')),19)

if __name__=='__main__':unittest.main(verbosity=2)
