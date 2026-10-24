"""Exercise generated AVM bytecode and preserve the installed hub semantics."""
import sys,copy,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_apt as screen
from package import *
from native_review_vm import open_native

def run(game,package):
    raw=(game/XML).read_bytes();changed=(package/XML).read_bytes();assert carousel(changed)==changed
    old=ET.fromstring(raw);new=ET.fromstring(changed)
    assert ET.tostring(old.find('components'))==ET.tostring(new.find('components'))
    for panel in ('panel_0','panel_1','panel_2','panel_3','panel_5'):
        assert ET.tostring(old.find(panel))==ET.tostring(new.find(panel)),panel
    tile=next(t for t in new.find('panel_4').findall('tile') if t.find('tileid').get('NAME')=='OTHER_LEAGUES')
    assert tile.find('main_tile').get('DESTINATION')=='ViewOtherCompetitions'
    assert tile.find('subtile1').get('DESTINATION')==EVENT
    assert navigation((package/NAV).read_bytes())==(package/NAV).read_bytes()
    nav=read_nav((package/NAV).read_bytes());previous=read_nav((game/NAV).read_bytes())
    # Removing just our two additions reproduces the entire prior flow.
    for tree in (nav,previous):
        for node in walk(tree):
            if 'states' in node:node['states']=[s for s in node['states'] if s.get('name')!=STATE]
            if 'transitions' in node:node['transitions']=[t for t in node['transitions'] if t.get('event')!=EVENT]
    assert nav==previous
    vm,view,apt,calls=open_native(package/'data/ui/game/screens/career/server16/clubbrowser.big',screen.FULL)
    if not view.get('screenReady'):vm.invoke(view.get('Ready'),view)
    assert view.get('screenReady');assert sum(n=='Initialize' for n,_ in calls)==1
    vm.invoke(view.get('OnAnimateInComplete'),view)
    assert sum(n=='SendSystemEvent' and a[1]=='DONE_LOADING' for n,a in calls)==1
    help_=vm.invoke(view.get('getHelpContext'),view)
    assert [x[0] for x in help_]==['ADVANCE','BACK','LAS_LR','L2R2','L1R1']
    vm.invoke(view.get('LocalEventHandler'),view,(2,True))
    assert view.get('detailOpen')
    assert [x[0] for x in vm.invoke(view.get('getHelpContext'),view)]==['BACK','ADVANCE']
    before=sum(n=='SendEvent' and list(a)==['Calendar','Back',''] for n,a in calls)
    vm.invoke(view.get('LocalEventHandler'),view,(1,True))
    assert not view.get('detailOpen')
    assert sum(n=='SendEvent' and list(a)==['Calendar','Back',''] for n,a in calls)==before
    vm.invoke(view.get('LocalEventHandler'),view,(1,True))
    assert any(n=='SendEvent' and list(a)==['Calendar','Back',''] for n,a in calls)
    vm.invoke(view.get('OnExitScreen'),view);vm.invoke(view.get('OnExitScreen'),view)
    assert sum(n=='Shutdown' for n,_ in calls)==1
    assert not any('Database' in n or 'SetBudget' in n for n,_ in calls)
    print('PASS native APT: ready once, original help, back, shutdown once; transparent; prior hub preserved')

if __name__=='__main__':run(Path(sys.argv[1]),Path(sys.argv[2]))
