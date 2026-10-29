"""Start the isolated market reader through the existing frozen preview entry.

No Server16 rebuild or replacement is needed. A fresh process keeps APT builder
globals and failures separate from the match preview, loans, and dressing room.
"""
from pathlib import Path
import os,runpy,subprocess,sys

FLAG='SERVER16_TRANSFER_MARKET_WORKER'

def dispatch(portable):
    if os.environ.get('SERVER16_MANAGER_MARKET_WORKER')=='1':
        source=portable.SOURCES/'manager_market'
        sys.path.insert(0,str(source))
        runpy.run_path(str(source/'worker.py'),run_name='__main__')
        return True
    if os.environ.get('SERVER16_CLUB_BROWSER_WORKER')=='1':
        source=portable.SOURCES.parent/'club_browser'
        sys.path.insert(0,str(source))
        runpy.run_path(str(source/'lineup_worker.py'),run_name='__main__')
        return True
    source=portable.SOURCES/'market'
    if os.environ.get(FLAG)!='1':return False
    sys.path.insert(0,str(source))
    runpy.run_path(str(source/'worker_market.py'),run_name='__main__')
    return True

def launch(portable,pid):
    source=portable.SOURCES/'market/worker_market.py'
    if not source.is_file():return None
    environment=dict(os.environ);environment[FLAG]='1'
    command=[sys.executable]
    if not getattr(sys,'frozen',False):command.append(str(portable.SOURCES.parent/'main.py'))
    command+=['--club-environment-worker','preview','--game-root',str(portable.GAME),'--pid',str(pid)]
    folder=portable.BASE/'market';folder.mkdir(parents=True,exist_ok=True)
    with (folder/'launcher.log').open('ab') as stream:
        return subprocess.Popen(command,cwd=portable.GAME,env=environment,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)

def launch_managers(portable,pid):
    if not (portable.SOURCES/'manager_market/worker.py').is_file():return None
    environment=dict(os.environ);environment['SERVER16_MANAGER_MARKET_WORKER']='1'
    command=[sys.executable]
    if not getattr(sys,'frozen',False):command.append(str(portable.SOURCES.parent/'main.py'))
    command+=['--club-environment-worker','preview','--game-root',str(portable.GAME),'--pid',str(pid)]
    folder=portable.GAME/'ModCarrerMode/runtime/manager_market';folder.mkdir(parents=True,exist_ok=True)
    with (folder/'launcher.log').open('ab') as stream:
        return subprocess.Popen(command,cwd=portable.GAME,env=environment,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
