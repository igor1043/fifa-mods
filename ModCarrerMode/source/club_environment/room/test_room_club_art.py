"""Catalog, Default/Custom isolation and non-mirrored corner image mapping."""
from pathlib import Path
import json,tempfile,unittest
import numpy as np
from PIL import Image
import room_appearance as appearance
import room_club_art as catalog
import room_hydration_r78 as hydration
import room_interior_r71 as interior
import room_v3 as room

D=Path(__file__).resolve().parents[4]


class ClubArtTests(unittest.TestCase):
    def test_current_catalog_resolves_area_and_respects_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/appearance.ROOT/'custom/1043';folder.mkdir(parents=True)
            Image.new('RGBA',(300,100),'red').save(folder/'hydration-wall.png')
            (folder/'profile.json').write_text(json.dumps({'assets':{'hydration_wall':'hydration-wall.png'}}))
            active=root/'ModCarrerMode/data/club_environment/room/active-version.txt';active.parent.mkdir(parents=True);active.write_text('3')
            self.assertEqual(hydration.source(root,1043),folder/'hydration-wall.png')
            self.assertIsNone(hydration.source(root,598))
            prefs=root/appearance.PREFERENCES/'1043.json';prefs.parent.mkdir(parents=True);prefs.write_text('{"style":"default"}')
            self.assertIsNone(hydration.source(root,1043))
            self.assertEqual(hydration.backdrop(root,1043).getpixel((0,0)),(255,255,255,255))
            self.assertEqual(catalog.paths(root,1043),[('hydration_wall',folder/'hydration-wall.png')])

    def test_catalog_image_edits_change_art_stamp_without_a_career(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/appearance.ROOT/'custom/1043';p.mkdir(parents=True)
            (p/'profile.json').write_text('{"assets":{"wall_mural":"wall-mural.png"}}')
            image=p/'wall-mural.png';Image.new('RGBA',(300,100),'red').save(image)
            before=interior.art_stamp(root,1043)
            Image.new('RGBA',(300,100),'blue').save(image)
            self.assertNotEqual(before,interior.art_stamp(root,1043))
            self.assertEqual(interior.mural_source(root,1043),image)

    def test_both_corner_faces_have_left_to_right_image_coordinates(self):
        for sign in (-1,1):
            points=[(sign*x,z) for x,z in ((675,-592),(832,-592),(832,-435),(748,-435),(675,-508))]
            vertices,ids=room.prism(points,1003,1287)
            for face in vertices[:len(points)*4].reshape(-1,4):
                raw=int(face['n'][0]);normal=np.array([(raw>>s)&1023 for s in (0,10,20)],dtype=float)
                normal=np.where(normal>=512,normal-1024,normal)/511
                tangent=np.cross((0,1,0),normal)
                horizontal=float(np.dot(face['p'][1]-face['p'][0],tangent))
                du=float(face['uv'][1,0]-face['uv'][0,0])
                self.assertGreater(horizontal*du,0)
            self.assertLess(ids.max(),len(vertices))

    def test_installed_catalog_uses_area_names_and_valid_assets(self):
        profiles=list((D/appearance.ROOT/'custom').glob('*/profile.json'));self.assertGreaterEqual(len(profiles),20)
        for profile in profiles:
            spec=json.loads(profile.read_text(encoding='utf8'))
            self.assertNotIn('prompts',spec.get('artwork',{}))
            for key,name in spec['assets'].items():
                self.assertNotEqual(name,'tribal.png')
                self.assertIsNotNone(appearance.asset(D,int(profile.parent.name),key),(profile,key,name))
        flame=appearance.custom_profile(D,1043)['assets']
        self.assertEqual(flame['hydration_wall'],'hydration-wall.png')
        self.assertEqual(flame['wall_mural'],'wall-mural.png')
        self.assertEqual(flame['corner'],'corner-panel.png')


if __name__=='__main__':unittest.main()
