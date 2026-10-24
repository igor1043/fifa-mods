"""Offline integration checks against native APT bytecode and real save data."""
from pathlib import Path
import copy,hashlib,json,tempfile,unittest,xml.etree.ElementTree as ET
from unittest.mock import patch
from build_package import carousel,navigation,read_nav,walk,flow,EVENT,PAGE
from native_review_vm import open_native
from native_screen import build,neighbors
from layout import TABS,make_scenes
from read_market import read_snapshot
import worker_market as worker
from apt_vm import Object,Native
import hub_bootstrap

class MarketIntegrationTests(unittest.TestCase):
    game=worker.GAME
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='FIFA mercado teste ');self.folder=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def saved(self):
        # Repository fixture is a read-only projection, not a copy of DATA.
        root=Path(__file__).resolve().parents[4]
        data=json.loads((root/'code-release/transfer_market_preview_20261024/market_97b12cb3.json').read_text(encoding='utf8'))
        return data
    def screen(self):
        data=self.saved();scenes=[s for s in make_scenes(data) if s['key']!='entry'];output=self.folder/'market.big';build(self.game,output,scenes,{})
        vm,screen,apt,calls=open_native(output)
        return scenes,vm,screen,calls
    def test_native_keyboard_and_controller_change_tabs_and_wrap(self):
        scenes,vm,screen,calls=self.screen();keys={s['key']:i for i,s in enumerate(scenes)}
        for name,_ in TABS:
            self.assertEqual(screen.get('page'),keys[name]);vm.invoke(screen.get('LocalEventHandler'),screen,[12,0])
        self.assertEqual(screen.get('page'),keys['overview'])
        vm.invoke(screen.get('LocalEventHandler'),screen,[11,0]);self.assertEqual(screen.get('page'),keys['mine'])
        league=next(s for s in scenes if s['key'].startswith('league:'));vm.invoke(screen.get('Go'),screen,[keys[league['key']]])
        vm.invoke(screen.get('LocalEventHandler'),screen,[12,0]);self.assertEqual(screen.get('page'),keys['clubs'])
    def test_original_footer_and_refresh_controller_dispatch(self):
        scenes,vm,screen,calls=self.screen()
        self.assertEqual(vm.invoke(screen.get('getHelpContext'),screen),[('ADVANCE','Selecionar'),('BACK','Voltar'),('L2R2','Abas')])
        vm.invoke(screen.get('LocalEventHandler'),screen,[10,0])
        self.assertNotIn(('SendSystemEvent',['Calendar','Server16RefreshTransferMarket','']),calls)
        vm.invoke(screen.get('Back'),screen);self.assertIn(('SendEvent',['Calendar','Back','']),calls)
    def test_directional_navigation_enter_and_nested_back(self):
        scenes,vm,screen,calls=self.screen();keys={s['key']:i for i,s in enumerate(scenes)}
        vm.invoke(screen.get('Go'),screen,[keys['leagues']]);scene=scenes[keys['leagues']]
        for code,direction in ((5,0),(6,1),(3,2),(4,3)):
            old=screen.get('focus');vm.invoke(screen.get('LocalEventHandler'),screen,[code,0]);self.assertEqual(screen.get('focus'),neighbors(scene['actions'])[old][direction])
        index=next(i for i,a in enumerate(scene['actions']) if a['target'].startswith('league:'));screen.set('focus',index)
        vm.invoke(screen.get('LocalEventHandler'),screen,[2,0]);self.assertEqual(screen.get('page'),keys[scene['actions'][index]['target']])
        vm.invoke(screen.get('LocalEventHandler'),screen,[1,0]);self.assertEqual(screen.get('page'),keys['leagues'])
    def test_shutdown_idempotent_and_clears_callbacks(self):
        scenes,vm,screen,calls=self.screen();vm.invoke(screen.get('OnExitScreen'),screen);vm.invoke(screen.get('OnExitScreen'),screen)
        self.assertEqual(sum(n=='Shutdown' for n,args in calls),1)
        for i,s in enumerate(scenes):
            for j in range(len(s['actions'])):self.assertIsNone(screen.get('scene'+str(i)).get('action'+str(j)).get('onRelease'))
    def test_static_carousel_preserves_scout_reports_components_and_other_cards(self):
        # Use the pre-integration layout so this stays a regression check after
        # installation, rather than comparing an installed layout to itself.
        original=self.game/'ModCarrerMode/backups/transfer_market_20261024/data/ui/layout/careermanagerhubcfg.xml'
        before=original.read_bytes();root=ET.fromstring(before);changed=ET.fromstring(carousel(before))
        self.assertEqual(carousel(carousel(before)),carousel(before))
        for old,new in zip(root,changed):
            if old.tag!='panel_2':self.assertEqual(ET.tostring(old),ET.tostring(new))
        for old,new in zip(root.find('panel_2'),changed.find('panel_2')):
            if old.tag!='tile' or old.find('tileid').get('NAME')!='GTN_STATIC':
                self.assertEqual(ET.tostring(old),ET.tostring(new))
        tile=next(t for t in changed.find('panel_2').findall('tile') if t.find('tileid').get('NAME')=='GTN_STATIC')
        original=next(t for t in root.find('panel_2').findall('tile') if t.find('tileid').get('NAME')=='GTN_STATIC')
        self.assertEqual(tile.find('settings').attrib,dict(FILE_PATH='TILE_NESTED',WIDTH='846',HEIGHT='204',X='109',Y='706',ENABLE_CYCLING='TRUE'))
        self.assertEqual(tile.find('number_of_subtiles').get('LENGTH'),'1')
        slides=[n for n in tile if n.tag=='main_tile' or n.tag.startswith('subtile')]
        self.assertEqual([n.get('DESTINATION') for n in slides],[EVENT,'EnterGTNHub'])
        self.assertEqual(len({n.get('ID') for n in slides}),2)
        for slide in slides:self.assertIsNone(slide.get('DATAPROVIDERID'))
        original_main=original.find('main_tile').attrib
        for key,value in original_main.items():self.assertEqual(slides[1].get(key),value)
        self.assertEqual([ET.tostring(n) for n in original.findall('data')],[ET.tostring(n) for n in slides[1].findall('data')])
        self.assertFalse(any('MarketHubBootstrap' in n.get('PATH','') for n in changed.iter()))
        self.assertEqual(sum(n.get('DESTINATION')==EVENT for n in changed.iter()),1)
    def test_card_callback_resolves_to_native_screen_and_back(self):
        root=ET.fromstring(carousel((self.game/'data/ui/layout/careermanagerhubcfg.xml').read_bytes()))
        card=next(n for n in root.iter('main_tile') if n.get('DESTINATION')==EVENT)
        nav=read_nav(navigation((self.game/'data/ui/nav/careermode/mainmenuhubflow.nav').read_bytes()))
        transition=next(n for n in walk(nav) if n.get('event')==card.get('DESTINATION'))
        self.assertEqual(transition['targets'],['Server16TransferMarket'])
        state=next(n for n in walk(nav) if n.get('name')=='Server16TransferMarket')
        self.assertEqual(state['file'],'/careerMode/server16TransferMarketFlow.nav')
        self.assertEqual(state['outputs'],dict(back='MainMenuHub',Back='MainMenuHub'))
        view=flow()['states'][0]
        self.assertIn(['loadView',['screen',PAGE]],view['onEnter'])
        for transition in view['transitions']:
            if transition['event'] in ('Back','back'):
                self.assertEqual(transition['targets'],['Back'])
                self.assertIn(['executeCMAction',['ReturnToHubFromCalendar']],transition['actions'])
    def test_retired_bootstrap_is_removed_without_adding_hub_dependencies(self):
        path=self.game/'ModCarrerMode/backups/transfer_market_20261024/data/ui/layout/careermanagerhubcfg.xml'
        root=ET.fromstring(path.read_bytes());before=len(root.find('components'))
        ET.SubElement(root.find('components'),'component',PATH='game/screens/career/server16/MarketHubBootstrap.swf',X='0',Y='0')
        changed=ET.fromstring(carousel(ET.tostring(root)))
        self.assertEqual(len(changed.find('components')),before)
        self.assertFalse(any(n.get('DATAPROVIDERID') for n in next(t for t in changed.find('panel_2').findall('tile') if t.find('tileid').get('NAME')=='GTN_STATIC').iter()))
    def test_navigation_only_adds_market_branch_and_uses_existing_lifecycle(self):
        before=(self.game/'data/ui/nav/careermode/mainmenuhubflow.nav').read_bytes();after=navigation(before)
        self.assertEqual(after,navigation(after));original=read_nav(before);modified=read_nav(after)
        self.assertEqual(sum(n.get('event')==EVENT for n in walk(modified)),1)
        for document in (original,modified):
            for node in walk(document):
                if 'transitions' in node:node['transitions']=[t for t in node['transitions'] if t.get('event')!=EVENT]
                if 'states' in node:node['states']=[s for s in node['states'] if s.get('name')!='Server16TransferMarket']
        self.assertEqual(original,modified)
        state=flow()['states'][0]
        self.assertIn(['loadView',['screen',PAGE]],state['onEnter']);self.assertIn(['unloadView',['screen',PAGE]],state['onExit'])
        self.assertFalse(any(a=='loadViewModel' for a,args in state['onEnter']))
        self.assertEqual({t['event'] for t in state['transitions']},{'Back','back','Server16RefreshTransferMarket'})
    def test_readonly_projection_uses_current_club_and_calendar_when_requested(self):
        sample=self.saved();path=Path(sample['saveFile']);before=hashlib.sha256(path.read_bytes()).hexdigest()
        result=read_snapshot(self.game,path,club_override=1043,date_override=20260210)
        self.assertEqual(result['clubId'],1043);self.assertEqual(result['careerDate'],'2026-02-10');self.assertEqual(result['myLeague']['clubId'],1043)
        self.assertEqual(result['summary']['completedDeals'],20);self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)
        with self.assertRaises(ValueError):read_snapshot(self.game,path,date_override=20250101)
    def test_never_publish_package_if_career_changes_during_build(self):
        snapshot=dict(save=dict(path='unused',pid=123),profile=dict(club_id=1043,userid=0,context_epoch=2),date=20260101,signature=('old',))
        payload=self.saved();payload['savedDate']=20260206
        with patch.object(worker,'read_snapshot',return_value=payload),patch.object(worker,'export_assets',return_value=({},[])),patch.object(worker,'ROOT',self.folder),patch.object(worker,'DEST',self.folder/'deployed.big'),patch.object(worker,'observe',return_value=dict(signature=('new',))):
            with self.assertRaisesRegex(RuntimeError,'mudou'):worker.publish(snapshot,object(),live=dict(entry=1,revision='x',capturedMs=1000))
            self.assertFalse((self.folder/'deployed.big').exists())
    def test_unavailable_view_has_safe_tab_targets_and_back(self):
        output=self.folder/'waiting.big';scenes=worker.placeholder();build(self.game,output,scenes,{})
        vm,screen,apt,calls=open_native(output);vm.invoke(screen.get('ChangeTab'),screen,[1]);self.assertEqual(screen.get('page'),1)
        vm.invoke(screen.get('Back'),screen);self.assertEqual(screen.get('page'),0)
    def test_runtime_never_requests_memory_write_or_remote_execution(self):
        text=Path(worker.__file__).read_text(encoding='utf8')
        self.assertIn('OpenProcess(0x410,False',text)
        for forbidden in ('WriteProcessMemory','CreateRemoteThread','VirtualAllocEx','sqlite3.connect'):
            self.assertNotIn(forbidden,text)
    def test_native_waiting_view_polls_automatically_and_back_remains_available(self):
        output=self.folder/'waiting.big';build(self.game,output,worker.placeholder(),{})
        vm,screen,apt,calls=open_native(output)
        self.assertTrue(screen.get('waiting'));self.assertTrue(screen.get('loadingCover').get('_visible'))
        for _ in range(90):vm.invoke(screen.get('PollAutomatic'),screen)
        self.assertIn(('SendSystemEvent',['Calendar','Server16RefreshTransferMarket','']),calls)
        self.assertTrue(screen.get('autoReloading'))
        self.assertIsNotNone(screen.get('onEnterFrame'))
        for _ in range(90):vm.invoke(screen.get('PollAutomatic'),screen)
        self.assertEqual(sum(c==('SendSystemEvent',['Calendar','Server16RefreshTransferMarket','']) for c in calls),2)
        vm.invoke(screen.get('LocalEventHandler'),screen,[1,0]);self.assertIn(('SendEvent',['Calendar','Back','']),calls)
        self.assertFalse(screen.get('autoReloading'))
    def test_physical_shoulders_change_tabs_but_triggers_do_not(self):
        scenes,vm,screen,calls=self.screen();first=screen.get('page')
        for trigger in (8,9):vm.invoke(screen.get('LocalEventHandler'),screen,[trigger,0]);self.assertEqual(screen.get('page'),first)
        vm.invoke(screen.get('LocalEventHandler'),screen,[12,0]);self.assertNotEqual(screen.get('page'),first)
        vm.invoke(screen.get('LocalEventHandler'),screen,[11,0]);self.assertEqual(screen.get('page'),first)
    def test_left_stick_and_keyboard_page_deals_circularly_without_changing_tabs(self):
        scenes,vm,screen,calls=self.screen();keys={s['key']:i for i,s in enumerate(scenes)}
        vm.invoke(screen.get('Go'),screen,[keys['deals']])
        for code,destination in ((14,'deals:1'),(6,'deals:2'),(13,'deals:1'),(5,'deals')):
            vm.invoke(screen.get('LocalEventHandler'),screen,[code,0]);self.assertEqual(screen.get('page'),keys[destination])
        vm.invoke(screen.get('LocalEventHandler'),screen,[13,0]);self.assertEqual(screen.get('page'),keys['deals:3'])
        help_items=vm.invoke(screen.get('getHelpContext'),screen)
        self.assertIn(('LAS_LR','Páginas'),[(code,label.encode('latin1').decode('utf8') if 'Ã' in label else label) for code,label in help_items])
        self.assertTrue(any(n['type']=='dot' for n in scenes[keys['deals']]['nodes']))
        self.assertFalse(any('Anterior' in a['label'] or 'Próxima' in a['label'] for a in scenes[keys['deals']]['actions']))
    def test_fresh_capture_republishes_even_if_entry_id_does_not_change(self):
        signature=('career','same-entry')
        self.assertFalse(worker.publication_due(signature,200,signature,100,3.9))
        self.assertTrue(worker.publication_due(signature,200,signature,100,4))
        self.assertFalse(worker.publication_due(signature,100,signature,100,20))
        self.assertTrue(worker.publication_due(('other',),100,signature,100,0))
    def test_ready_snapshot_with_same_entry_gets_new_token_without_decoding_again(self):
        snapshot=dict(save=dict(path='unused',pid=123),profile=dict(club_id=1043,userid=0,context_epoch=2),date=20260111,signature=('fresh-capture',))
        payload=self.saved();payload['savedDate']=20260101
        with patch.object(worker,'_prepared',None),patch.object(worker,'read_snapshot',return_value=payload) as reader,patch.object(worker,'export_assets',return_value=({},[])) as artwork,patch.object(worker,'ROOT',self.folder),patch.object(worker,'DEST',self.folder/'deployed.big'):
            first=worker.publish(snapshot,live=dict(entry=7,revision='same-deals',capturedMs=1000))
            second=worker.publish(snapshot,live=dict(entry=7,revision='same-deals',capturedMs=5000))
            self.assertNotEqual(first['entry_token'],second['entry_token']);self.assertEqual(reader.call_count,1);self.assertEqual(artwork.call_count,1)
            def setup(vm,calls):
                vm.global_.set('Server16MarketEntryAwaiting',True);vm.global_.set('Server16MarketEntryToken',first['entry_token'])
            vm,screen,apt,calls=open_native(self.folder/'deployed.big',setup=setup)
            self.assertFalse(screen.get('waiting'));self.assertFalse(screen.get('loadingCover').get('_visible'))
    def test_auto_reload_requires_a_new_entry_snapshot_and_stops_once_ready(self):
        data=self.saved();scenes=[s for s in make_scenes(data) if s['key']!='entry']
        for s in scenes:s.update(automatic=True,ready=True,entryToken='same-session:12')
        output=self.folder/'market.big';build(self.game,output,scenes,{})
        def state(old):
            def setup(vm,calls):
                vm.global_.set('Server16MarketEntryAwaiting',True);vm.global_.set('Server16MarketEntryToken',old)
            return setup
        vm,screen,apt,calls=open_native(output,setup=state('same-session:12'))
        self.assertTrue(screen.get('waiting'))
        vm,screen,apt,calls=open_native(output,setup=state('same-session:11'))
        self.assertFalse(screen.get('waiting'));self.assertFalse(screen.get('loadingCover').get('_visible'))
        self.assertFalse(vm.global_.get('Server16MarketEntryAwaiting'));self.assertIsNone(screen.get('onEnterFrame'))
        vm.invoke(screen.get('OnExitScreen'),screen);self.assertFalse(vm.global_.get('Server16MarketEntryAwaiting'))
    def test_empty_states_and_all_actions_stay_clear_of_native_footer(self):
        data=self.saved();data['transfers']=[];data['myLeague']['transfers']=[]
        for scene in make_scenes(data):
            if scene['key']=='entry':continue
            for node in scene['nodes']:
                if node['y']>=930:continue
                if node['x']==0 and node['y']==0:continue
                self.assertLessEqual(node['y']+node['h'],918,(scene['key'],node))
            self.assertNotIn('refresh',[a['target'] for a in scene['actions']])
            self.assertFalse(any('Atualização automática' in n.get('text','') for n in scene['nodes']))
    def bootstrap(self):
        file=self.folder/'bootstrap.big';hub_bootstrap.build(self.game,file)
        proto=Object({'ProcessData':Native('original_scout_process')})
        def setup(vm,calls):
            vm.global_.get('game').set('fluxHelpers',Object({'CareerHubDataHelper':Object({'prototype':proto})}))
            vm.global_.get('game').set('uif',Object({'UIFDataProviderList':Object({'CM_SCOUT_REPORT_DP':123})}))
            vm.global_.get('game').set('components',Object({'FluxCore':Object({'FluxComponent':Object({'prototype':Object({'SetHelper':Native('stock_SetHelper'),'UnregisterForData':Native('stock_UnregisterForData')})})})}))
            vm.global_.set('MovieClip',Object({'prototype':Object()}))
        def original(owner,args):
            new,sender,view=args
            if new.get('header').get('dpId')==123:sender.set('LENGTH',new.get('data')[0].get('LENGTH')-1)
            else:sender.set('original_other_called',True)
            return sender
        vm,screen,apt,calls=open_native(file,hub_bootstrap.FULL,setup,{'original_scout_process':original})
        return vm,screen,proto,calls,apt
    def test_dynamic_scout_count_keeps_exactly_one_market_and_no_empty_reports(self):
        vm,screen,proto,calls,apt=self.bootstrap();helper=Object(prototype=proto)
        for count in range(1,7):
            data=Object({'ID':208});new=Object({'header':Object({'dpId':123}),'data':[Object({'LENGTH':count})]})
            vm.invoke(proto.get('ProcessData'),helper,[new,data,Object()])
            self.assertEqual(data.get('LENGTH'),count)
            if count<6:
                self.assertEqual(data.get(f'SUBTILE_{count}_DESTINATION'),EVENT)
                # The generic offline APT reader exposes string bytes as latin1;
                # our emitted strings are UTF-8, as in the other native screens.
                self.assertEqual(data.get(f'SUBTILE_{count}_TITLE_PARAM').encode('latin1').decode('utf8'),'MERCADO DE TRANSFERÊNCIAS')
                self.assertEqual(data.get(f'SUBTILE_{count}_INFO_0_VISIBLE'),'FALSE')
            self.assertTrue(proto.get('Server16MarketInstalled'))
        self.assertEqual(sum(name=='original_scout_process' for name,args in calls),6)
    def test_market_scout_wrapper_restores_layout_when_report_count_changes(self):
        vm,screen,proto,calls,apt=self.bootstrap();helper=Object(prototype=proto);data=Object({'ID':208})
        for slot in (1,2):
            data.set(f'SUBTILE_{slot}_DESTINATION','EnterGTNScoutReportFromReportTile')
            data.set(f'SUBTILE_{slot}_INFO_0_VISIBLE','TRUE')
            data.set(f'SUBTILE_{slot}_TITLE_PARAM','Relatório '+str(slot))
        def apply(count):
            new=Object({'header':Object({'dpId':123}),'data':[Object({'LENGTH':count})]})
            vm.invoke(proto.get('ProcessData'),helper,[new,data,Object()])
        apply(1);self.assertEqual(data.get('SUBTILE_1_DESTINATION'),EVENT)
        apply(2);self.assertEqual(data.get('SUBTILE_1_DESTINATION'),'EnterGTNScoutReportFromReportTile')
        self.assertEqual(data.get('SUBTILE_1_TITLE_PARAM'),'Relatório 1')
        self.assertEqual(data.get('SUBTILE_1_INFO_0_VISIBLE'),'TRUE');self.assertEqual(data.get('SUBTILE_2_DESTINATION'),EVENT)
        apply(6);self.assertEqual(data.get('LENGTH'),6);self.assertEqual(data.get('SUBTILE_2_TITLE_PARAM'),'Relatório 2')
    def test_helper_delegates_every_other_provider_and_installs_only_once(self):
        vm,screen,proto,calls,apt=self.bootstrap();original=proto.get('Server16MarketOriginalProcessData')
        vm.invoke(screen.get('Install'),screen);self.assertIs(proto.get('Server16MarketOriginalProcessData'),original)
        data=Object({'ID':208});new=Object({'header':Object({'dpId':999}),'data':[]})
        vm.invoke(proto.get('ProcessData'),Object(prototype=proto),[new,data,Object()])
        self.assertTrue(data.get('original_other_called'));self.assertIsNone(data.get('Server16MarketLastSlot'))
    def test_hub_component_readiness_never_blocks_the_entire_career_screen(self):
        vm,component,proto,calls,apt=self.bootstrap()
        # FluxHub waits on every XML component, including invisible components.
        # A generic MovieClip has no such contract and leaves the whole hub hidden.
        self.assertIsNotNone(component.get('IsLoaded'))
        self.assertIsNotNone(component.get('IsReady'))
        self.assertIs(vm.invoke(component.get('IsLoaded'),component),True)
        self.assertIs(vm.invoke(component.get('IsReady'),component),True)
        base=vm.path('game.components.FluxCore.FluxComponent').get('prototype')
        self.assertIs(component.prototype.prototype,base)
        data=Object({'ID':'SERVER16_MARKET_BOOTSTRAP'})
        vm.invoke(component.get('Initialize'),component,[data])
        self.assertIs(component.get('m_oData'),data)
        vm.invoke(component.get('Shutdown'),component)
        self.assertIsNone(component.get('onEnterFrame'))
        self.assertIsNone(component.get('m_oDataHelper'))
    def test_native_function_headers_match_fifa_relocation_contract(self):
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
        from validate_frontend_ui import validate_native_headers
        from apt_actions import Actions
        scenes,vm,screen,calls=self.screen();file=self.folder/'market.big'
        from formats import AptFile,BigFile
        validate_native_headers(Actions(AptFile(BigFile(file))).read_all())
        vm,screen,proto,calls,apt=self.bootstrap();validate_native_headers(Actions(apt).read_all())

if __name__=='__main__':unittest.main(verbosity=2)
