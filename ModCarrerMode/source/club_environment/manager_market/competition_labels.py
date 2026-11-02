"""Competition titles from the installed language cache, never an ID label."""
from functools import lru_cache
from pathlib import Path
import json,subprocess

@lru_cache(maxsize=4)
def _cached(path,mtime,size):
 try:return json.loads(Path(path).read_text(encoding='utf8'))
 except (OSError,ValueError):return {}

def resolve(game,ident,fallback=''):
 game=Path(game);path=game/'ModCarrerMode/runtime/club_environment/preview/runtime/competition_labels_r57.json'
 try:
  stat=path.stat();data=_cached(str(path),stat.st_mtime_ns,stat.st_size);loc=(game/'data/loc/por_br.db').stat()
  names=data.get('names',{}) if isinstance(data,dict) and data.get('revision')==3 and data.get('stamp')==[loc.st_mtime_ns,loc.st_size] else {}
  if not isinstance(names,dict):names={}
  for key in (f'TrophyName_{ident}',f'TrophyName_Abbr15_{ident}',f'LeagueName_{ident}',f'LEAGUE_NAME_{ident}',f'CompetitionName_{ident}',f'TournamentName_{ident}'):
   value=str(names.get(key) or '').strip()
   if value and '\ufffd' not in value:return value
 except OSError:pass
 if fallback and not fallback.startswith(('Competição ', 'Competition ')):return fallback
 # The existing match-preview resolver also reads custom FSW competition names.
 if (game/'data/loc/por_br.db').is_file():
  try:
   from competition_names_r57 import competition_name
   return competition_name(ident,lambda _:[])
  except (OSError,ValueError,KeyError,ImportError,RuntimeError,subprocess.SubprocessError):pass
 return 'Competição da carreira'
