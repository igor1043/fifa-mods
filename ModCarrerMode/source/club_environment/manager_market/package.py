"""Add one office carousel slide and an isolated native controller flow."""
from pathlib import Path
import json,xml.etree.ElementTree as ET
from build_package import read_nav,walk
EVENT='Server16EnterManagerMarket';PAGE='game/screens/career/server16/ManagerMarket'
XML='data/ui/layout/careermanagerhubcfg.xml';NAV='data/ui/nav/careermode/mainmenuhubflow.nav';FLOW='data/ui/nav/careermode/server16managermarketflow.nav'

def layout(raw):
 root=ET.fromstring(raw)
 if any(n.get('DESTINATION')==EVENT for n in root.iter()):return raw
 # Append beside the existing finance entry so current Office cards survive.
 tile=next((t for t in root.iter('tile') if any(n.get('DESTINATION')=='Server16EnterClubFinance' for n in t)),None)
 if tile is None:raise ValueError('Card do Escritório/Finanças não encontrado')
 if tile.find('settings').get('FILE_PATH')!='TILE_NESTED':raise ValueError('Carrossel do Escritório incompatível')
 used={n.get('ID') for n in root.iter()}|{n.get('tileid') for n in root.iter('tileid')};ident=next(str(i) for i in range(1001,1100) if str(i) not in used);count=sum(n.tag.startswith('subtile') for n in tile)
 node=ET.SubElement(tile,'subtile'+str(count+1),SUBTILE_TYPE='TILE',DESTINATION=EVENT,FG_PATH='',BG_ICON='GlobalTransferNetwork_Med',ID=ident)
 ET.SubElement(node,'data',ID='TITLE',TYPE='title',PARAM='MERCADO DE TÉCNICOS',TRANSLATE='FALSE',FORMAT='HS')
 ET.SubElement(node,'data',TYPE='text',PARAM='Clubes, demissões e técnicos livres no mercado',TRANSLATE='FALSE',FORMAT='I',WIDTH='365',HEIGHT='80',X='18',REL_TARGET='TITLE',REL_Y='-17')
 tile.find('number_of_subtiles').set('LENGTH',str(count+1));tile.find('settings').set('ENABLE_CYCLING','TRUE')
 return ET.tostring(root,encoding='utf-8',xml_declaration=True)
def navigation(raw):
 nav=read_nav(raw.decode('utf-8-sig') if isinstance(raw,bytes) else raw);hosts=[n for n in walk(nav) if any(t.get('event')=='Server16EnterBankLoans' for t in n.get('transitions',[]))];owners=[n for n in walk(nav) if any(s.get('name')=='Server16BankLoans' for s in n.get('states',[]))]
 if len(hosts)!=1 or len(owners)!=1:raise ValueError('Hub da carreira incompatível')
 if not any(t.get('event')==EVENT for t in hosts[0]['transitions']):hosts[0]['transitions'].append(dict(event=EVENT,targets=['Server16ManagerMarket']))
 if not any(s.get('name')=='Server16ManagerMarket' for s in owners[0]['states']):owners[0]['states'].append(dict(name='Server16ManagerMarket',type='external',file='/careerMode/server16ManagerMarketFlow.nav',outputs=dict(back='MainMenuHub',Back='MainMenuHub')))
 return (json.dumps(nav,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def flow():
 return dict(name='Server16ManagerMarketFlow',initial=dict(targets=['Managers']),states=[dict(name='Managers',onEnter=[['executeCMAction',['EnterCalendar']],['loadScreenController',['Calendar']],['loadView',['screen',PAGE]],['loadView',['background','BOOTFLOW']]],onExit=[['unloadView',['screen']],['unloadScreenController',['Calendar']],['unloadView',['background']]],transitions=[dict(event='Server16RefreshManagerMarket',actions=[['unloadView',['screen']],['loadView',['screen',PAGE]]])]+[dict(event=e,targets=['Back'],actions=[['executeCMAction',['ReturnToHubFromCalendar']]]) for e in ('Back','back')])])
def stage(game,target):
 game,target=Path(game),Path(target);files={XML:layout((game/XML).read_bytes()),NAV:navigation((game/NAV).read_bytes()),FLOW:(json.dumps(flow(),ensure_ascii=False,indent=2)+'\n').encode('utf8')}
 for rel,raw in files.items():p=target/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 return list(files)
