import io,unittest
from unittest.mock import patch
from pathlib import Path
import tempfile
import numpy as np
from PIL import Image
import room_print_batches as prints
from room_visual_r68 import VERT,packed,read_mesh
from rx3 import Rx3

class PrintBatchesTests(unittest.TestCase):
 def test_full_squad_keeps_all_pixels_and_bounded_pages(self):
  items=[dict(image=Image.new('RGBA',(2048,512),(i,0,0,255))) for i in range(38)]
  pages=prints.pages(items)
  self.assertEqual([len(p) for p in pages],[16,16,6])
  for page in pages:
   for item,x,y in page:
    self.assertLessEqual(x+item['image'].width,4096);self.assertLessEqual(y+item['image'].height,4096)
   for i,(_,x,y) in enumerate(page):
    for _,ox,oy in page[:i]:self.assertTrue(x>=ox+2048 or ox>=x+2048 or y>=oy+512 or oy>=y+512)

 def test_transforms_preserve_world_position_normal_and_texture_cell(self):
  v=np.zeros(3,dtype=VERT);v['p']=[[0,0,0],[1,0,0],[0,1,0]];v['n']=packed([0,0,1]);v['g']=packed([1,0,0]);v['uv']=[[0,0],[1,0],[0,1]]
  m=np.array([[0,0,1,100010],[0,2,0,1080],[-3,0,0,500],[0,0,0,1]],dtype=float)
  out=prints.transformed(v,m.T.reshape(-1),(2048,512,2048,512),(4096,4096))
  np.testing.assert_allclose(out['p'],[[10,1080,500],[10,1080,497],[10,1082,500]])
  self.assertTrue((out['n']==packed([1,0,0])).all())
  self.assertTrue((out['uv'][:,0]>=.5).all() and (out['uv'][:,0]<=1).all())
  self.assertTrue((out['uv'][:,1]>=.125).all() and (out['uv'][:,1]<=.25).all())
  np.testing.assert_array_equal(v['p'],[[0,0,0],[1,0,0],[0,1,0]])

 def test_empty_and_oversize_atlas(self):
  self.assertEqual(prints.pages([]),[])
  with self.assertRaises(ValueError):prints.pages([dict(image=Image.new('RGBA',(4097,4)))])

 def test_installed_geometry_preserved_and_second_prepare_uses_cache(self):
  import portable_paths as portable
  template=portable.GAME/prints.PREFIX/'locker_support_r68.rx3'
  model=portable.GAME/prints.PREFIX/'print_surface.rx3'
  with tempfile.TemporaryDirectory() as temporary:
   game=Path(temporary);folder=game/prints.PREFIX;folder.mkdir(parents=True)
   (folder/template.name).write_bytes(template.read_bytes())
   m=np.eye(4);m[0,3]=100000;m[1,3]=1000
   items=[dict(image=Image.new('RGBA',(32,16),(255,0,0,255)),model='panel',matrix=m.T.reshape(-1).tolist())]
   calls=[]
   def add(*args):calls.append(args)
   def texture(image,path,name):path.write_bytes(b'cached texture')
   with patch.object(prints,'texture_package',side_effect=texture) as encode:
    for _ in range(2):prints.prepare(game,'plate',items,lambda _:model.read_bytes(),add,m.T.reshape(-1).tolist(),False)
    self.assertEqual(encode.call_count,1)
   self.assertEqual(calls[0],calls[1]);self.assertEqual(calls[0][0],'plate_batch_0')
   out=Rx3((game/calls[0][1]).read_bytes());old=Rx3(model.read_bytes())
   a,idx=read_mesh(out,0);b,ids=prints.mesh(old,0)
   self.assertEqual(len(idx),len(ids));np.testing.assert_allclose(a['p'],b['p']+[0,1000,0])

if __name__=='__main__':unittest.main()
