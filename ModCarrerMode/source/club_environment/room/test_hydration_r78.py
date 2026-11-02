"""Native mesh, artwork and fallback regression checks for the hydration bay."""
from pathlib import Path
import hashlib,json,os,tempfile,unittest
import numpy as np
from PIL import Image
from rx3 import Rx3
from room_visual_r68 import read_mesh
import room_interior_r71 as prior
import room_hydration_r78 as hydration

REPO=Path(__file__).resolve().parents[4]
OUT=REPO/'code-release/hydration-r78-20261102'
BASE=Path(os.environ['SERVER16_GAME_ROOT'])/prior.PREFIX


class HydrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=json.loads((OUT/'built/interior_r78.json').read_text(encoding='utf8'))
        cls.rx=Rx3((OUT/'built/interior_r78.rx3').read_bytes())

    def test_supplied_art_is_the_original_file(self):
        reference=Path(r'C:\Users\igorv\AppData\Local\Temp\codex-clipboard-66a9a6f0-2d73-4a83-be08-64e2728a7d34.png')
        installed=hydration.source(REPO,1043)
        self.assertEqual(hashlib.sha256(reference.read_bytes()).digest(),hashlib.sha256(installed.read_bytes()).digest())
        with Image.open(installed) as im:self.assertEqual(im.size,(2172,724))

    def test_white_fallback_has_no_other_club_art(self):
        with tempfile.TemporaryDirectory() as tmp:
            im=hydration.backdrop(tmp,111046)
            self.assertEqual(im.getextrema(),((255,255),)*4)
            self.assertIsNone(hydration.source(tmp,1043))
            textures=hydration.material_images(dict(club=111046,colors=[(1,.8,0),(0,0,0)]),None,tmp)
            self.assertEqual(textures['hydration_header'].size,(2048,256))

    def test_art_plane_has_source_aspect_and_complete_uv(self):
        slot=next(i for i,b in enumerate(self.spec['bindings']) if b['material']=='hydration_wall')
        v,idx=read_mesh(self.rx,slot);span=np.ptp(v['p'],axis=0)
        self.assertAlmostEqual(float(span[0]/span[1]),3,places=4)
        np.testing.assert_array_equal(v['uv'].min(0),[0,0]);np.testing.assert_array_equal(v['uv'].max(0),[1,1])

    def test_all_native_buffers_are_finite_and_within_uint16(self):
        self.assertLess(len(self.spec['bindings']),64)
        for i,b in enumerate(self.spec['bindings']):
            v,idx=read_mesh(self.rx,i)
            self.assertGreater(len(idx),0,b['material']);self.assertLess(len(v),65536)
            self.assertLess(int(idx.max()),len(v));self.assertTrue(np.isfinite(v['p']).all());self.assertTrue(np.isfinite(v['uv']).all())

    def test_new_round_props_face_outward(self):
        v,idx=hydration.turned_lathe((0,0,0),[(0,4),(10,4)],24)
        tri=v['p'][idx.reshape(-1,3)];norm=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);center=tri.mean(1)
        self.assertTrue((np.sum(norm*center,axis=1)>0).all())

    def test_other_rooms_are_preserved_triangle_for_triangle(self):
        oldspec=json.loads((BASE/'interior_r77.json').read_text(encoding='utf8'));old=Rx3((BASE/'interior_r77.rx3').read_bytes())
        for i,b in enumerate(oldspec['bindings']):
            v,idx=read_mesh(old,i);tri=idx.reshape(-1,3);keep=~prior.within(v['p'][tri],hydration.CUT_LO,hydration.CUT_HI)
            expected=v[tri[keep]].tobytes()
            slot=next(j for j,e in enumerate(self.spec['bindings']) if e['material']==b['material'])
            nv,ni=read_mesh(self.rx,slot)
            self.assertEqual(nv[ni[:int(keep.sum())*3]].tobytes(),expected,b['material'])

    def test_fridge_bottles_and_aperture_are_not_occluded(self):
        self.assertEqual(self.spec['hydration']['bottles'],18)
        i=next(i for i,b in enumerate(self.spec['bindings']) if b['material']=='glass')
        v,idx=read_mesh(self.rx,i);tri=v['p'][idx.reshape(-1,3)]
        fridge=(tri[:,:,0].min(1)>=254)&(tri[:,:,0].max(1)<=334)&(tri[:,:,1].min(1)>=1098)
        self.assertTrue((np.ptp(tri[fridge,:,0],axis=1)<=2.01).all())
        for key in ('bottle','drink_amber','drink_red'):
            i=next(i for i,b in enumerate(self.spec['bindings']) if b['material']==key)
            v,idx=read_mesh(self.rx,i);points=v['p'][idx]
            self.assertGreater(np.count_nonzero((points[:,0]>260)&(points[:,0]<325)&(points[:,2]>1497)&(points[:,2]<1507)),1000)

    def test_moved_dispenser_and_collision_footprints(self):
        cooler=Rx3((OUT/'built/water_cooler_r78.rx3').read_bytes())
        v,idx=read_mesh(cooler,0);self.assertGreater(v['p'][:,0].min(),690);self.assertLess(v['p'][:,0].max(),753)
        objects=[o for o in self.spec['obstacles'] if o['name'].startswith('Hidratação /')]
        self.assertEqual(len(objects),3)
        for o in objects:self.assertTrue(all(a<b for a,b in zip(o['lo'],o['hi'])))


if __name__=='__main__':unittest.main()
