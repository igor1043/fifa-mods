"""Execute the compiled APT draft/apply flow and its scoped native mailbox."""
import copy,json,tempfile,unittest,struct
from pathlib import Path
from unittest.mock import patch
from apt_vm import Object,Native
import room_appearance as art
import room_v3 as geometry
import build_dressing_card_20261022 as card
from test_room_visual_r62 import open_room


def open_personalization():
    original=card.screen
    settings=art.ui_data(card.GAME,1043)
    def build(payload,asset):
        payload=copy.deepcopy(payload);payload.update(room_version=3,room_settings=settings)
        return original(payload,asset)
    with patch.object(card,'screen',side_effect=build):vm,screen,calls,scope,apt=open_room()
    modal=screen.get('roomSettings')
    for i in range(6):
        modal.set('setting'+str(i),Object({key:Object({'label':Object()}) for key in ('title','value','highlight','previous','next')}))
    for key in ('close','apply'):modal.set(key,Object({'highlight':Object(),'label':Object()}))
    codes=vm.path('game.globalClasses.InputCodes');codes.set('L1',50);codes.set('OPTION_TOP',51);codes.set('R3',52)
    return vm,screen,calls,scope


def commands(calls):return [args[-1] for name,args in calls if name=='SendSystemEvent' and args[1]=='Server16RoomScene']


class PersonalizationTests(unittest.TestCase):
    def test_native_help_stays_below_actions_in_every_room_mode_and_restores_on_exit(self):
        vm,s,calls,_=open_personalization()
        holder=Object({'_y':930});scroller=Object({'_y':930})
        vm.path('game.globalClasses.HelpManager').set('mcHelpDisplay',Object({'mcHelpItemsHolder':holder,'mcTextScroller':scroller}))
        for method in ('RefreshRosterHelp','OpenRoomSettings','CloseRoomSettings','OpenFreeCamera','CloseFreeCamera','OpenPlayers','RoomPlayersBack'):
            vm.invoke(s.get(method),s)
            self.assertEqual(holder.get('_y'),1030,method)
            self.assertEqual(scroller.get('_y'),1030,method)
        vm.invoke(s.get('OnExitScreen'),s)
        self.assertEqual(holder.get('_y'),930);self.assertEqual(scroller.get('_y'),930)

    def test_apply_preserves_every_option_after_many_commands_in_float32_apt(self):
        import apt_vm
        native_text=apt_vm.text
        def fifa_text(value):
            if isinstance(value,(int,float)) and not isinstance(value,bool):
                value=struct.unpack('<f',struct.pack('<f',value))[0]
            return native_text(value)
        vm,s,calls,_=open_personalization()
        for counter in (0,15,16,28,29,127,9999):
            for indices in ([1,1,4,1,0,0],[1,5,4,0,0,1],[0,1,0,0,0,0]):
                vm.invoke(s.get('OpenRoomSettings'),s)
                for i,index in enumerate(indices):
                    s.set('settingIndex'+str(i),index);s.set('appliedSettingIndex'+str(i),-1)
                vm.global_.set('Server16RoomSequence',counter)
                with patch.object(apt_vm,'text',side_effect=fifa_text):vm.invoke(s.get('ApplyRoomSettings'),s)
                sequence=int(commands(calls)[-1].split('|')[3])
                self.assertEqual(sequence,(counter+1)*art.SEQUENCE_STRIDE+sum(n*8**i for i,n in enumerate(indices)))
                decoded=art.decode_draft(card.GAME,1043,sequence)
                self.assertEqual(decoded['style'],'custom' if indices[0] else 'default')
                with patch.object(apt_vm,'text',side_effect=fifa_text):vm.invoke(s.get('PublishScene'),s,[-4])
                self.assertEqual(int(commands(calls)[-1].split('|')[3]),(counter+2)*art.SEQUENCE_STRIDE)

    def test_default_custom_roundtrip_keeps_black_cabinets_and_custom_backs(self):
        vm,s,calls,_=open_personalization();vm.invoke(s.get('OpenRoomSettings'),s)
        for i,index in enumerate((1,1,4,0,0,0)):s.set('settingIndex'+str(i),index)
        vm.invoke(s.get('ShiftRoomSetting'),s,[0,1])
        self.assertEqual(s.get('settingIndex0'),0);self.assertEqual(s.get('settingIndex2'),0)
        vm.invoke(s.get('ShiftRoomSetting'),s,[0,1])
        self.assertEqual([s.get('settingIndex'+str(i)) for i in (0,1,2)],[1,1,4])
        vm.invoke(s.get('ApplyRoomSettings'),s)
        seq=int(commands(calls)[-1].split('|')[3]);decoded=art.decode_draft(card.GAME,1043,seq)
        self.assertEqual((decoded['style'],decoded['finish'],decoded['backs']),('custom','dark','custom'))

    def test_draft_does_not_publish_and_back_cancels(self):
        vm,s,calls,_=open_personalization();before=len(commands(calls))
        initial=s.get('settingIndex1');vm.invoke(s.get('OpenRoomSettings'),s)
        vm.invoke(s.get('ShiftRoomSetting'),s,[1,1]);self.assertNotEqual(s.get('settingIndex1'),initial)
        self.assertEqual(len(commands(calls)),before)
        vm.invoke(s.get('CloseRoomSettings'),s);vm.invoke(s.get('OpenRoomSettings'),s)
        self.assertEqual(s.get('settingIndex1'),initial)

    def test_apply_publishes_one_full_draft_and_noop_publishes_nothing(self):
        vm,s,calls,scope=open_personalization();before=len(commands(calls))
        vm.invoke(s.get('OpenRoomSettings'),s);vm.invoke(s.get('ShiftRoomSetting'),s,[3,1]);vm.invoke(s.get('ShiftRoomSetting'),s,[5,1])
        expected=[int(s.get('settingIndex'+str(i))) for i in range(6)]
        vm.invoke(s.get('ApplyRoomSettings'),s)
        self.assertEqual(len(commands(calls)),before+1);self.assertFalse(s.get('settingsOpen'))
        wire=commands(calls)[-1].split('|');self.assertEqual(wire[-2],'120');seq=int(wire[3]);packed=seq%art.SEQUENCE_STRIDE
        self.assertEqual([(packed//8**i)%8 for i in range(6)],expected)
        vm.invoke(s.get('OpenRoomSettings'),s);vm.invoke(s.get('ApplyRoomSettings'),s)
        self.assertEqual(len(commands(calls)),before+1)
        vm.invoke(s.get('PublishScene'),s,[-4]);self.assertGreater(int(commands(calls)[-1].split('|')[3]),seq)

    def test_d_does_not_open_settings_in_free_camera(self):
        vm,s,calls,_=open_personalization();vm.invoke(s.get('OpenFreeCamera'),s)
        vm.invoke(s.get('LocalEventHandler'),s,[51,True]);self.assertFalse(s.get('settingsOpen'))
        vm.invoke(s.get('LocalEventHandler'),s,[50,True]);self.assertFalse(s.get('settingsOpen'))
        vm.invoke(s.get('LocalEventHandler'),s,[52,True]);self.assertTrue(s.get('settingsOpen'))

    def test_q_uses_the_installed_native_mapping_without_flash_key(self):
        import re
        mapping=(card.GAME/'buttonDataKeyBoardMouse.ini').read_text()
        self.assertRegex(mapping,r'AddMap\s+SC_Q\s+VB_FE_R3\b')
        self.assertNotRegex(mapping,r'AddMap\s+SC_W\s+VB_FE_R3\b')
        vm,s,calls,_=open_personalization();self.assertIsNone(vm.global_.get('Key'))
        vm.invoke(s.get('OpenFreeCamera'),s)
        vm.invoke(s.get('LocalEventHandler'),s,[50,True]);self.assertFalse(s.get('settingsOpen'))
        vm.invoke(s.get('LocalEventHandler'),s,[52,True]);self.assertTrue(s.get('settingsOpen'))

    def test_bottom_buttons_are_reachable_by_controller(self):
        vm,s,calls,_=open_personalization();codes=vm.path('game.globalClasses.InputCodes');codes.set('LAS_DOWN',71)
        vm.invoke(s.get('OpenRoomSettings'),s)
        for _ in range(7):vm.invoke(s.get('LocalEventHandler'),s,[71,True])
        self.assertEqual(s.get('settingsFocus'),7)
        vm.invoke(s.get('LocalEventHandler'),s,[2,True]);self.assertFalse(s.get('settingsOpen'))

    def test_atomic_mailbox_is_scoped_validated_and_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);runtime=root/'ModCarrerMode/runtime/club_environment/room/runtime';runtime.mkdir(parents=True)
            runtime.joinpath('room_control_scope.txt').write_text('S16ROOMSCOPE 1 42 99999 0123456789abcdef')
            # Generic club has five/six options but no custom image choices.
            indices=[0,1,1,2,2,1];seq=art.SEQUENCE_STRIDE+sum(n*8**i for i,n in enumerate(indices))
            wire=f'S16ROOM 1 42 99999 0123456789abcdef {seq} 120'
            self.assertFalse(art.save_command(root,99,wire));self.assertTrue(art.save_command(root,42,wire))
            prefs=art.preferences(root,99999);self.assertEqual(prefs['finish'],'dark');self.assertEqual(prefs['logo'],'ceiling')
            p=root/art.PREFERENCES/'99999.json';stamp=p.stat().st_mtime_ns
            self.assertFalse(art.save_command(root,42,wire));self.assertEqual(stamp,p.stat().st_mtime_ns)
            self.assertFalse(art.save_command(root,42,f'S16ROOM 1 42 99999 0123456789abcdef {2*art.SEQUENCE_STRIDE+7} 120'))
            self.assertEqual(stamp,p.stat().st_mtime_ns)

    def test_table_collision_and_corner_assets_are_independent(self):
        original=[{'name':'Door','lo':[-20,0,-20],'hi':[20,200,-10]}];saved=copy.deepcopy(original)
        obstacles=geometry.obstacles(original);self.assertEqual(original,saved)
        table=next(o for o in obstacles if o['name'].endswith('central table'))
        self.assertEqual(table['lo'],[-160,3,77]);self.assertEqual(table['hi'],[160,86.5,213]);self.assertIn(original[0],obstacles)
        for club in (1043,598,383):
            assets=art.custom_profile(card.GAME,club)['assets']
            # Installed sources will be synchronized after these checks.
            source=Path(__file__).resolve().parents[3]/'data/club_environment/current_dressing_room/custom'/str(club)/'profile.json'
            assets=json.loads(source.read_text(encoding='utf8'))['assets']
            self.assertEqual(len({assets[k] for k in ('cabinet','backing','corner')}),3)


if __name__=='__main__':unittest.main()
