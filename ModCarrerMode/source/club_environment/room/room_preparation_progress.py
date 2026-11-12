"""Small atomic phase marker shared with the native loading card.

Milestones represent completed preparation phases, never a timed countdown.
Native model readiness remains the final authority for exposing the room.
"""
from pathlib import Path
import os

def publish(folder,pid,club,stage):
    if not (int(pid)>0 and int(club)>0 and 1<=int(stage)<=6):
        raise ValueError('Invalid room preparation identity or stage')
    target=Path(folder)/'runtime/native_preparation.txt'
    target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_suffix('.tmp')
    temp.write_text(f'S16PREP 1 {int(pid)} {int(club)} {int(stage)}\n',encoding='ascii')
    os.replace(temp,target)
