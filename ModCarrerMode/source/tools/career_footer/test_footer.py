"""Execute the patched native APT, with real HelpItem-shaped callouts."""
from pathlib import Path
import os,sys,tempfile,unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));import build
from formats import AptFile,BigFile,Reader
from apt_actions import Actions
from apt_vm import Object,Native
from apt_test_vm import NativeVM

SOURCE=Path(os.environ['SERVER16_FOOTER_BASELINE'])


class FooterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.output=Path(cls.temp.name)/'fluxhub.big'
        cls.report=build.generate(SOURCE,cls.output)
        cls.apt=AptFile(BigFile(cls.output));cls.actions=Actions(cls.apt).read_all()
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def setup_vm(self,base=None,helper=None,nav=None,career=True,locked=False,animated=True):
        self.calls=[]
        def native(name,owner,args):
            self.calls.append((name,args))
            if name=='CreateHelpTickerItem':return Object(dict(Icon=args[0],TickerText=args[1]))
            if name=='indexOf':return owner.find(args[0])
            if name=='ltxt':
                self.assertIs(owner,vm.global_,'ltxt must be called on the actual global, not an uninitialized register')
                return {'Select':'Selecionar','Back':'Voltar','CM_Settings_Save':'Salvar','CM_Hub_Callout_Inbox':'Caixa de e-mails'}[args[0]]
            if name=='helper':return helper
            if name=='GetDataHelper':return self.helper
            if name=='nav':return nav
            if name=='GetHighlightedIndex':return 0
            if name=='GetTile':return self.tile
            if name=='GetNumberOfTabs':return 8
            if name=='IsInSubpanelMode':return False
            if name=='GetCustomHelpContext':return self.callouts('L3')
            if name=='original':return self.original
            if name=='Create':return (args[0],args[1])
            if name=='SetCustomSource':owner.set('m_cbCustomSource',args[0])
        vm=NativeVM(native)
        get=vm.get
        vm.get=lambda owner,key:Native('indexOf') if isinstance(owner,str) and key=='indexOf' else get(owner,key)
        for block in self.actions.cache.values():
            if block[0].op==136:vm.run(block,vm.global_,vm.global_)
        proto=vm.path('.'.join(build.CLASS)+'.prototype')
        proto.set(build.OLD,Native('original'))
        proto.set(build.ANIMATE,Native('animateNative'));proto.set(build.EXIT,Native('exitNative'))
        for name in build.REFRESH:proto.set('Server16FooterOriginal'+name,Native('original'+name))
        helper_method=Native('helper')
        self.helper=Object(dict(GetHelpContext=helper_method,ProcessData=Native('careerData' if career else 'otherData')))
        game=vm.global_.get('game')
        game.set('fluxHelpers',Object(dict(CareerHubDataHelper=Object(dict(prototype=Object(dict(GetHelpContext=helper_method,ProcessData=Native('careerData'))))))))
        game.set('globalClasses',Object(dict(HelpManager=Object(dict(CompareHelpItemsOrder=Native('sortHelp'))))))
        vm.global_.set('ion',Object(dict(manager=Object(dict(HelpItem=Object(dict(CreateHelpTickerItem=Native('CreateHelpTickerItem'))))))))
        vm.global_.set('ltxt',Native('ltxt'))
        vm.global_.set('cafe',Object(dict(utility=Object(dict(Delegate=Object(dict(Create=Native('Create'))))))))
        hub=Object(dict(mcFluxNavigator=Object(dict(GetDataHelper=Native('GetDataHelper'),GetHelpContext=Native('nav'))),
                        m_arrHubHelpItems=base,m_isAnimatedIn=animated,m_bLockNavigation=locked),proto)
        self.vm,self.hub,self.proto=vm,hub,proto;self.original=[]
        self.tile=None
        return vm,hub
    def callouts(self,*icons):return [Object(dict(Icon=i,TickerText=i)) for i in icons]
    def result(self):return self.vm.invoke(self.proto.get('getHelpContext'),self.hub)
    def test_central_empty_helper_retains_save_back_inbox_and_navigation(self):
        self.setup_vm(self.callouts('BACK','OPTION_LEFT','OPTION_TOP'),[],self.callouts('RAS_UD'))
        items=self.result();self.assertEqual([i.get('Icon') for i in items],['BACK','OPTION_LEFT','OPTION_TOP','RAS_UD','ADVANCE'])
        self.assertEqual(items[-1].get('TickerText'),'Selecionar')
    def test_helper_only_pages_does_not_replace_hub_commands(self):
        self.setup_vm(self.callouts('BACK','OPTION_LEFT','OPTION_TOP'),self.callouts('L2R2'),[])
        self.assertEqual([i.get('Icon') for i in self.result()],['BACK','OPTION_LEFT','OPTION_TOP','L2R2','ADVANCE'])
    def test_all_career_tabs_keep_contextual_actions_after_switching_tiles(self):
        self.setup_vm(self.callouts('BACK','OPTION_LEFT','OPTION_TOP'),[],[])
        for tab in range(7):
            self.hub.set('m_nCurrentFocus',tab%2)
            items=self.result()
            self.assertEqual([i.get('Icon') for i in items],['BACK','OPTION_LEFT','OPTION_TOP','ADVANCE'])
    def test_duplicate_native_and_helper_icons_are_not_shown_twice(self):
        base=self.callouts('BACK','OPTION_LEFT','ADVANCE')
        self.setup_vm(base,base,self.callouts('BACK','L2R2','ADVANCE'))
        self.assertEqual([i.get('Icon') for i in self.result()],['BACK','OPTION_LEFT','ADVANCE','L2R2','OPTION_TOP'])
        self.assertEqual(len(base),3)
    def test_other_hubs_and_tournaments_keep_exact_native_behavior(self):
        self.setup_vm(self.callouts('BACK'),[],[],career=False)
        self.assertIs(self.result(),self.original)
    def test_calendar_lock_retains_native_context_without_stale_save(self):
        self.setup_vm(self.callouts('BACK','OPTION_LEFT'),[],[],locked=True)
        self.assertIs(self.result(),self.original)
    def test_no_footer_before_animation_and_missing_providers_are_safe(self):
        self.setup_vm(None,None,None,animated=False);self.assertEqual(self.result(),[])
        self.hub.set('m_isAnimatedIn',True)
        self.assertEqual([i.get('Icon') for i in self.result()],['ADVANCE','BACK','OPTION_LEFT','OPTION_TOP'])
    def test_wrapped_instance_is_identified_by_its_actual_career_components(self):
        self.setup_vm(self.callouts('BACK'),[],[],career=False)
        self.hub.set('m_arrComponentData',[Object(dict(PATH='game/components/CareerComponents/CareerHubWidget.swf'))])
        self.assertEqual([i.get('Icon') for i in self.result()],['BACK','ADVANCE','OPTION_LEFT','OPTION_TOP'])
    def test_helper_arriving_after_animate_in_still_binds_footer(self):
        self.setup_vm(self.callouts('BACK'),[],[],career=False)
        self.vm.invoke(self.proto.get('AnimateInComplete'),self.hub)
        self.assertIsNone(self.hub.get('Server16CareerFooterDelegate'))
        self.hub.set('m_arrComponentData',[Object(dict(PATH='data/ui/game/components/CareerComponents/CareerHubWidget.swf'))])
        self.vm.invoke(self.proto.get('LoadComponents'),self.hub,[[]])
        self.assertIsNotNone(self.hub.get('Server16CareerFooterDelegate'))
        self.assertEqual({i.get('Icon') for i in self.result()},{'ADVANCE','BACK','OPTION_LEFT','OPTION_TOP'})

    def test_full_asset_path_case_is_supported(self):
        self.setup_vm([],[],[],career=False)
        self.hub.set('m_arrComponentData',[Object(dict(PATH='data/UI/game/components/CAREERCOMPONENTS/CareerHubWidget.swf'))])
        self.assertEqual([i.get('Icon') for i in self.result()],['ADVANCE','BACK','OPTION_LEFT','OPTION_TOP'])
    def test_previous_header_owner_cannot_brand_other_hubs_as_career(self):
        self.setup_vm([],[],[],career=False)
        self.vm.global_.set('Server16CareerBrandOwner',Object())
        self.assertIs(self.result(),self.original)
    def test_native_notification_and_carousel_help_are_retained(self):
        self.setup_vm(self.callouts('BACK'),self.callouts('L3'),self.callouts('LAS_LR'))
        self.original=self.callouts('RAS_UD','BACK')
        self.assertEqual([i.get('Icon') for i in self.result()],['RAS_UD','BACK','L3','LAS_LR','ADVANCE','OPTION_LEFT','OPTION_TOP'])

    def focus_tile(self,tile,focused=True,loading=False):
        self.tile=tile
        nav=self.hub.get('mcFluxNavigator')
        for key,value in dict(m_bIsFocused=focused,m_isPanelLoading=loading,
                              GetHighlightedIndex=Native('GetHighlightedIndex'),GetTile=Native('GetTile')).items():nav.set(key,value)

    def test_actual_nested_count_adds_carousel_help_without_hiding_hub_actions(self):
        self.setup_vm(self.callouts('BACK'),[],self.callouts('ADVANCE'))
        tile=Object(dict(m_nLength=4,NextSubtile=Native('NextSubtile'),PreviousSubtile=Native('PreviousSubtile')))
        self.focus_tile(tile)
        items=self.result()
        self.assertEqual([i.get('Icon') for i in items],['BACK','ADVANCE','RAS_LR','OPTION_LEFT','OPTION_TOP'])
        # The bounded APT decoder exposes raw UTF-8 strings as Latin-1.
        label=next(i for i in items if i.get('Icon')=='RAS_LR').get('TickerText')
        self.assertEqual(label.encode('latin1').decode('utf-8'),'Páginas do card')
        for count in (0,1):
            tile.set('m_nLength',count)
            self.assertNotIn('RAS_LR',[i.get('Icon') for i in self.result()])

    def test_no_carousel_hint_on_unfocused_loading_or_plain_tile(self):
        self.setup_vm([],[],[])
        tile=Object(dict(m_nLength=4,NextSubtile=Native('NextSubtile'),PreviousSubtile=Native('PreviousSubtile')))
        for focused,loading in ((False,False),(True,True)):
            self.focus_tile(tile,focused,loading)
            self.assertNotIn('RAS_LR',[i.get('Icon') for i in self.result()])
        self.focus_tile(Object(dict(m_nLength=4)))
        self.assertNotIn('RAS_LR',[i.get('Icon') for i in self.result()])

    def test_long_news_keeps_native_scroll_callout_with_carousel_and_hub_commands(self):
        self.setup_vm(self.callouts('BACK'),[],[])
        news=Object(dict(m_isNeedAScroll=True,GetCustomHelpContext=Native('GetCustomHelpContext')))
        tile=Object(dict(m_nLength=3,NextSubtile=Native('NextSubtile'),PreviousSubtile=Native('PreviousSubtile'),m_oCurrentSubtile=news))
        self.focus_tile(tile)
        self.assertEqual({i.get('Icon') for i in self.result()},{'RAS_LR','L3','ADVANCE','BACK','OPTION_LEFT','OPTION_TOP'})
        news.set('m_isNeedAScroll',False)
        self.assertNotIn('L3',[i.get('Icon') for i in self.result()])
        tile.set('m_oCurrentSubtile',tile)
        self.assertLess(len(self.result()),10)

    def test_news_timer_delegate_cannot_replace_the_hub_commands(self):
        self.setup_vm(self.callouts('BACK'),[],[])
        news=Object(dict(m_isNeedAScroll=True,GetCustomHelpContext=Native('GetCustomHelpContext')))
        self.focus_tile(Object(dict(m_nLength=2,NextSubtile=Native('NextSubtile'),PreviousSubtile=Native('PreviousSubtile'),m_oCurrentSubtile=news)))
        self.vm.invoke(self.proto.get('AnimateInComplete'),self.hub)
        self.result() # Native HelpManager.Update consumes the newly bound delegate.
        expected={'RAS_LR','L3','ADVANCE','BACK','OPTION_LEFT','OPTION_TOP'}
        for _ in range(5):
            self.assertEqual({i.get('Icon') for i in self.vm.invoke(news.get('GetCustomHelpContext'),news)},expected)
        self.focus_tile(Object())
        self.assertEqual({i.get('Icon') for i in self.vm.invoke(news.get('GetCustomHelpContext'),news)},{'ADVANCE','BACK','OPTION_LEFT','OPTION_TOP'})
        self.vm.invoke(self.proto.get('OnExitScreen'),self.hub)
        self.assertIsNone(self.vm.global_.get('Server16CareerFooterOwner'))
        self.assertEqual([i.get('Icon') for i in self.vm.invoke(news.get('GetCustomHelpContext'),news)],['L3'])

    def test_tabs_are_described_only_when_the_native_tab_menu_is_available(self):
        self.setup_vm([],[],[])
        menu=Object(dict(GetNumberOfTabs=Native('GetNumberOfTabs'),IsInSubpanelMode=Native('IsInSubpanelMode')))
        self.hub.set('mcToggleMenu',menu)
        self.assertEqual(next(i for i in self.result() if i.get('Icon')=='L2R2').get('TickerText'),'Abas')
        self.hub.set('mcToggleMenu',None)
        self.assertNotIn('L2R2',[i.get('Icon') for i in self.result()])

    def test_installed_revision_rejects_repeated_wrapping(self):
        with self.assertRaisesRegex(ValueError,'already installed'):
            build.generate(self.output,Path(self.temp.name)/'repeat.big')
    def test_all_tab_provider_updates_reclaim_the_hub_context(self):
        self.setup_vm(self.callouts('BACK'),[],[])
        manager=self.vm.path('game.globalClasses.HelpManager')
        self.vm.invoke(self.proto.get('AnimateInComplete'),self.hub)
        delegate=self.hub.get('Server16CareerFooterDelegate')
        for tab in range(7):
            manager.set('m_cbCustomSource',None)
            self.vm.invoke(self.proto.get('UpdateButtonData'),self.hub,[Object(dict(tab=tab))])
            self.assertIs(manager.get('m_cbCustomSource'),delegate)
            self.assertEqual({i.get('Icon') for i in self.vm.invoke(delegate,None)},{'ADVANCE','BACK','OPTION_LEFT','OPTION_TOP'})
        self.assertEqual(sum(n=='originalUpdateButtonData' for n,_ in self.calls),7)
        self.vm.invoke(self.proto.get('OnExitScreen'),self.hub)
        self.vm.invoke(self.proto.get('SetFocus'),self.hub,[0])
        self.assertIsNone(manager.get('m_cbCustomSource'))

    def test_hub_reclaims_context_after_custom_view_and_releases_only_its_own_delegate(self):
        self.setup_vm(self.callouts('BACK'),[],[])
        manager=self.vm.path('game.globalClasses.HelpManager');manager.set('m_cbCustomSource',Native('previousScreen'))
        self.vm.invoke(self.proto.get('AnimateInComplete'),self.hub)
        owned=self.hub.get('Server16CareerFooterDelegate');self.assertIsNotNone(owned)
        self.assertIs(manager.get('m_cbCustomSource'),owned)
        self.vm.invoke(self.proto.get('OnExitScreen'),self.hub);self.assertIsNone(manager.get('m_cbCustomSource'))
        self.vm.invoke(self.proto.get('AnimateInComplete'),self.hub);popup=Native('popup');manager.set('m_cbCustomSource',popup)
        self.vm.invoke(self.proto.get('OnExitScreen'),self.hub);self.assertIs(manager.get('m_cbCustomSource'),popup)
    def test_frontend_tick_survives_career_exit_without_changing_native_frame(self):
        self.setup_vm([],[],[],career=False)
        ion=Object(dict(SendSystemEvent=Native('SendSystemEvent')));self.vm.global_.set('ION_CareerMode',ion)
        original=Native('originalFrame');self.hub.set('onEnterFrame',original)
        self.vm.invoke(self.proto.get('AnimateInComplete'),self.hub)
        tick=self.hub.get('onEnterFrame');self.assertIsNot(tick,original)
        for _ in range(30):self.vm.invoke(tick,self.hub)
        self.assertEqual(sum(n=='originalFrame' for n,_ in self.calls),30)
        self.assertEqual(sum(n=='SendSystemEvent' and a==['Calendar','Server16FrontendTick','tick'] for n,a in self.calls),2)
        self.vm.invoke(self.proto.get('AnimateInComplete'),self.hub)
        self.assertIs(self.hub.get('Server16FrontendOriginalFrame'),original)
        self.vm.invoke(self.proto.get('OnExitScreen'),self.hub)
        self.assertIs(self.hub.get('onEnterFrame'),original)

    def test_active_club_identity_changes_with_native_hub_data(self):
        self.setup_vm([],[],[])
        self.vm.global_.set('Server16CareerBrandOwner',Object(dict(m_objData=Object(dict(ASSET_ID=1043,TEAM_NAME='Flamengo')))))
        self.vm.invoke(self.proto.get('AnimateInComplete'),self.hub)
        self.assertEqual(self.vm.global_.get('Server16ActiveCareerClubId'),1043)
        self.vm.global_.get('Server16CareerBrandOwner').get('m_objData').set('ASSET_ID',567)
        self.vm.invoke(self.proto.get('AnimateInComplete'),self.hub)
        self.assertEqual(self.vm.global_.get('Server16ActiveCareerClubId'),567)

    def test_reloading_initializer_does_not_capture_own_wrapper(self):
        self.setup_vm([],[],[]);wrapper=self.proto.get('getHelpContext');original=self.proto.get(build.OLD)
        for block in self.actions.cache.values():
            if block[0].op==136:self.vm.run(block,self.vm.global_,self.vm.global_)
        self.assertIs(self.proto.get('getHelpContext'),wrapper);self.assertIs(self.proto.get(build.OLD),original)
    def test_resources_native_action_bodies_and_function_pointers_preserved(self):
        source=AptFile(BigFile(SOURCE));actions=Actions(source).read_all()
        for meta,code in actions.functions:
            self.assertEqual(bytes(self.apt.data[meta['start']:code[-1].end]),bytes(source.data[meta['start']:code[-1].end]))
        self.assertEqual(self.apt.imports,source.imports);self.assertEqual(self.apt.exports,source.exports)
        for meta,code in self.actions.functions:
            self.assertTrue(all(i.op!=0 for i in code))
        for block in self.actions.cache.values():
            for ins in block:
                if ins.op==142:
                    reader=Reader(self.apt.data,ins.offset+1,8)
                    self.assertGreater(reader.ptr(),0)


if __name__=='__main__':unittest.main()
