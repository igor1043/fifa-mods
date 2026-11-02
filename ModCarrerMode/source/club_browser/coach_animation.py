"""Choose one native manager idle per screen request, without adjacent repeats."""
from pathlib import Path
import json,os,random
from preview_files import atomic

CLIPS=('coach_crossed.json','coach_hands_on_hips.json','coach_standing.json')

def select(folder,request,directory,rng=None,*,clips=CLIPS,state_name='coach-animation-choice.json',player=False):
    directory=Path(directory);available=[name for name in clips if (directory/name).is_file()]
    if not available:raise FileNotFoundError('Nenhuma animação de técnico instalada.')
    state=Path(folder)/state_name;key=[int(request[k]) for k in ('pid','seq','club')]
    if player:key.append(int(request['player']))
    try:previous=json.loads(state.read_text(encoding='utf8'))
    except (OSError,ValueError):previous={}
    if isinstance(previous,dict) and previous.get('request')==key and previous.get('clip') in available:return directory/previous['clip']
    last=previous.get('clip') if isinstance(previous,dict) else None
    choices=[name for name in available if name!=last] or available;chosen=(rng or random.SystemRandom()).choice(choices)
    atomic(state,json.dumps({'schema':1,'request':key,'clip':chosen}).encode('utf8'))
    return directory/chosen
