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
 def test_explicit_retired_room_is_ignored_without_weakening_required_assets(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);stage=root/'clean';stage.mkdir();payload=b'v3';rel='data/sceneassets/server16_dressing_room_v3/shared/base.rx3';old='data/sceneassets/server16_dressing_room_20261022/old.rx3';expected={rel:dict(bytes=2,sha256=hashlib.sha256(payload).hexdigest())}
   with zipfile.ZipFile(root/'base.zip','w') as z:z.writestr(old,b'v2');z.writestr(rel,payload)
   self.assertEqual({rel},verify.extract_complements(stage,expected,set(),[root/'base.zip'],{old}));self.assertFalse((stage/old).exists())
   with self.assertRaisesRegex(AssertionError,'unexpected'):verify.extract_complements(stage,expected,set(),[root/'base.zip'])
 def test_unchanged_seed_is_verified_and_cannot_hide_missing_new_asset(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);stage=root/'clean';stage.mkdir();(stage/'same.png').write_bytes(b'base');expected={n:dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()) for n,raw in [('same.png',b'base'),('new.png',b'new')]}
   with zipfile.ZipFile(root/'delta.zip','w') as z:z.writestr('new.png',b'new')
   self.assertEqual(set(expected),verify.extract_complements(stage,expected,set(),[root/'delta.zip'],seeded={'same.png'}))
   with zipfile.ZipFile(root/'empty.zip','w'):pass
   with self.assertRaisesRegex(AssertionError,'missing'):verify.extract_complements(stage,expected,set(),[root/'empty.zip'],seeded={'same.png'})
 def test_path_traversal_is_rejected(self):
  with self.assertRaises(ValueError):verify.safe('../outside.rx3')

if __name__=='__main__':unittest.main()
