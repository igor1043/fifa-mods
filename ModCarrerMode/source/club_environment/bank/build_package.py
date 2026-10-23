import portable_paths as portable
"""Add a bank card and an independent NAV branch; stage without publishing."""
from pathlib import Path
import hashlib,json,re,shutil,xml.etree.ElementTree as ET
from build_screen import HERE,PAGE,build

GAME=portable.GAME
NAV='data/ui/nav/careermode/mainmenuhubflow.nav'
XML='data/ui/layout/careermanagerhubcfg.xml'

def digest(data):return hashlib.sha256(data).hexdigest()

def read_nav(text):
    text=re.sub(r'"(?:\\.|[^"\\])*"|/\*.*?\*/|//[^\r\n]*',lambda m:m[0] if m[0].startswith('"') else '',text,flags=re.S)
    return json.loads(re.sub(r',\s*([\]}])',r'\1',text))

def walk(value):
    if isinstance(value,dict):
        yield value
        for child in value.values():yield from walk(child)
    elif isinstance(value,list):
        for child in value:yield from walk(child)

def make_layout(data):
    root=ET.fromstring(data)
    assert root.find("panel_3/tile/tileid[@NAME='SERVER16_BANK_LOANS']") is None
    panel=root.find('panel_3');assert panel is not None
    contracts=next(t for t in panel.findall('tile') if t.find('tileid').get('NAME')=='PLAYER_CONTRACTS')
    settings=contracts.find('settings');assert settings.get('HEIGHT')=='418' and settings.get('X')=='965'
    settings.set('HEIGHT','204');contracts.find('main_tile').set('FG_PATH','')
    contracts.find('main_tile').set('BG_ICON','Contracts_Small')
    used={int(n.get('tileid')) for n in root.iter('tileid')}
    assert 900 not in used
    tile=ET.SubElement(panel,'tile')
    ET.SubElement(tile,'tileid',tileid='900',NAME='SERVER16_BANK_LOANS',PARAM='')
    ET.SubElement(tile,'settings',FILE_PATH='TILE',WIDTH='418',HEIGHT='204',X='965',Y='492')
    ET.SubElement(tile,'main_tile',FG_PATH='',BG_ICON='RequestFunds_Small',DESTINATION='Server16EnterBankLoans')
    ET.SubElement(tile,'number_of_subtiles',LENGTH='0')
    ET.SubElement(tile,'data',ID='TITLE',TYPE='title',PARAM='EMPRESTIMOS',TRANSLATE='FALSE',FORMAT='HS')
    ET.SubElement(tile,'data',ID='S16_BANK_DESCRIPTION',TYPE='text',PARAM='Bancos, valores e parcelas',TRANSLATE='FALSE',FORMAT='SM',WIDTH='380',HEIGHT='60',X='18',Y='76')
    panel.find('entries').set('numberoftiles',str(len(panel.findall('tile'))))
    # Every visible office tile retains its own non-overlapping rectangle.
    rects=[]
    for t in panel.findall('tile'):
        s=t.find('settings');rect=tuple(int(s.get(k)) for k in ('X','Y','WIDTH','HEIGHT'))
        for old in rects:
            x,y,w,h=rect;ox,oy,ow,oh=old
            assert min(x+w,ox+ow)<=max(x,ox) or min(y+h,oy+oh)<=max(y,oy),(rect,old)
        rects.append(rect)
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def make_nav(data):
    nav=read_nav(data.decode('utf-8-sig'))
    containers=[v for v in walk(nav) if any(t.get('event')=='EnterCalendar' for t in v.get('transitions',[]))]
    assert len(containers)==1
    containers[0]['transitions'].append({'event':'Server16EnterBankLoans','targets':['Server16BankLoans']})
    parents=[v for v in walk(nav) if any(t.get('name')=='Calendar' for t in v.get('states',[]))]
    assert len(parents)==1
    parents[0]['states'].append({'name':'Server16BankLoans','type':'external','file':'/careerMode/server16BankLoansFlow.nav',
                                 'outputs':{'back':'MainMenuHub','Back':'MainMenuHub'}})
    return (json.dumps(nav,ensure_ascii=False,indent=2)+'\n').encode('utf8')

def make_flow():
    return {'name':'Server16BankLoansFlow','initial':{'targets':['Server16BankLoansScreen']},'states':[
        {'name':'Server16BankLoansScreen','onEnter':[
            ['executeCMAction',['EnterCalendar']],
            ['loadScreenController',['Calendar']],
            ['loadView',['screen',PAGE]],
            ['loadView',['background','BOOTFLOW']]],
         'onExit':[['unloadView',['screen',PAGE]],['unloadScreenController',['Calendar']],['unloadView',['background']]],
         'transitions':[{'event':'Server16RefreshBank','actions':[['unloadView',['screen',PAGE]],['loadView',['screen',PAGE]]]},
                        {'event':'Back','targets':['Back'],'actions':[['executeCMAction',['ReturnToHubFromCalendar']]]},
                        {'event':'back','targets':['Back'],'actions':[['executeCMAction',['ReturnToHubFromCalendar']]]}]}]}

def main():
    build();package=HERE/'package'
    changes={XML:make_layout((GAME/XML).read_bytes()),NAV:make_nav((GAME/NAV).read_bytes()),
             'data/ui/nav/careermode/server16bankloansflow.nav':(json.dumps(make_flow(),indent=2)+'\n').encode()}
    for relative,data in changes.items():
        target=package/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    manifest=[]
    for path in package.rglob('*'):
        if not path.is_file():continue
        relative=path.relative_to(package).as_posix();before=GAME/relative
        manifest.append({'path':relative,'bytes':path.stat().st_size,'sha256':digest(path.read_bytes()),
                         'before_sha256':digest(before.read_bytes()) if before.exists() else None})
    (HERE/'manifest.json').write_text(json.dumps({'experimental':True,'github_publication':False,'files':manifest,
        'native_screen':PAGE,'controller_transport':'Existing Calendar controller used only for lifecycle/Back; no Calendar view or calendar action is opened',
        'financial_storage':'sidecar snapshots keyed by exact native DATA hash; native save files are not edited by the bridge'},indent=2)+'\n')
    print('Staged',len(manifest),'files;',sum(f['bytes'] for f in manifest),'bytes')

if __name__=='__main__':main()
