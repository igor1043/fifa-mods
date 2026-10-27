"""Validate actual save-to-pose inputs and reject malformed/mixed rosters."""
import sys,struct,hashlib,json
from pathlib import Path
from lineup_data import project,pack_fixture,starting_sheet

def run(game,save):
    save=Path(save);before=hashlib.sha256(save.read_bytes()).hexdigest()
    for club in (1043,1629):
        result=project(Path(game),save,club)
        magic,count,team,_=struct.unpack_from('<8sIII',result['fixture']);assert magic==b'C3DQA003' and count==11 and team==club
        assert len(result['roster'])==11 and len({p['id'] for p in result['roster']})==11
        assert len(result['fixture'])==struct.calcsize('<8sIII128s')+11*struct.calcsize('<29i4I34i128s6i')
        assert result['revision']==hashlib.sha256(result['fixture']).hexdigest()
    try:pack_fixture(1,'Club',{}, {},[],{},{});raise AssertionError('Missing XI accepted')
    except ValueError:pass
    try:starting_sheet(lambda *_:[dict(teamid=1,isfavourite=1,**{'playerid'+str(i):2 for i in range(11)})],1,{2:{}});raise AssertionError('Duplicate XI accepted')
    except ValueError:pass
    assert hashlib.sha256(save.read_bytes()).hexdigest()==before
    print('PASS two clubs: unique linked starting XI, player appearance/kit inputs, immutable save, malformed XI rejected')

if __name__=='__main__':run(*sys.argv[1:])
