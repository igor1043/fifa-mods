"""Offline tests for dressing-room actions, dedicated roster and return route."""
import copy,json,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent/'club_environment/market')]
import room_players as route
import build_apt
from native_review_vm import open_native

def run(game,output):
    game,output=Path(game),Path(output);original=(game/route.FLOW).read_bytes();paths=route.stage(game,output);new=(output/route.FLOW).read_bytes();assert route.navigation(new)==new
    before=json.loads(original);after=json.loads(new);room=next(s for s in after['states'] if s['name']=='Room');old=next(s for s in before['states'] if s['name']=='Room')
    without=copy.deepcopy(room);old=copy.deepcopy(old)
    for state in (without,old):state['transitions']=[t for t in state['transitions'] if t['event']!=route.EVENT]
    assert without==old
    players=next(s for s in after['states'] if s['name']=='Players');assert all(t['targets']==['Room'] and not t.get('actions') for t in players['transitions'])
    for invalid in ({},dict(before,name='OtherFlow')):
        try:route.integrate(invalid);raise AssertionError('Invalid flow accepted')
        except ValueError:pass
    conflict=copy.deepcopy(after);next(s for s in conflict['states'] if s['name']=='Players')['onExit']=[]
    try:route.integrate(conflict);raise AssertionError('Conflicting state overwritten')
    except ValueError:pass
    vm,view,apt,calls=open_native(output/route.BIG,build_apt.ROOM_FULL)
    if not view.get('screenReady'):vm.invoke(view.get('Ready'),view)
    assert view.get('screenReady') and view.get('navPage')==3
    assert not any(name=='SendSystemEvent' and args[-1]=='open' for name,args in calls)
    assert [x[0] for x in vm.invoke(view.get('getHelpContext'),view)]==['ADVANCE','BACK','LAS_UD','L2R2','RAS_LR','L1R1']
    def press(code):return vm.invoke(view.get('LocalEventHandler'),view,(code,True))
    def backs():return sum(n=='SendEvent' and list(a)==['Calendar','Back',''] for n,a in calls)
    count=backs();press(2);assert view.get('navPage')==4;press(1);assert view.get('navPage')==3 and backs()==count
    press(1);assert backs()==count+1
    # Every round trip balances native view/controller/background ownership.
    counts={'screen':0,'controller':0,'background':0}
    def actions(items):
        for method,args in items:
            if method in ('loadView','unloadView'):key=args[0];counts[key]+=1 if method=='loadView' else -1
            elif method in ('loadScreenController','unloadScreenController'):counts['controller']+=1 if method=='loadScreenController' else -1
            assert all(v>=0 for v in counts.values()),counts
    actions(room['onEnter'])
    for _ in range(4):
        actions(room['onExit']);actions(players['onEnter']);assert counts==dict(screen=1,controller=1,background=1)
        actions(players['onExit']);actions(room['onEnter']);assert counts==dict(screen=1,controller=1,background=0)
    actions(room['onExit']);assert not any(counts.values())
    assert (game/route.FLOW).read_bytes()==original
    print('PASS room roster route: direct list, original help, detail back vs room back, preserved scenes/hub exits, idempotent integration, balanced native lifecycles and unchanged live flow')

class FlowTests(unittest.TestCase):
    def base(self):
        return dict(name='Server16DressingRoomFlow',initial=dict(targets=['Room']),states=[dict(name='Room',onEnter=[['loadView',['screen','game/screens/career/server16/DressingRoom']]],onExit=[['unloadView',['screen']]],transitions=[dict(event='Back',targets=['Back']),dict(event='Server16RefreshDressingRoom',actions=[['reload',[]]])])])
    def test_integration_is_idempotent_and_preserves_existing_room_actions(self):
        before=self.base();original=copy.deepcopy(before);after=route.integrate(before)
        self.assertEqual(before,original);self.assertEqual(route.integrate(after),after)
        room=after['states'][0];self.assertEqual(room['transitions'][:-1],before['states'][0]['transitions'])
        self.assertTrue(all(t['targets']==['Room'] for t in after['states'][1]['transitions']))
    def test_conflicting_or_ambiguous_flow_is_rejected(self):
        for edit in (lambda f:f.update(name='OtherFlow'),lambda f:f['states'].append(copy.deepcopy(f['states'][0])),lambda f:f['states'][0].update(onEnter=[])):
            fixture=self.base();edit(fixture)
            with self.assertRaises(ValueError):route.integrate(fixture)

if __name__=='__main__':run(sys.argv[1],sys.argv[2])
