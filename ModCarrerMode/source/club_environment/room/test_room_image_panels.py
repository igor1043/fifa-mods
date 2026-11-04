"""Exercise the image path used by FIFA, including UV density and file edits."""
from pathlib import Path
import json,tempfile,unittest
from unittest.mock import patch
import numpy as np
from PIL import Image
from rx3 import Rx3,VERTEX,TEXTURE
from room_visual_r68 import read_mesh
import room_v3 as room
import room_appearance as appearance
import room_fascia as fascia
import room_image_panels as panels
import portable_paths

D=Path(__file__).resolve().parents[4]


class ImagePanelTests(unittest.TestCase):
    def test_wide_editable_art_keeps_detail_with_bounded_pixel_budget(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'wide.png';Image.new('RGBA',(4096,1024),'red').save(p)
            self.assertEqual(room.editable_image(p).size,(4096,1024))
            p=Path(folder)/'large.png';Image.new('RGBA',(4096,4096),'red').save(p)
            self.assertEqual(room.editable_image(p).size,(2048,2048))

    def test_board_image_keeps_scene_extent_and_balanced_sampling(self):
        import room_visual_r68
        quad=np.zeros(4,dtype=room_visual_r68.VERT)
        quad['p']=[[-117.5,1250,-512.55],[117.5,1250,-512.55],[117.5,1102,-512.55],[-117.5,1102,-512.55]]
        quad['uv']=[(0,0),(1,0),(1,1),(0,1)]
        w=4064;h=round(w*148/235)
        image=Image.new('RGBA',(w,h),(73,85,96,255));atlas,(v,ids)=panels.planar(image,quad)
        self.assertEqual(atlas.size,(4096,4096));self.assertLess(ids.max(),len(v))
        np.testing.assert_allclose(v['p'].min(axis=0),quad['p'].min(axis=0))
        np.testing.assert_allclose(v['p'].max(axis=0),quad['p'].max(axis=0))
        for cell in v.reshape(-1,4):
            pixel_size=np.ptp(cell['uv'].astype(float),axis=0)*atlas.size
            physical_size=[np.linalg.norm(cell['p'][1]-cell['p'][0]),np.linalg.norm(cell['p'][3]-cell['p'][0])]
            density=pixel_size/physical_size
            self.assertLess(max(density)/min(density),1.01)
        with self.assertRaises(ValueError):panels.planar(image,np.zeros(3,dtype=quad.dtype))

    def test_native_uv_density_matches_physical_panel_and_preserves_edges(self):
        groups=panels.geometry(room.fascia_specs(),45.)
        for key,center,width,normal in room.fascia_specs():
            count,size=panels.layout(width,45.)
            self.assertEqual(len(groups[key]),count)
            for v,ids in groups[key]:
                self.assertLess(ids.max(),len(v));self.assertTrue(np.isfinite(v['p']).all())
                uv=np.ptp(v['uv'].astype(float),axis=0)*size
                density=uv/np.array([width/count,45.])
                self.assertLess(max(density)/min(density),1.2)
            positions=np.concatenate([v['p'] for v,ids in groups[key]])
            axis=np.cross((0,1,0),normal)
            self.assertAlmostEqual(float(np.ptp(positions@axis)),width,places=3)
            im=Image.new('RGBA',(count*panels.INNER_WIDTH,panels.INNER_HEIGHT),(9,33,71,255))
            tile=panels.atlas(im,width,45.);self.assertEqual(tile.size,size)
            self.assertEqual(tile.getpixel((0,0)),(9,33,71,255))
            self.assertEqual(tile.getpixel((1023,count*256-1)),(9,33,71,255))

    def test_authored_png_is_entire_surface_and_changes_without_code_or_text(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);club=1043;p=root/appearance.ROOT/'custom'/str(club);p.mkdir(parents=True)
            image=p/'strip.png';Image.new('RGBA',(3072,256),(87,9,3,255)).save(image)
            (p/'profile.json').write_text(json.dumps({'assets':{'fascia_back_left':'strip.png'}}))
            spec={'panels':[{'mode':'image','asset_key':'fascia_back_left'}]}
            reject=lambda *a,**k:self.fail('Authored PNG must not generate text')
            self.assertTrue(appearance.has_custom(root,club))
            first=fascia.render(root,club,spec,0,3072,540,reject)
            self.assertEqual(first.getpixel((100,100)),(87,9,3,255))
            Image.new('RGBA',(3072,256),(3,81,127,255)).save(image)
            second=fascia.render(root,club,spec,0,3072,540,reject)
            self.assertEqual(second.getpixel((100,100)),(3,81,127,255))

    def test_all_custom_clubs_use_four_real_images_and_no_phrase_fields(self):
        profiles=list((D/appearance.ROOT/'custom').glob('*/profile.json'));self.assertGreaterEqual(len(profiles),20)
        for path in profiles:
            spec=json.loads(path.read_text(encoding='utf8'))
            if spec.get('surface_layout_revision')!=4:continue
            banner=spec['theme']['banner'];self.assertNotIn('lines',banner)
            self.assertEqual(len(banner['panels']),4)
            for panel in banner['panels']:
                self.assertEqual(panel['mode'],'image');self.assertNotIn('text',panel)
                source=appearance.asset(D,int(path.parent.name),panel['asset_key']);self.assertIsNotNone(source)

    def test_prepare_uses_original_material_full_mips_and_no_letter_meshes(self):
        runtime=portable_paths.GAME/'ModCarrerMode/runtime/club_environment/room/runtime'
        context=json.loads((runtime/'native_components_manifest_r46.json').read_text(encoding='utf8'))['context']
        import copy,struct
        calls=[]
        # Stock native inputs live in the installed game, not in the Git tree.
        with patch.object(room,'OLD',str(portable_paths.GAME/room.OLD)+'\\'),patch.object(appearance,'preferences',return_value={'style':'custom','finish':'dark','backs':'custom','trim':'primary','floor':'rubber','logo':'floor'}):
            room.prepare(copy.deepcopy(context),D,lambda *a,**k:calls.append((a,k)),[1,0,0,0,0,1,0,0,0,0,1,0,100000,0,0,1])
        images=[(a,k) for a,k in calls if a[0].startswith('v3_image_band_')]
        self.assertEqual(len(images),4)
        self.assertFalse(any(a[0].startswith(('v3_fascia_','v3_native_letters_')) for a,k in calls))
        for a,k in images:
            raw=Rx3((D/a[2]).read_bytes()).get(TEXTURE)[0]
            w,h,_,mips=struct.unpack_from('<4H',raw,8)
            self.assertEqual(w,1024);self.assertIn(h,(1024,2048));self.assertEqual(mips,max(w,h).bit_length())


if __name__=='__main__':unittest.main()
