import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from . import cabinet,worker


class CabinetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.game=Path(self.temp.name)
        self.folder=self.game/'ModCarrerMode/runtime/trophy_room';self.folder.mkdir(parents=True)
        self.req=dict(pid=12,club=1043,epoch=3,requested=True,presentation='list',shelf_page=0,collection='coach')
        self.snap=dict(pid=12,club=1043,fceContextEpoch=3,date=20261201,savePath=str(self.game/'career/DATA'))
        self.identity=dict(club=1043,name='Flamengo',colors=[(100,0,0),(0,0,0)])
        thumbnail=patch.object(cabinet.assets,'trophy_thumbnail',return_value='');thumbnail.start();self.addCleanup(thumbnail.stop)
        self.publish_request()
        (self.game/'ModCarrerMode/runtime/career_fce_snapshot.json').write_text(json.dumps(self.snap),encoding='utf8')
    def tearDown(self):self.temp.cleanup()
    def publish_request(self):
        (self.folder/'request.json').write_text(json.dumps(self.req),encoding='utf8')
    def rows(self,n):
        return [dict(competition=7,root=i,date=20260101+i,year=2026,name='Competição '+str(i),club=1043 if i%2 else 2,origin='career') for i in range(n)]
    def test_list_does_not_generate_or_load_3d_assets(self):
        with patch.object(worker.assets,'club_identity',return_value=(self.identity,{7:7})),patch.object(worker.data,'title_rows',return_value=(self.rows(40),'b')),patch.object(worker.assets,'native_cup',side_effect=AssertionError('3D loaded')),patch.object(worker.assets,'rx_texture',side_effect=AssertionError('3D texture generated')):
            worker.generate(self.game,12,self.req)
        self.assertTrue((self.folder/'cabinet.tsv').is_file());self.assertFalse((self.folder/'components.txt').exists())
        self.assertFalse((self.game/worker.assets.PREFIX).exists())
    def test_all_pages_keep_winning_club_year_and_no_titles_are_lost(self):
        all_rows=self.rows(41);seen=[]
        with patch.object(cabinet.assets,'club_identity',side_effect=lambda game,club:(dict(name='Clube '+str(club)),{})):
            for page in range(3):
                self.req['shelf_page']=page;self.publish_request();cabinet.publish(self.game,12,self.req,self.snap,self.identity,{7:1003},all_rows,'b')
                result=json.loads((self.folder/'cabinet.json').read_bytes());seen+=result['rows']
                self.assertEqual(result['pages'],3);self.assertLessEqual(len(result['rows']),18)
                self.assertTrue(all(r['trophy']==1003 and r['club_name']=='Clube '+str(r['club']) for r in result['rows']))
        self.assertEqual(len(seen),41);self.assertEqual(len({r['root'] for r in seen}),41)
    def test_thumbnail_uses_competition_mapping_even_when_the_graph_id_collides(self):
        row=dict(self.rows(1)[0],competition=1003,root=1460)
        with patch.object(cabinet.assets,'club_identity',return_value=(self.identity,{})):
            self.assertEqual(1003,cabinet.records(self.game,self.req,{1460:1007},[row])[0]['trophy'])
            self.assertEqual(77,cabinet.records(self.game,self.req,{1460:1007,1003:77},[row])[0]['trophy'])
    def test_changed_save_or_collection_cannot_publish_stale_titles(self):
        self.req['collection']='club';self.publish_request();stale=dict(self.req,collection='coach')
        with patch.object(cabinet.assets,'club_identity',return_value=(self.identity,{})),self.assertRaises(InterruptedError):
            cabinet.publish(self.game,12,stale,self.snap,self.identity,{},self.rows(1),'b')
        self.assertFalse((self.folder/'cabinet.tsv').exists())
    def test_empty_collection_is_a_valid_list(self):
        cabinet.publish(self.game,12,self.req,self.snap,self.identity,{},[],'b');result=json.loads((self.folder/'cabinet.json').read_bytes())
        self.assertEqual(result['rows'],[]);self.assertEqual(result['pages'],1)


if __name__=='__main__':unittest.main()
