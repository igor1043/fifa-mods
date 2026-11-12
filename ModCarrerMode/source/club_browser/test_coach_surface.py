"""Coach-only hair masks and material separation preserve body and players."""
import unittest,copy
import numpy as np
from PIL import Image
from coach_surface import hair_matte,prepare,manager

class CoachSurface(unittest.TestCase):
 def test_supplied_amorim_and_farke_cutouts_survive_material_preparation(self):
  a=np.full((120,120,4),[60,45,30,255],dtype='u1');a[100:,40:68,3]=0
  v=np.zeros(3,dtype=[('p','f4',3),('n','f4',3),('uv','f4',2)]);v['p'][:,1]=170;v['n']=[0,0,1];v['uv']=[[.34,.84],[.99,.84],[.34,.99]]
  for source in [190226,190236]:
   part={'v':v,'idx':np.arange(3,dtype='u4'),'texture':0,'asset':f'data/sceneassets/slc/specificmanager_{source}_0_0.rx3','blend':0,'alpha':1,'coeff':-1}
   rig={'id':100000999,'bones':[{}]*31,'parts':[part],'textures':[(120,120,3,a.tobytes())]};out,report=prepare(rig)
   self.assertTrue(report['hairMasks'][0]['sourceContainsAuthoredAlpha']);self.assertFalse(report['hairMasks'][0]['approximateMask'])
   rgba=np.frombuffer(out['textures'][out['parts'][0]['texture']][3],dtype='u1').reshape(120,120,4);np.testing.assert_array_equal(rgba[:,:,3],a[:,:,3])
 def test_new_native_id_and_authored_hair_alpha_are_preserved(self):
  self.assertTrue(manager({'id':100000999,'bones':[{}]*31,'parts':[{'asset':'data/sceneassets/manager_market/211/model_0.rx3'}]}))
  a=np.full((120,120,4),255,dtype='u1');a[100:,45:65,3]=0;a[20:30,20:30,3]=0
  image,report=hair_matte(Image.fromarray(a),preserve_authored=True);np.testing.assert_array_equal(image[100:,40:,3],a[100:,40:,3]);self.assertTrue(report['sourceContainsAuthoredAlpha']);self.assertFalse(report['approximateMask']);self.assertTrue(np.all(image[:100,:,3]==255))
 def test_alpha_is_restricted_to_hair_strip(self):
  a=np.full((120,120,4),[150,150,150,255],dtype='u1');a[102:110,45:52,:3]=20
  image,report=hair_matte(Image.fromarray(a));self.assertTrue(report['nonHairAlphaOpaque']);self.assertTrue(np.all(image[:100,:,3]==255));self.assertTrue(np.all(image[100:,:40,3]==255));self.assertGreater(np.count_nonzero(image[100:,40:,3]<255),0)
 def test_noncoach_is_unchanged(self):
  rig={'id':1234,'bones':[{}]*31};out,report=prepare(rig);self.assertIs(out,rig);self.assertIsNone(report)
 def test_compact_rig_and_audited_id_required(self):
  self.assertTrue(manager({'id':100001043,'bones':[{}]*31}));self.assertFalse(manager({'id':100001043,'bones':[{}]*43}));self.assertFalse(manager({'id':100000001,'bones':[{}]*31}))
 def test_registered_career_coach_keeps_surface_on_another_club(self):
  rig={'id':100000001,'bones':[{}]*31,'parts':[{'asset':'data/sceneassets/slc/specificmanager_14_0_0.rx3'}]};self.assertTrue(manager(rig));rig['bones']=[{}]*400;self.assertFalse(manager(rig));rig['bones']=[{}]*31;rig['id']=1234;self.assertFalse(manager(rig))
 def test_alpha_does_not_change_color(self):
  a=np.random.default_rng(10).integers(0,256,(120,120,4),dtype='u1');a[:,:,3]=255;image,_=hair_matte(Image.fromarray(a));np.testing.assert_array_equal(a[:,:,:3],image[:,:,:3])
 def test_dark_and_gray_hair_keep_dense_roots_and_cut_strand_tips(self):
  masks=[]
  for shade in [0,20,150,255]:
   a=np.full((600,600,4),[shade,shade,shade,255],dtype='u1');image,report=hair_matte(Image.fromarray(a));masks.append(image[:,:,3]);self.assertTrue(report['denseRoots']);self.assertGreater(np.mean(image[501:510,205:595,3]>230),.4);self.assertGreater(np.mean(image[580:599,205:595,3]<32),.5)
  for mask in masks[1:]:np.testing.assert_array_equal(mask,masks[0])
 def test_color_key_removes_flat_background_and_retains_dark_and_light_fibers(self):
  a=np.full((120,120,4),[95,80,65,255],dtype='u1');a[101:116,50:53,:3]=20;a[101:116,60:63,:3]=200
  box=[(np.array([1/3,5/6]),np.array([1,1]))];image,_=hair_matte(Image.fromarray(a),box,'color-key');self.assertLess(image[110,90,3],32);self.assertGreater(image[110,51,3],200);self.assertGreater(image[110,61,3],200)
 def test_reverse_hair_faces_have_independent_opposite_normals(self):
  v=np.zeros(6,dtype=[('p','f4',3),('n','f4',3),('uv','f4',2)]);v['p'][:,1]=170;v['n']=[0,0,1];v['uv'][:3]=[[.4,.85],[.45,.85],[.4,.9]];v['uv'][3:]=[[.1,.1],[.2,.1],[.1,.2]]
  part={'v':v,'idx':np.arange(6,dtype='u4'),'texture':0,'asset':'coach/body','blend':0,'alpha':1,'coeff':-1};rig={'id':100000383,'bones':[{}]*31,'parts':[part],'textures':[(120,120,3,bytes([20,20,20,255])*120*120)]};out,_=prepare(rig);body,hair=out['parts'];np.testing.assert_array_equal(body['v'],v[3:]);np.testing.assert_array_equal(hair['v']['n'][3:],-hair['v']['n'][:3]);np.testing.assert_array_equal(hair['idx'],[0,1,2,3,5,4]);np.testing.assert_array_equal(rig['parts'][0]['v'],v)

if __name__=='__main__':unittest.main()
