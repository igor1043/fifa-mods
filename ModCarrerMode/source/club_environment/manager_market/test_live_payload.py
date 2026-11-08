"""Real APT payload: no navigation, UI recreation or input-handler takeover."""
from pathlib import Path
import tempfile,unittest,json,sqlite3
from types import SimpleNamespace
from unittest.mock import patch
from apt_vm import Object
from native_review_vm import open_native
from live_payload import build,publish
from loading_progress import payload
from catalog_meta import Labels
from contextlib import closing
import test_screen

class LivePayloadTests(unittest.TestCase):
 def test_data_only_native_child_carries_rows_without_screen_or_input_events(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'data.big';data=dict(kind='history',token='career-123',club=1043,date=20261106,data=dict(rows=[['Nome','head_1',52.4]],name='Flamengo'))
   build(test_screen.GAME,path,data)
   vm,state,apt,calls=open_native(path,full='game.screens.career.server16.ManagerLiveData')
   self.assertTrue(state.get('payloadReady'));loaded=state.get('payload')
   self.assertEqual(1043,loaded.get('club'));self.assertEqual('career-123',loaded.get('token'))
   self.assertAlmostEqual(52.4,loaded.get('data').get('rows')[0][2],places=3)
   self.assertFalse(any(name in ('SendEvent','SendSystemEvent','SetLocalEventHandler','Initialize','BeginAnimateIn') for name,args in calls))
 def test_progress_payload_retains_real_dates_and_counters(self):
  p=payload(['session'],2,9,dict(first=20260101,last=20260201,current=20260120,through=20260120,clubs=20,hires=2,exits=3,renewals=1))
  self.assertEqual('2 / 3',p['fields']['detailValue1']);self.assertIn('19 / 31',p['fields']['periodLabel']);self.assertEqual(2,p['stage'])
 def test_profile_data_updates_mounted_screen_and_rejects_other_scope(self):
  from screen import profile_payload
  fixture=test_screen.NativeScreenTest;fixture.setUpClass()
  try:
   vm,state,calls=fixture().open();state.set('profile',True);state.set('person',0)
   state.set('profileLoaded',[]);person=fixture.model['people'][0]
   payload=Object(dict(kind='profile',token='wrong',person=0,date=fixture.model['date'],encoded=profile_payload(person)))
   child=Object(dict(payloadReady=True,payload=payload));state.set('profileHolder',Object(dict(content=child)));state.set('profileRetry',6)
   vm.invoke(state.get('profilePoll'),state);self.assertFalse(state.get('profileLoaded'))
   payload.set('token',fixture.model.get('profileToken',''));before=len(calls)
   vm.invoke(state.get('profilePoll'),state)
   self.assertTrue(state.get('profileLoaded')[0]);self.assertTrue(state.get('scene1').get('_visible'))
   self.assertFalse(any(name in ('SendEvent','Initialize','BeginAnimateIn') for name,args in calls[before:]))
  finally:fixture.tearDownClass()
 def test_brazil_portuguese_and_english_share_one_real_flag(self):
  with tempfile.TemporaryDirectory() as folder:
   db=Path(folder)/'catalog.sqlite3'
   with closing(sqlite3.connect(db)) as con:
    con.execute('CREATE TABLE country_catalog(nation_id INT,name TEXT,source_name TEXT)')
    con.executemany('INSERT INTO country_catalog VALUES(?,?,?)',[(54,'Brazil','Brazil'),(223,'Brasil Nordeste','Brasil Nordeste')]);con.commit()
   labels=Labels(db)
   for name in ('Brasil','Brazil','BRASIL','Brasil Nordeste'):
    self.assertEqual(('Brasil','flag_54'),labels.nationality(name));self.assertEqual(('Brasil',54),labels.country(name))

 def test_live_history_updates_existing_timeline_and_percentage_bar(self):
  fixture=test_screen.NativeScreenTest
  fixture.setUpClass()
  try:
   vm,state,calls=fixture().open();root=state.get('scene7');root.set('tlBar0',Object())
   state.set('historyPending',True);state.set('clubTimeline',True);state.set('requestedHistoryClub',1)
   rows=[['Técnico','head_NOTFOUND_DEFAULT','01/01/2026 - Atual','289 dias no cargo','Atual','7','3','1','3','47,6%','1',0,47.6]]
   details=Object(dict(club=1,name='Clube 1',crest='crest_1',rows=rows))
   data=Object(dict(kind='history',token='wrong',club=1,date=fixture.model['date'],data=details))
   child=Object(dict(payloadReady=True,payload=data));state.set('historyHolder',Object(dict(content=child)));state.set('historyRetry',30)
   vm.invoke(state.get('historyPoll'),state);self.assertTrue(state.get('historyPending'))
   data.set('token',fixture.model.get('profileToken',''));before=len(calls)
   vm.invoke(state.get('historyPoll'),state)
   self.assertFalse(state.get('historyPending'));self.assertTrue(root.get('_visible'));self.assertEqual(1,state.get('historyLoadedClub'))
   self.assertAlmostEqual(47.6*7.6,root.get('tlBar0').get('_width'),places=2)
   self.assertIn(' - 289 dias',root.get('tlDates0').get('text'))
   self.assertFalse(any(n in ('SendEvent','BeginAnimateIn','Initialize') for n,args in calls[before:]))
  finally:fixture.tearDownClass()
 def test_long_career_payload_uses_bounded_row_pushes(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'long.big';rows=[[str(i),i,50.0] for i in range(500)]
   build(test_screen.GAME,path,dict(kind='history',data=dict(rows=rows)))
   vm,state,apt,calls=open_native(path,full='game.screens.career.server16.ManagerLiveData')
   self.assertEqual(500,len(state.get('payload').get('data').get('rows')))

if __name__=='__main__':unittest.main()
