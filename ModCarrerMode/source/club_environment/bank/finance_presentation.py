"""Discard presentation only when changing careers; never touch the ledger/save."""
from pathlib import Path
import os,json

def waiting_package(game):
 game=Path(game);path=game/'ModCarrerMode/cache/finance/awaiting-career.big'
 if not path.is_file():
  import finance_ui
  path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix('.'+str(os.getpid())+'.new')
  finance_ui.build(dict(ready=False,club=0,club_name='Aguardando dados da carreira',
   date=0,start=0,budget=0,months=[],agreements=[],settings={},nonce='DISABLED',currency=0,ack=0,
   message='Carregando as finanças da carreira atual...'),temp)
  os.replace(temp,path)
 return path

def invalidate(game,folder):
 game=Path(game);folder=Path(folder)
 # Unpublish before replacing the file. The UI-owner must not reload an old
 # ready package while the new career is still being verified.
 (folder/'view_ready.tsv').unlink(missing_ok=True)
 source=waiting_package(game);target=game/'data/ui/game/screens/career/server16/clubfinance.big'
 target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_suffix('.'+str(os.getpid())+'.new')
 temp.write_bytes(source.read_bytes());os.replace(temp,target)
 folder.mkdir(parents=True,exist_ok=True)
 temp=folder/('club_finance_view.'+str(os.getpid())+'.new')
 temp.write_text(json.dumps(dict(ready=False,nonce='DISABLED',months=[],entries=[],agreements=[])),encoding='utf8')
 os.replace(temp,folder/'club_finance_view.json')
