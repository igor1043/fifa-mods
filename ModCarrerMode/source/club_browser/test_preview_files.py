from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import ctypes,os,threading,time,unittest
from concurrent.futures import ThreadPoolExecutor
import preview_files as files

class PreviewFiles(unittest.TestCase):
 def test_atomic_retries_sharing_denial_without_partial_file(self):
  with TemporaryDirectory() as temp:
   target=Path(temp)/'status.tsv';target.write_bytes(b'old');replace=os.replace;calls=[]
   def locked(a,b):
    calls.append(1)
    if len(calls)<3:raise PermissionError(13,'temporarily open')
    return replace(a,b)
   with patch.object(files.os,'replace',side_effect=locked),patch.object(files.time,'sleep'):
    files.atomic(target,b'complete new status')
   self.assertEqual(target.read_bytes(),b'complete new status');self.assertEqual(len(calls),3);self.assertEqual(list(Path(temp).glob('*.new')),[])
 def test_permanent_denial_is_bounded_and_preserves_previous_file(self):
  with TemporaryDirectory() as temp:
   target=Path(temp)/'status.tsv';target.write_bytes(b'old')
   with patch.object(files.os,'replace',side_effect=PermissionError(13,'denied')) as replace,patch.object(files.time,'sleep'):
    with self.assertRaises(PermissionError):files.atomic(target,b'new')
   self.assertEqual(replace.call_count,8);self.assertEqual(target.read_bytes(),b'old');self.assertEqual(list(Path(temp).glob('*.new')),[])
 def test_shared_cache_writers_do_not_replace_the_published_inode(self):
  with TemporaryDirectory() as temp:
   target=Path(temp)/'hash.rx3';blob=b'complete texture'*1000
   with ThreadPoolExecutor(max_workers=8) as pool:self.assertTrue(all(pool.map(lambda _:files.store_immutable(target,blob),range(24))))
   inode=target.stat().st_ino
   with patch.object(files.os,'replace',side_effect=AssertionError('immutable cache was replaced')):self.assertTrue(files.store_immutable(target,b'other bytes'))
   self.assertEqual(target.read_bytes(),blob);self.assertEqual(inode,target.stat().st_ino);self.assertEqual(list(Path(temp).glob('*.new')),[])
 def test_complete_directory_is_reused_without_touching_loaded_files(self):
  with TemporaryDirectory() as temp:
   root=Path(temp);winner=root/'cache';winner.mkdir();(winner/'assets.json').write_text('{}');source=root/'new';source.mkdir();(source/'assets.json').write_text('{"new":true}')
   with patch.object(files.os,'rename',side_effect=AssertionError('loaded cache was renamed')):files.publish_directory(source,winner)
   self.assertEqual((winner/'assets.json').read_text(),'{}');self.assertTrue(source.exists())
 @unittest.skipUnless(os.name=='nt','Windows sharing semantics')
 def test_cache_survives_real_fifa_style_open_handle(self):
  from ctypes import wintypes
  api=ctypes.WinDLL('kernel32',use_last_error=True);api.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE];api.CreateFileW.restype=wintypes.HANDLE;api.CloseHandle.argtypes=[wintypes.HANDLE]
  with TemporaryDirectory() as temp:
   target=Path(temp)/'cached.rx3';target.write_bytes(b'texture');alias=Path(temp)/'published.rx3';os.link(target,alias);replacement=Path(temp)/'replacement';replacement.write_bytes(b'new')
   # Cache validation also opens this exact path while another material
   # encoder may be finishing the same fingerprint.
   handle=api.CreateFileW(str(target),0x80000000,1,None,3,0,None);self.assertNotEqual(handle,ctypes.c_void_p(-1).value)
   try:
    with self.assertRaises(PermissionError):os.replace(replacement,target)
    self.assertTrue(files.store_immutable(target,b'texture'));self.assertEqual(target.read_bytes(),b'texture')
    # Direct creation of a fresh alias needs no rename/delete sharing.
    out=Path(temp)/'next-preview.rx3';os.link(target,out);self.assertEqual(out.read_bytes(),b'texture')
   finally:api.CloseHandle(handle)

if __name__=='__main__':unittest.main()
