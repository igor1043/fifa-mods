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
    modal=screen.get('sceneModal')
    for name in ('groupTitle','counter','previousPage','nextPage','backGroup'):
        modal.set(name,Object({'label':Object()}))
    for i in range(5):modal.set('row'+str(i),Object({'label':Object(),'highlight':Object(),'head233605':Object(),'head213629':Object()}))
    vm.invoke(klass,screen);vm.invoke(screen.get('WaitForSceneClips'),screen)
    return vm,screen,calls,saved_scope,apt

class VisualRoomTests(unittest.TestCase):
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
