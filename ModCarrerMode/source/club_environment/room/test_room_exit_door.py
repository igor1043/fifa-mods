"""Exit replacement safety, exact native commands and per-career door finishes."""
import json, math, tempfile, unittest, struct
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
import room_exit_door as door
import room_appearance as art
import room_v3 as room
import portable_paths
from room_visual_r68 import read_mesh
from rx3 import Rx3, VERTEX
from test_room_personalization import open_personalization, commands


class DoorTests(unittest.TestCase):
    def test_door_moves_right_and_remains_closed_with_safety_hardware(self):
        groups=door.geometry(include_annex=False);self.assertEqual(len(groups['leaves']),2)
        for vertices, indices in groups['leaves']:
            self.assertEqual(len(indices),36)
            self.assertAlmostEqual(float(vertices['p'][:,1].min()),1001.5)
            self.assertTrue(np.isfinite(vertices['p']).all())
            self.assertTrue(((vertices['uv']>=0)&(vertices['uv']<=1)).all())
        centers=[v['p'].mean(0)[2] for v,_ in groups['leaves']]
        self.assertAlmostEqual(sum(centers)/2,1450-door.RIGHT_SHIFT_CM)
        self.assertGreater(len(groups['metal']),20)
        for vertices,_ in groups['metal']:
            def unpack(values):
                channels=np.stack([(values.astype(np.int64)>>(a*10))&1023 for a in range(3)],axis=1)
                return np.where(channels>=512,channels-1024,channels)/511.
            self.assertLess(np.abs((unpack(vertices['n'])*unpack(vertices['g'])).sum(1)).max(),.005)
        # All fixtures stay at the closed wall; nothing intrudes on the lockers.
        points=np.concatenate([v['p'] for parts in groups.values() for v,_ in parts])
        self.assertLess(points[:,0].max(),-834)
        self.assertLess(points[:,1].max(),1280)

    def test_only_old_fixture_triangles_are_removed(self):
        game=portable_paths.GAME
        source=game/room.OLD/'interior_r78.rx3'
        rx=Rx3(source.read_bytes())
        from room_visual_r68 import replace_mesh
        # Account for the installed V3 shell's 100 cm wider left wall.
        for slot in (0,1,3):
            v,idx=read_mesh(rx,slot);p=v['p']
            mask=(p[:,0]>=-752)&(p[:,0]<=-743)&(p[:,2]>=1365)&(p[:,2]<=1534)&(p[:,1]<=1280)
            v['p'][mask,0]-=100;replace_mesh(rx,slot,v,idx)
        before=[read_mesh(rx,i) for i in range(len(rx.get(VERTEX)))]
        self.assertEqual(door.replace_old_fixture(rx),[60,48])
        for slot,(v,idx) in enumerate(before):
            after,ids=read_mesh(rx,slot)
            if slot==3:
                self.assertEqual(len(ids),6);continue
            selected=idx.reshape(-1,3)
            if slot in (0,1):selected=selected[~door.old_door_triangles(v,idx)]
            self.assertEqual(sorted(v[t].tobytes() for t in selected),sorted(after[t].tobytes() for t in ids.reshape(-1,3)),slot)
        with self.assertRaises(ValueError):door.replace_old_fixture(rx)

    def test_all_eight_door_choices_round_trip_in_float32_without_overflow(self):
        import apt_vm
        text=apt_vm.text
        def fifa(value):
            if isinstance(value,(int,float)) and not isinstance(value,bool):value=struct.unpack('<f',struct.pack('<f',value))[0]
            return text(value)
        vm,s,calls,_=open_personalization()
        for finish in range(8):
            vm.invoke(s.get('OpenRoomSettings'),s)
            for i,row in enumerate(art.rows(portable_paths.GAME,1043)):
                s.set('settingIndex'+str(i),finish if row['key']=='door_finish' else len(row['options'])-1)
                s.set('appliedSettingIndex'+str(i),-1)
            with patch.object(apt_vm,'text',side_effect=fifa):vm.invoke(s.get('ApplyRoomSettings'),s)
            wire=commands(calls)[-1].split('|');code=int(wire[-2]);sequence=int(wire[3])
            decoded=art.decode_draft(portable_paths.GAME,1043,sequence,code)
            self.assertEqual(decoded['door_finish'],door.FINISHES[finish])
            self.assertEqual(decoded['table_base'],'secondary')
            self.assertLess(sequence%art.SEQUENCE_STRIDE,10_000_000)

    def test_mouse_and_keyboard_controller_can_reach_the_portas_group(self):
        from test_room_pointer import click
        vm,s,calls,_=open_personalization();click(vm,s,700,950)
        for _ in range(3):click(vm,s,1730,267)
        self.assertEqual(s.get('settingsGroup'),3)
        self.assertTrue(s.get('roomSettings').get('setting10').get('_visible'))
        click(vm,s,1720,352);self.assertEqual(s.get('settingIndex10'),1)
        click(vm,s,1500,780)
        wire=commands(calls)[-1].split('|')
        self.assertEqual(art.decode_draft(portable_paths.GAME,1043,int(wire[3]),int(wire[-2]))['door_finish'],'graphite')

    def test_custom_image_fallback_is_safe_and_scoped_to_club(self):
        ctx={'club':1043,'colors':[(.8,0,0),(0,0,0)]}
        with tempfile.TemporaryDirectory() as tmp:
            game=Path(tmp);baseline=door.finish_image(game,ctx,'black')
            self.assertEqual(baseline.tobytes(),door.finish_image(game,ctx,'custom').tobytes())
            folder=art.club_folder(game,1043);folder.mkdir(parents=True)
            Image.new('RGBA',(256,512),(100,50,20,255)).save(folder/'exit-door.png')
            self.assertEqual(door.finish_image(game,ctx,'custom').getpixel((50,50)),(100,50,20,255))
            self.assertNotEqual(door.finish_image(game,dict(ctx,club=1),'custom').getpixel((50,50)),(100,50,20,255))
            (folder/'profile.json').write_text(json.dumps({'assets':{'exit_door':'../../escape.png'}}))
            self.assertIsNone(art.asset(game,1043,'exit_door'))

    def test_save_is_atomic_per_career_and_legacy_command_preserves_the_door(self):
        with tempfile.TemporaryDirectory() as tmp:
            game=Path(tmp);r=game/'ModCarrerMode/runtime/club_environment/room/runtime';r.mkdir(parents=True)
            snap=game/'ModCarrerMode/runtime/career_fce_snapshot.json'
            snap.write_text(json.dumps(dict(pid=42,club=1043,savePath=r'C:\Careers\one\DATA')))
            (r/'room_control_scope.txt').write_text('S16ROOMSCOPE 1 42 1043 nonce')
            wire=f'S16ROOM 1 42 1043 nonce 10000000 {art.DOOR_APPLY_BASE+5}'
            self.assertTrue(art.save_command(game,42,wire));self.assertFalse(art.save_command(game,42,wire))
            self.assertEqual(art.preferences(game,1043)['door_finish'],'primary')
            self.assertTrue(art.save_command(game,42,'S16ROOM 1 42 1043 nonce 20000002 121'))
            self.assertEqual(art.preferences(game,1043)['door_finish'],'primary')
            self.assertFalse(art.save_command(game,42,'S16ROOM 1 42 1043 nonce 30000000 188'))
            snap.write_text(json.dumps(dict(pid=42,club=1043,savePath=r'C:\Careers\two\DATA')))
            self.assertEqual(art.preferences(game,1043)['door_finish'],'black')


if __name__=='__main__':unittest.main()
