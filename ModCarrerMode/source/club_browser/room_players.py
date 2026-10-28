"""Dedicated career-club roster entry from the existing dressing room flow."""
import copy,json,sys
from pathlib import Path
SOURCE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SOURCE/'club_environment/market'))
from build_package import read_nav
PAGE='game/screens/career/server16/DressingRoomPlayers'
BIG='data/ui/game/screens/career/server16/dressingroomplayers.big'
FLOW='data/ui/nav/careermode/server16dressingroomflow.nav'
EVENT='Server16OpenRoomPlayers'

def integrate(flow):
    result=copy.deepcopy(flow)
    if result.get('name')!='Server16DressingRoomFlow':raise ValueError('Fluxo do vestiário incompatível.')
    rooms=[s for s in result.get('states',[]) if s.get('name')=='Room']
    if len(rooms)!=1:raise ValueError('Estado do vestiário ausente ou ambíguo.')
    room=rooms[0]
    if ['loadView',['screen','game/screens/career/server16/DressingRoom']] not in room.get('onEnter',[]):raise ValueError('Tela original do vestiário não identificada.')
    transition=dict(event=EVENT,targets=['Players'])
    existing=[t for t in room.get('transitions',[]) if t.get('event')==EVENT]
    if existing and existing!=[transition]:raise ValueError('A entrada do elenco já possui outra rota.')
    if not existing:room.setdefault('transitions',[]).append(transition)
    player_state=dict(name='Players',onEnter=[['loadScreenController',['Calendar']],['loadView',['screen',PAGE]],['loadView',['background','FIFA','BOOTFLOW']]],
        onExit=[['unloadView',['screen',PAGE]],['unloadScreenController',['Calendar']],['unloadView',['background']]],
        transitions=[dict(event=e,targets=['Room']) for e in ('Back','back')])
    existing=[s for s in result['states'] if s.get('name')=='Players']
    if existing and existing!=[player_state]:raise ValueError('O estado do elenco já possui outro comportamento.')
    if not existing:result['states'].append(player_state)
    return result

def navigation(raw):return (json.dumps(integrate(read_nav(raw)),ensure_ascii=False,indent=2)+'\n').encode('utf8')

def stage(game,output):
    import build_apt
    game,output=Path(game),Path(output);target=output/BIG;target.parent.mkdir(parents=True,exist_ok=True);build_apt.build(game,target,from_room=True)
    flow=output/FLOW;flow.parent.mkdir(parents=True,exist_ok=True);flow.write_bytes(navigation((game/FLOW).read_bytes()))
    return [BIG,FLOW]

if __name__=='__main__':print(stage(Path(sys.argv[1]),Path(sys.argv[2])))
