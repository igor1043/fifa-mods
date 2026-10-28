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
    assert any(n=='SetCustomSource' for n,a in calls) and any(n=='Show' for n,a in calls)
    vm.invoke(view.get('OnAnimateInComplete'),view)
    assert sum(n=='SendSystemEvent' and a[1]=='DONE_LOADING' for n,a in calls)==1
    help_=vm.invoke(view.get('getHelpContext'),view)
    assert [x[0] for x in help_]==['ADVANCE','BACK','LAS_LR','L2R2','L1R1']
    def press(code):return vm.invoke(view.get('LocalEventHandler'),view,(code,True))
    def command(name):return any(n=='SendSystemEvent' and list(a)==['Calendar','Server16ClubBrowser',name] for n,a in calls)
    press(2);assert view.get('navPage')==1 and command('open')
    assert [x[0] for x in vm.invoke(view.get('getHelpContext'),view)]==['ADVANCE','BACK','LAS_LR']
    press(5);assert view.get('hubIndex')==0;press(2);assert view.get('navPage')==2 and command('xi')
    assert [x[0] for x in vm.invoke(view.get('getHelpContext'),view)]==['BACK','ADVANCE']
    press(2);assert command('refresh')
    before=sum(n=='SendEvent' and list(a)==['Calendar','Back',''] for n,a in calls)
    press(1);assert view.get('navPage')==1
    button=view.get('scene0').get('action2');vm.invoke(button.get('onRollOver'),button);assert view.get('hubIndex')==1 and command('focus_roster');vm.invoke(button.get('onRelease'),button);assert view.get('navPage')==3 and command('roster')
    assert [x[0] for x in vm.invoke(view.get('getHelpContext'),view)]==['ADVANCE','BACK','LAS_UD','L2R2','RAS_LR','L1R1']
    press(16);assert command('next');press(15);assert command('prev')
    press(11);assert command('tab_prev');press(12);assert command('tab_next');press(10);assert command('sort')
    count=sum(n=='Update' for n,a in calls)
    for _ in range(3):vm.invoke(view.get('Tick'),view)
    assert sum(n=='Update' for n,a in calls)>count
    press(5);assert command('left');press(6);assert command('right')
    press(2);assert view.get('navPage')==4 and command('detail')
    assert [x[0] for x in vm.invoke(view.get('getHelpContext'),view)]==['BACK','L2R2','RAS_LR','L1R1']
    press(1);assert view.get('navPage')==3
    press(1);assert view.get('navPage')==1
    press(1);assert view.get('navPage')==0
    assert sum(n=='SendEvent' and list(a)==['Calendar','Back',''] for n,a in calls)==before
    press(1);assert any(n=='SendEvent' and list(a)==['Calendar','Back',''] for n,a in calls)
    vm.invoke(view.get('OnExitScreen'),view);vm.invoke(view.get('OnExitScreen'),view)
    assert sum(n=='Shutdown' for n,_ in calls)==1
    assert not any('Database' in n or 'SetBudget' in n for n,_ in calls)
    print('PASS native APT: ready once, original help, back, shutdown once; transparent; prior hub preserved')

if __name__=='__main__':run(Path(sys.argv[1]),Path(sys.argv[2]))
