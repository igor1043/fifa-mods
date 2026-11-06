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
            if name=='CreateHelpTickerItem':return Object(dict(icon=args[0],text=args[1]))
            if name=='ltxt':
                self.assertIs(owner,vm.global_,'ltxt must be called on the actual global, not an uninitialized register')
                return {'Select':'Selecionar','Back':'Voltar','CM_Settings_Save':'Salvar','CM_Hub_Callout_Inbox':'Caixa de e-mails'}[args[0]]
            if name=='helper':return helper
            if name=='GetDataHelper':return self.helper
            if name=='nav':return nav
            if name=='original':return self.original
            if name=='Create':return (args[0],args[1])
            if name=='SetCustomSource':owner.set('m_cbCustomSource',args[0])
        vm=NativeVM(native)
        for block in self.actions.cache.values():
            if block[0].op==136:vm.run(block,vm.global_,vm.global_)
        proto=vm.path('.'.join(build.CLASS)+'.prototype')
        proto.set(build.OLD,Native('original'))
        proto.set(build.ANIMATE,Native('animateNative'));proto.set(build.EXIT,Native('exitNative'))
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
        self.vm,self.hub,self.proto=vm,hub,proto;self.original=['native unchanged']
        return vm,hub
    def callouts(self,*icons):return [Object(dict(icon=i,text=i)) for i in icons]
    def result(self):return self.vm.invoke(self.proto.get('getHelpContext'),self.hub)
    def test_central_empty_helper_retains_save_back_inbox_and_navigation(self):
        self.setup_vm(self.callouts('BACK','OPTION_LEFT','OPTION_TOP'),[],self.callouts('RAS_UD'))
        items=self.result();self.assertEqual([i.get('icon') for i in items],['BACK','OPTION_LEFT','OPTION_TOP','RAS_UD','ADVANCE'])
        self.assertEqual(items[-1].get('text'),'Selecionar')
    def test_helper_only_pages_does_not_replace_hub_commands(self):
        self.setup_vm(self.callouts('BACK','OPTION_LEFT','OPTION_TOP'),self.callouts('L2R2'),[])
        self.assertEqual([i.get('icon') for i in self.result()],['BACK','OPTION_LEFT','OPTION_TOP','L2R2','ADVANCE'])
    def test_all_career_tabs_keep_contextual_actions_after_switching_tiles(self):
        self.setup_vm(self.callouts('BACK','OPTION_LEFT','OPTION_TOP'),[],[])
        for tab in range(7):
            self.hub.set('m_nCurrentFocus',tab%2)
            items=self.result()
            self.assertEqual([i.get('icon') for i in items],['BACK','OPTION_LEFT','OPTION_TOP','ADVANCE'])
    def test_duplicate_native_and_helper_icons_are_not_shown_twice(self):
        base=self.callouts('BACK','OPTION_LEFT','ADVANCE')
        self.setup_vm(base,base,self.callouts('BACK','L2R2','ADVANCE'))
        self.assertEqual([i.get('icon') for i in self.result()],['BACK','OPTION_LEFT','ADVANCE','L2R2','OPTION_TOP'])
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
        self.assertEqual([i.get('icon') for i in self.result()],['ADVANCE','BACK','OPTION_LEFT','OPTION_TOP'])
    def test_wrapped_instance_is_identified_by_its_actual_career_components(self):
        self.setup_vm(self.callouts('BACK'),[],[],career=False)
        self.hub.set('m_arrComponentData',[Object(dict(PATH='game/components/CareerComponents/CareerHubWidget.swf'))])
        self.assertEqual([i.get('icon') for i in self.result()],['BACK','ADVANCE','OPTION_LEFT','OPTION_TOP'])
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
