import unittest,tempfile,json,ctypes
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import room_control_bridge_r52 as room

class RoomCommandTests(unittest.TestCase):
 def test_scene_request_is_found_in_heap_larger_than_256mb_and_scoped(self):
  pid=123;nonce='0123456789abcdef';base=0x10000000;found_at=base+64*1024**2
  message=f'S16ROOM1|{pid}|{nonce}|12|3|ENDROOM'.encode()
  class Query:
   def __call__(self,handle,address,out,size):
    if address.value and address.value>=base+1024**3:return 0
    row=ctypes.cast(out,ctypes.POINTER(room.Region))[0]
    row.base=base;row.size=1024**3;row.state=0x1000;row.type=0x20000;row.protect=4;return size
  reads=[]
  def read(at,size):
   if at==0x1000:return room.PAGE.encode()+b'\0'
   reads.append((at,size))
   return message if at<=found_at<at+size else b''
  memory=SimpleNamespace(kernel32=SimpleNamespace(OpenProcess=lambda *args:1),_get_base_address=lambda _:0x140000000,read_int64=lambda _:0x1000,read_process_memory=read,close=lambda:None)
  kernel=SimpleNamespace(VirtualQueryEx=Query())
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'runtime').mkdir();(root/'runtime/room_control_scope.json').write_text(json.dumps(dict(pid=pid,club=1629,nonce=nonce,scenes=list(range(10)))))
   with patch.object(room,'ROOT',root),patch('server16_py.memory_access.Memory',return_value=memory),patch('psutil.Process',return_value=SimpleNamespace(exe=lambda:'fifa16.exe')),patch('psutil.pid_exists',side_effect=[True,True,False]),patch.object(room.C,'WinDLL',return_value=kernel),patch.object(room.time,'sleep'),patch.object(room.time,'monotonic',return_value=20):
    room.run(pid)
   text=(root/'runtime/room_camera_command.txt').read_text()
   self.assertEqual(text,f'S16ROOM 1 {pid} 1629 {nonce} 12 3\n')
   self.assertLessEqual(max(size for at,size in reads),512*1024+256)

if __name__=='__main__':unittest.main()
