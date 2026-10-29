"""Read-only portrait lookup for the exact coach identity, shared with the market."""
from pathlib import Path
from contextlib import closing
import re,sqlite3,unicodedata

DEFAULT='minifaces/NOTFOUND_DEFAULT.png'

def key(name):
 return ' '.join(''.join(c for c in unicodedata.normalize('NFKD',str(name or '')) if not unicodedata.combining(c)).casefold().split())

def installed(folder,value):
 if not isinstance(value,str) or not re.fullmatch(r'minifaces/[A-Za-z0-9_-][A-Za-z0-9_.-]{0,99}\.png',value) or '..' in value:return None
 path=folder/value
 try:return value if path.is_file() and path.resolve().is_relative_to(folder.resolve()) else None
 except OSError:return None

def portrait(game,name,person=None):
 folder=Path(game)/'ModCarrerMode/data/manager_market'
 # An active appointment is authoritative; never replace its missing face
 # with an unrelated coach of the same display name.
 if person is not None:return installed(folder,person.get('image')) or DEFAULT
 database=folder/'catalog.sqlite3'
 if not database.is_file() or not key(name):return DEFAULT
 try:
  with closing(sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True,timeout=1)) as db:
   matches=[image for label,image in db.execute('SELECT name,image FROM coaches') if key(label)==key(name)]
  return installed(folder,matches[0]) or DEFAULT if len(matches)==1 else DEFAULT
 except (OSError,ValueError,sqlite3.Error):return DEFAULT
