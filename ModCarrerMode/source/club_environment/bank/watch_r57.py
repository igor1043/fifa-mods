import portable_paths as portable
"""Local financial session supervisor. Every mutation requires a scoped UI request."""
import time,json,sys,hashlib
from pathlib import Path
import runtime as r

def main():
 last_error=None;last_disabled=None
 while any((p.info.get('name') or '').lower()=='fifa16.exe' for p in r.psutil.process_iter(['name'])):
  bridge=None;attached=False
  try:
   bridge=r.Bridge.__new__(r.Bridge);r.Bridge.__init__(bridge,apply=True);attached=True
   while bridge.process.is_running():
    bridge.tick()
    # Financial/calendar events keep the same cadence outside the Loans screen.
    time.sleep(.12)
  except Exception as error:
   message=str(error)
   if message!=last_error:r.log('waiting_for_financial_context',error=message);last_error=message
   if not attached:
    view={'club':0,'budget':0,'date':None,'used':0,'can_borrow':False,'schedule':[],'active':None,'ready':False,'nonce':'DISABLED','error':message}
    signature=hashlib.sha256(json.dumps(view,sort_keys=True).encode()).hexdigest()
    if signature!=last_disabled:
     try:
      from bank_ui_r57 import build
      build(view);source=r.HERE/'package/data/ui/game/screens/career/server16/bankloans.big';target=r.GAME/'data/ui/game/screens/career/server16/bankloansv2.big';temp=target.with_suffix('.new');temp.write_bytes(source.read_bytes());temp.replace(target);r.write_json(r.STATE/'finance_view.json',view);last_disabled=signature
     except Exception as screen_error:r.log('financial_wait_screen_pending',error=str(screen_error))
   r.write_json(r.STATE/'status.json',{'active':False,'error':message});time.sleep(3)
  finally:
   if bridge:bridge.close()

if __name__=='__main__':main()
