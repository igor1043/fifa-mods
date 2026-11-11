"""Table surfaces, grouped navigation and exact persistence of all ten choices."""
import json,math,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
import room_appearance as art
import room_table as table
import room_v3 as room
import portable_paths
from room_visual_r68 import read_mesh
from rx3 import Rx3
from test_room_personalization import open_personalization,commands


class TableTests(unittest.TestCase):
    def test_split_preserves_all_original_triangles_and_every_attribute(self):
        game=portable_paths.GAME;m=room.build_manifest(str(game))
        model=Rx3((game/room.PREFIX/m['model_files']['furniture_wood.rx3']).read_bytes())
        original=[read_mesh(model,i) for i in range(len(m['furniture_bindings']))]
        result=table.split(original)
        def triangles(parts):return sorted(v[i].tobytes() for v,idx in parts for i in idx.reshape(-1,3))
        self.assertEqual(triangles(original),triangles(result['top']+result['base']))
        self.assertTrue(all(v['p'][:,1].min()>=table.TOP_Y-.001 for v,_ in result['top']))
        self.assertTrue(any(v['p'][:,1].min()<1010 for v,_ in result['base']))

    def test_top_and_base_finishes_do_not_affect_each_other(self):
        context={'club':1043,'colors':[(.8,0,0),(0,0,0)]}
        self.assertEqual(table.image(portable_paths.GAME,context,'base','black').getpixel((0,0)),(25,28,30,255))
        self.assertEqual(table.image(portable_paths.GAME,context,'base','white').getpixel((0,0)),(235,236,233,255))
        self.assertEqual(table.image(portable_paths.GAME,context,'top','primary').getpixel((0,0)),(204,12,12,255))
        default=table.image(portable_paths.GAME,context,'top','default')
        original=room.editable_image(portable_paths.GAME/art.ROOT/'generic/materials/oak_light.png')
        self.assertEqual(default.tobytes(),original.tobytes())

    def test_all_choices_round_trip_without_float32_loss(self):
        vm,s,calls,_=open_personalization();vm.invoke(s.get('OpenRoomSettings'),s)
        rows=art.rows(portable_paths.GAME,1043);chosen=[];factor=1;packed=0
        for i,row in enumerate(rows[:art.PACKED_ROWS]):
            index=len(row['options'])-1;chosen.append(index);s.set('settingIndex'+str(i),index);s.set('appliedSettingIndex'+str(i),-1)
            packed+=index*factor;factor*=len(row['options'])
        self.assertLess(packed,2**24);self.assertLess(packed,art.SEQUENCE_STRIDE)
        import apt_vm,struct
        original_text=apt_vm.text
        def text(value):
            if isinstance(value,(int,float)) and not isinstance(value,bool):value=struct.unpack('<f',struct.pack('<f',value))[0]
            return original_text(value)
        with patch.object(apt_vm,'text',side_effect=text):vm.invoke(s.get('ApplyRoomSettings'),s)
        wire=commands(calls)[-1].split('|');self.assertEqual(wire[-2],str(art.DOOR_APPLY_BASE))
        decoded=art.decode_draft(portable_paths.GAME,1043,int(wire[3]),int(wire[-2]))
        self.assertEqual(decoded['table_top'],'custom');self.assertEqual(decoded['table_base'],'secondary')

    def test_group_switch_preserves_draft_and_shows_only_its_own_rows(self):
        vm,s,calls,_=open_personalization();vm.invoke(s.get('OpenRoomSettings'),s)
        self.assertEqual(s.get('settingsGroup'),0)
        vm.invoke(s.get('ShiftRoomSetting'),s,[1,1]);draft=s.get('settingIndex1')
        vm.invoke(s.get('ShiftSettingsGroup'),s,[1]);self.assertEqual(s.get('settingsGroup'),1)
        visible=[i for i in range(len(art.CATALOG)) if s.get('roomSettings').get('setting'+str(i)).get('_visible')]
        self.assertEqual(visible,[8,9]);self.assertFalse(s.get('roomSettings').get('scrollTrack').get('_visible'))
        vm.invoke(s.get('ShiftRoomSetting'),s,[8,5]);vm.invoke(s.get('ShiftRoomSetting'),s,[9,1])
        vm.invoke(s.get('ShiftSettingsGroup'),s,[-1]);self.assertEqual(s.get('settingIndex1'),draft)
        self.assertEqual(s.get('settingIndex8'),5);self.assertEqual(s.get('settingIndex9'),1)
        vm.invoke(s.get('ApplyRoomSettings'),s)
        wire=commands(calls)[-1].split('|');decoded=art.decode_draft(portable_paths.GAME,1043,int(wire[3]),int(wire[-2]))
        self.assertEqual((decoded['table_top'],decoded['table_base']),('primary','black'))

    def test_legacy_packet_preserves_new_table_preferences(self):
        with tempfile.TemporaryDirectory() as tmp:
            game=Path(tmp);r=game/'ModCarrerMode/runtime/club_environment/room/runtime';r.mkdir(parents=True)
            (game/'ModCarrerMode/runtime/career_fce_snapshot.json').write_text(json.dumps(dict(pid=42,club=1043,savePath=r'C:\Careers\one\DATA')))
            (r/'room_control_scope.txt').write_text('S16ROOMSCOPE 1 42 1043 nonce')
            values=art.preferences(game,1043);values.update(table_top='walnut',table_base='black')
            art.write_preferences(game,42,1043,'nonce',1,120,values)
            # Legacy index 1 of finish is black; all other old rows use index 0.
            seq=art.SEQUENCE_STRIDE+8
            self.assertTrue(art.save_command(game,42,f'S16ROOM 1 42 1043 nonce {seq} 120'))
            current=art.preferences(game,1043)
            self.assertEqual((current['table_top'],current['table_base']),('walnut','black'))

    def test_grouped_packet_persists_all_choices_per_career(self):
        with tempfile.TemporaryDirectory() as tmp:
            game=Path(tmp);r=game/'ModCarrerMode/runtime/club_environment/room/runtime';r.mkdir(parents=True)
            snap=game/'ModCarrerMode/runtime/career_fce_snapshot.json'
            snap.write_text(json.dumps(dict(pid=42,club=1043,savePath=r'C:\Careers\one\DATA')))
            (r/'room_control_scope.txt').write_text('S16ROOMSCOPE 1 42 1043 nonce')
            wanted=art.preferences(game,1043);wanted.update(table_top='walnut',table_base='black',floor='dark')
            packed=0;factor=1
            for row in art.rows(game,1043)[:art.PACKED_ROWS]:
                index=next(i for i,o in enumerate(row['options']) if o['value']==wanted[row['key']])
                packed+=index*factor;factor*=len(row['options'])
            wire=f'S16ROOM 1 42 1043 nonce {art.SEQUENCE_STRIDE+packed} {art.GROUPED_APPLY_CODE}'
            self.assertTrue(art.save_command(game,42,wire));self.assertFalse(art.save_command(game,42,wire))
            actual=art.preferences(game,1043)
            self.assertEqual((actual['table_top'],actual['table_base'],actual['floor']),('walnut','black','dark'))
            snap.write_text(json.dumps(dict(pid=42,club=1043,savePath=r'C:\Careers\two\DATA')))
            self.assertEqual(art.preferences(game,1043)['table_base'],'default')

    def test_controller_changes_groups_without_touching_the_finishes(self):
        vm,s,calls,_=open_personalization();vm.invoke(s.get('OpenRoomSettings'),s)
        codes=vm.path('game.globalClasses.InputCodes');codes.set('R1',75)
        vm.invoke(s.get('LocalEventHandler'),s,[75,True]);self.assertEqual(s.get('settingsGroup'),1)
        vm.invoke(s.get('ShiftRoomSetting'),s,[9,1])
        vm.invoke(s.get('LocalEventHandler'),s,[50,True]);self.assertEqual(s.get('settingsGroup'),0)
        self.assertEqual(s.get('settingIndex9'),1)


if __name__=='__main__':unittest.main()
