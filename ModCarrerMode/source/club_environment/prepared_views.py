"""Atomic readiness metadata; only FIFA's existing UI owner opens the view."""
from pathlib import Path
import ctypes,os

def ticks():
    timer=ctypes.WinDLL('kernel32').GetTickCount64;timer.restype=ctypes.c_ulonglong
    return timer()

def publish(path,save,profile,today,revision,captured_ms=None,fixture=0):
    fields=dict(schema=1,pid=save['pid'],process_created_100ns=save.get('process_created_100ns',0),
                club=profile['club_id'],context=format(profile.get('context_address',0),'x'),
                registry=format(profile.get('registry_address',0),'x'),epoch=profile.get('context_epoch',0),
                date=today,captured_ms=ticks() if captured_ms is None else captured_ms,fixture=fixture,revision=revision)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_name(path.name+'.'+str(os.getpid())+'.new')
    temporary.write_text(''.join(f'{key}={value}\n' for key,value in fields.items()),encoding='ascii');os.replace(temporary,path)
