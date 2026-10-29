"""Bind durable native save receipts to the last committed market state.

Only the mod SQLite is written. DATA, INDEX and FIFA's DB remain read-only.
An I/O read cannot consume/replace an unprocessed write receipt. A state newer
than the completed save is never lent to an older save or another career.
"""
from pathlib import Path
import hashlib,json,zlib

def record(path):
 return dict(line.split('=',1) for line in Path(path).read_text(encoding='utf-8-sig').splitlines() if '=' in line)

def bind_pending(market,game):
 folder=Path(game)/'ModCarrerMode/runtime/manager_market/save_events';bound=[]
 if not folder.is_dir():return bound
 for path in sorted(folder.glob('*.tsv')):
  try:
   event=record(path);pid=int(event['pid']);created=int(event['process_created_100ns']);tick=int(event['access_tick_ms']);size=int(event['size_bytes']);crc=int(event['payload_crc32']);context=int(event['context'],16);epoch=int(event['epoch'])
   if event.get('operation')!='write' or event.get('complete_file')!='1' or event.get('save_type')!='SaveType_Career':continue
   ident=path.stem
   if market.db.execute('SELECT 1 FROM save_receipts WHERE event_id=?',(ident,)).fetchone():continue
   save=Path(event['path']);before=save.stat()
   if save.name.upper()!='DATA' or not (save.parent/'INDEX').is_file() or before.st_size!=size:continue
   raw=save.read_bytes()
   if before.st_mtime_ns!=save.stat().st_mtime_ns or len(raw)!=size or raw[116:132]!=b'SaveType_Career\0' or int.from_bytes(raw[136:140],'little')!=56:continue
   if int.from_bytes(raw[132:136],'little')!=crc or zlib.crc32(raw[160:])!=crc:continue
   # Process identity plus a monotonic timestamp joins an actual write to its
   # committed SQL world, including when the helper was busy drawing the UI.
   candidate=market.db.execute('SELECT * FROM session_states WHERE pid=? AND created=? AND context=? AND epoch=? AND captured_ms<=? ORDER BY captured_ms DESC LIMIT 1',(pid,created,context,epoch,tick)).fetchone()
   if not candidate:continue
   from lineup_data import databases
   dbs=databases(raw,Path(game));calendars=[d for d in dbs if 'career_calendar' in d.tables];users=[d for d in dbs if 'career_users' in d.tables]
   if len(calendars)!=1 or len(users)!=1:continue
   dates=calendars[0].rows('career_calendar',['currdate']);clubs=users[0].rows('career_users',['clubteamid'])
   state=json.loads(zlib.decompress(candidate['state']));info=state['info']
   if len(dates)!=1 or len(clubs)!=1 or info['game_date']>dates[0]['currdate'] or info['user_club']!=clubs[0]['clubteamid']:continue
   digest=hashlib.sha256(raw).hexdigest()
   # A real repeated save can have identical DATA bytes while SQL changed.
   # The newer explicit write wins; ordinary loads never overwrite snapshots.
   newer=market.db.execute('SELECT 1 FROM save_receipts WHERE save_hash=? AND created=? AND write_ms>?',(digest,created,tick)).fetchone()
   if not newer:market.checkpoint(digest,save,replace=True,state=candidate['state'])
   market.db.execute('INSERT INTO save_receipts VALUES(?,?,?,?,?,?,?,?)',(ident,digest,info['id'],info['game_date'],pid,created,tick,'native_write'))
   bound.append(dict(event=ident,digest=digest,branch=info['id'],date=info['game_date'],path=str(save)))
  except (OSError,ValueError,KeyError,TypeError,UnicodeError):continue
 return bound
