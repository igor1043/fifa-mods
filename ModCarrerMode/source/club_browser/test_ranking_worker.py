from pathlib import Path
from unittest.mock import patch
import unittest
import ranking_worker as worker

class RankingWorker(unittest.TestCase):
 def run_job(self,snapshots,req_change=False,times=None):
  req=dict(schema=1,pid=123,seq=42,club=1,kind='rankings');saved=dict(path='unchanged/DATA',size=100,mtime_ns=100)
  data=dict(club=1,date=20260101,national=3,clubName='Club',matches=0,years=4,referenceDate=0,groups=dict(clubs=[],nations=[],coaches=[]))
  with patch('lineup_worker.observe',return_value=(saved,(90,7,1))),patch('lineup_worker.request',return_value=dict(req,seq=43) if req_change else req),patch('lineup_worker.atomic') as atomic,patch('lineup_worker.publish') as publish,patch('career_results.live_leagues',return_value=None),patch.object(worker,'competition_session',return_value={}),patch.object(worker,'current',side_effect=snapshots),patch.object(worker,'project',return_value=data),patch.object(worker.time,'monotonic',side_effect=times or [0,0]),patch.object(worker.time,'sleep'):
   result=worker.generate(Path('.'),Path('unused'),req,object(),None)
  return result,atomic,publish
 def test_atomic_payload_has_identity_of_own_request(self):
  snap=dict(club=1,date=20260101,generation=1);result,atomic,publish=self.run_job([snap,dict(snap,generation=99)]);self.assertTrue(result);self.assertEqual(atomic.call_count,2);self.assertIn(b'H\t1\t42\t1',atomic.call_args_list[0].args[1]);self.assertEqual(publish.call_args.kwargs['kind'],'rankings')
 def test_calendar_change_discards_old_response(self):
  result,atomic,publish=self.run_job([dict(club=1,date=20260101),dict(club=1,date=20260102)]);atomic.assert_not_called();self.assertEqual(publish.call_args.kwargs['retry'],1)
 def test_late_ram_retries_instead_of_forever_loading(self):
  result,atomic,publish=self.run_job([None],times=[0,0,13]);atomic.assert_not_called();self.assertEqual(publish.call_args.kwargs['retry'],1)
 def test_request_changed_cannot_overwrite_new_page(self):
  result,atomic,publish=self.run_job([],req_change=True);self.assertFalse(result);atomic.assert_not_called();publish.assert_not_called()

if __name__=='__main__':unittest.main(verbosity=2)
