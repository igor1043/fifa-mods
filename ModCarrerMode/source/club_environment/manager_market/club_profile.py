"""Read the current club spell from the exact published career SQL branch."""
from pathlib import Path
from contextlib import closing
import json,sqlite3
try:from .board_confidence import for_spell as confidence_for_spell
except ImportError:from board_confidence import for_spell as confidence_for_spell

def same_path(a,b):
 return Path(str(a).removeprefix('\\\\?\\')).resolve()==Path(str(b).removeprefix('\\\\?\\')).resolve()

def io_token(game,saved):
 records=[]
 for name in ('career_save_source.tsv','career_active_save.tsv'):
  try:
   r=dict(line.split('=',1) for line in (Path(game)/'ModCarrerMode/runtime'/name).read_text(encoding='utf-8-sig').splitlines() if '=' in line)
   if r.get('complete_file')=='1' and int(r['pid'])==saved['pid'] and int(r['process_created_100ns'])==saved['process_created_100ns'] and same_path(r['path'],saved['path']):records.append(r)
  except (OSError,ValueError,KeyError):pass
 r=max(records,key=lambda v:int(v.get('access_tick_ms',0)),default={})
 return [r.get('operation'),r.get('access_tick_ms'),saved['path']]

def spell(db,branch,club,today):
 """Renewing a contract keeps a spell; returning after dismissal starts another."""
 appointments=[dict(r) for r in db.execute('SELECT * FROM appointments WHERE branch=? AND club_id=? ORDER BY start_date DESC',(branch,club))]
 current=[a for a in appointments if a['end_date'] is None and a['start_date']<=today]
 if len(current)!=1:return None
 a=current[0];chain=[a];start=a['start_date']
 while True:
  event=db.execute('SELECT kind FROM movements WHERE branch=? AND id=?',(branch,chain[-1]['id'])).fetchone()
  if not event or event['kind']!='renewal':break
  previous=[r for r in appointments if r['coach_id']==a['coach_id'] and r['end_date']==start and r['end_reason']=='renewed' and r['id'] not in {v['id'] for v in chain}]
  if len(previous)!=1:break
  chain.append(previous[0]);start=previous[0]['start_date']
 person=db.execute('SELECT * FROM coaches WHERE branch=? AND coach_id=?',(branch,a['coach_id'])).fetchone()
 if not person:return None
 results=[dict(r) for r in db.execute('SELECT * FROM results WHERE branch=? AND game_date BETWEEN ? AND ? AND (home=? OR away=?)',(branch,start,today,club,club))]
 initial=chain[-1]['origin'] in ('Vínculo inicial desde o início da carreira','Estimado a partir da ativação do mod')
 reviews=[dict(r) for r in db.execute('SELECT * FROM reviews WHERE branch=? AND club_id=? AND game_date BETWEEN ? AND ?',(branch,club,start,today))]
 return dict(coach=dict(person),appointment=a,appointments=[r['id'] for r in chain],start=start,initial=initial,results=results,confidence=confidence_for_spell(reviews,start,today,initial))

def read(game,saved,profile,today,club,digest):
 """Never guess a branch by date, club, newest file or latest SQLite row."""
 game=Path(game);publication=game/'ModCarrerMode/runtime/manager_market/state_ready.json'
 try:
  raw=publication.read_bytes();state=json.loads(raw);path=Path(saved['path']);database=Path(str(path.parent.parent/'server16_manager_market.sqlite3').removeprefix('\\\\?\\'))
  expected=dict(schema=1,pid=saved['pid'],created=saved['process_created_100ns'],context=profile['context_address'],epoch=profile['context_epoch'],club=profile['club_id'],date=today,digest=digest)
  if any(state.get(k)!=v for k,v in expected.items()) or not same_path(state['save'],path) or not same_path(state['database'],database) or state.get('io')!=io_token(game,saved):return None
  with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True,timeout=1)) as db:
   db.row_factory=sqlite3.Row;db.execute('BEGIN')
   branch=db.execute('SELECT * FROM branches WHERE id=?',(state['branch'],)).fetchone()
   if not branch or branch['game_date']!=today or branch['user_club']!=profile['club_id']:return None
   result=spell(db,state['branch'],club,today)
  if publication.read_bytes()!=raw or io_token(game,saved)!=state['io']:return None
  return result
 except (OSError,ValueError,KeyError,TypeError,sqlite3.Error):return None
