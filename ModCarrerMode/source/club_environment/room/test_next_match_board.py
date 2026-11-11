"""Approved native geometry encloses the full dynamic image without covering it."""
from pathlib import Path
import hashlib,json,tempfile,unittest
from unittest.mock import patch
import numpy as np
import room_next_match_board as board
import room_v3
import portable_paths
from rx3 import Rx3,VERTEX,TEXTURE
from room_visual_r68 import read_mesh

DEV=Path(__file__).resolve().parents[4]


class NextMatchBoardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.groups,cls.palette,cls.spec=board.geometry(DEV)

    def test_complete_content_is_inside_backing_and_frame(self):
        white=np.concatenate([v['p'] for v,_ in self.groups['white']])
        lo,hi=white.min(0),white.max(0)
        self.assertLess(lo[0],board.DISPLAY_LO[0]);self.assertGreater(hi[0],board.DISPLAY_HI[0])
        self.assertLess(lo[1],board.DISPLAY_LO[1]);self.assertGreater(hi[1],board.DISPLAY_HI[1])
        self.assertLess(hi[2],board.DISPLAY_LO[2])
        self.assertEqual(self.spec['dynamic_image'],dict(lo=board.DISPLAY_LO.tolist(),hi=board.DISPLAY_HI.tolist()))

    def test_frame_tray_and_details_never_cover_dynamic_content(self):
        for material,parts in self.groups.items():
            for vertices,indices in parts:
                p=vertices['p'][indices.reshape(-1,3)];lo=p.min(1);hi=p.max(1)
                in_front=hi[:,2]>board.DISPLAY_LO[2]+.02
                overlaps=(hi[:,0]>board.DISPLAY_LO[0]+.02)&(lo[:,0]<board.DISPLAY_HI[0]-.02)&(hi[:,1]>board.DISPLAY_LO[1]+.02)&(lo[:,1]<board.DISPLAY_HI[1]-.02)
                self.assertFalse((in_front&overlaps).any(),material)

    def test_native_buffers_fit_existing_limits_and_scene_space(self):
        total_triangles=0
        for material,parts in self.groups.items():
            for vertices,indices in parts:
                self.assertLess(len(vertices),60000)
                self.assertTrue(np.isfinite(vertices['p']).all())
                self.assertTrue(np.isfinite(vertices['uv']).all())
                self.assertLess(indices.max(),len(vertices))
                total_triangles+=len(indices)//3
        self.assertLess(total_triangles,5000)
        self.assertEqual(len(self.groups),5)

    def test_only_three_legacy_parts_are_replaced_and_old_installs_still_work(self):
        manifest={'next_match_board':{'model':'test.rx3'}}
        for key in board.LEGACY_KEYS:self.assertTrue(board.replaces(key,manifest))
        for key in ('role_board_23','role_floor_2','role_ceiling_3','jersey_0','v3_bay_wood','coach_dark'):
            self.assertFalse(board.replaces(key,manifest))
        for key in board.LEGACY_KEYS:self.assertFalse(board.replaces(key,{}))

    def test_native_package_rebuild_is_deterministic_and_texture_has_mips(self):
        with tempfile.TemporaryDirectory() as tmp:
            first=board.stage(DEV,Path(tmp)/'one');second=board.stage(DEV,Path(tmp)/'two')
            self.assertEqual(first,second)
            model=Rx3((Path(tmp)/'one'/first['model']).read_bytes())
            self.assertEqual(len(model.get(VERTEX)),5)
            for slot in range(5):
                vertices,indices=read_mesh(model,slot);self.assertLess(indices.max(),len(vertices))
            import struct
            raw=Rx3((Path(tmp)/'one'/first['texture']).read_bytes()).get(TEXTURE)[0]
            w,h,_,mips=struct.unpack_from('<4H',raw,8)
            self.assertEqual((w,h,mips),(512,512,10))

    def test_components_use_existing_identity_and_leave_dynamic_image_separate(self):
        manifest={'next_match_board':dict(model='frame.rx3',texture='palette.rx3',
                    bindings=[dict(material=k,submesh=f'room_part_{i+1}') for i,k in enumerate(self.groups)])}
        calls=[];identity=[1,0,0,0,0,1,0,0,0,0,1,0,100000,0,0,1]
        board.prepare(manifest,lambda *a,**kw:calls.append((a,kw)),identity)
        self.assertEqual(len(calls),5)
        self.assertTrue(all(a[4] is identity for a,_ in calls))
        self.assertTrue(all(a[0].startswith('v3_next_match_board_') for a,_ in calls))
        self.assertFalse(any(a[0]=='role_board_23' for a,_ in calls))
        calls.clear();board.prepare({},lambda *a,**kw:calls.append(a),identity);self.assertFalse(calls)


if __name__=='__main__':unittest.main()
