from copy import deepcopy
import unittest
import club_finance as f
from finance_history import years
from test_club_finance import step,match,context
from loans import empty
from pathlib import Path
import hashlib,tempfile
import save_sidecar as sql


class FinanceYears(unittest.TestCase):
 def setUp(self):
  self.s,self.b,_=step(empty(1043,20261201),20261201,10_000_000)
  for k in ('coach','sponsor','staff','facilities'):self.s=f.toggle(self.s,k,False,20261201)
 def test_unsaved_rollover_uses_new_contract_and_reused_match_id_is_not_skipped(self):
  s,b,_=step(self.s,20261231,self.b,[match(1,20261220)])
  old=deepcopy(s['finance']['years']['2026']);terms=deepcopy(s['finance']['agreements']['20260101:7'])
  s,b,e=step(s,20270120,2_000_000,[match(1,20261220),match(1,20270115)])
  self.assertEqual(old,s['finance']['years']['2026']);self.assertEqual(terms,s['finance']['agreements']['20260101:7'])
  self.assertIn('20270101:7',s['finance']['agreements']);self.assertEqual(1,sum(r['kind']=='tv' for r in e))
  self.assertEqual(2_000_000,s['finance']['years']['2027']['opening_budget'])
  again,b2,e2=step(s,20270120,b,[match(1,20261220),match(1,20270115)]);self.assertEqual(b,b2);self.assertFalse(e2)
  self.assertEqual({2026,2027},{r['year'] for r in years(again)})
 def test_pending_december_due_is_posted_after_jump_and_belongs_to_previous_year(self):
  s,b,e=step(self.s,20270103,self.b,[match(2,20261231),match(3,20270102)])
  tv=[r for r in e if r['kind']=='tv'];self.assertEqual([20261231,20270102],sorted(r['date'] for r in tv))
  self.assertTrue(all(r['paid_date']==20270103 for r in tv));self.assertEqual(2,len(years(s)))
 def test_native_save_season_change_does_not_repeat_old_revenue_or_reset_settings(self):
  s,b,_=step(self.s,20261231,self.b,[match(1,20261220)])
  s=f.toggle(s,'tv',False,20261231);before=deepcopy(s['finance']['entries'])
  s,b,e=step(s,20270120,b,[match(1,20261220)],season=20270109)
  self.assertFalse(s['finance']['settings']['tv']);self.assertEqual(before,[r for r in s['finance']['entries'] if r['date']//10000==2026]);self.assertFalse(any(r['kind']=='tv' for r in e))
 def test_history_is_a_read_only_report(self):
  s,b,_=step(self.s,20261231,self.b,[match()]);before=deepcopy(s);years(s);years(s);self.assertEqual(before,s)
 def test_recording_next_year_attendance_does_not_mutate_the_input_ledger(self):
  before=deepcopy(self.s);reading=dict(match(90,20270105),percent=70,capacity=50000,source='native')
  result,changed=f.record_attendance(self.s,reading,20261231)
  self.assertTrue(changed);self.assertEqual(before,self.s);self.assertIn('20270101:7:90:1043:567',result['finance']['attendance'])
 def test_sql_checkpoints_keep_years_and_restore_the_selected_save_only(self):
  with tempfile.TemporaryDirectory() as tmp:
   save=Path(tmp)/'slot/DATA';save.parent.mkdir();save.write_bytes(b'native file remains unchanged');original=save.read_bytes()
   s,b,_=step(self.s,20261231,self.b,[match(1,20261220)]);digest=hashlib.sha256(original).hexdigest()
   sql.save_snapshot(save,dict(hash=digest,club=1043,date=20261231,budget=b),s,[],dict(operation='write',complete_file='1',access_tick_ms=1))
   old=deepcopy(s);s,b,_=step(s,20270120,b,[match(1,20270115)])
   newer=save.parent/'DATA_2027';newer.write_bytes(b'next native save fixture');newdigest=hashlib.sha256(newer.read_bytes()).hexdigest()
   sql.save_snapshot(newer,dict(hash=newdigest,club=1043,date=20270120,budget=b),s,[],dict(operation='write',complete_file='1',access_tick_ms=2))
   self.assertEqual(old,sql.load_snapshot(save,digest,1043)['state']);self.assertEqual(s,sql.load_snapshot(newer,newdigest,1043)['state'])
   with self.assertRaises(ValueError):sql.load_snapshot(newer,newdigest,567)
   self.assertEqual(original,save.read_bytes())
   with sql.connection(save) as db:
    self.assertEqual(2,db.execute('SELECT count(*) FROM finance_years WHERE checkpoint=?',(newdigest,)).fetchone()[0])

if __name__=='__main__':unittest.main()
