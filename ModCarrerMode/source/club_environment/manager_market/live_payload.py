"""Tiny native movie payloads: update a mounted screen without re-entering it."""
from pathlib import Path
import os,struct

def value(item):
 if isinstance(item,dict):return ('map',{k:value(v) for k,v in item.items()})
 if isinstance(item,(list,tuple)):return ('array',tuple(value(v) for v in item))
 return item

def build(game,path,payload):
 import build_screen as b
 import native_screen as native
 from build_preview import Code
 from layout import Scene
 full='game.screens.career.server16.ManagerLiveData';cls=tuple(full.split('.'))
 artwork=payload.get('artwork');scenes=None;assets={}
 if artwork:
  from profile_media import prepare
  scene,assets=prepare(game,artwork);scenes=[scene]
 rows=payload.get('data',{}).get('rows') if payload.get('kind')=='history' else None
 base=dict(payload,data=dict(payload['data'],rows=[])) if rows is not None else dict(payload)
 base.pop('artwork',None)
 def script(data,dictionaries,scenes):
  b.CLASS=cls;b.FULL=full;a=Code(data);a.align();start=len(data);data.extend(dictionaries[0])
  for i,name in enumerate(cls[:-1]):
   parent=b.GLOBAL if not i else b.path(*cls[:i]);a.when(b.prop(parent,name),lambda a:None,lambda a,p=parent,n=name:a.set(p,n,('object',)))
  def ctor(a):
   a.set(b.reg(1),'payload',value(base))
   if rows is not None:
    for row in rows:a.do(b.prop(b.prop(b.this('payload'),'data'),'rows'),'push',value(row))
   if artwork:
    a.set(b.this('payload'),'artworkNames',('array',()))
    for node in scenes[0]['nodes']:a.do(b.prop(b.this('payload'),'artworkNames'),'push',node['name'])
   a.set(b.reg(1),'payloadReady',True)
   # A loaded APT retains the native root placement named Screen. Mirror its
   # data after frame-one children exist for older mounted consumers too.
   a.set(b.reg(1),'onEnterFrame',b.this('PublishToLoader'))
  a.function(cls[-1],0,ctor,True);a.expr(b.path(*cls));a.expr(b.path('MovieClip'));a.op(105)
  def publish_to_loader(a):
   a.when(('not',b.this('scene0')),lambda a:a.ret())
   parent=b.this('_parent')
   a.when(parent,lambda a:(a.set(parent,'payload',b.this('payload')),a.set(parent,'scene0',b.this('scene0')),a.set(parent,'payloadReady',True)))
   a.set(b.reg(1),'onEnterFrame',None)
  a.function('PublishToLoader',0,publish_to_loader)
  # loadMovie executes timeline actions but does not instantiate the exported
  # screen class through ScreenManager. Publish on the loaded clip itself;
  # keeping the constructor too preserves explicit native screen creation.
  a.op(86);a.op(135);a.align();data.extend(struct.pack('<I',1));a.op(23)
  ctor(a);a.op(0);a.finish()
  a.align();registration=len(data);data.extend(dictionaries[1]);a.string(full);a.op(28);a.string(full);a.expr(2);a.expr(b.path('Object'));a.method('registerClass');a.op(23);a.op(0);a.finish();return start,registration
 return native.build(game,path,scenes or [Scene('payload','').pack()],assets,script_factory=script,full_name=full,compression_level=1)

def publish(game,root,name,payload):
 root=Path(root);temporary=root/(name+'-'+str(os.getpid())+'.big')
 build(game,temporary,payload);blob=temporary.read_bytes()
 if payload.get('artwork') and payload.get('kind')=='profile':
  import re
  token=str(payload.get('token',''))[:16]
  if not re.fullmatch('[A-Za-z0-9]{1,16}',token):raise ValueError('Identidade de perfil inválida')
  name=name+'_'+token+'_'+str(int(payload['person']))+'_'
 for i in (0,1):
  target=Path(game)/('data/ui/game/screens/career/server16/'+name+str(i)+'.big')
  target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_name(target.name+'.'+str(os.getpid())+'.new');temp.write_bytes(blob);os.replace(temp,target)
 temporary.unlink(missing_ok=True)
 return len(blob)

def emit(a,prefix,name,accept,consume,interval=30,*,parent=None,artwork=False,filename=None,art_host=None):
 """Poll a data child without repeatedly aborting its native resource load."""
 import build_screen as b
 R=b.reg;T=b.this;P=b.prop;CALL=b.call
 holder=T(prefix+'Holder');mount=parent if parent is not None else R(1)
 def poll(a):
  a.when(holder,lambda a:None,lambda a:(a.set(R(1),prefix+'Holder',CALL(mount,'createEmptyMovieClip',prefix+'Payload',810 if prefix=='history' else 811)),a.set(holder,'_visible',True),a.set(holder,'_alpha',0),a.set(R(1),prefix+'Retry',0),a.set(R(1),prefix+'Slot',0),a.set(R(1),prefix+'Loading',False)))
  if art_host is not None:a.set(art_host,prefix+'Payload',holder)
  loaded=P(holder,'content')
  # ScreenManager creates the exported symbol directly. loadMovie instead
  # retains the APT's outer timeline, whose native placement is named Screen.
  a.set(holder,'view',loaded)
  a.when(P(loaded,'Screen'),lambda a:a.set(holder,'view',P(loaded,'Screen')))
  child=P(holder,'view');data=P(child,'payload')
  def delivered(a):
   def accepted(a):
    if artwork:
     # APT can run a loaded movie's constructor before its timeline children.
     # Keep the holder hidden until every selected clip exists; the UI frame
     # checks readiness without cancelling or recreating the loaded movie.
     names=P(data,'artworkNames');index=T(prefix+'ArtworkIndex')
     a.set(R(1),prefix+'ArtworkReady',True);a.set(R(1),prefix+'ArtworkIndex',0)
     start,end=a.uid(),a.uid();a.label(start)
     a.expr(('not',('bin',72,index,P(names,'length'))));a.branch(end)
     clip=('index',P(child,'scene0'),('index',names,index))
     a.when(clip,lambda a:a.set(clip,'_visible',False),lambda a:a.set(R(1),prefix+'ArtworkReady',False))
     a.set(R(1),prefix+'ArtworkIndex',('bin',71,index,1));a.branch(start,False);a.label(end)
     a.when(('not',T(prefix+'ArtworkReady')),lambda a:a.ret())
    consume(a,data)
    if not artwork:a.do(loaded,'unloadMovie')
    a.set(R(1),prefix+'Loading',False);a.set(R(1),prefix+'Retry',interval);a.ret()
   a.when(accept(data),accepted)
   a.do(loaded,'unloadMovie');a.set(R(1),prefix+'Loading',False)
  a.when(P(child,'payloadReady'),delivered)
  def in_flight(a):
   a.set(R(1),prefix+'LoadFrames',('bin',71,T(prefix+'LoadFrames'),1))
   a.when(('bin',72,T(prefix+'LoadFrames'),30),lambda a:a.ret())
   a.set(R(1),prefix+'Loading',False)
  a.when(T(prefix+'Loading'),in_flight)
  a.set(R(1),prefix+'Retry',('bin',11,T(prefix+'Retry'),1))
  a.when(('bin',103,T(prefix+'Retry'),0),lambda a:a.ret())
  a.set(R(1),prefix+'Retry',interval)
  a.when(loaded,lambda a:a.do(loaded,'unloadMovie'))
  a.do(holder,'createEmptyMovieClip','content',1)
  a.set(R(1),prefix+'Slot',('bin',11,1,T(prefix+'Slot')))
  a.set(R(1),prefix+'Loading',True);a.set(R(1),prefix+'LoadFrames',0)
  stem=filename if filename is not None else 'game/screens/career/server16/'+name
  if filename is not None:stem=('bin',71,'game/screens/career/server16/',stem)
  a.do(P(holder,'content'),'loadMovie',('bin',71,('bin',71,stem,T(prefix+'Slot')),'.swf'))
 a.function(prefix+'Poll',0,poll)

def cleanup_profile_media(game):
 """Only our small session-generated CV packets, after FIFA has exited."""
 import re
 folder=Path(game)/'data/ui/game/screens/career/server16';count=0
 for file in folder.glob('managerprofile_*.big'):
  if not re.fullmatch(r'managerprofile_[A-Za-z0-9]{1,16}_[0-9]+_[01]\.big',file.name):continue
  try:file.unlink();count+=1
  except OSError:pass
 return count
