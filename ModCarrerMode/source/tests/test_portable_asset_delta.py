from pathlib import Path
import hashlib,importlib.util,tempfile,unittest,zipfile
spec=importlib.util.spec_from_file_location('delta_release',Path(__file__).resolve().parents[3]/'ModCarrerMode/tools/Verify-PortablePackage.py');verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)

class AssetDeltaTests(unittest.TestCase):
 def test_base_and_delta_verify_final_bytes_and_missing_base_is_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);stage=root/'clean';stage.mkdir();expected={}
   for name,raw in (('models/one.rx3',b'new'),('faces/two.png',b'face')):expected[name]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
   with zipfile.ZipFile(root/'base.zip','w') as z:z.writestr('models/one.rx3',b'old');z.writestr('faces/two.png',b'face')
   with zipfile.ZipFile(root/'delta.zip','w') as z:z.writestr('models/one.rx3',b'new')
   self.assertEqual(set(expected),verify.extract_complements(stage,expected,set(),[root/'base.zip',root/'delta.zip']))
   with self.assertRaisesRegex(AssertionError,'missing'):verify.extract_complements(stage,expected,set(),[root/'delta.zip'])
   with self.assertRaisesRegex(AssertionError,'duplicates'):verify.extract_complements(stage,expected,{'models/one.rx3'},[root/'base.zip',root/'delta.zip'])
 def test_path_traversal_is_rejected(self):
  with self.assertRaises(ValueError):verify.safe('../outside.rx3')

if __name__=='__main__':unittest.main()
