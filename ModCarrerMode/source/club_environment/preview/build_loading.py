"""Small native waiting view: never display the previous fixture while preparing."""
from pathlib import Path
import shutil,tempfile
import build_screen as b
from build_preview import Code

CLASS=('game','screens','career','server16','MatchPreviewLoading')
PAGE='/'.join(CLASS)
FIELDS=(('title',130,170,1620,65,42),('message',130,350,1620,70,34),
        ('detail',130,450,1620,65,26),('status',130,850,1620,40,24))

def build(output):
    # Keep builder globals isolated: the bank worker uses the same template.
    names=('HERE','CLASS','FULL','PAGE','Code','FIELDS','make_script','USE_R57','USE_R60')
    saved={name:getattr(b,name,None) for name in names}
    def script(data,dictionaries):
        a=Code(data);a.align();start=len(data);data.extend(dictionaries[0])
        for i,name in enumerate(CLASS[:-1]):
            parent=b.GLOBAL if not i else b.path(*CLASS[:i])
            a.when(b.prop(parent,name),lambda a:None,lambda a,parent=parent,name=name:a.set(parent,name,('object',)))
        def constructor(a):
            a.op(89);a.reg(2);a.op(118);a.op(93)
            a.do(b.MANAGER('ScreenManager'),'SetOnExitScreenCallback',b.call(b.path('cafe','utility','Delegate'),'Create',b.reg(1),b.this('OnExitScreen')))
            a.do(b.reg(1),'Initialize',b.FULL,None,True)
            a.set(b.reg(1),'staticData',b.call(b.ION,'GetScreenStaticData'))
            a.set(b.reg(1),'navEvents',b.call(b.ION,'GetEvents','Navigation'));a.do(b.reg(1),'InitComponents')
            a.do(b.MANAGER('ScreenManager'),'BeginAnimateIn',b.call(b.path('cafe','utility','Delegate'),'Create',b.reg(1),b.this('OnAnimateInComplete')))
            a.do(b.reg(1),'OnAnimateInComplete')
        def complete(a):
            a.when(b.this('screenReady'),lambda a:a.ret());a.set(b.reg(1),'screenReady',True)
            a.set(b.reg(1),'_visible',True);a.set(b.reg(1),'_alpha',100)
            a.do(b.ION,'SendEvent',b.prop(b.this('staticData'),'SCREEN_CONTROLLER_ID'),'SCREEN_READY','')
            a.do(b.ION,'SendSystemEvent',b.prop(b.this('staticData'),'SCREEN_CONTROLLER_ID'),'DONE_LOADING','')
            a.do(b.MANAGER('InputManager'),'SetLocalEventHandler',b.call(b.path('cafe','utility','Delegate'),'Create',b.reg(1),b.this('LocalEventHandler')))
            a.do(b.MANAGER('HelpManager'),'Update')
        a.function(CLASS[-1],0,constructor,True);a.expr(b.path(*CLASS));a.expr(b.path('ion','screen','BaseScreen'));a.op(105)
        a.function('getHelpContext',0,lambda a:a.ret(('array',(b.call(b.path('ion','manager','HelpItem'),'CreateHelpTickerItem','BACK','Voltar'),))))
        def init(a):
            a.when(('not',('bin',16,b.this('title'),b.this('status'))),lambda a:(a.set(b.reg(1),'onEnterFrame',b.this('InitComponents')),a.ret()))
            a.set(b.reg(1),'onEnterFrame',None)
            a.set(b.this('mcGridControl'),'_visible',False)
            for field,value in (('title','PRÓXIMA PARTIDA'),('message','Atualizando as informações da partida...'),
                                ('detail','Preparando escalações, estádio e últimos resultados.'),('status','Esc / B: voltar')):
                a.set(b.this(field),'text',value)
            a.set(b.reg(1),'_visible',True);a.set(b.reg(1),'_alpha',100)
        def back(a):
            a.do(b.ION,'SendEvent',b.prop(b.this('staticData'),'SCREEN_CONTROLLER_ID'),b.prop(b.this('navEvents'),'BACK'),'')
            a.do(b.MANAGER('InputManager'),'DisableCurrentLocalEventHandler')
        def key(a):
            a.when(b.equal(b.reg(2),b.prop(b.MANAGER('InputCodes'),'BACK')),back);a.ret(True)
        def shutdown(a):
            a.set(b.reg(1),'exiting',True);a.set(b.reg(1),'onEnterFrame',None);a.do(b.MANAGER('InputManager'),'DisableCurrentLocalEventHandler')
            a.do(b.MANAGER('HelpManager'),'Clear');a.do(b.reg(1),'Shutdown')
        for name,count,body in (('InitComponents',0,init),('OnAnimateInComplete',0,complete),('LocalEventHandler',2,key),('OnExitScreen',0,shutdown)):
            a.function(name,count,body)
        a.op(0);a.finish();a.align();registration=len(data);data.extend(dictionaries[1])
        a.string(b.FULL);a.op(28);a.string(b.FULL);a.expr(2);a.expr(b.path('Object'));a.method('registerClass');a.op(23);a.op(0);a.finish()
        return start,registration
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix='server16_preview_loading_') as directory:
            folder=Path(directory);shutil.copy2(saved['HERE']/'careertype.big',folder/'careertype.big')
            b.HERE=folder;b.CLASS=CLASS;b.FULL='.'.join(CLASS);b.PAGE=PAGE;b.Code=Code;b.FIELDS=FIELDS
            b.make_script=script;b.USE_R57=False;b.USE_R60=True;b.build()
            shutil.copy2(folder/'package/data/ui/game/screens/career/server16/bankloans.big',output)
    finally:
        for name,value in saved.items():
            if value is None:delattr(b,name)
            else:setattr(b,name,value)
    return output

if __name__=='__main__':
    import portable_paths as portable
    build(portable.GAME/'data/ui/game/screens/career/server16/matchpreviewloading.big')
