"""Session isolation, exact cup identity, repeated slots and native navigation."""
import copy,json,sqlite3,tempfile,unittest,sys,shutil
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from trophy_room import data,geometry


class TrophyDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.game=Path(self.tmp.name);self.runtime=self.game/'ModCarrerMode/runtime/manager_market';self.runtime.mkdir(parents=True)
        self.save=self.game/'career/DATA';self.save.parent.mkdir();self.save.write_bytes(b'career untouched')
        self.db=self.save.with_name('server16_manager_market.sqlite3')
        with closing(sqlite3.connect(self.db)) as c, c:
            c.executescript('CREATE TABLE branches(id TEXT,game_date INT,user_club INT);CREATE TABLE honours(branch TEXT,club_id INT,season INT,root INT,competition_id INT,game_date INT,name TEXT);')
            c.execute('INSERT INTO branches VALUES(?,?,?)',('current',20261101,1043))
            c.executemany('INSERT INTO honours VALUES(?,?,?,?,?,?,?)',[
                ('current',1043,20260101,55,1003,20261030,'Copa'),('current',1043,20260101,55,1003,20261030,'Copa'),
                ('current',1043,20260101,66,1009,20261201,'Futuro'),('other',1043,20260101,11,7,20261010,'Outro save'),
                ('current',2,20260101,33,1005,20261010,'Outro clube')])
        self.snapshot=dict(pid=99,processCreated100ns=1234,fceContextEpoch=7,club=1043,date=20261101,savePath=str(self.save))
        self.state=dict(pid=99,created=1234,epoch=7,club=1043,date=20261101,save=str(self.save),database=str(self.db),branch='current')
        self.publish()

    def tearDown(self):self.tmp.cleanup()
    def publish(self):(self.runtime/'state_ready.json').write_text(json.dumps(self.state),encoding='utf8')
    def test_only_current_club_branch_and_completed_titles(self):
        rows,branch=data.title_rows(self.game,self.snapshot);self.assertEqual(branch,'current');self.assertEqual(len(rows),1);self.assertEqual(rows[0]['year'],2026);self.assertEqual(rows[0]['competition'],1003)
    def test_does_not_write_database_or_save(self):
        before=self.db.read_bytes(),self.save.read_bytes();data.title_rows(self.game,self.snapshot)
        self.assertEqual(before,(self.db.read_bytes(),self.save.read_bytes()))
    def test_coach_collection_keeps_winning_club_and_excludes_other_coaches(self):
        with closing(sqlite3.connect(self.db)) as c, c:
            c.execute('ALTER TABLE honours ADD COLUMN coach_id TEXT')
            c.execute('CREATE TABLE appointments(branch TEXT,club_id INT,coach_id TEXT,start_date INT,end_date INT)')
            c.execute('INSERT INTO appointments VALUES(?,?,?,?,?)',('current',1043,'USER-1',20260101,None))
            c.execute('DELETE FROM honours')
            c.executemany('INSERT INTO honours VALUES(?,?,?,?,?,?,?,?)',[
                ('current',1043,20260101,1,1003,20260301,'Copa A','USER-1'),
                ('current',2,20250101,2,7,20251001,'Copa B','USER-1'),
                ('current',1043,20260101,3,1009,20260401,'Outro técnico','CPU-4'),
                ('other',1043,20260101,4,23,20260501,'Outro save','USER-1')])
        before=self.db.read_bytes();club,_=data.title_rows(self.game,self.snapshot,'club');coach,_=data.title_rows(self.game,self.snapshot,'coach')
        self.assertEqual([r['name'] for r in club],['Copa A']);self.assertEqual({r['name'] for r in coach},{'Copa A','Copa B'})
        self.assertEqual({r['club'] for r in coach},{1043,2});self.assertEqual(before,self.db.read_bytes())
    def test_rejects_another_process_epoch_club_or_date(self):
        for field,value in [('pid',100),('created',1235),('epoch',8),('club',2),('date',20260101)]:
            with self.subTest(field=field):
                snap=dict(self.snapshot);key={'created':'processCreated100ns','epoch':'fceContextEpoch'}.get(field,field);snap[key]=value
                with self.assertRaises(ValueError):data.title_rows(self.game,snap)
    def test_national_cups_belong_to_coach_collection_and_keep_selection_identity(self):
        with closing(sqlite3.connect(self.db)) as c, c:
            c.execute('ALTER TABLE honours ADD COLUMN coach_id TEXT')
            c.execute('CREATE TABLE appointments(branch TEXT,club_id INT,coach_id TEXT,start_date INT,end_date INT)')
            c.execute('INSERT INTO appointments VALUES(?,?,?,?,?)',('current',1043,'USER-1',20260101,None))
            c.execute('CREATE TABLE trophy_history(branch TEXT,coach_id TEXT,club_id INT,season INT,competition_id INT,root INT,game_date INT,name TEXT,source TEXT,team_kind TEXT)')
            c.executemany('INSERT INTO trophy_history VALUES(?,?,?,?,?,?,?,?,?,?)',[
                ('current','USER-1',1370,20260101,28,100,20260712,'Copa de seleções','confirmed_calendar','national'),
                ('current','CPU-2',1318,20260101,28,100,20260712,'Outro treinador','confirmed_calendar','national')])
        club,_=data.market_title_rows(self.game,self.snapshot,'club');coach,_=data.market_title_rows(self.game,self.snapshot,'coach')
        self.assertEqual([],club);self.assertEqual([(1370,'national')],[(r['club'],r['team_kind']) for r in coach])
    def test_rejects_database_from_another_career(self):
        self.state['database']=str(self.game/'other/db.sqlite');self.publish()
        with self.assertRaises(ValueError):data.title_rows(self.game,self.snapshot)
    def test_page_capacity_does_not_lose_titles(self):
        rows=[dict(date=20260101+i,competition=i,root=i) for i in range(65)]
        all=[]
        for p in range(3):
            chunk,page,pages=data.page_rows(rows,p);all+=chunk;self.assertEqual(pages,3)
        self.assertEqual(len(all),65);self.assertEqual(len({r['root'] for r in all}),65)
    def test_exact_trophy_mapping_precedes_asset_id(self):self.assertEqual(data.trophy_id(7,40,{7:1003},lambda i:i in (7,1003)),1003)
    def test_never_replaces_missing_cup_with_unrelated_node_or_generic(self):self.assertEqual(data.trophy_id(9000,13,{},lambda i:i in (13,999)),0)
    def test_exact_native_asset_is_supported(self):self.assertEqual(data.trophy_id(1003,40,{},lambda i:i==1003),1003)
    def test_custom_requires_the_clubs_own_editable_image(self):
        self.assertEqual(data.appearance(self.game,1043),'default')
        folder=self.game/'ModCarrerMode/data/trophy_room/custom/1043';folder.mkdir(parents=True);(folder/'identity-wall.png').write_bytes(b'PNG')
        self.assertEqual(data.appearance(self.game,1043),'custom');self.assertEqual(data.appearance(self.game,2),'default')
    def test_demo_is_opt_in_and_does_not_create_titles(self):
        self.assertEqual(data.demo_rows(self.game,1043,2026),[])
        model=self.game/'data/sceneassets/trophy/trophy_7.rx3';model.parent.mkdir(parents=True,exist_ok=True);model.write_bytes(b'model')
        settings=self.game/'ModCarrerMode/config/trophy_room.ini';settings.parent.mkdir(parents=True);settings.write_text('[1043]\npreview_trophies=true\n')
        rows=data.demo_rows(self.game,1043,2026)
        self.assertIn(7,[r['competition'] for r in rows]);self.assertTrue(all(r['origin']=='preview' for r in rows))
        self.assertIn('DEMONSTRAÇÃO',rows[0]['name']);self.assertEqual(data.demo_rows(self.game,2,2026),[])


class GalleryGeometryTests(unittest.TestCase):
    def test_symmetric_slots(self):
        slots=geometry.slots();self.assertEqual(len(slots),30)
        for a,b in zip(slots[:15],slots[15:]):
            self.assertEqual(a['x'],-b['x']);self.assertEqual(a['z'],b['z']);self.assertEqual(a['yaw'],-b['yaw'])
    def test_no_generated_trophy_geometry(self):
        doc=geometry.build();self.assertFalse(any('cup' in p['name'].lower() or 'trophy' in p['name'].lower() for p in doc['parts']))
    def test_identity_wall_is_a_separate_editable_surface(self):
        doc=geometry.build();self.assertEqual(sum(p['material']=='identity' for p in doc['parts']),1)
    def test_closed_door_bench_and_two_display_walls(self):
        doc=geometry.build();names=[p['name'] for p in doc['parts']]
        self.assertIn('Closed exit door',names);self.assertIn('Museum bench base',names)
        self.assertEqual(names.count('Cabinet lower body'),2);self.assertEqual(sum(n.startswith('Pedestal ') and 'foot' not in n for n in names),30)
    def test_all_geometry_is_bounded_and_indexed(self):
        for p in geometry.build()['parts']:
            self.assertEqual(len(p['positions']),len(p['uvs']));self.assertEqual(len(p['indices'])%3,0)
            self.assertLess(max(p['indices']),len(p['positions']))
    def test_loading_card_faces_the_camera_and_preserves_its_image_ratio(self):
        from trophy_room.loading import quad
        part=quad(0,166,100,1296,729)
        self.assertEqual(len(part['positions']),4);self.assertEqual(part['indices'],[0,1,2,0,2,3])
        self.assertEqual(part['normals'],[[0,0,1]]*4)
        self.assertAlmostEqual((part['positions'][1][0]-part['positions'][0][0])/(part['positions'][2][1]-part['positions'][1][1]),16/9)


class GalleryPublicationTests(TrophyDataTests):
    def setUp(self):
        super().setUp()
        from trophy_room import worker
        self.worker=worker;self.installed=Path(__file__).resolve().parents[4]
        # Assets can be tested from either the dev checkout or this installation.
        if not (self.installed/'data/sceneassets/server16_trophy_room/layout.json').is_file():
            self.installed=Path('U:/fifa 16')
        if not (self.installed/'data/sceneassets/server16_trophy_room/layout.json').is_file():self.skipTest('Native gallery asset build is not present')
        for relative in ('data/sceneassets/server16_trophy_room/layout.json',
                         'ModCarrerMode/data/trophy_room/texture-template.rx3',
                         'data/sceneassets/trophy/trophy_1003.rx3','data/sceneassets/trophy/trophy_1003_textures.rx3',
                         'data/ui/imgAssets/crest/light/l1043.dds'):
            source=self.installed/relative
            if not source.is_file():source=Path('U:/fifa 16')/relative
            target=self.game/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        layout=self.game/'data/sceneassets/server16_trophy_room/layout.json'
        doc=json.loads(layout.read_bytes());doc['slots']=geometry.slots();layout.write_text(json.dumps(doc))
        relative='ModCarrerMode/data/trophy_room/prop-template.rx3'
        shutil.copy2(self.installed/relative,self.game/relative)
        self.request=dict(pid=99,club=1043,epoch=7,requested=True,custom=False,page=0)
        self.folder=self.game/'ModCarrerMode/runtime/trophy_room';self.folder.mkdir(parents=True)
        (self.game/'ModCarrerMode/runtime/career_fce_snapshot.json').write_text(json.dumps(self.snapshot),encoding='utf8')
        (self.folder/'request.json').write_text(json.dumps(self.request),encoding='utf8')

    def generate(self):
        with patch.object(self.worker.assets,'club_identity',return_value=(dict(club=1043,name='Flamengo',colors=[(185,10,20),(20,20,20)]),{1003:1003})):
            return self.worker.generate(self.game,99,self.request)

    def test_native_manifest_contains_only_the_won_competitions_model(self):
        self.generate();manifest=(self.folder/'components.txt').read_text(encoding='utf8');publication=json.loads((self.folder/'publication.json').read_bytes())
        self.assertIn('trophy_1003.rx3',manifest);self.assertNotIn('trophy_999.rx3',manifest)
        self.assertEqual(len(publication['shown']),1);self.assertEqual(publication['shown'][0]['trophy_id'],1003)
        self.assertEqual(publication['missing_models'],[])
    def test_missing_exact_model_keeps_plaque_and_reports_no_substitution(self):
        (self.game/'data/sceneassets/trophy/trophy_1003.rx3').unlink();self.generate()
        publication=json.loads((self.folder/'publication.json').read_bytes());self.assertEqual(len(publication['missing_models']),1)
        self.assertNotIn('data/sceneassets/trophy/trophy_', (self.folder/'components.txt').read_text(encoding='utf8'))
    def test_unchanged_titles_do_not_repaint_or_republish(self):
        first=self.generate();stamp=(self.folder/'components.txt').stat().st_mtime_ns
        self.assertEqual(self.generate(),first);self.assertEqual((self.folder/'components.txt').stat().st_mtime_ns,stamp)
    def test_native_size_is_not_enlarged_to_fill_case(self):
        from trophy_room.assets import native_cup
        cup=native_cup(self.game,1003);self.assertLessEqual(cup['scale'],1)
        self.assertEqual(cup['display_dimensions_cm'],cup['native_dimensions_cm'])
    def test_enhanced_gallery_publishes_cameras_and_ui_history_without_tinted_3d_cards(self):
        self.request['gallery_views']=2;(self.folder/'request.json').write_text(json.dumps(self.request))
        self.generate();pub=json.loads((self.folder/'publication.json').read_bytes())
        self.assertEqual(pub['gallery_views'],2);self.assertEqual(len(pub['cameras']),1)
        self.assertEqual((self.folder/'cameras.txt').read_text().splitlines()[0],f'S16TROPHYCAM 1 {pub["generation"]} 1')
        self.assertNotIn('"detail_', (self.folder/'components.txt').read_text(encoding='utf8'))
        self.assertTrue((self.folder/'detail-cards.tsv').read_text(encoding='utf8').startswith('S16TITLECARDS 2 '))
    def test_collection_change_reuses_room_materials_and_meshes(self):
        from PIL import Image
        wall=self.game/'ModCarrerMode/data/trophy_room/custom/1043/identity-wall.png'
        wall.parent.mkdir(parents=True);Image.new('RGBA',(1920,640),'#a81020').save(wall)
        self.request.update(gallery_views=4,custom=True);(self.folder/'request.json').write_text(json.dumps(self.request))
        self.generate();first=json.loads((self.folder/'publication.json').read_bytes())
        import shlex
        def room_lines():
            return [shlex.split(line)[:9] for line in (self.folder/'components.txt').read_text().splitlines()
                    if line.startswith('"') and not line.startswith(('"cup_','"plaque_','"detail_'))]
        initial=room_lines();self.request['collection']='coach';(self.folder/'request.json').write_text(json.dumps(self.request))
        with patch.object(self.worker.assets,'identity_image',side_effect=AssertionError('Coach room must not load club art')):
            self.generate()
        second=json.loads((self.folder/'publication.json').read_bytes())
        self.assertNotEqual(first['signature'],second['signature']);self.assertEqual(first['appearance'],second['appearance'])
        self.assertEqual(1,len([r for r in initial if r[0]=='identity']))
        self.assertEqual([r for r in initial if r[0]!='identity'],room_lines());self.assertEqual(second['collection'],'coach')
        # Keep the wire style equal to the request: native loading validates it
        # even when the optional club panel is hidden in the coach collection.
        self.assertEqual('1',(self.folder/'components.txt').read_text().splitlines()[0].split()[6])
        self.request['collection']='club';(self.folder/'request.json').write_text(json.dumps(self.request))
        self.generate();self.assertEqual(initial,room_lines())
    def test_clean_architecture_has_no_baked_lighting_and_publishes_local_probes(self):
        self.request['gallery_views']=4;(self.folder/'request.json').write_text(json.dumps(self.request));self.generate()
        import shlex
        lines=(self.folder/'components.txt').read_text().splitlines();self.assertTrue(lines[0].startswith('S16TROPHY 3 '))
        surfaces=[shlex.split(line) for line in lines if line.startswith('"surface_')]
        self.assertGreater(len(surfaces),8)
        self.assertNotIn('room-lighting.rx3','\n'.join(lines))
        for fields in surfaces:
            self.assertEqual(fields[10],'0');self.assertEqual(len(fields),15)
            self.assertIn('gallery-clean',fields[1]);self.assertTrue(all(abs(float(v))<=1000 for v in fields[12:15]))
    def test_thirty_wins_share_one_cup_camera_and_preserve_all_dates(self):
        with closing(sqlite3.connect(self.db)) as c, c:
            c.execute('DELETE FROM honours')
            c.executemany('INSERT INTO honours VALUES(?,?,?,?,?,?,?)',[
                ('current',1043,20260101,100+i,1003,20261001+i,'Copa') for i in range(30)])
        self.request['gallery_views']=2;(self.folder/'request.json').write_text(json.dumps(self.request))
        self.generate();pub=json.loads((self.folder/'publication.json').read_bytes());lines=(self.folder/'components.txt').read_text().splitlines()
        self.assertEqual(len(pub['shown']),1);self.assertEqual(len(pub['cameras']),1)
        self.assertEqual(len(pub['shown'][0]['wins']),30)
        self.assertEqual(pub['shown'][0]['title_count'],30)
        cup_lines=[line for line in lines if line.startswith('"cup_')];self.assertEqual(len(cup_lines),1)
        self.assertTrue(cup_lines[0].endswith(' 1'));self.assertFalse(any(line.startswith('"detail_') for line in lines))
    def test_generated_maps_use_fifas_native_data_mount(self):
        self.generate();manifest=(self.folder/'components.txt').read_text(encoding='utf8')
        self.assertNotIn('ModCarrerMode/runtime/trophy_room/assets/',manifest)
        self.assertIn('data/sceneassets/server16_trophy_room/99/',manifest)
        for line in manifest.splitlines()[1::2]:
            import shlex
            fields=shlex.split(line)
            for index in (1,3,5,7):
                self.assertTrue(fields[index].startswith('data/sceneassets/'))
                self.assertTrue((self.game/fields[index]).is_file() or fields[index].startswith('data/sceneassets/server16_trophy_room/'))
    def test_demo_publication_preserves_real_honours(self):
        settings=self.game/'ModCarrerMode/config/trophy_room.ini';settings.parent.mkdir(parents=True);settings.write_text('[1043]\npreview_trophies=true\n')
        before=self.db.read_bytes();self.generate()
        publication=json.loads((self.folder/'publication.json').read_bytes())
        self.assertFalse(publication['preview']);self.assertEqual(publication['real_titles'],1)
        self.assertTrue(all(r['origin']=='career' for r in publication['shown']))
        self.assertEqual(self.db.read_bytes(),before)


class InspectionFramingTests(unittest.TestCase):
    def test_authored_close_cues_aim_at_the_cup_not_the_old_left_panel(self):
        from .presentation import visit
        for slot in geometry.slots():
            cue=visit(slot,{'display_dimensions_cm':[40,80,40]})
            self.assertEqual(cue['target'],[slot['x'],slot['y']+40,slot['z']])
            self.assertEqual(cue['detail_target'],cue['target'])
            self.assertEqual(cue['slot'],slot['index'])

if __name__=='__main__':unittest.main()
