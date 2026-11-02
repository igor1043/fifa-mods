"""Player screen idle choices; no texture, hair or skin processing."""
from coach_animation import select as select_idle

CLIPS=('idle_crossed.json','idle_standing.json','idle_hands_on_hips.json','idle_shift_weight.json')

def select(folder,request,directory,rng=None):
    return select_idle(folder,request,directory,rng,clips=CLIPS,state_name='player-animation-choice.json',player=True)
