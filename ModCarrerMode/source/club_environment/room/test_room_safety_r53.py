import portable_paths as portable
import unittest,json,struct,sys
from pathlib import Path
from room_roster_r52 import roster_order,scene_catalog
from room_control_bridge_r52 import decode_requests
class Link:
 def __init__(self,n):self.n=n
 def value(self,key):return self.n
class Safety(unittest.TestCase):
 def test_incomplete_rosters_and_duplicates(self):
  for count in (0,1,2,10,11,20,34,35,40):
   players={i:object() for i in range(1,count+1)};links={i:Link(i) for i in players}
   order=roster_order(players,links,[0,-1,1,1,999999]);self.assertEqual(len(order),min(count,35));self.assertEqual(len(set(order)),len(order));self.assertTrue(all(i in players and i in links for i in order))
 def test_ui_command_scope_and_encodings(self):
  nonce='0123456789abcdef';command=f'S16ROOM1|22812|{nonce}|91|2|ENDROOM'
  for raw in (command.encode(),command.encode('utf-16-le')):self.assertIn((91,2),decode_requests(raw,22812,nonce))
  self.assertFalse(decode_requests(command.encode(),1,nonce));self.assertFalse(decode_requests(command.encode(),22812,'wrong'))
 def test_classic_ui_dds_headers(self):
  from formats import BigFile
  root=portable.ROOM;big=BigFile(root/'package/data/ui/game/screens/career/server16/dressingroom.big')
  for e in big.entries.values():
   raw=e.data
   if raw[:4]==b'DDS ' and raw[84:88]==b'DXT5' and struct.unpack_from('<I',raw,28)[0]<=1:
    h,w=struct.unpack_from('<II',raw,12);self.assertEqual(struct.unpack_from('<I',raw,20)[0],((w+3)//4)*((h+3)//4)*16);self.assertEqual(struct.unpack_from('<I',raw,88)[0],0)
if __name__=='__main__':unittest.main(verbosity=2)
