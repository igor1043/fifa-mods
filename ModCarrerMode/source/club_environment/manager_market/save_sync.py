"""Bind durable native save receipts to the last committed market state.

Only the mod SQLite is written. DATA, INDEX and FIFA's DB remain read-only.
An I/O read cannot consume/replace an unprocessed write receipt. A state newer
than the completed save is never lent to an older save or another career.
"""
from pathlib import Path
import hashlib,json,zlib

def record(path):
 return dict(line.split('=',1) for line in Path(path).read_text(encoding='utf-8-sig').splitlines() if '=' in line)

def pending_checkpoint(market,game,save,context=None):
 """A known native write must bind before any load may seed/restore its slot."""
 folder=Path(game)/'ModCarrerMode/runtime/manager_market/save_events';save=Path(save)
 from durable_store import approved_reset
 waived=approved_reset(game,save,context)
 def normal(path):return Path(str(path).removeprefix('\\\\?\\')).resolve()
 for path in folder.glob('*.tsv'):
  if path.stem in waived:continue
  try:
   event=record(path)
   if not event.get('market_revision') or event.get('operation')!='write' or normal(event['path'])!=normal(save):continue
   # A slot may be overwritten/copied after this receipt was captured. Its
   # old marker cannot belong to a different saved club or a future date.
   # Use the already-decoded save, never poll/decode DATA again here.
   if context and (int(event['market_club'])!=context.get('saved_club',context['club']) or int(event['market_date'])>context.get('saved_date',context['date'])):continue
   if market.db.execute('SELECT 1 FROM save_receipts WHERE event_id=?',(path.stem,)).fetchone():continue
   with save.open('rb') as stream:header=stream.read(160)
   if len(header)==160 and save.stat().st_size==int(event['size_bytes']) and int.from_bytes(header[132:136],'little')==int(event['payload_crc32']):return True
  except (OSError,ValueError,KeyError,TypeError):continue
 return False

def bind_pending(market,game,current=None):
 folder=Path(game)/'ModCarrerMode/runtime/manager_market/save_events';bound=[]
 if not folder.is_dir():return bound
 for path in sorted(folder.glob('*.tsv')):
  try:
   event=record(path);pid=int(event['pid']);created=int(event['process_created_100ns']);tick=int(event['access_tick_ms']);size=int(event['size_bytes']);crc=int(event['payload_crc32']);context=int(event['context'],16);epoch=int(event['epoch'])
   if event.get('operation')!='write' or event.get('complete_file')!='1' or event.get('save_type')!='SaveType_Career':continue
   ident=path.stem
   if market.db.execute('SELECT 1 FROM save_receipts WHERE event_id=?',(ident,)).fetchone():continue
   revision=event.get('market_revision')
   query='SELECT s.* FROM session_states s LEFT JOIN session_observations o ON o.pid=s.pid AND o.created=s.created AND o.context=s.context AND o.captured_ms=s.captured_ms WHERE s.pid=? AND s.created=? AND s.epoch=? AND COALESCE(o.observed_ms,s.captured_ms)<=?'
   args=(pid,created,epoch,tick)
   if revision:
    # Exact revision selected by the real completed write, not whichever SQL
    # branch happens to be active when a verification read finishes later.
    if len(revision)!=64 or any(c not in '0123456789abcdef' for c in revision):continue
    candidate=market.db.execute(query+' AND s.state_hash=? AND s.context=? AND s.captured_ms<=? ORDER BY s.captured_ms DESC LIMIT 1',args+(revision,int(event['market_context'],16),tick)).fetchone()
    if candidate is None:continue
   else:
    candidate=market.db.execute(query+' AND s.context=? ORDER BY s.game_date DESC,s.captured_ms DESC LIMIT 1',args+(context,)).fetchone()
   owner=dict(pid=pid,created=created,context=context,epoch=epoch)
   # An unrelated old receipt cannot bind a SQL world. Do not repeatedly
   # reopen and decode its complete FIFA save on every background poll.
   if candidate is None and (not current or any(current.get(k)!=v for k,v in owner.items())):continue
   save=Path(event['path']);before=save.stat()
   if save.name.upper()!='DATA' or not (save.parent/'INDEX').is_file() or before.st_size!=size:continue
   raw=save.read_bytes()
   if before.st_mtime_ns!=save.stat().st_mtime_ns or len(raw)!=size or raw[116:132]!=b'SaveType_Career\0' or int.from_bytes(raw[136:140],'little')!=56:continue
   if int.from_bytes(raw[132:136],'little')!=crc or zlib.crc32(raw[160:])!=crc:continue
   # Process identity plus a monotonic timestamp joins an actual write to its
   # committed SQL world, including when the helper was busy drawing the UI.
   from lineup_data import databases
   dbs=databases(raw,Path(game));calendars=[d for d in dbs if 'career_calendar' in d.tables];users=[d for d in dbs if 'career_users' in d.tables]
   if len(calendars)!=1 or len(users)!=1:continue
   dates=calendars[0].rows('career_calendar',['currdate']);clubs=users[0].rows('career_users',['clubteamid'])
   if len(dates)!=1 or len(clubs)!=1:continue
   digest=hashlib.sha256(raw).hexdigest()
   payload=candidate['state'] if candidate else None
   state=json.loads(zlib.decompress(payload)) if payload else None
   info=state['info'] if state else {}
   if revision and (info.get('game_date')!=int(event['market_date']) or info.get('user_club')!=int(event['market_club'])):continue
   if info.get('game_date')!=dates[0]['currdate'] or info.get('user_club')!=clubs[0]['clubteamid']:
    # The calendar may advance faster than the Python worker. An older SQL
    # world must not be permanently attached to a newly completed native save.
    # Catch up first, then join only the still-current exact write receipt.
    expected=dict(pid=pid,created=created,context=context,epoch=epoch,
                  date=dates[0]['currdate'],club=clubs[0]['clubteamid'],digest=digest)
    if not current or any(current.get(k)!=v for k,v in expected.items()):continue
    if current.get('io')!=['write',str(tick),str(save)] or current.get('branch')!=market.branch:continue
    payload=market.snapshot();state=json.loads(zlib.decompress(payload));info=state['info']
    if info['game_date']!=dates[0]['currdate'] or info['user_club']!=clubs[0]['clubteamid']:continue
   # A real repeated save can have identical DATA bytes while SQL changed.
   # The newer explicit write wins; ordinary loads never overwrite snapshots.
   newer=market.db.execute('SELECT 1 FROM save_receipts WHERE save_hash=? AND created=? AND write_ms>?',(digest,created,tick)).fetchone()
   if not newer:
    from save_database import store_receipt
    store_receipt(market,save,digest,payload,(ident,digest,info['id'],info['game_date'],pid,created,tick,'native_write_v2'))
   market.db.execute('INSERT INTO save_receipts VALUES(?,?,?,?,?,?,?,?)',(ident,digest,info['id'],info['game_date'],pid,created,tick,'native_write_v2'))
   bound.append(dict(event=ident,digest=digest,branch=info['id'],date=info['game_date'],path=str(save)))
  except (OSError,ValueError,KeyError,TypeError,UnicodeError):continue
 return bound
