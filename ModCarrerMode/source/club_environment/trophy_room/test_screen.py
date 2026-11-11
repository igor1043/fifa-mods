"""Execute the built FIFA APT: input works before scene assets finish loading."""
from pathlib import Path
import os,sys,tempfile,unittest
ENV=Path(__file__).resolve().parents[1]
os.environ.setdefault('SERVER16_GAME_ROOT','U:/fifa 16')
sys.path[:0]=[str(ENV.parent),str(ENV),str(ENV/'vendor'),str(ENV/'market'),str(ENV/'bank'),str(ENV/'preview')]
from apt_vm import Object,Native
from native_review_vm import open_native
from .build_screen import screen,FULL,background_flow

class GalleryScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.package=Path(cls.tmp.name)/'trophyroom.big'
        cls.game=Path(os.environ.get('SERVER16_GAME_ROOT','U:/fifa 16'))
        screen(cls.game,cls.package)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def open(self,shelf=False):
        def setup(vm,calls):
            vm.global_.set('Key',Object(dict(addListener=Native('addListener'),removeListener=Native('removeListener'),getCode=Native('getCode'))))
            vm.global_.set('Mouse',Object(dict(addListener=Native('Mouse.addListener'),removeListener=Native('Mouse.removeListener'))))
            vm.path('game.globalClasses.ScreenManager').set('AddItemToAnimateIn',Native('AddItemToAnimateIn'))
            vm.path('game.globalClasses.HelpManager').set('Hide',Native('Hide'))
            vm.global_.get('game').set('uif',Object(dict(
                UIFDataProviderList=Object(dict(BackgroundDP=91)),
                UIFUtility=Object(dict(RegisterDataProvider=Native('RegisterDataProvider'),UnregisterDataProvider=Native('UnregisterDataProvider'))),
                DataProviders=Object(dict(BackgroundDP=Native('BackgroundDP'))))))
        result=open_native(self.package,full=FULL,setup=setup,callbacks={
            'GetEvents':lambda owner,args:Object({'BACK':42}),
            'BackgroundDP':lambda owner,args:Object(dict(value=args[0].get('Param'),GetParam=Native('GetParam'))),
            'GetParam':lambda owner,args:owner.get('value')})
        if shelf is not None:result[1].set('shelfOpen',shelf)
        return result
    def test_back_works_before_loading_and_returns_to_list_from_3d(self):
        for free in (False,True):
            vm,s,_,calls=self.open();s.set('freeOpen',free);calls.clear()
            vm.invoke(s.get('LocalEventHandler'),s,(1,True))
            self.assertTrue(s.get('shelfOpen'));self.assertNotIn(('SendEvent',['Calendar',42,'']),[(n,list(a)) for n,a in calls])
            vm.invoke(s.get('LocalEventHandler'),s,(1,True))
            self.assertIn(('SendEvent',['Calendar',42,'']),[(n,list(a)) for n,a in calls]);self.assertEqual(vm.errors,[])
    def test_a_opens_details_then_back_closes_details_then_list_then_exits(self):
        vm,s,_,calls=self.open();calls.clear();vm.invoke(s.get('LocalEventHandler'),s,(2,True))
        self.assertTrue(s.get('detailOpen'));self.assertIn(('SendSystemEvent',['Calendar','Server16TrophyRoom','detail']),[(n,list(a)) for n,a in calls])
        calls.clear();vm.invoke(s.get('LocalEventHandler'),s,(1,True));self.assertFalse(s.get('detailOpen'))
        self.assertNotIn('SendEvent',[n for n,_ in calls]);vm.invoke(s.get('LocalEventHandler'),s,(1,True));self.assertTrue(s.get('shelfOpen'))
        vm.invoke(s.get('LocalEventHandler'),s,(1,True))
        self.assertIn(('SendEvent',['Calendar',42,'']),[(n,list(a)) for n,a in calls]);self.assertEqual(vm.errors,[])
    def test_free_camera_wasd_does_not_trigger_fifas_action_alias(self):
        vm,s,_,calls=self.open();vm.invoke(s.get('Choose'),s,(1,));calls.clear();s.set('move68',True)
        vm.invoke(s.get('LocalEventHandler'),s,(10,True));self.assertEqual(calls,[]);self.assertTrue(s.get('freeOpen'))
        s.set('move68',False);vm.invoke(s.get('LocalEventHandler'),s,(10,True));self.assertFalse(s.get('freeOpen'));self.assertEqual(vm.errors,[])
    def test_footer_exposes_details_back_camera_and_more_trophies(self):
        vm,s,_,_=self.open();normal=vm.invoke(s.get('getHelpContext'),s)
        # The offline APT reader exposes raw UTF-8 label bytes as Latin-1.
        self.assertIn(('ADVANCE','Detalhes'),normal);self.assertIn(('BACK','Voltar'),normal)
        labels=[item[1].encode('latin1').decode('utf8') for item in normal]
        self.assertTrue(all(label in labels for label in ('Detalhes','Voltar','Próxima taça','Câmera livre','Galeria','Sala 3D')))
        s.set('freeOpen',True);free=vm.invoke(s.get('getHelpContext'),s);self.assertIn('Andar',str(free));self.assertIn('Voltar',str(free));self.assertEqual(vm.errors,[])
    def test_detail_footer_exposes_rotation_and_zoom(self):
        vm,s,_,calls=self.open();vm.invoke(s.get('Choose'),s,(4,));items=vm.invoke(s.get('getHelpContext'),s)
        self.assertIn(('L1R1','Zoom'),items);self.assertIn(('RAS_LR','Rotacionar'),items);self.assertEqual(vm.errors,[])
        decoded=[(code,label.encode('latin1').decode('utf8')) for code,label in items]
        self.assertIn(('L2R2','Taças'),decoded)

    def test_shoulders_step_between_cups_without_closing_inspection(self):
        for detail in (False,True):
            vm,s,_,calls=self.open();s.set('detailOpen',detail)
            codes=vm.path('game.globalClasses.InputCodes');codes.set('L2',94);codes.set('R2',95);calls.clear()
            for value in (94,95):vm.invoke(s.get('LocalEventHandler'),s,(value,True))
            commands=[args[-1] for name,args in calls if name=='SendSystemEvent' and args[1]=='Server16TrophyRoom']
            self.assertEqual(commands,['previous','camera']);self.assertEqual(s.get('detailOpen'),detail)
            self.assertFalse(s.get('shelfOpen'));self.assertEqual(vm.errors,[])
        vm,s,_,calls=self.open();s.set('freeOpen',True);codes=vm.path('game.globalClasses.InputCodes');codes.set('R2',95);calls.clear()
        vm.invoke(s.get('LocalEventHandler'),s,(95,True));self.assertFalse(calls);self.assertTrue(s.get('freeOpen'))
    def test_collection_button_and_controller_switch_both_views(self):
        vm,s,_,calls=self.open(None);self.assertFalse(s.get('coachCollection'))
        codes=vm.path('game.globalClasses.InputCodes');codes.set('R2',91)
        vm.invoke(s.get('LocalEventHandler'),s,(91,True));self.assertTrue(s.get('coachCollection'))
        vm.invoke(s.get('Choose'),s,(5,));self.assertFalse(s.get('coachCollection'));self.assertEqual(vm.errors,[])
    def test_mouse_picks_only_inside_the_scene_not_buttons_or_heading(self):
        vm,s,_,calls=self.open()
        for y in (100,1050):
            s.set('_ymouse',y);calls.clear();vm.invoke(s.get('onMouseDown'),s);self.assertFalse(calls)
        s.set('_xmouse',600);s.set('_ymouse',540);vm.invoke(s.get('onMouseDown'),s)
        self.assertIn(('SendSystemEvent',['Calendar','Server16TrophyRoom','pick']),[(n,list(a)) for n,a in calls]);self.assertTrue(s.get('detailOpen'));self.assertEqual(vm.errors,[])

    def test_list_is_initial_view_and_a_opens_selected_trophy_in_3d(self):
        vm,s,_,calls=self.open(None);self.assertTrue(s.get('shelfOpen'));calls.clear()
        vm.invoke(s.get('LocalEventHandler'),s,(2,True))
        self.assertFalse(s.get('shelfOpen'));self.assertTrue(s.get('detailOpen'))
        self.assertIn(('SendSystemEvent',['Calendar','Server16TrophyRoom','shelf_detail']),[(n,list(a)) for n,a in calls]);self.assertEqual(vm.errors,[])
    def test_list_navigation_and_header_mouse_controls(self):
        vm,s,_,calls=self.open(None);codes=vm.path('game.globalClasses.InputCodes');codes.set('DOWN',97);calls.clear()
        vm.invoke(s.get('LocalEventHandler'),s,(97,True))
        self.assertIn(('SendSystemEvent',['Calendar','Server16TrophyRoom','shelf_down']),[(n,list(a)) for n,a in calls])
        s.set('_xmouse',1680);s.set('_ymouse',86.4);vm.invoke(s.get('onMouseDown'),s);self.assertFalse(s.get('shelfOpen'))
        s.set('_xmouse',1440);vm.invoke(s.get('onMouseDown'),s);self.assertTrue(s.get('shelfOpen'));self.assertEqual(vm.errors,[])
    def test_list_footer_and_back_need_no_3d_resources(self):
        vm,s,_,calls=self.open(None);labels=vm.invoke(s.get('getHelpContext'),s)
        labels=[(a,b.encode('latin1').decode('utf8')) for a,b in labels]
        self.assertIn(('L1','Galeria'),labels);self.assertIn(('R1','Sala 3D'),labels);self.assertIn(('BACK','Voltar'),labels);calls.clear()
        vm.invoke(s.get('LocalEventHandler'),s,(1,True));self.assertIn(('SendEvent',['Calendar',42,'']),[(n,list(a)) for n,a in calls]);self.assertEqual(vm.errors,[])

    def test_triggers_switch_views_and_shoulders_choose_collection_without_toggling(self):
        vm,s,_,calls=self.open(None);codes=vm.path('game.globalClasses.InputCodes')
        for name,value in [('L1',92),('R1',93),('L2',94),('R2',95)]:codes.set(name,value)
        for value,shelf in [(93,False),(93,False),(92,True),(92,True)]:
            vm.invoke(s.get('LocalEventHandler'),s,(value,True));self.assertEqual(s.get('shelfOpen'),shelf)
        for value,coach in [(95,True),(95,True),(94,False),(94,False)]:
            vm.invoke(s.get('LocalEventHandler'),s,(value,True));self.assertEqual(s.get('coachCollection'),coach)
        self.assertEqual(vm.errors,[])

    def test_click_on_cup_opens_its_3d_details_and_updates_footer(self):
        vm,s,_,calls=self.open(None);s.set('_xmouse',120);s.set('_ymouse',300);calls.clear()
        vm.invoke(s.get('onMouseDown'),s)
        self.assertFalse(s.get('shelfOpen'));self.assertTrue(s.get('detailOpen'))
        self.assertIn(('SendSystemEvent',['Calendar','Server16TrophyRoom','shelf_open_0']),[(n,list(a)) for n,a in calls])
        self.assertIn(('L1R1','Zoom'),vm.invoke(s.get('getHelpContext'),s));self.assertEqual(vm.errors,[])

    def test_inspection_reserves_triggers_for_zoom_and_blocks_view_shortcuts(self):
        vm,s,_,calls=self.open();vm.invoke(s.get('Choose'),s,(4,));self.assertTrue(s.get('detailOpen'))
        codes=vm.path('game.globalClasses.InputCodes');codes.set('L1',92);codes.set('R1',93);calls.clear()
        for value in (92,93):vm.invoke(s.get('LocalEventHandler'),s,(value,True))
        vm.invoke(s.get('Choose'),s,(6,));vm.invoke(s.get('Choose'),s,(7,))
        self.assertFalse(s.get('shelfOpen'));self.assertTrue(s.get('detailOpen'))
        self.assertFalse([a for n,a in calls if n=='SendSystemEvent'])
        help=vm.invoke(s.get('getHelpContext'),s);self.assertIn(('L1R1','Zoom'),help)
        self.assertFalse(any(a in ('L1','R1') and b in ('Galeria','Sala 3D') for a,b in help))
        vm.invoke(s.get('LocalEventHandler'),s,(1,True));self.assertFalse(s.get('detailOpen'))
        vm.invoke(s.get('LocalEventHandler'),s,(92,True));self.assertTrue(s.get('shelfOpen'))

    def test_footer_is_below_the_native_card_and_restores_on_exit(self):
        vm,s,_,calls=self.open(None);holder=Object({'_y':930});scroller=Object({'_y':930})
        vm.path('game.globalClasses.HelpManager').set('mcHelpDisplay',Object({'mcHelpItemsHolder':holder,'mcTextScroller':scroller}))
        for method,args in [('RefreshButtons',()),('Choose',(7,)),('Choose',(4,)),('Choose',(1,))]:
            vm.invoke(s.get(method),s,args);self.assertEqual(holder.get('_y'),1030);self.assertEqual(scroller.get('_y'),1030)
        vm.invoke(s.get('OnExitScreen'),s);self.assertEqual(holder.get('_y'),930);self.assertEqual(scroller.get('_y'),930)
        self.assertIn('Mouse.removeListener',[name for name,_ in calls]);self.assertEqual(vm.errors,[])

    def test_native_footer_does_not_wait_for_calendar_help_clips(self):
        vm,s,_,calls=self.open(None)
        self.assertIn('BeginAnimateIn',[name for name,_ in calls])
        self.assertIsNotNone(s.get('onEnterFrame'))
        holder=Object({'_y':930});scroller=Object({'_y':930})
        vm.path('game.globalClasses.HelpManager').set('mcHelpDisplay',Object({'mcHelpItemsHolder':holder,'mcTextScroller':scroller}))
        calls.clear();vm.invoke(s.get('RefreshButtons'),s)
        self.assertEqual(holder.get('_y'),1030);self.assertEqual(scroller.get('_y'),1030)
        self.assertIn('Show',[name for name,_ in calls]);self.assertNotIn('Hide',[name for name,_ in calls]);self.assertIsNotNone(s.get('onEnterFrame'))
        vm.invoke(s.get('OnAnimateInComplete'),s)
        self.assertIsNotNone(s.get('onEnterFrame'));self.assertEqual(vm.errors,[])

    def test_click_never_removes_loading_cover_before_native_readiness(self):
        vm,s,_,calls=self.open(None);calls.clear()
        for index in (7,6,4):
            vm.invoke(s.get('Choose'),s,(index,))
            self.assertIn(('SendSystemEvent',['Calendar','Server16FrontendTick','tick']),[(n,list(a)) for n,a in calls])
            self.assertFalse(any(args[1] in ('Server16TrophyScene','Server16TrophyGallery') for n,args in calls if n=='SendSystemEvent'));calls.clear()
        vm.invoke(s.get('UiTick'),s)
        self.assertIn(('SendSystemEvent',['Calendar','Server16FrontendTick','tick']),[(n,list(a)) for n,a in calls])
        self.assertEqual(vm.errors,[])

    def test_native_flow_loads_the_finance_background_and_keeps_back_actions(self):
        import json
        original=json.loads((self.game/'data/ui/nav/careermode/server16trophyroomflow.nav').read_text(encoding='utf8'))
        updated=background_flow(original);self.assertEqual(updated,background_flow(updated))
        before=next(s for s in original['states'] if s['name']=='Gallery')
        state=next(s for s in updated['states'] if s['name']=='Gallery')
        for action in before['onEnter']:
            if action[0]!='loadView' or action[1][0]!='background':self.assertIn(action,state['onEnter'])
        for transition in before['transitions']:
            if transition['event'] not in ('Server16TrophyScene','Server16TrophyGallery'):self.assertIn(transition,state['transitions'])
        self.assertIn(['loadView',['background','FIFA','BOOTFLOW']],state['onEnter'])
        self.assertNotIn(['loadView',['background','BOOTFLOW']],state['onEnter'])
        self.assertIn(['unloadView',['background']],state['onExit'])
        actions={t['event']:t.get('actions') for t in state['transitions']}
        self.assertNotIn('Server16TrophyScene',actions);self.assertNotIn('Server16TrophyGallery',actions)

    def test_native_help_is_the_only_footer_and_has_a_real_timeline_anchor(self):
        vm,s,_,calls=self.open(None)
        self.assertIsNotNone(s.get('uiAnchor'))
        self.assertIn('SetCustomSource',[name for name,_ in calls]);self.assertIn('Show',[name for name,_ in calls])
        self.assertNotIn('Hide',[name for name,_ in calls])
        s.set('_xmouse',600);s.set('_ymouse',1040);calls.clear()
        vm.invoke(s.get('onMouseDown'),s);self.assertFalse(calls)

    def test_selected_background_really_subscribes_to_native_provider(self):
        from formats import AptFile,BigFile
        from apt_actions import Actions
        root=self.game/'data/ui/game/background'
        static=AptFile(BigFile(root/'backgroundbootflow.big'))
        dynamic=AptFile(BigFile(root/'backgroundfifa.big'))
        def symbols(apt):
            values=set()
            def visit(rows):
                for row in rows:
                    if isinstance(row.value,str):values.add(row.value)
                    elif isinstance(row.value,list):values.update(v for v in row.value if isinstance(v,str))
                    visit(row.body)
            for rows in Actions(apt).read_all().cache.values():visit(rows)
            return values
        self.assertNotIn('BackgroundDP',symbols(static))
        self.assertTrue({'BackgroundDP','RegisterDataProvider','GetParam'}.issubset(symbols(dynamic)))

    def test_actual_background_clips_hide_only_after_native_ready_and_restore(self):
        vm,s,_,calls=self.open(None)
        boot_child=Object(dict(_visible=True));boot=Object(dict(_visible=True,mcImageLoader=boot_child))
        photo_child=Object(dict(_visible=True));photo=Object(dict(_visible=True,mcImage=photo_child))
        vm.global_.set('Server16ManagerFaceBootBackgroundOwner',boot)
        vm.global_.set('Server16ManagerFaceBackgroundOwner',photo)
        vm.invoke(s.get('Choose'),s,(7,));vm.invoke(s.get('SyncBackgroundCover'),s)
        for node in (boot,boot_child,photo,photo_child):self.assertTrue(node.get('_visible'))
        vm.invoke(s.get('Publish'),s,(Object(dict(Param='BOOTFLOW')),91))
        for node in (boot,boot_child,photo,photo_child):self.assertTrue(node.get('_visible'))
        vm.invoke(s.get('Publish'),s,(Object(dict(Param='server16_frontend_clear')),92))
        self.assertFalse(s.get('backgroundReady'))
        vm.invoke(s.get('Publish'),s,(Object(dict(Param='server16_frontend_clear')),91))
        for node in (boot,boot_child,photo,photo_child):self.assertFalse(node.get('_visible'))
        # A late ImageLoader completion must not re-cover the finished room.
        boot_child.set('_visible',True);vm.invoke(s.get('SyncBackgroundCover'),s);self.assertFalse(boot_child.get('_visible'))
        vm.invoke(s.get('Choose'),s,(6,));vm.invoke(s.get('SyncBackgroundCover'),s)
        vm.invoke(s.get('Publish'),s,(Object(dict(Param='BOOTFLOW')),91))
        for node in (boot,boot_child,photo,photo_child):self.assertTrue(node.get('_visible'))
        vm.invoke(s.get('Choose'),s,(7,));vm.invoke(s.get('SyncBackgroundCover'),s)
        for node in (boot,boot_child,photo,photo_child):self.assertTrue(node.get('_visible'))
        vm.invoke(s.get('Publish'),s,(Object(dict(Param='server16_frontend_clear')),91))
        vm.invoke(s.get('OnExitScreen'),s)
        for node in (boot,boot_child,photo,photo_child):self.assertTrue(node.get('_visible'))
        self.assertIn('UnregisterDataProvider',[n for n,_ in calls]);self.assertEqual(vm.errors,[])

    def test_background_tracks_native_mouse_view_even_if_apt_alias_is_late(self):
        vm,s,_,_=self.open(None);owner=Object(dict(_visible=True))
        vm.global_.set('Server16ManagerFaceBootBackgroundOwner',owner)
        self.assertTrue(s.get('shelfOpen'))
        vm.invoke(s.get('Publish'),s,(Object(dict(Param='server16_frontend_clear')),91))
        self.assertFalse(owner.get('_visible'))
        vm.invoke(s.get('Publish'),s,(Object(dict(Param='BOOTFLOW')),91));self.assertTrue(owner.get('_visible'))

    def test_cover_preserves_preexisting_visibility_and_new_background_owner(self):
        vm,s,_,_=self.open();s.set('backgroundReady',True)
        original=Object(dict(_visible=False));vm.global_.set('Server16ManagerFaceBootBackgroundOwner',original)
        vm.invoke(s.get('SyncBackgroundCover'),s)
        replacement=Object(dict(_visible=True));vm.global_.set('Server16ManagerFaceBootBackgroundOwner',replacement)
        vm.invoke(s.get('SyncBackgroundCover'),s);self.assertFalse(original.get('_visible'));self.assertFalse(replacement.get('_visible'))
        vm.invoke(s.get('OnExitScreen'),s);self.assertFalse(original.get('_visible'));self.assertTrue(replacement.get('_visible'))

if __name__=='__main__':unittest.main()
