"""Calendar progression must replace the opponent, venue and result list."""
import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import projection


class Row:
    def __init__(self,**fields):self.fields=fields
    def value(self,key):return self.fields[key]


class PreviewProgressionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        db=self.root/'data/db';db.mkdir(parents=True);(db/'fifa_ng_db.db').write_bytes(b'test');(db/'fifa_ng_db-meta.xml').write_text('<database/>')
        (self.root/'save').mkdir();self.save=self.root/'save/DATA';self.save.write_bytes(b'original save');self.today=20260126
        self.snapshot=dict(schema=3,pid=123,club=1629,date=self.today,savePath=str(self.save),saveSize=13,processCreated100ns=100,
            saveWriteTime100ns=self.save.stat().st_mtime_ns//100+116444736000000000,
            fixtures=[[720,0,0,20260126,2100,569,1629,-1,-1,0,0],[721,0,0,20260130,1600,1629,694,-1,-1,0,0]],nodes=[])
        self.path=self.root/'snapshot.json';self.tables={'teams':[Row(teamid=i,teamname=n) for i,n in ((1629,'Flamengo'),(569,'Vasco'),(694,'Chapecoense'))],
            'players':[],'default_teamsheets':[],'teamsheets':[],'teamplayerlinks':[],
            'teamstadiumlinks':[Row(teamid=1629,stadiumid=10),Row(teamid=569,stadiumid=20)],
            'stadiums':[Row(stadiumid=10,name='Maracanã',capacity=78000),Row(stadiumid=20,name='São Januário',capacity=21000)]}
        names={}
        for team in (1629,569,694):
            sheet=dict(teamid=team,isfavourite=1)
            for i in range(11):
                pid=team*100+i;names[str(pid)]='Jogador '+str(pid)
                self.tables['players'].append(Row(playerid=pid,commonnameid=pid,playerjerseynameid=pid,lastnameid=pid,overallrating=70))
                self.tables['teamplayerlinks'].append(Row(teamid=team,playerid=pid))
                sheet.update({f'playerid{i}':pid,f'position{i}':0 if i==0 else 14,f'offset{i}x':.5,f'offset{i}y':i/11})
            self.tables['teamsheets'].append(Row(**sheet))
        stat=(db/'fifa_ng_db.db').stat();(self.root/'base_name_cache.json').write_text(json.dumps(dict(stamp=[stat.st_size,stat.st_mtime_ns],queried=list(map(int,names)),names=names)))
    def run_projection(self):
        self.path.write_text(json.dumps(self.snapshot))
        class Kernel:
            def OpenProcess(self,*args):return 1
        memory=SimpleNamespace(kernel32=Kernel(),_get_base_address=lambda _:0x140000000,close=lambda:None,
            read_int64=lambda _:0x1000,read_process_memory=lambda at,n:(bytes(7)+b'\xc7\x01'+(1).to_bytes(4,'little')+bytes(11)) if n==24 else __import__('struct').pack('<3i',self.today%100,self.today//100%100,self.today//10000))
        active=dict(path=str(self.save),process_created_100ns=100,mtime_ns=self.save.stat().st_mtime_ns)
        with patch.object(projection,'GAME',self.root),patch.object(projection,'__file__',str(self.root/'projection.py')),patch.object(projection,'tables',side_effect=[self.tables,{}]),patch.object(projection,'blocks',return_value=[]),patch('psutil.Process',return_value=SimpleNamespace(pid=123,name=lambda:'fifa16.exe',exe=lambda:'fifa16.exe')),patch('server16_py.memory_access.Memory',return_value=memory),patch('server16_py.career_context.competition_session',return_value=dict(club_id=1629,registry_address=0x1000,context_address=0x2000)),patch('server16_py.career_active_save.read_active_save',return_value=active):
            return projection.project(self.path)
    def test_calendar_advance_replaces_vasco_with_chapecoense_and_keeps_completed_result(self):
        first=self.run_projection();self.assertEqual(first['opponent']['name'],'Vasco');self.assertEqual(first['details']['stadium'],'São Januário')
        self.today=20260129;self.snapshot['date']=self.today;self.snapshot['fixtures'][0][7:10]=[0,2,1]
        after=self.run_projection();self.assertEqual(after['opponent']['name'],'Chapecoense');self.assertEqual(after['details']['stadium'],'Maracanã');self.assertEqual(after['details']['date'],'30/01/2026')
        self.assertEqual(after['user']['recent'][0]['opponent'],'Vasco');self.assertEqual(after['user']['recent'][0]['score'],'2 – 0');self.assertEqual(len(after['opponent']['players']),11)
    def test_old_snapshot_cannot_mix_with_a_new_calendar_day(self):
        self.today=20260129
        with self.assertRaisesRegex(ValueError,'mesma data'):self.run_projection()
    def test_departed_opponent_starter_does_not_block_venue_or_history(self):
        self.tables['teamsheets'][1].fields['playerid0']=208670
        after=self.run_projection()
        self.assertEqual(after['opponent']['source'],'probable-roster')
        self.assertEqual(len({p['id'] for p in after['opponent']['players']}),11)
        self.assertNotIn(208670,{p['id'] for p in after['opponent']['players']})
        self.assertEqual(after['details']['stadium'],'São Januário')
    def test_missing_opponent_players_do_not_remove_other_cards(self):
        self.tables['teamplayerlinks']=[r for r in self.tables['teamplayerlinks'] if r.fields['teamid']!=569]
        after=self.run_projection()
        self.assertEqual(after['opponent']['players'],[]);self.assertEqual(after['details']['stadium'],'São Januário')
    def test_calendar_advancing_during_asset_build_never_publishes_obsolete_package(self):
        import prepare
        payload=self.run_projection();candidate=self.root/'candidate.big';candidate.write_bytes(b'new package')
        target=self.root/'published.big';target.write_bytes(b'previous package')
        runtime=self.root/'ModCarrerMode/runtime';runtime.mkdir(parents=True)
        self.snapshot['fixtures'][0][7:10]=[0,2,1]
        (runtime/'career_fce_snapshot.json').write_text(json.dumps(self.snapshot))
        with patch.object(prepare,'GAME',self.root),patch.object(prepare,'HERE',self.root),patch.object(prepare,'DEST',target),patch.object(prepare,'project',return_value=payload),patch.object(prepare,'build',return_value=candidate),patch.object(prepare,'current_state',return_value=('preview',self.today,dict(club_id=1629,context_address=0x2000))):
            with self.assertRaisesRegex(RuntimeError,'avançou durante'):prepare.once()
        self.assertEqual(target.read_bytes(),b'previous package')

if __name__=='__main__':unittest.main()
