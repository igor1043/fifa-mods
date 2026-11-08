import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import test_screen
from test_engine import catalog,context,matches
from engine import Market
from model import project
from profile_request import RESUME,read
from screen import script_factory,FULL,stars
from manager_layout import scenes_for
from native_review_vm import open_native
import native_screen
from PIL import Image

TOKEN='a'*64
class LazyProfileTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);catalog(self.root/'catalog.db');self.market=Market(self.root/'world.db',self.root/'catalog.db');self.market.open_save('initial','DATA',context())
  with self.market.db:self.market.advance(context(20260120,matches(5)))
 def tearDown(self):self.market.close();self.tmp.cleanup()
 def light(self,coach=None):return dict(project(self.market,lightweight=True,detail_coach=coach),lazyProfiles=True,profileToken=TOKEN)
 def open(self,model):
  assets={'head_NOTFOUND_DEFAULT':Image.new('RGBA',(64,64),'gray'),**{'stars_'+str(i):stars(i) for i in range(11)}}
  path=self.root/'lazy.big';native_screen.build(test_screen.GAME,path,scenes_for(model,assets),assets,script_factory=script_factory(model,assets),full_name=FULL)
  vm,s,_,calls=open_native(path,full=FULL);test_screen.load_data(vm,s);return vm,s,calls
 def request_file(self,wire,**changes):
  data=dict(schema=1,pid=10,created=20,club=3,context='1e',epoch=2,date=20260120,captured_tick=1000,wire=wire);data.update(changes)
  path=self.root/'profile.tsv';path.write_text(''.join(f'{k}={v}\n' for k,v in data.items()));return path
 def observed(self):return dict(save=dict(pid=10,process_created_100ns=20),profile=dict(club_id=3,context_address=30,context_epoch=2),date=20260120)

 def test_list_projection_does_not_query_histories_or_calculate_full_careers(self):
  queries=[];self.market.db.set_trace_callback(queries.append)
  with patch('model.career_profile',side_effect=AssertionError('No full profile on list entry')):model=self.light()
  for table in ('results','reviews','honours','appointment_campaigns','annual_campaigns'):
   self.assertFalse(any(('FROM '+table+' ').lower() in q.lower() for q in queries),table)
  self.assertTrue(all(p.get('profilePending') for p in model['people']))
  self.assertFalse(any(p.get('spellCards') or p.get('yearCards') for p in model['people']))

 def test_one_profile_matches_legacy_complete_data_and_queries_only_that_coach(self):
  full=project(self.market);queries=[];self.market.db.set_trace_callback(queries.append)
  with patch('model.career_profile',wraps=__import__('model').career_profile) as detail:
   light=self.light('1');self.assertEqual(1,detail.call_count)
  actual=next(p for p in light['people'] if p['id']=='1');expected=next(p for p in full['people'] if p['id']=='1')
  self.assertEqual(expected,actual)
  self.assertTrue(any('home_coach=' in q and 'away_coach=' in q for q in queries));self.assertTrue(all(p.get('profilePending') for p in light['people'] if p['id']!='1'))

 def test_mouse_opens_waiting_profile_once_and_escape_returns_to_list(self):
  model=self.light();vm,s,calls=self.open(model)
  box=scenes_for(model,{})[0]['actions'];box=next(b for b in box if int(b['target'])==40)
  s.set('_xmouse',box['x']+box['w']/2);s.set('_ymouse',box['y']+box['h']/2);vm.invoke(s.get('onMouseDown'),s)
  self.assertTrue(s.get('profile'));self.assertTrue(s.get('scene2').get('_visible'))
  sent=[args for name,args in calls if name=='SendSystemEvent' and 'Server16ManagerProfile' in args]
  self.assertEqual(1,len(sent));wire=sent[0][-1]
  result=read(self.request_file(wire),self.observed(),model,1100);self.assertEqual(model['people'][s.get('person')]['id'],result['coach'])
  vm.invoke(s.get('Refresh'),s);self.assertEqual(1,len([a for n,a in calls if n=='SendSystemEvent' and 'Server16ManagerProfile' in a]))
  vm.invoke(s.get('Command'),s,(60,));self.assertFalse(s.get('profile'));self.assertTrue(s.get('scene0').get('_visible'));self.assertFalse(vm.errors)
  self.assertEqual(1,len([args for name,args in calls if name=='SendSystemEvent' and 'Server16ManagerProfile' in args]))

 def test_completed_profile_preserves_filters_page_selection_and_tabs(self):
  model=self.light('1');person=next(i for i,p in enumerate(model['people']) if p['id']=='1')
  model['resume']=dict(tab=0,page=0,country=0,league=100,movementCountry=1,movementLeague=1,month=0,hirePage=0,movePage=0,nation=0,focus=40,profile=True,person=person,profileTab=0,profileVenue=0,historyPage=0)
  vm,s,calls=self.open(model);self.assertTrue(s.get('profile'));self.assertTrue(s.get('scene1').get('_visible'))
  self.assertEqual('5',str(s.get('scene1').get('metric0').get('text')));self.assertEqual(1,len([a for n,a in calls if n=='SendSystemEvent' and 'Server16ManagerProfile' in a]))
  vm.invoke(s.get('Command'),s,(81,));self.assertEqual(1,s.get('profileTab'));vm.invoke(s.get('Command'),s,(84,));self.assertEqual(4,s.get('profileTab'));self.assertFalse(vm.errors)

 def test_request_rejects_old_catalog_foreign_career_date_and_invalid_person(self):
  model=self.light();wire='S16MGRP1|'+TOKEN+'|0|'+'|'.join('0' for _ in RESUME)+'|END'
  for fields in (dict(pid=11),dict(epoch=3),dict(context='ff'),dict(date=20260121),dict(wire=wire.replace(TOKEN,'b'*64)),dict(wire=wire.replace('|0|','|99999|',1)),dict(captured_tick=-40000)):
   with self.subTest(fields=fields),self.assertRaises((ValueError,KeyError)):read(self.request_file(wire,**fields) if 'wire' not in fields else self.request_file(**fields),self.observed(),model,1100)

 def test_profile_cannot_read_results_from_another_branch(self):
  branch=self.market.branch;before=next(p for p in self.light('1')['people'] if p['id']=='1')
  with self.market.db:
   self.market.branch=self.market.clone(branch);self.market.ingest(matches(10),20260220)
  # Both branches deliberately remain, as with protected active sessions.
  self.market.branch=branch
  selected=next(p for p in self.light('1')['people'] if p['id']=='1')
  self.assertEqual(before,selected);self.assertEqual(5,selected['overview'][0])

 def test_service_queries_only_clicked_coach_without_rebuilding_screen_on_return(self):
  import worker
  game=self.root/'game';root=game/'runtime';cat=game/'ModCarrerMode/data/manager_market/catalog.sqlite3';cat.parent.mkdir(parents=True);catalog(cat)
  snapshot=game/'ModCarrerMode/runtime/career_fce_snapshot.json';snapshot.parent.mkdir(parents=True);snapshot.write_text(json.dumps(dict(fixtures=matches(5),standings=[])))
  save=game/'saves/slot/DATA';save.parent.mkdir(parents=True);save.write_bytes(b'unchanged')
  observed=self.observed();observed['save']['path']=str(save);observed['signature']=('A',20260120)
  def build(game,path,model):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(json.dumps(dict(resume=model.get('resume'),profiles=sum(not p.get('profilePending',False) for p in model['people']))).encode())
  with patch.multiple(worker,GAME=game,ROOT=root,DEST=game/'screen.big'),patch.object(worker,'Inputs') as inputs,patch.object(worker,'io_event',return_value=dict(operation='read',access_tick_ms='1')),patch.object(worker,'observe',return_value=observed),patch.object(worker,'build',side_effect=build),patch.object(worker,'log'),patch('prepared_views.ticks',return_value=1100),patch('live_payload.publish') as publish_data:
   inputs.return_value.read.return_value=dict(context(20260120,matches(5)),digest='A',saved_date=20260120);service=worker.Service()
   try:
    service.update(observed,None);base=service.model_cache[0];self.assertTrue(base['lazyProfiles']);self.assertEqual(0,json.loads((game/'screen.big').read_bytes())['profiles'])
    index=next(i for i,p in enumerate(base['people']) if p['id']=='1');wire='S16MGRP1|'+base['profileToken']+'|'+str(index)+'|'+'|'.join('0' for _ in RESUME)+'|END'
    event=self.request_file(wire);root.mkdir(exist_ok=True);(root/'profile_request.tsv').write_bytes(event.read_bytes())
    service.update(observed,None);self.assertEqual(0,json.loads((game/'screen.big').read_bytes())['profiles']);self.assertEqual(['1'],list(service.profile_cache));self.assertEqual('profile',publish_data.call_args.args[3]['kind'])
    old=service.latest_request;before=(game/'screen.big').read_bytes();service.profile_serial+=1
    service.publish(old,observed,None,True,0);self.assertEqual(before,(game/'screen.big').read_bytes())
    cancel=wire.replace('|'+str(index)+'|','|-1|',1);event=self.request_file(cancel,captured_tick=1001);(root/'profile_request.tsv').write_bytes(event.read_bytes());service.update(observed,None)
    self.assertEqual(before,(game/'screen.big').read_bytes());self.assertEqual(1,publish_data.call_count);self.assertEqual(b'unchanged',save.read_bytes())
   finally:service.close()

if __name__=='__main__':unittest.main()
