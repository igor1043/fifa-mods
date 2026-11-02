"""Real preparation stages, scoped to one native career. No save/SQL writes."""
from pathlib import Path
from contextlib import contextmanager
import ctypes,hashlib,json,os,time
from ctypes import wintypes

STAGES=('Consultando a carreira aberta','Lendo ligas e resultados',
 'Atualizando contratos e técnicos','Organizando os perfis','Preparando a tela e as imagens')

def scope(observed,io):
 s=observed['save'];p=observed['profile']
 return [s['pid'],s['process_created_100ns'],p['context_address'],p.get('context_epoch',0),p['club_id'],observed['date'],s['path'].casefold(),io.get('operation'),io.get('access_tick_ms')]

def atomic(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+'.'+str(os.getpid())+'.new')
 temp.write_bytes(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode('utf8'));os.replace(temp,path)

@contextmanager
def view_lock(pid):
 kernel=ctypes.WinDLL('kernel32',use_last_error=True)
 kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR];kernel.CreateMutexW.restype=wintypes.HANDLE
 kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
 kernel.ReleaseMutex.argtypes=[wintypes.HANDLE];kernel.CloseHandle.argtypes=[wintypes.HANDLE]
 handle=kernel.CreateMutexW(None,False,'Local\\Server16ManagerView_'+str(pid))
 if not handle:raise ctypes.WinError(ctypes.get_last_error())
 try:
  if kernel.WaitForSingleObject(handle,10000) not in (0,128):raise TimeoutError('Publicação visual ocupada')
  try:yield
  finally:kernel.ReleaseMutex(handle)
 finally:kernel.CloseHandle(handle)

class Progress:
 def __init__(self,path):self.path=Path(path);self.value=None
 def begin(self,observed,io):
  owner=scope(observed,io)
  if self.value and self.value['scope']==owner:return
  self.value=dict(schema=1,scope=owner,started_ms=round(time.monotonic()*1000),stage=0,active=True)
  atomic(self.path,self.value)
 def set(self,stage):
  if not self.value or not self.value['active']:return
  stage=max(0,min(len(STAGES)-1,int(stage)))
  if stage>self.value['stage']:
   self.value.update(stage=stage,active=True);atomic(self.path,self.value)
 def done(self):
  if self.value:self.value.update(active=False);atomic(self.path,self.value)

def scene(stage,elapsed):
 from layout import Scene
 from ui_theme import ACCENT
 from manager_layout import PAPER,INK,MUTED,LIGHT,text
 stage=max(0,min(4,stage));s=Scene('loading','Carregando o mercado')
 s.rect(60,90,1800,828,PAPER);s.text(110,130,1680,64,'MERCADO DE TÉCNICOS',39,INK)
 s.text(180,330,1550,52,STAGES[stage],31,INK)
 s.rect(180,415,1550,20,LIGHT)
 if stage:s.rect(180,415,1550*stage/5,20,ACCENT)
 # A narrow moving marker says the current stage is active. The filled part
 # advances only when a real stage finishes, never on a cosmetic timer.
 s.rect(180+1550*stage/5,411,8,28,ACCENT)
 s.text(180,462,1040,38,f'Etapa {stage+1} de 5 · {stage*20}% das etapas concluídas',25,INK)
 s.text(1270,462,460,38,'Em segundo plano',25,MUTED,1)
 s.text(180,515,1550,34,'A barra acompanha etapas reais; o tempo restante varia conforme os dados da carreira.',21,MUTED)
 for i,label in enumerate(STAGES):
  y=598+i*46;s.rect(184,y+8,12,12,ACCENT if i<=stage else LIGHT)
  s.text(218,y,1460,32,('Concluído · ' if i<stage else 'Em andamento · ' if i==stage else '')+label,22,INK if i==stage else MUTED)
 return [s.pack()]

def build(game,path,stage,elapsed):
 import build_screen as b
 import native_screen as native
 from build_preview import Code
 FULL='game.screens.career.server16.ManagerMarket';CLASS=tuple(FULL.split('.'))
 R=b.reg;T=b.this;P=b.prop;CALL=b.call;PATH=b.path;M=b.MANAGER;ION=b.ION
 def script(data,dictionaries,scenes):
  b.CLASS=CLASS;b.FULL=FULL;a=Code(data);a.align();start=len(data);data.extend(dictionaries[0])
  for i,name in enumerate(CLASS[:-1]):
   parent=b.GLOBAL if not i else PATH(*CLASS[:i]);a.when(P(parent,name),lambda a:None,lambda a,parent=parent,name=name:a.set(parent,name,('object',)))
  def ctor(a):
   a.op(89);a.reg(2);a.op(118);a.op(93)
   a.do(M('ScreenManager'),'SetOnExitScreenCallback',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('OnExitScreen')))
   a.do(R(1),'Initialize',FULL,None,True);a.set(R(1),'staticData',CALL(ION,'GetScreenStaticData'));a.set(R(1),'navEvents',CALL(ION,'GetEvents','Navigation'))
   a.set(R(1),'_visible',True);a.set(R(1),'_alpha',100);a.set(R(1),'onEnterFrame',T('Ready'))
  a.function(CLASS[-1],0,ctor,True);a.expr(PATH(*CLASS));a.expr(PATH('ion','screen','BaseScreen'));a.op(105)
  def ready(a):
   a.when(('not',T('scene0')),lambda a:a.ret());a.set(R(1),'onEnterFrame',None)
   a.do(M('InputManager'),'SetLocalEventHandler',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('LocalEventHandler')))
   a.do(M('ScreenManager'),'BeginAnimateIn',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('OnAnimateInComplete')));a.do(R(1),'OnAnimateInComplete')
  a.function('Ready',0,ready)
  a.function('OnAnimateInComplete',0,lambda a:(a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'SCREEN_READY',''),a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'DONE_LOADING','')))
  def local(a):
   a.when(b.equal(R(2),P(M('InputCodes'),'BACK')),lambda a:a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),P(T('navEvents'),'BACK'),''));a.ret(True)
  a.function('LocalEventHandler',2,local)
  a.function('getHelpContext',0,lambda a:a.ret(native.arr([CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem','BACK','Voltar')])))
  def shutdown(a):
   a.set(R(1),'onEnterFrame',None);a.do(M('InputManager'),'DisableCurrentLocalEventHandler');a.do(M('HelpManager'),'Clear');a.do(R(1),'Shutdown')
  a.function('OnExitScreen',0,shutdown);a.op(0);a.finish();a.align();registration=len(data);data.extend(dictionaries[1]);a.string(FULL);a.op(28);a.string(FULL);a.expr(2);a.expr(PATH('Object'));a.method('registerClass');a.op(23);a.op(0);a.finish();return start,registration
 return native.build(game,path,scene(stage,elapsed),{},script_factory=script,full_name=FULL,compression_level=1)
