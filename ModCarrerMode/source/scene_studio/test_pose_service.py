import base64,io,unittest
from PIL import Image
from pose_service import PoseService
class PoseValidation(unittest.TestCase):
 def setUp(self):
  self.service=PoseService();buffer=io.BytesIO();Image.new('RGB',(64,128),'white').save(buffer,format='PNG');self.valid={'image':'data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode()}
 def tearDown(self):self.service.close()
 def test_invalid_payloads(self):
  for edit in ({'max_people':0},{'max_people':49},{'max_people':True},{'confidence':float('nan')},{'confidence':1.2},{'image':'http://example.invalid/photo.png'},{'image':'data:image/png;base64,%%%bad'},{'image':'data:image/png;base64,YmFk'},{'regions':[[0,0,1000,1000]]}):
   with self.assertRaises(ValueError):self.service.start({**self.valid,**edit})
  self.assertIsNone(self.service.child)
 def test_busy_rejected_before_launch(self):
  self.service.work.acquire()
  try:
   with self.assertRaises(BlockingIOError):self.service.start(self.valid)
  finally:self.service.work.release()
  self.assertIsNone(self.service.child)
 def test_unknown_job_is_empty(self):self.assertEqual(self.service.status('no-job'),{})
if __name__=='__main__':unittest.main(verbosity=2)
