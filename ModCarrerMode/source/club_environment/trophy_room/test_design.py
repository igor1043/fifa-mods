"""Safety checks for editable wall art and the shared museum furniture."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
from . import assets,geometry


class MuseumDesignTests(unittest.TestCase):
    def test_floor_skirting_does_not_overlay_the_identity_wall(self):
        doc=geometry.build();mural=next(p for p in doc['parts'] if p['material']=='identity')
        lo=np.min(mural['positions'],axis=0);hi=np.max(mural['positions'],axis=0)
        for part in doc['parts']:
            if 'skirting' not in part['name'].lower():continue
            p=np.asarray(part['positions']);lower=p.min(axis=0);upper=p.max(axis=0)
            if lower[2]<=lo[2]<=upper[2]:
                self.assertTrue(upper[0]<lo[0] or lower[0]>hi[0])

    def test_wall_and_texture_have_the_same_ratio_and_stay_inside_room(self):
        wall=next(p for p in geometry.build()['parts'] if p['material']=='identity')
        p=np.asarray(wall['positions']);span=np.ptp(p,axis=0)
        self.assertAlmostEqual(span[0]/span[1],geometry.IDENTITY_SIZE[0]/geometry.IDENTITY_SIZE[1])
        self.assertTrue((p[:,1]>=0).all() and (p[:,1]<=geometry.HEIGHT).all())
        self.assertLess(span[0],geometry.WIDTH)

    def test_legacy_portrait_custom_art_is_not_stretched_or_cropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'ModCarrerMode/data/trophy_room/custom/1043/identity-wall.png'
            file.parent.mkdir(parents=True);Image.new('RGBA',(300,600),'red').save(file)
            image=assets.identity_image(tmp,dict(club=1043),True)
            a=np.asarray(image);red=(a[:,:,0]==255)&(a[:,:,1]==0)&(a[:,:,2]==0)
            y,x=np.where(red)
            self.assertEqual(image.size,geometry.IDENTITY_SIZE)
            self.assertAlmostEqual((x.max()-x.min()+1)/(y.max()-y.min()+1),.5)

    def test_mural_fits_entirely_between_the_two_display_cases(self):
        doc=geometry.build();wall=next(p for p in doc['parts'] if p['material']=='identity')
        artwork=np.asarray(wall['positions'])
        glass=[np.asarray(p['positions']) for p in doc['parts'] if p['material']=='glass']
        left=max(p[:,0].max() for p in glass if p[:,0].mean()<0)
        right=min(p[:,0].min() for p in glass if p[:,0].mean()>0)
        self.assertGreater(artwork[:,0].min(),left+10)
        self.assertLess(artwork[:,0].max(),right-10)

    def test_missing_custom_uses_the_current_clubs_crest(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(assets,'crest',return_value=Image.new('RGBA',(100,200),'blue')) as crest:
            image=assets.identity_image(tmp,dict(club=2,name='Other club',colors=[(1,2,3)]),True)
            self.assertEqual(image.size,geometry.IDENTITY_SIZE);self.assertEqual(crest.call_args.args[1],2)

    def test_bench_collision_covers_every_cushion_and_door_stays_closed(self):
        doc=geometry.build();cushions=[p for p in doc['parts'] if p['name'].startswith('Bench cushion ')]
        self.assertEqual(len(cushions),6)
        obstacle=next(o for o in doc['obstacles'] if o['lo']==[-44,0,9])
        for part in cushions:
            p=np.asarray(part['positions']);self.assertTrue((p>=obstacle['lo']).all() and (p<=obstacle['hi']).all())
        leaves=[p for p in doc['parts'] if p['material']=='door'];self.assertEqual(len(leaves),2)
        p=np.concatenate([np.asarray(part['positions']) for part in leaves])
        self.assertGreater(p[:,2].min(),730);self.assertLess(p[:,2].max(),750)
        self.assertTrue(any(p['name'].startswith('Exit door metal') for p in doc['parts']))

    def test_furniture_does_not_intersect_the_display_slots(self):
        doc=geometry.build();self.assertEqual(len(doc['slots']),30)
        for part in doc['parts']:
            if part['name'].startswith(('Bench','Museum bench','Exit door','Closed exit')):
                p=np.asarray(part['positions']);self.assertLess(np.abs(p[:,0]).max(),390)

    def test_cushion_caps_and_sides_have_no_collapsed_triangles_or_uvs(self):
        for part in geometry.build()['parts']:
            if not part['name'].startswith('Bench cushion '):continue
            p=np.asarray(part['positions']);uv=np.asarray(part['uvs']);idx=np.asarray(part['indices']).reshape(-1,3)
            area=np.linalg.norm(np.cross(p[idx[:,1]]-p[idx[:,0]],p[idx[:,2]]-p[idx[:,0]]),axis=1)
            u,v=uv[idx[:,1]]-uv[idx[:,0]],uv[idx[:,2]]-uv[idx[:,0]]
            self.assertTrue((area>1e-7).all())
            self.assertTrue((np.abs(u[:,0]*v[:,1]-u[:,1]*v[:,0])>1e-8).all())


if __name__=='__main__':unittest.main()
