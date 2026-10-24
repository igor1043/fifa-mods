"""Real kit regression: cloth placement, native font and digit/name separation."""
import unittest
import numpy as np
from unittest.mock import patch
import portable_paths as portable
from rx3 import Rx3,read_model
from room_kit_print_r56 import kit_hotspots,name_model,number_models,name_stamp
from room_native_kit_rules_r46 import name_candidates

class KitPrint(unittest.TestCase):
    def test_native_hotspots_for_home_and_goalkeeper_kits(self):
        for club in (1043,1629,598):
            for typ in (0,2):
                with self.subTest(club=club,kit=typ):
                    rx=Rx3(portable.read_asset(f'data/sceneassets/kit/kit_{club}_{typ}_0.rx3'))
                    hotspots=kit_hotspots(rx)['jersey']
                    path,name_rect=name_model(club,typ,rx)
                    self.assertEqual(name_rect,list(hotspots['name']))
                    parts,_=read_model(Rx3(portable.read_asset(path)))
                    name_points=np.array(parts[0]['positions']).reshape(-1,3)
                    for slot,(path,rect) in number_models(club,typ,rx).items():
                        parts,_=read_model(Rx3(portable.read_asset(path)))
                        points=np.array(parts[0]['positions']).reshape(-1,3)
                        # On these original kits the name is above the number.
                        # Fixed Y=180 placed the number over the Grêmio name.
                        self.assertGreater(name_points[:,1].min(),points[:,1].max())
                        self.assertEqual((rect[1],rect[3]),(hotspots['numberback'][1],hotspots['numberback'][3]))
                        self.assertTrue(np.isfinite(points).all())

    def test_absent_hotspot_cannot_fall_back_to_a_fixed_shirt_decal(self):
        class Empty:
            def get(self,_):return []
        self.assertEqual(name_model(1,0,Empty()),(None,None))
        self.assertEqual(number_models(1,0,Empty()),{})

    def test_actual_native_font_fills_vertical_bounds_and_preserves_black(self):
        paths=name_candidates(1629,0,30,30,19)
        selected=None
        for path in paths:
            try:font=portable.read_asset(path);selected=path;break
            except FileNotFoundError:continue
        self.assertIsNotNone(selected)
        for name in ('PAVON','WAGNER LEONARDO','JOAO PEDRO DE OLIVEIRA'):
            stamp=name_stamp(name,font,[0,0,0],[.585,.352,.415,.327])
            box=stamp.getchannel('A').getbbox()
            self.assertEqual((box[1],box[3]),(0,stamp.height))
            self.assertLessEqual(box[2],stamp.width)
            colors=np.asarray(stamp)
            self.assertTrue((colors[:,:,:3][colors[:,:,3]>0]==0).all())

if __name__=='__main__':unittest.main(verbosity=2)
