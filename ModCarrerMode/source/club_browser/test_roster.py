"""Read-only real-save regression for the full roster and individual actor jobs."""
from pathlib import Path
import hashlib,struct,tempfile
from unittest.mock import patch
from roster_data import project,tsv
from lineup_data import ProjectionCache
from lineup_worker import request

def run(game,save,output):
 game,save,output=map(Path,(game,save,output));output.mkdir(parents=True,exist_ok=True)
 digest=hashlib.sha256(save.read_bytes()).hexdigest();cache=ProjectionCache();rosters=[]
 for club in (1043,1629,1035,1043):
  data=project(game,save,club,cache);players=data['players'];assert len(players)>11
  assert len({p['id'] for p in players})==len(players)
  for p in players:
   assert len(p['attributes'])==34 and 130<=p['height']<=230
   magic,count,team=struct.unpack_from('<8sII',p['fixture']);assert (magic,count,team)==(b'C3DQA003',1,club)
  encoded=tsv(data);assert encoded.decode().splitlines()[0].startswith('S16ROSTER2\t'+str(club)+'\t')
  assert all(len(row.split('\t'))==52 for row in encoded.decode().splitlines()[1:])
  (output/f'roster-{club}.tsv').write_bytes(encoded);rosters.append(data)
 assert rosters[0]==rosters[-1] and rosters[0]['players']!=rosters[1]['players']
 with patch('lineup_data.FifaDatabase',side_effect=AssertionError('Unchanged save parsed again')):
  assert project(game,save,1043,cache)==rosters[0]
 with tempfile.TemporaryDirectory(prefix='roster á ') as folder:
  path=Path(folder)/'request.tsv'
  def put(extra):path.write_text('schema=1\npid=42\nseq=2\nclub=1043\n'+extra,encoding='ascii')
  put('');assert set(request(path,42))=={'schema','pid','seq','club'}
  put('kind=roster\n');assert request(path,42)['kind']=='roster'
  put('kind=player\nplayer=205498\n');assert request(path,42)['player']==205498
  for extra in ('kind=other\n','kind=player\nplayer=0\n','kind=player\nplayer=200000000\n'):
   put(extra)
   try:request(path,42);raise AssertionError('Invalid request accepted')
   except ValueError:pass
  put('kind=roster\n')
  try:request(path,43);raise AssertionError('Foreign session accepted')
  except ValueError:pass
 assert hashlib.sha256(save.read_bytes()).hexdigest()==digest
 print('PASS full rosters: three clubs, substitutes, unique players, all attributes, one-player fixture ABI, cache reuse, bounded requests, immutable save')
 return rosters[0]
