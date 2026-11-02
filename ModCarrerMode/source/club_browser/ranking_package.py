"""Keep both world ranking destinations in one career carousel."""
from pathlib import Path
import sys,json,xml.etree.ElementTree as ET
from package import read_nav,walk
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from reorganize_career_hub import pages,arrange
XML='data/ui/layout/careermanagerhubcfg.xml';NAV='data/ui/nav/careermode/mainmenuhubflow.nav'
ENTRIES=(('clubs','panel_4','PLAYER_STATS','WorldClubRanking','RANKING DE CLUBES'),('nations','panel_4','PLAYER_STATS','WorldNationRanking','RANKING DE SELEÇÕES'))

def layout(raw):
    root=ET.fromstring(raw);used={n.get('ID') for n in root.iter()}|{n.get('tileid') for n in root.iter()}
    events={'Server16Enter'+entry[3] for entry in ENTRIES};found={}
    # Also migrate installations where the selection ranking was in Other
    # leagues. Preserve that card's other slides, IDs, artwork and callbacks.
    for panel in root:
        for card in panel.findall('tile'):
            slides=pages(card);ranked=[s for s in slides if s.get('DESTINATION') in events]
            for slide in ranked:
                event=slide.get('DESTINATION')
                if event in found:raise ValueError('Card de ranking duplicado.')
                found[event]=slide
            if ranked:
                remaining=[s for s in slides if s.get('DESTINATION') not in events]
                if not remaining:raise ValueError('O carrossel de origem precisa manter sua página principal.')
                arrange(card,remaining)
    for kind,panel,name,page,title in ENTRIES:
        event='Server16Enter'+page
        tiles=[t for t in root.find(panel).findall('tile') if t.find('tileid').get('NAME')==name]
        if len(tiles)!=1:raise ValueError('Card de origem do ranking não identificado.')
        tile=tiles[0];content=pages(tile)
        for slide in content:
            if not slide.get('ID'):
                value=next(str(i) for i in range(1951,1999) if str(i) not in used);used.add(value);slide.set('ID',value)
        extra=found.get(event)
        if extra is None:
            ident=next(str(i) for i in range(1951,1999) if str(i) not in used);used.add(ident)
            extra=ET.Element('subtile',ID=ident,SUBTILE_TYPE='TILE',DESTINATION=event,FG_PATH='',BG_ICON='OtherLeagues_Small')
            ET.SubElement(extra,'data',ID='TITLE',TYPE='title',PARAM=title,TRANSLATE='FALSE',FORMAT='HS',WIDTH='730',HEIGHT='48',X='22',Y='18')
            ET.SubElement(extra,'data',ID='S16_RANKING_DESCRIPTION',TYPE='text',PARAM='Pontuação mundial e resultados da carreira',TRANSLATE='FALSE',FORMAT='SM',WIDTH='730',HEIGHT='55',X='22',Y='94')
        content.append(extra);arrange(tile,content)
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def navigation(raw):
    if isinstance(raw,bytes):raw=raw.decode('utf-8-sig')
    nav=read_nav(raw);hosts=[n for n in walk(nav) if any(t.get('event')=='Server16EnterClubBrowser' for t in n.get('transitions',[]))];owners=[n for n in walk(nav) if any(s.get('name')=='Server16ClubBrowser' for s in n.get('states',[]))]
    if len(hosts)!=1 or len(owners)!=1:raise ValueError('Navegação de carreira incompatível.')
    for _,_,_,page,_ in ENTRIES:
        event='Server16Enter'+page;state='Server16'+page
        if not any(t.get('event')==event for t in hosts[0]['transitions']):hosts[0]['transitions'].append(dict(event=event,targets=[state]))
        if not any(s.get('name')==state for s in owners[0]['states']):owners[0]['states'].append(dict(name=state,type='external',file='/careerMode/server16'+page+'Flow.nav',outputs=dict(back='MainMenuHub',Back='MainMenuHub')))
    return (json.dumps(nav,ensure_ascii=False,indent=2)+'\n').encode('utf8')

def flow(page):
    full='game/screens/career/server16/'+page
    return dict(name='Server16'+page+'Flow',initial=dict(targets=['Ranking']),states=[dict(name='Ranking',onEnter=[['executeCMAction',['EnterCalendar']],['loadScreenController',['Calendar']],['loadView',['screen',full]],['loadView',['background','FIFA','BOOTFLOW']]],onExit=[['unloadView',['screen',full]],['unloadScreenController',['Calendar']],['unloadView',['background']]],transitions=[dict(event=e,targets=['Back'],actions=[['executeCMAction',['ReturnToHubFromCalendar']]]) for e in ('Back','back')])])

def stage(game,output):
    game,output=Path(game),Path(output);files={XML:layout((game/XML).read_bytes()),NAV:navigation((game/NAV).read_bytes())}
    for _,_,_,page,_ in ENTRIES:files['data/ui/nav/careermode/server16'+page.lower()+'flow.nav']=(json.dumps(flow(page),ensure_ascii=False,indent=2)+'\n').encode('utf8')
    for name,blob in files.items():p=output/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(blob)
    return list(files)
