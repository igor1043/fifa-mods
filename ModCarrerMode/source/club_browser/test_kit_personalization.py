"""Regression: classic kit rows must not override the active kit's font."""
import unittest
from unittest.mock import patch
import numpy as np
from PIL import ImageFont
from roster_data import current_kits
from kit_personalization import surface
import kit_personalization as k

class KitTests(unittest.TestCase):
 def test_current_year_is_independent_of_database_order(self):
  current=dict(teamtechid=1043,teamkittypetechid=0,year=0,numberfonttype=201,numbercolor=7)
  classic=dict(current,year=1989,numberfonttype=248,numbercolor=13)
  other=dict(current,teamtechid=1,numberfonttype=225)
  for rows in ([current,classic,other],[classic,other,current]):
   self.assertEqual(current_kits(rows,1043),{0:current})
  self.assertEqual(current_kits([classic],1043),{})
  with self.assertRaises(ValueError):current_kits([current,dict(current,numberfonttype=8)],1043)
  first=dict(current,teamkitid=1685);later=dict(current,teamkitid=2607,numberfonttype=248)
  self.assertEqual(current_kits([later,first],1043),{0:first})

 def test_decals_keep_original_mesh_and_skeleton_weights(self):
  dtype=np.dtype([('p','<f4',3),('n','<f4',3),('uv','<f4',2),('j','<u2',8),('w','u1',8)])
  v=np.zeros(4,dtype=dtype);v['p']=[[0,0,0],[1,0,0],[1,1,0],[0,1,0]];v['uv']=[[0,0],[1,0],[1,1],[0,1]];v['n']=[0,0,1];v['j'][:,0]=7;v['w'][:,0]=255
  source=dict(v=v,idx=np.array([0,1,2,0,2,3],dtype='<u4'),skinned=True);before=v.tobytes()
  for rect in ((.2,.2,.8,.8),(.8,.8,.2,.2)):
   out=surface(source,rect,3,'number');self.assertEqual(v.tobytes(),before);self.assertTrue(out['skinned']);self.assertEqual(out['texture'],3)
   self.assertTrue((out['v']['w'][:,0]==255).all());self.assertTrue((out['v']['j'][:,0]==7).all());self.assertTrue(np.isfinite(out['v']['p']).all());self.assertLess(out['idx'].max(),len(out['v']))

 def test_zero_area_hotspots_never_reach_font_or_logarithm(self):
  # Actual name hotspot from both Novorizontino kits (130045), including
  # Jordi's goalkeeper shirt. Zero U width disables this native print area.
  collapsed=(0.,.4297800064086914,0.,.3884199857711792)
  for rect in (collapsed,(.2,.4,.6,.4),(0,0,0,0),(0,0,float('nan'),1),
               (0,0,1,float('inf')),None,(0,0,1),(0,0,'bad',1)):
   with self.subTest(rect=rect):
    self.assertFalse(k.printable_rect(rect))
    self.assertIsNone(k.stamp('JORDI',b'not a font',[255,255,255],rect))
    with self.assertRaises(ValueError):k.surface({},rect,0,'name')

 def test_regular_and_mirrored_name_rects_keep_the_same_print(self):
  font=ImageFont.load_default()
  with patch.object(k.ImageFont,'truetype',return_value=font):
   normal=k.stamp('PLAYER',b'font',[255,255,255],(.2,.2,.8,.3))
   mirrored=k.stamp('PLAYER',b'font',[255,255,255],(.8,.3,.2,.2))
  self.assertEqual(normal.size,mirrored.size)
  self.assertEqual(normal.tobytes(),mirrored.tobytes())

 def test_disabled_or_unmapped_print_does_not_discard_the_player(self):
  dtype=np.dtype([('p','<f4',3),('n','<f4',3),('uv','<f4',2),('j','<u2',8),('w','u1',8)])
  v=np.zeros(4,dtype=dtype);v['p']=[[0,0,0],[1,0,0],[1,1,0],[0,1,0]];v['uv']=[[0,0],[1,0],[1,1],[0,1]];v['n']=[0,0,1];v['w'][:,0]=255
  part=dict(asset='data/sceneassets/jersey/jersey_0.rx3',texture=0,v=v,idx=np.array([0,1,2,0,2,3],dtype='<u4'),skinned=True)
  rig=dict(parts=[part],textures=[(1,1,3,b'\xff'*4)]);before=v.tobytes()
  class Digits:
   def names(self):return [(k.TEXTURE,'digit_'+str(i)) for i in range(10)]
  def read(path):
   if '/kit/' in path:return b'kit'
   if path=='name-font':return b'font'
   if '/kitnumbers/' in path:return b'digits'
   raise FileNotFoundError(path)
  cases=[((0.,.4297800064086914,0.,.3884199857711792),(.8,.4,.2,.2),False,True),
         ((.2,.2,.8,.3),(.2,.4,.2,.6),True,False),
         ((0.,0.,0.,0.),(0.,0.,0.,0.),False,False),
         ((1.2,1.2,1.8,1.4),(.2,.4,.8,.6),False,True)]
  font=ImageFont.load_default()
  for club in (130045,1043,567):
   for name_rect,number_rect,has_name,has_number in cases:
    for position in ('GOL','ATA'):
     with self.subTest(club=club,position=position,name_rect=name_rect,number_rect=number_rect):
      with patch.object(k,'Rx3',return_value=object()),patch.object(k,'hotspots',return_value={'jersey':{'name':name_rect,'numberback':number_rect}}),patch.object(k,'number_rx3',return_value=Digits()),patch.object(k,'texture_layout'),patch.object(k,'texture_record',return_value=(1,1,3,b'\xff'*4)),patch('room_native_kit_rules_r46.name_candidates',return_value=['name-font']),patch.object(k.ImageFont,'truetype',return_value=font):
       out,report=k.personalize(rig,dict(club=club,position=position,league=7,name='Jordi',number=93),read)
      self.assertEqual(report['name'],has_name);self.assertEqual(report['number'],has_number)
      self.assertTrue(report['skipped_prints']);self.assertIs(out['parts'][0],part)
      self.assertEqual(v.tobytes(),before);self.assertEqual(len(rig['parts']),1);self.assertEqual(len(rig['textures']),1)
      self.assertEqual(out['textures'][0],rig['textures'][0])
      self.assertEqual(len(out['parts']),1+int(has_name)+2*int(has_number))

if __name__=='__main__':unittest.main()
