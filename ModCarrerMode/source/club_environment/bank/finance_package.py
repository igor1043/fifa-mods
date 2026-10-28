"""Add a finance slide to the existing Office carousel; preserve every tile."""
from pathlib import Path
import json,xml.etree.ElementTree as ET
from build_package import read_nav,walk
from finance_ui import PAGE

XML='data/ui/layout/careermanagerhubcfg.xml';NAV='data/ui/nav/careermode/mainmenuhubflow.nav'
FLOW='data/ui/nav/careermode/server16clubfinanceflow.nav';EVENT='Server16EnterClubFinance'

def layout(raw):
 root=ET.fromstring(raw);panel=root.find('panel_3')
 candidates=[t for t in panel.findall('tile') if t.find('tileid').get('NAME')=='REQUEST_FUNDS']
 if len(candidates)!=1:raise ValueError('Card do Escritório não encontrado')
 tile=candidates[0]
 if any(n.get('DESTINATION')==EVENT for n in tile):return raw
 if tile.find('settings').get('FILE_PATH')!='TILE_NESTED':raise ValueError('Carrossel financeiro incompatível')
 subtiles=[n for n in tile if n.tag.startswith('subtile')];used={n.get('ID') for n in root.iter()}|{n.get('tileid') for n in root.iter('tileid')}
 ident=next(str(i) for i in range(920,1000) if str(i) not in used)
 node=ET.SubElement(tile,'subtile'+str(len(subtiles)+1),SUBTILE_TYPE='TILE',DESTINATION=EVENT,FG_PATH='',BG_ICON='RequestFunds_Small',ID=ident)
 ET.SubElement(node,'data',ID='TITLE',TYPE='title',PARAM='FINANÇAS DO CLUBE',TRANSLATE='FALSE',FORMAT='HS')
 ET.SubElement(node,'data',TYPE='text',PARAM='TV, bilheteria, despesas e extrato mensal',TRANSLATE='FALSE',FORMAT='I',WIDTH='365',HEIGHT='80',X='18',REL_TARGET='TITLE',REL_Y='-17')
 tile.find('number_of_subtiles').set('LENGTH',str(len(subtiles)+1));tile.find('settings').set('ENABLE_CYCLING','TRUE')
 return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def navigation(raw):
 nav=read_nav(raw.decode('utf-8-sig'));hosts=[n for n in walk(nav) if any(t.get('event')=='Server16EnterBankLoans' for t in n.get('transitions',[]))]
 owners=[n for n in walk(nav) if any(s.get('name')=='Server16BankLoans' for s in n.get('states',[]))]
 if len(hosts)!=1 or len(owners)!=1:raise ValueError('Fluxo financeiro da carreira incompatível')
 if not any(t.get('event')==EVENT for t in hosts[0]['transitions']):hosts[0]['transitions'].append(dict(event=EVENT,targets=['Server16ClubFinance']))
 if not any(s.get('name')=='Server16ClubFinance' for s in owners[0]['states']):owners[0]['states'].append(dict(name='Server16ClubFinance',type='external',file='/careerMode/server16ClubFinanceFlow.nav',outputs=dict(back='MainMenuHub',Back='MainMenuHub')))
 return (json.dumps(nav,ensure_ascii=False,indent=2)+'\n').encode('utf8')

def flow():
 return dict(name='Server16ClubFinanceFlow',initial=dict(targets=['Finance']),states=[dict(name='Finance',
  onEnter=[['executeCMAction',['EnterCalendar']],['loadScreenController',['Calendar']],['loadView',['screen',PAGE]],['loadView',['background','BOOTFLOW']]],
  onExit=[['unloadView',['screen']],['unloadScreenController',['Calendar']],['unloadView',['background']]],
  transitions=[dict(event='Server16RefreshClubFinance',actions=[['unloadView',['screen']],['loadView',['screen',PAGE]]])]+
   [dict(event=e,targets=['Back'],actions=[['executeCMAction',['ReturnToHubFromCalendar']]]) for e in ('Back','back')])])

def stage(game,folder):
 game=Path(game);folder=Path(folder)
 files={XML:layout((game/XML).read_bytes()),NAV:navigation((game/NAV).read_bytes()),FLOW:(json.dumps(flow(),ensure_ascii=False,indent=2)+'\n').encode('utf8')}
 for relative,blob in files.items():
  target=folder/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob)
 return list(files)
