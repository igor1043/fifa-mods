"""Native APT navigation, scoped scene delivery and material regressions."""
import io,json,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import portable_paths as portable
import build_dressing_card_20261022 as card
from formats import AptFile,BigFile,Placement
from apt_actions import Actions
from apt_vm import Object,Native
from test_finance_live_ui import BankInputVM,open_screen
from loans import empty,presentation
from room_control_bridge_r52 import decode_requests,arena_chunks
from room_roster_r52 import scene_catalog

def open_room():
    # Reuse only the test engine's native manager stubs, not a live game.
    vm,_,calls=open_screen(presentation(empty(1043,20260211),20260211,10_000_000,ready=True,nonce='TEST'))
    codes=vm.path('game.globalClasses.InputCodes');codes.set('LAS_LEFT',13);codes.set('LAS_RIGHT',14)
    scope={'pid':42,'club':1043,'club_name':'Flamengo','focus':[{'number':9,'name':'Pedro','player':233605,'locker':0}]}
    roster=[{'id':233605,'number':9,'name':'Pedro'},{'id':213629,'number':5,'name':'Pulgar'}]
    scope['scene_catalog']=scene_catalog(scope,roster)
    def asset(path):
        if '/crest/' in path or '/heads/p233605.' in path:
            image=Image.new('RGBA',(128,128),(150,25,35,255));stream=io.BytesIO();image.save(stream,format='DDS',pixel_format='DXT5');return stream.getvalue()
        raise FileNotFoundError(path)
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder);(root/'runtime').mkdir()
        with patch.object(card,'ROOT',root),patch.multiple(card.b,CLASS=card.CLASS,FULL=card.FULL):
            output=card.screen(scope,asset);apt=AptFile(BigFile(output));actions=Actions(apt).read_all()
            saved_scope=json.loads((root/'runtime/room_control_scope.json').read_text(encoding='utf8'))
    blocks=list(actions.cache.values());vm.pending_packages[card.FULL]=blocks[0];vm.run(blocks[1],vm.global_,vm.global_);klass=vm.path(card.FULL)
    stage=[p for p in apt.characters[9].frames[0] if isinstance(p,Placement)]
    screen=Object({p.name:Object() for p in stage if p.name},klass.get('prototype'))
    screen.get('roomHeader').set('title',Object());screen.get('roomHeader').set('subtitle',Object())
    modal=screen.get('sceneModal')
    for name in ('groupTitle','counter','previousPage','nextPage','backGroup'):
        modal.set(name,Object({'label':Object()}))
    for i in range(5):modal.set('row'+str(i),Object({'label':Object(),'highlight':Object(),'head233605':Object(),'head213629':Object()}))
    for button in ('sceneButton','playersButton','freeButton'):
        screen.get(button).set('label',Object());screen.get(button).set('highlight',Object())
    vm.invoke(klass,screen);vm.invoke(screen.get('WaitForSceneClips'),screen)
    return vm,screen,calls,saved_scope,apt

class VisualRoomTests(unittest.TestCase):
    def test_free_camera_is_third_action_and_back_returns_without_unloading_room(self):
        vm,screen,calls,scope,_=open_room()
        vm.invoke(screen.get('LocalEventHandler'),screen,[14,True])
        vm.invoke(screen.get('LocalEventHandler'),screen,[14,True])
        self.assertEqual(screen.get('roomActionFocus'),2)
        vm.invoke(screen.get('LocalEventHandler'),screen,[2,True])
        self.assertTrue(screen.get('freeCameraOpen'));self.assertFalse(screen.get('roomPlayersOpen'))
        self.assertTrue(screen.get('freeHint').get('_visible'))
        self.assertFalse(screen.get('roomHeader').get('_visible'))
        self.assertIn(('RAS_LR','Olhar'),vm.invoke(screen.get('getHelpContext'),screen))
        self.assertEqual(decode_requests(vm.global_.get('Server16RoomRequest').encode(),42,scope['nonce'],1043)[-1][1],-4)
        vm.invoke(screen.get('LocalEventHandler'),screen,[14,True]);self.assertEqual(screen.get('roomActionFocus'),2)
        vm.invoke(screen.get('LocalEventHandler'),screen,[1,True])
        self.assertFalse(screen.get('freeCameraOpen'));self.assertTrue(screen.get('freeButton').get('_visible'))
        self.assertEqual(decode_requests(vm.global_.get('Server16RoomRequest').encode(),42,scope['nonce'],1043)[-1][1],-5)
        self.assertFalse(any(name=='SendEvent' and args[1]=='Back' for name,args in calls))

    def test_header_is_a_single_clip_and_remains_hidden_after_animate_in(self):
        vm,screen,_,_,apt=open_room()
        stage=[p for p in apt.characters[9].frames[0] if isinstance(p,Placement)]
        self.assertEqual(sum(p.name=='roomHeader' for p in stage),1)
        self.assertFalse(any(p.name in ('clubCrest','title','subtitle') for p in stage))
        vm.invoke(screen.get('OpenPlayers'),screen)
        screen.get('roomHeader').set('_visible',True)
        vm.invoke(screen.get('RoomPlayersTick'),screen)
        self.assertFalse(screen.get('roomHeader').get('_visible'))
        vm.invoke(screen.get('RoomPlayersBack'),screen)
        self.assertTrue(screen.get('roomHeader').get('_visible'))

    def test_opening_and_closing_scenes_keeps_the_camera_running_with_original_select_help(self):
        vm,screen,calls,scope,_=open_room()
        self.assertEqual(vm.invoke(screen.get('getHelpContext'),screen),[('ADVANCE','Selecionar'),('BACK','Voltar'),('LAS_LR','OpÃ§Ãµes')])
        for _ in range(4):
            vm.invoke(screen.get('OpenScenes'),screen)
            command=vm.global_.get('Server16RoomRequest')
            decoded=decode_requests(command.encode(),42,scope['nonce'],1043)
            self.assertTrue(decoded)
            self.assertTrue(all(code==-3 for seq,code in decoded))
            self.assertTrue(screen.get('modalOpen'))
            vm.invoke(screen.get('CloseScenes'),screen)
            self.assertFalse(screen.get('modalOpen'))
            self.assertTrue(all(code==-3 for seq,code in decode_requests(vm.global_.get('Server16RoomRequest').encode(),42,scope['nonce'],1043)))

    def test_room_actions_select_roster_with_arrows_and_keep_scenes_independent(self):
        vm,screen,calls,scope,_=open_room()
        self.assertEqual(screen.get('roomActionFocus'),0)
        vm.invoke(screen.get('LocalEventHandler'),screen,[14,True])
        self.assertEqual(screen.get('roomActionFocus'),1)
        self.assertEqual(screen.get('playersButton').get('highlight').get('_alpha'),100)
        vm.invoke(screen.get('LocalEventHandler'),screen,[2,True])
        opened=[args for name,args in calls if name=='SendSystemEvent' and args==['Calendar','Server16ClubBrowser','room_roster']]
        self.assertEqual(len(opened),1)
        self.assertFalse(screen.get('modalOpen'))
        vm.invoke(screen.get('OpenPlayers'),screen)
        self.assertEqual(sum(name=='SendSystemEvent' and args==['Calendar','Server16ClubBrowser','room_roster'] for name,args in calls),1)
        self.assertTrue(all(code==-3 for seq,code in decode_requests(vm.global_.get('Server16RoomRequest').encode(),42,scope['nonce'],1043)))
        vm,screen,calls,scope,_=open_room()
        vm.invoke(screen.get('LocalEventHandler'),screen,[6,True]);vm.invoke(screen.get('LocalEventHandler'),screen,[5,True]);vm.invoke(screen.get('LocalEventHandler'),screen,[2,True])
        self.assertTrue(screen.get('modalOpen'))
        self.assertFalse(any(name=='SendSystemEvent' and args==['Calendar','Server16ClubBrowser','room_roster'] for name,args in calls))

    def test_mouse_focus_and_click_open_the_current_club_roster(self):
        vm,screen,calls,_,_=open_room();button=screen.get('playersButton')
        vm.invoke(button.get('onRollOver'),button)
        self.assertEqual(screen.get('roomActionFocus'),1)
        self.assertEqual(button.get('highlight').get('_alpha'),100)
        self.assertEqual(screen.get('sceneButton').get('highlight').get('_alpha'),0)
        vm.invoke(button.get('onRelease'),button)
        self.assertTrue(any(name=='SendSystemEvent' and args==['Calendar','Server16ClubBrowser','room_roster'] for name,args in calls))
        self.assertFalse(any(name=='SendSystemEvent' and 'Server16SubmitBank' in args for name,args in calls))

    def test_roster_keeps_room_loaded_routes_all_inputs_and_returns_from_detail_before_scenes(self):
        vm,screen,calls,_,_=open_room()
        codes=vm.path('game.globalClasses.InputCodes')
        for key,value in [('LAS_UP',15),('LAS_DOWN',16),('L2',11),('R2',12),('OPTION_TOP',10)]:codes.set(key,value)
        vm.invoke(screen.get('OpenPlayers'),screen)
        self.assertTrue(screen.get('roomPlayersOpen'))
        for name in ('roomHeader','sceneButton','playersButton','freeButton','sceneModal'):
            self.assertFalse(screen.get(name).get('_visible'))
        help=vm.invoke(screen.get('getHelpContext'),screen)
        self.assertIn(('ADVANCE','Detalhes'),help);self.assertIn(('BACK','Voltar'),help)
        self.assertIn(('L2R2','Abas'),help);self.assertIn(('RAS_LR','Girar'),help);self.assertIn(('L1R1','Zoom'),help)
        for key,command in [(15,'prev'),(16,'next'),(13,'left'),(14,'right'),(11,'tab_prev'),(12,'tab_next'),(10,'sort')]:
            vm.invoke(screen.get('LocalEventHandler'),screen,[key,True])
            self.assertIn(('SendSystemEvent',['Calendar','Server16ClubBrowser',command]),calls)
        vm.invoke(screen.get('LocalEventHandler'),screen,[2,True])
        self.assertTrue(screen.get('roomPlayersDetail'))
        vm.invoke(screen.get('LocalEventHandler'),screen,[1,True])
        self.assertTrue(screen.get('roomPlayersOpen'));self.assertFalse(screen.get('roomPlayersDetail'))
        self.assertIn(('SendSystemEvent',['Calendar','Server16ClubBrowser','back']),calls)
        vm.invoke(screen.get('LocalEventHandler'),screen,[1,True])
        self.assertFalse(screen.get('roomPlayersOpen'))
        self.assertIn(('SendSystemEvent',['Calendar','Server16ClubBrowser','room_close']),calls)
        self.assertFalse(any(name=='SendEvent' and args[1] in ('Back','Server16OpenRoomPlayers') for name,args in calls))
        for name in ('roomHeader','sceneButton','playersButton','freeButton'):self.assertTrue(screen.get(name).get('_visible'))
        vm.invoke(screen.get('OpenPlayers'),screen)
        self.assertTrue(screen.get('roomPlayersOpen'))

    def test_original_help_footer_moves_below_cards_only_while_roster_is_open(self):
        vm,screen,calls,_,_=open_room()
        display=Object({'mcHelpItemsHolder':Object({'_y':940}),'mcTextScroller':Object({'_y':942})})
        vm.path('game.globalClasses.HelpManager').set('mcHelpDisplay',display)
        vm.invoke(screen.get('OpenPlayers'),screen)
        self.assertEqual(display.get('mcHelpItemsHolder').get('_y'),1030)
        self.assertEqual(display.get('mcTextScroller').get('_y'),1030)
        vm.invoke(screen.get('RefreshRosterHelp'),screen)
        vm.invoke(screen.get('RoomPlayersBack'),screen)
        self.assertEqual(display.get('mcHelpItemsHolder').get('_y'),940)
        self.assertEqual(display.get('mcTextScroller').get('_y'),942)
        vm.invoke(screen.get('OpenPlayers'),screen)
        vm.invoke(screen.get('OnExitScreen'),screen)
        self.assertEqual(display.get('mcHelpItemsHolder').get('_y'),940)

    def test_locker_plate_renders_text_at_double_resolution_and_keeps_the_native_crest(self):
        from room_kit_print_r56 import locker_plate
        crest=Image.new('RGBA',(256,256),(255,255,255,255))
        plate=locker_plate('Luiz Araujo',[[.84,0,.05],[1,1,1]],crest)
        self.assertEqual(plate.size,(2048,512))
        self.assertEqual(plate.getpixel((200,200)),(255,255,255,255))

    def test_player_cards_show_the_face_of_the_selected_real_player(self):
        vm,screen,_,scope,_=open_room()
        vm.invoke(screen.get('OpenScenes'),screen);screen.set('sceneFocus',2);vm.invoke(screen.get('ApplyScene'),screen)
        self.assertEqual(screen.get('sceneGroup'),1)
        first=screen.get('sceneModal').get('row0')
        self.assertTrue(first.get('head233605').get('_visible'))
        self.assertFalse(first.get('head213629').get('_visible'))
        self.assertEqual(first.get('label').get('_x'),76)
        self.assertTrue(first.get('highlight').get('_alpha'))
        # Mouse selection dispatches that exact row, without waiting for auto.
        vm.invoke(first.get('onRelease'),first)
        self.assertFalse(screen.get('modalOpen'))
        command=vm.global_.get('Server16RoomRequest')
        self.assertIn((3,1),decode_requests(command.encode(),42,scope['nonce'],1043))

    def test_native_input_uses_original_help_and_stops_auto_for_manual_selection(self):
        vm,screen,calls,scope,_=open_room()
        vm.invoke(screen.get('LocalEventHandler'),screen,[2,0])
        self.assertTrue(screen.get('modalOpen'))
        help_=vm.invoke(screen.get('getHelpContext'),screen)
        self.assertEqual(help_,[('ADVANCE','Selecionar'),('BACK','Voltar')])
        screen.set('sceneFocus',1);vm.invoke(screen.get('ApplyScene'),screen)
        screen.set('sceneFocus',0);vm.invoke(screen.get('ApplyScene'),screen)
        self.assertFalse(screen.get('modalOpen'))
        self.assertTrue(decode_requests(vm.global_.get('Server16RoomRequest').encode(),999,scope['nonce'],1043))
        self.assertFalse(decode_requests(vm.global_.get('Server16RoomRequest').encode(),999,scope['nonce'],517))

    def test_session_cached_apt_command_is_scoped_to_club_and_token(self):
        raw=b'S16ROOM2|1043|ABCD|16|22|ENDROOM'
        for payload in (raw,raw.decode().encode('utf-16-le')):
            self.assertIn((16,22),decode_requests(payload,123,'ABCD',1043))
            self.assertFalse(decode_requests(payload,123,'ABCD',1629))
            self.assertFalse(decode_requests(payload,123,'OTHER',1043))
        self.assertTrue(all(size<=512*1024+256 for _,size in arena_chunks(0x10000,10*1024**2,0x30000)))

    def test_solid_locker_panels_are_not_in_a_club_colour_atlas(self):
        spec=json.loads((portable.GAME/'ModCarrerMode/data/club_environment/room/runtime/room_roles_r62.json').read_text(encoding='utf8'))
        self.assertEqual(spec['version'],62)
        self.assertTrue(any(r['role']=='neutral' and r['rgb']==[245,246,247] for r in spec['roles']))
        removed=spec['removed_decorations'];self.assertTrue(any('costura do assento' in p for p in removed))
        self.assertTrue(any('superior' in p for p in removed))
        self.assertEqual(len(spec['neutral_bindings']),3)

if __name__=='__main__':unittest.main(verbosity=2)
