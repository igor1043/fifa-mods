import json,sqlite3,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from detail_service import ReadOnlyMarket,DetailResponder
from engine import Market
from model import project
from test_engine import catalog,context
from worker import view_scope

class DetailTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  catalog(self.root/'catalog.sqlite3');self.market=Market(self.root/'world.sqlite3',self.root/'catalog.sqlite3')
  self.addCleanup(self.market.close);self.market.open_save('A','DATA',context())
  with self.market.db.read_batch():self.base=project(self.market,lightweight=True)
  self.base.update(profileToken='TEST',lazyProfiles=True)
  self.observed=dict(save=dict(pid=10,process_created_100ns=20,path=str(self.root/'DATA')),
                     profile=dict(context_epoch=3,context_address=1234,club_id=3),date=20260101)
  self.current=dict(generation=('view',self.market.branch),scope=view_scope(self.observed),base=self.base,
                    path=self.market.path,catalog=self.market.catalog,branch=self.market.branch)
  self.sent=[];self.events=[]
  self.responder=DetailResponder(self.root,self.root,SimpleNamespace(),lambda:self.current,lambda _:self.observed,
    lambda _:None,lambda:1000,lambda *a:self.sent.append(a),lambda event,**fields:self.events.append((event,fields)))
  self.addCleanup(lambda:self.responder.reader and self.responder.reader.close())
 def request(self):
  wire='S16MGRP1|TEST|0|'+'|'.join(['0']*11)+'|END'
  fields=dict(schema=1,pid=10,created=20,epoch=3,context=format(1234,'x'),club=3,date=20260101,captured_tick=999,wire=wire)
  (self.root/'profile_request.tsv').write_text(''.join(f'{k}={v}\n' for k,v in fields.items()),encoding='ascii')
 def test_profile_uses_its_own_read_only_connection_and_writes_no_market_facts(self):
  self.request();before=self.market.db.total_changes
  self.responder.tick(None)
  self.assertEqual(len(self.sent),1);self.assertEqual(self.sent[0][3]['kind'],'profile')
  self.assertEqual(self.market.db.total_changes,before)
  with self.assertRaises(sqlite3.OperationalError):self.responder.reader.db.execute('DELETE FROM coaches')
  self.responder.tick(None);self.assertEqual(len(self.sent),1)
 def test_same_click_is_rejected_on_a_different_save_or_day(self):
  self.request();self.observed=dict(self.observed,date=20260102)
  self.responder.tick(None);self.assertFalse(self.sent)
 def test_changed_generation_after_query_cannot_publish_stale_data(self):
  self.request()
  import profile_query
  original=profile_query.build
  def changed(*a,**kw):
   result=original(*a,**kw);self.current=dict(self.current,generation=('different',self.market.branch));return result
  with patch.object(profile_query,'build',side_effect=changed):self.responder.tick(None)
  self.assertFalse(self.sent)
 def test_cache_is_invalidated_after_an_external_commit(self):
  self.request();self.responder.tick(None)
  with self.market.db:self.market.db.execute('UPDATE coaches SET salary=salary+100 WHERE branch=?',(self.market.branch,))
  self.request();self.responder.stamps.clear();self.responder.completed.clear();self.responder.tick(None)
  self.assertEqual(len(self.sent),2);self.assertFalse(self.events[-1][1]['cached'])
 def test_or_predicates_do_not_escape_the_selected_branch(self):
  foreign=dict(self.market.one('clubs','club_id',2),branch='FOREIGN')
  with self.market.db:self.market.db.execute('INSERT INTO clubs('+','.join(foreign)+') VALUES('+','.join('?' for _ in foreign)+')',tuple(foreign.values()))
  reader=ReadOnlyMarket(self.market.path,self.market.catalog,self.market.branch)
  try:
   self.assertEqual(reader.rows('clubs','club_id=? OR club_id=?',(1,2)),[dict(r) for r in self.market.db.execute('SELECT * FROM clubs WHERE branch=? AND (club_id=? OR club_id=?)',(self.market.branch,1,2))])
  finally:reader.close()

if __name__=='__main__':unittest.main()
