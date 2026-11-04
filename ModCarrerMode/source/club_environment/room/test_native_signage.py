import json,tempfile,unittest
from pathlib import Path
import numpy as np
from rx3 import Rx3,VERTEX
from room_visual_r68 import read_mesh
import room_v3 as room
import room_native_signage as signs
import portable_paths

D=Path(__file__).resolve().parents[4]


class NativeSignageTests(unittest.TestCase):
    def test_all_twenty_club_titles_fit_native_mesh_limits(self):
        data=signs.alphabet(D);self.assertIsNotNone(data)
        for profile in (D/'ModCarrerMode/data/club_environment/current_dressing_room/custom').glob('*/profile.json'):
            spec=json.loads(profile.read_text(encoding='utf8'));club=int(profile.parent.name)
            if spec.get('surface_layout_revision')!=4:continue
            strings=spec['theme']['banner'].get('lines',[])+[spec['name'].upper()]
            for text in strings:
                for normal in ((0,0,1),(1,0,0),(-1,0,0)):
                    groups=signs.label(data,text,'#151719','#BF0010',club,[0,1309.5,0],540,normal,'text')
                    for parts in groups.values():
                        self.assertLess(sum(len(v) for v,i in parts),65536)
                        for vertices,ids in parts:
                            self.assertTrue(np.isfinite(vertices['p']).all());self.assertLess(ids.max(),len(vertices))
                            self.assertGreaterEqual(vertices['p'][:,1].min(),1287);self.assertLessEqual(vertices['p'][:,1].max(),1332)
                            p=vertices['p'][ids.reshape(-1,3)];area=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0])@np.array(normal)
                            self.assertTrue(np.all(area>=-.0001))

    def test_generated_asset_uses_native_geometry_and_flat_color_uv(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=root/signs.GLYPHS;p.parent.mkdir(parents=True);p.write_bytes((D/signs.GLYPHS).read_bytes())
            spec={'lines':['ISSO AQUI É FLAMENGO'],'base':'#151719','accent':'#BF0010'}
            model,bindings=signs.build(root,1043,spec,room.band_specs(),portable_paths.GAME/room.OLD/'locker_support_r68.rx3',room.PREFIX)
            self.assertTrue(model);self.assertEqual(len(bindings),2)
            rx=Rx3((root/model).read_bytes())
            for slot in range(len(rx.get(VERTEX))):
                v,i=read_mesh(rx,slot);self.assertTrue(np.all(v['uv']==.5))
                self.assertGreater(len(i),100)
            self.assertEqual(signs.build(root,1043,spec,room.band_specs(),portable_paths.GAME/room.OLD/'locker_support_r68.rx3',room.PREFIX),(model,bindings))

    def test_missing_glyph_catalog_keeps_bitmap_fallback(self):
        with tempfile.TemporaryDirectory() as folder:self.assertIsNone(signs.alphabet(folder))

if __name__=='__main__':unittest.main()
