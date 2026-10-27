"""Narrow, idempotent hub integration, based on the installed layout."""
import copy,json,sys,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'club_environment/market'))
from build_package import read_nav,walk

EVENT='Server16EnterClubBrowser';STATE='Server16ClubBrowser'
XML='data/ui/layout/careermanagerhubcfg.xml'
NAV='data/ui/nav/careermode/mainmenuhubflow.nav'
FLOW='data/ui/nav/careermode/server16clubbrowserflow.nav'
PAGE='game/screens/career/server16/ClubBrowser'

def carousel(raw):
    root=ET.fromstring(raw)
    candidates=[t for t in root.find('panel_4').findall('tile') if t.find('tileid').get('NAME')=='OTHER_LEAGUES']
    if len(candidates)!=1:raise ValueError('Card Outras ligas não identificado')
    tile=candidates[0]
    if tile.find('tileid').get('DATAPROVIDERID'):raise ValueError('Card possui provider externo')
    if not any(n.get('DESTINATION')==EVENT for n in tile):
        if any(n.tag.startswith('subtile') for n in tile):raise ValueError('Outras ligas já possui outro carrossel')
        used={n.get('ID') for n in root.iter() if n.get('ID')}|{n.get('tileid') for n in root.iter('tileid')}
        def ident():
            value=next(str(i) for i in range(1901,1999) if str(i) not in used);used.add(value);return value
        main=tile.find('main_tile');main.set('SUBTILE_TYPE','TILE');main.set('ID',ident())
        extra=ET.SubElement(tile,'subtile1',SUBTILE_TYPE='TILE',ID=ident(),NAME='SERVER16_CLUB_BROWSER',DESTINATION=EVENT,FG_PATH='',BG_ICON='OtherLeagues_Small')
        ET.SubElement(extra,'data',ID='TITLE',TYPE='title',PARAM='VER CLUBES',TRANSLATE='FALSE',FORMAT='HS')
        ET.SubElement(extra,'data',ID='CLUB_BROWSER_DESCRIPTION',TYPE='text',PARAM='Explore os clubes, as ligas e o mundo do futebol',TRANSLATE='FALSE',FORMAT='I',WIDTH='590',HEIGHT='45',X='18',REL_TARGET='TITLE',REL_Y='-17')
        settings=tile.find('settings');settings.set('FILE_PATH','TILE_NESTED');settings.set('ENABLE_CYCLING','TRUE')
        counter=tile.find('number_of_subtiles')
        if counter is None:counter=ET.SubElement(tile,'number_of_subtiles')
        counter.set('LENGTH','1')
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def navigation(raw):
    nav=read_nav(raw)
    hosts=[n for n in walk(nav) if any(t.get('event')=='Server16EnterBankLoans' for t in n.get('transitions',[]))]
    owners=[n for n in walk(nav) if any(s.get('name')=='Server16BankLoans' for s in n.get('states',[]))]
    if len(hosts)!=1 or len(owners)!=1:raise ValueError('Navegação de carreira incompatível')
    if not any(t.get('event')==EVENT for t in hosts[0]['transitions']):hosts[0]['transitions'].append(dict(event=EVENT,targets=[STATE]))
    if not any(s.get('name')==STATE for s in owners[0]['states']):owners[0]['states'].append(dict(name=STATE,type='external',file='/careerMode/server16ClubBrowserFlow.nav',outputs=dict(back='MainMenuHub',Back='MainMenuHub')))
    return (json.dumps(nav,ensure_ascii=False,indent=2)+'\n').encode('utf8')

def flow():
    return dict(name='Server16ClubBrowserFlow',initial=dict(targets=['Clubs']),states=[dict(name='Clubs',
        onEnter=[['executeCMAction',['EnterCalendar']],['loadScreenController',['Calendar']],['loadView',['screen',PAGE]],['loadView',['background','FIFA','BOOTFLOW']]],
        onExit=[['unloadView',['screen',PAGE]],['unloadScreenController',['Calendar']],['unloadView',['background']]],
        transitions=[dict(event=e,targets=['Back'],actions=[['executeCMAction',['ReturnToHubFromCalendar']]]) for e in ('Back','back')])])

def stage(game,output):
    files={XML:carousel((game/XML).read_bytes()),NAV:navigation((game/NAV).read_bytes()),FLOW:(json.dumps(flow(),ensure_ascii=False,indent=2)+'\n').encode('utf8')}
    for name,blob in files.items():
        target=output/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob)
    return list(files)

if __name__=='__main__':print(stage(Path(sys.argv[1]),Path(sys.argv[2])))
