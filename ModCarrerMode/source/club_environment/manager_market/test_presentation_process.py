from pathlib import Path
from types import SimpleNamespace
import json,tempfile,threading,time,unittest
import test_screen
from presentation_process import PresentationExecutor

class PresentationProcessTest(unittest.TestCase):
 def test_render_ipc_does_not_block_the_caller_or_accept_another_job_result(self):
  with tempfile.TemporaryDirectory() as tmp:
   executor=PresentationExecutor(Path(tmp),123);executor.child=SimpleNamespace(poll=lambda:None)
   try:
    future=executor.submit(None,dict(key='a'*64,model=dict(date=20260101)))
    deadline=time.monotonic()+3;request=executor.folder/'request.json'
    while not request.exists() and time.monotonic()<deadline:time.sleep(.01)
    job=json.loads(request.read_bytes());result=executor.folder/'result.json'
    result.write_text(json.dumps(dict(job='old',cached=False,seconds=99)));self.assertFalse(future.done())
    result.write_text(json.dumps(dict(job=job['job'],cached=True,seconds=.5)));self.assertEqual((True,.5),future.result(timeout=3))
   finally:
    executor.child=None;executor.shutdown(wait=True)
 def test_render_failure_propagates_without_publishing_a_ready_package(self):
  with tempfile.TemporaryDirectory() as tmp:
   executor=PresentationExecutor(Path(tmp),123);executor.child=SimpleNamespace(poll=lambda:None)
   try:
    future=executor.submit(None,dict(key='a'*64,model={}))
    deadline=time.monotonic()+3;request=executor.folder/'request.json'
    while not request.exists() and time.monotonic()<deadline:time.sleep(.01)
    job=json.loads(request.read_bytes());(executor.folder/'result.json').write_text(json.dumps(dict(job=job['job'],error='Failed texture validation')))
    with self.assertRaisesRegex(RuntimeError,'Failed texture validation'):future.result(timeout=3)
   finally:
    executor.child=None;executor.shutdown(wait=True)

if __name__=='__main__':unittest.main()
