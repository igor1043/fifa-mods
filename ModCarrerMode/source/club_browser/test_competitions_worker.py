"""Publication races must retry without publishing a stale career view."""
from pathlib import Path
from unittest.mock import patch
import unittest
import competitions_worker as worker

class Worker(unittest.TestCase):
 def setUp(self):
  self.req=dict(schema=1,pid=123,seq=42,club=11,kind='competitions');self.saved=dict(path='career.DATA',size=100,mtime_ns=1);self.context=(90,7,11);self.snapshot=dict(club=11,date=20260110,generation=8);self.folder=Path('unused')
 def run_job(self,snapshots,latest_request=None,times=None):
  with patch('lineup_worker.observe',return_value=(self.saved,self.context)),patch('lineup_worker.request',return_value=latest_request or self.req),patch('lineup_worker.atomic') as atomic,patch('lineup_worker.publish') as publish,patch.object(worker,'competition_session',return_value={}),patch.object(worker,'current',side_effect=snapshots),patch.object(worker,'project',return_value=dict(club=11,clubName='Club',date=20260110,competitions=[])),patch.object(worker.time,'monotonic',side_effect=times or [0,0,0]),patch.object(worker.time,'sleep'):
   result=worker.generate(Path('.'),self.folder,self.req,object(),None)
  return result,atomic,publish
 def test_ready_result_uses_own_request(self):
  result,atomic,publish=self.run_job([self.snapshot,self.snapshot]);self.assertTrue(result);self.assertEqual(atomic.call_count,1);self.assertIn(b'H\t1\t42\t11\t20260110',atomic.call_args.args[1]);self.assertEqual(publish.call_args.kwargs['kind'],'competitions')
 def test_calendar_change_discards_result_and_retries(self):
  result,atomic,publish=self.run_job([self.snapshot,dict(self.snapshot,date=20260111)]);atomic.assert_not_called();self.assertTrue(result);self.assertEqual(publish.call_args.kwargs['retry'],1)
 def test_late_publication_has_a_retry_instead_of_infinite_loading(self):
  result,atomic,publish=self.run_job([None],times=[0,0,13]);atomic.assert_not_called();self.assertTrue(result);self.assertEqual(publish.call_args.kwargs['retry'],1)
 def test_superseded_request_cannot_replace_newer_screen(self):
  result,atomic,publish=self.run_job([],dict(self.req,seq=43));atomic.assert_not_called();publish.assert_not_called();self.assertFalse(result)

if __name__=='__main__':unittest.main(verbosity=2)
