"""Towel shape, cotton UVs and removal of the intrusive pale plate."""
import unittest
import numpy as np
from room_visual_r68 import join
import room_v3
import room_linen


class LinenTests(unittest.TestCase):
    def test_bay_has_no_pale_plate_and_backing_reaches_the_shelf(self):
        groups=room_v3.bay_groups();self.assertNotIn('light',groups)
        p=groups['niche'][0][0]['p']
        self.assertAlmostEqual(float(p[:,1].min()),46)
        self.assertAlmostEqual(float(p[:,1].max()),235)
        self.assertIn('safe',groups);self.assertIn('safe_metal',groups)

    def test_towel_is_rounded_layered_and_clear_of_seat_and_shirt(self):
        body,seam=room_linen.folded_towel();self.assertEqual(len(body),2)
        lo=[];hi=[]
        for v,idx in body:
            lo.append(v['p'].min(0));hi.append(v['p'].max(0))
            self.assertGreater(v['p'][:,1].min(),55)
            self.assertLess(v['p'][:,1].max(),61)
            self.assertLess(int(idx.max()),len(v))
            self.assertGreater(len(np.unique(v['n'])),10)
            self.assertGreater(np.ptp(v['uv'][:,0].astype(float)),1)
        self.assertGreater(lo[1][1],hi[0][1])
        self.assertGreater(seam[0][0]['p'][:,1].min(),hi[1][1]-.12)
        self.assertLess(np.concatenate([v['p'] for v,_ in body])[:,1].max(),120)

    def test_native_winding_agrees_with_packed_normals(self):
        body,seam=room_linen.folded_towel()
        for v,idx in body+seam:
            tri=idx.reshape(-1,3);p=v['p'][tri];bits=v['n'].astype(np.int64)
            normals=np.stack([(bits>>s)&1023 for s in (0,10,20)],axis=1)
            normals=np.where(normals>=512,normals-1024,normals)/511
            face=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0])
            self.assertTrue((np.einsum('ij,ij->i',face,normals[tri].mean(1))>=0).all())
        merged,_=join(body);self.assertLess(len(merged),2000)
        self.assertLess(sum(len(i)//3 for _,i in body+seam),1000)
        for p in seam[0][0]['p']:
            height,_=room_linen.top_surface(body[1],float(p[0]),float(p[2]))
            self.assertGreater(float(p[1])-height,.03)

    def test_textures_are_shared_repeatable_and_have_visible_weave(self):
        first=room_linen.fabric_image();second=room_linen.fabric_image()
        self.assertEqual(first.size,(512,512));self.assertEqual(first.tobytes(),second.tobytes())
        pixels=np.asarray(first);self.assertGreater(pixels[:,:,:3].std(),4)
        self.assertGreater(pixels[:,:,:3].min(),190)
        self.assertTrue((pixels[:,:,3]==255).all())
        hem=room_linen.seam_image();self.assertEqual(hem.size,(128,64))
        self.assertGreater(len(hem.getcolors()),1)


if __name__=='__main__':unittest.main()
