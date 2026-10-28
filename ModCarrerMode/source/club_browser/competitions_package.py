"""Redirect only the classification tile; preserve every other career destination."""
import json,xml.etree.ElementTree as ET
from pathlib import Path
from package import read_nav,walk
EVENT='Server16EnterCareerCompetitions';STATE='Server16CareerCompetitions'
XML='data/ui/layout/careermanagerhubcfg.xml';NAV='data/ui/nav/careermode/mainmenuhubflow.nav';FLOW='data/ui/nav/careermode/server16careercompetitionsflow.nav';PAGE='game/screens/career/server16/CareerCompetitions'

def layout(raw):
 root=ET.fromstring(raw);tiles=[t for t in root.find('panel_5').findall('tile') if t.find('tileid').get('NAME')=='COMPETITIONS_STANDINGS']
 if len(tiles)!=1:raise ValueError('Card de classificação não identificado.')
 main=tiles[0].find('main_tile')
 if main.get('DESTINATION') not in ('EnterStandings',EVENT):raise ValueError('Destino do card foi alterado por outra implementação.')
 main.set('DESTINATION',EVENT);return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def navigation(raw):
 nav=read_nav(raw);hosts=[n for n in walk(nav) if any(t.get('event')=='Server16EnterClubBrowser' for t in n.get('transitions',[]))];owners=[n for n in walk(nav) if any(s.get('name')=='Server16ClubBrowser' for s in n.get('states',[]))]
 if len(hosts)!=1 or len(owners)!=1:raise ValueError('Navegação de carreira incompatível.')
 if not any(t.get('event')==EVENT for t in hosts[0]['transitions']):hosts[0]['transitions'].append(dict(event=EVENT,targets=[STATE]))
 if not any(s.get('name')==STATE for s in owners[0]['states']):owners[0]['states'].append(dict(name=STATE,type='external',file='/careerMode/server16CareerCompetitionsFlow.nav',outputs=dict(back='MainMenuHub',Back='MainMenuHub')))
 return (json.dumps(nav,ensure_ascii=False,indent=2)+'\n').encode('utf8')

def flow():
 return dict(name='Server16CareerCompetitionsFlow',initial=dict(targets=['Competitions']),states=[dict(name='Competitions',onEnter=[['executeCMAction',['EnterCalendar']],['loadScreenController',['Calendar']],['loadView',['screen',PAGE]],['loadView',['background','FIFA','BOOTFLOW']]],onExit=[['unloadView',['screen',PAGE]],['unloadScreenController',['Calendar']],['unloadView',['background']]],transitions=[dict(event=e,targets=['Back'],actions=[['executeCMAction',['ReturnToHubFromCalendar']]]) for e in ('Back','back')])])

def stage(game,output):
 files={XML:layout((game/XML).read_bytes()),NAV:navigation((game/NAV).read_bytes()),FLOW:(json.dumps(flow(),ensure_ascii=False,indent=2)+'\n').encode('utf8')}
 for name,blob in files.items():
  p=output/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(blob)
 return list(files)
