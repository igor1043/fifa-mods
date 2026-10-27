"""Add only the transfer-market carousel slides and its isolated NAV flow."""
import copy,json,re,xml.etree.ElementTree as ET
from pathlib import Path

EVENT='Server16EnterTransferMarket'
PAGE='game/screens/career/server16/TransferMarket'
XML='data/ui/layout/careermanagerhubcfg.xml'
NAV='data/ui/nav/careermode/mainmenuhubflow.nav'
FLOW='data/ui/nav/careermode/server16transfermarketflow.nav'
BOOTSTRAP='game/screens/career/server16/MarketHubBootstrap.swf'

def read_nav(raw):
    text=raw.decode('utf-8-sig') if isinstance(raw,bytes) else raw
    text=re.sub(r'"(?:\\.|[^"\\])*"|/\*.*?\*/|//[^\r\n]*',lambda m:m[0] if m[0].startswith('"') else '',text,flags=re.S)
    return json.loads(re.sub(r',\s*([\]}])',r'\1',text))

def walk(v):
    if isinstance(v,dict):
        yield v
        for x in v.values():yield from walk(x)
    elif isinstance(v,list):
        for x in v:yield from walk(x)

def carousel(raw):
    root=ET.fromstring(raw)
    components=root.find('components')
    # Retire the standalone component. It must never join the hub load barrier.
    for node in list(components):
        if node.get('PATH')==BOOTSTRAP:components.remove(node)
    panel=root.find('panel_2')
    # Upgrade an installation of the first prototype without touching reports.
    for tile in panel.findall('tile'):
        if tile.find('tileid').get('NAME')!='SCOUT_REPORT':continue
        removed=False
        for node in list(tile):
            if node.get('DESTINATION')==EVENT:tile.remove(node);removed=True
        if removed:
            settings=tile.find('settings');settings.attrib.pop('ENABLE_CYCLING',None)
            counter=tile.find('number_of_subtiles')
            if tile.find('tileid').get('tileid')=='215':
                settings.set('FILE_PATH','TILE');tile.find('main_tile').attrib.pop('ID',None)
                if counter is not None:tile.remove(counter)
            elif counter is not None:counter.set('LENGTH',str(sum(n.tag.startswith('subtile') for n in tile)))
    candidates=[t for t in panel.findall('tile') if t.find('tileid').get('NAME')=='GTN_STATIC']
    if len(candidates)!=1:raise ValueError('Não foi encontrado o card Rede Mundial na aba Transferências.')
    tile=candidates[0]
    if tile.find('tileid').get('DATAPROVIDERID'):raise ValueError('O card estático recebeu um provider; não alterar esse layout.')
    if not any(n.get('DESTINATION')==EVENT for n in tile):
        if any(n.tag.startswith('subtile') for n in tile):raise ValueError('O carrossel da Rede Mundial já foi modificado por outro recurso.')
        original=copy.deepcopy(tile.find('main_tile'));original.tag='subtile1';original.set('SUBTILE_TYPE','TILE')
        used={n.get('ID') for n in root.iter() if n.get('ID')}|{n.get('tileid') for n in root.iter('tileid')}
        def ident():
            value=next(str(n) for n in range(225,240) if str(n) not in used);used.add(value);return value
        original.set('ID',ident())
        for node in list(tile.findall('data')):tile.remove(node);original.append(node)
        tile.append(original)
        settings=tile.find('settings');settings.set('FILE_PATH','TILE_NESTED');settings.set('ENABLE_CYCLING','TRUE')
        main=tile.find('main_tile');main.attrib.clear();main.attrib.update(SUBTILE_TYPE='TILE',DESTINATION=EVENT,FG_PATH='',BG_ICON='GlobalTransferNetwork_Med',ID=ident(),NAME='SERVER16_TRANSFER_MARKET')
        tile.find('number_of_subtiles').set('LENGTH','1')
        ET.SubElement(tile,'data',ID='TITLE',TYPE='title',PARAM='MERCADO DE TRANSFERÊNCIAS',TRANSLATE='FALSE',FORMAT='HS')
        ET.SubElement(tile,'data',ID='MARKET_DESCRIPTION',TYPE='text',PARAM='Resumo, ligas, clubes e negócios da carreira',TRANSLATE='FALSE',FORMAT='I',WIDTH='590',HEIGHT='65',X='18',REL_TARGET='TITLE',REL_Y='-17')
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def navigation(raw):
    nav=read_nav(raw)
    hosts=[n for n in walk(nav) if any(t.get('event')=='Server16EnterBankLoans' for t in n.get('transitions',[]))]
    owners=[n for n in walk(nav) if any(s.get('name')=='Server16BankLoans' for s in n.get('states',[]))]
    if len(hosts)!=1 or len(owners)!=1:raise ValueError('Fluxo de carreira incompatível.')
    if not any(t.get('event')==EVENT for t in hosts[0]['transitions']):hosts[0]['transitions'].append(dict(event=EVENT,targets=['Server16TransferMarket']))
    if not any(s.get('name')=='Server16TransferMarket' for s in owners[0]['states']):
        owners[0]['states'].append(dict(name='Server16TransferMarket',type='external',file='/careerMode/server16TransferMarketFlow.nav',outputs=dict(back='MainMenuHub',Back='MainMenuHub')))
    return (json.dumps(nav,ensure_ascii=False,indent=2)+'\n').encode('utf8')

def flow():
    # Use the existing Calendar controller only for the native screen lifecycle,
    # exactly as loans. No calendar view/model is opened or date advanced.
    return dict(name='Server16TransferMarketFlow',initial=dict(targets=['Market']),states=[dict(name='Market',
        onEnter=[['executeCMAction',['EnterCalendar']],['loadScreenController',['Calendar']],['loadView',['screen',PAGE+'Loading']],['loadView',['background','BOOTFLOW']]],
        onExit=[['unloadView',['screen']],['unloadScreenController',['Calendar']],['unloadView',['background']]],
        transitions=[dict(event='Server16RefreshTransferMarket',actions=[['unloadView',['screen']],['loadView',['screen',PAGE]]])]+
        [dict(event=e,targets=['Back'],actions=[['executeCMAction',['ReturnToHubFromCalendar']]]) for e in ('Back','back')])])

def stage(game,folder):
    game=Path(game);folder=Path(folder)
    files={XML:carousel((game/XML).read_bytes()),NAV:navigation((game/NAV).read_bytes()),FLOW:(json.dumps(flow(),ensure_ascii=False,indent=2)+'\n').encode('utf8')}
    for name,blob in files.items():
        path=folder/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob)
    return list(files)
