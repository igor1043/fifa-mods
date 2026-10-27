"""Small APT helper limited to the scouting carousel (native DP 208).

FIFA's original CareerHubDataHelper returns LENGTH=report_count-1. This helper
calls the original method, keeps each report, then appends our market slide at
report_count. It never patches native code, retains a provider, or queries DBs.
"""
import build_screen as b
from build_preview import Code
from native_screen import build as build_apt,arr

CLASS=('game','screens','career','server16','MarketHubBootstrap')
FULL='.'.join(CLASS)
R=b.reg;P=b.prop;T=b.this;PATH=b.path;EQ=b.equal;CALL=b.call
HELPER=PATH('game','fluxHelpers','CareerHubDataHelper','prototype')
PROPERTIES=('TYPE','PARAM','FORMAT','WIDTH','HEIGHT','X','Y','REL_TARGET','REL_X','REL_Y','VISIBLE','TRANSLATE','HLALPHA','UHLALPHA','PATH')
FIELDS=('TITLE','SUBTITLE','NEW_ICON','NEW_ICON_INACTIVE','NEW_TEXT','UPDATES_ICON','UPDATES_ICON_INACTIVE','UPDATES_TEXT','INFO_0','INFO_1','INFO_2','INFO_3','MESSAGE','DESCRIPTION')

def original_key(slot,field,prop):return f'SUBTILE_{slot}_{field}_{prop}'

def script(data,dictionaries,scenes):
    b.CLASS=CLASS;b.FULL=FULL
    a=Code(data);a.align();start=len(data);data.extend(dictionaries[0])
    for index,name in enumerate(CLASS[:-1]):
        parent=b.GLOBAL if not index else PATH(*CLASS[:index])
        a.when(P(parent,name),lambda a:None,lambda a,p=parent,n=name:a.set(p,n,('object',)))
    def ctor(a):
        a.op(89);a.reg(2);a.op(118);a.op(93)
        a.set(R(1),'_visible',False);a.set(R(1),'onEnterFrame',T('Install'));a.do(R(1),'Install')
    a.function(CLASS[-1],0,ctor,True)
    # XML components participate in FluxHub's readiness barrier even when they
    # are invisible. A bare MovieClip leaves IsLoaded/IsReady undefined and
    # consequently prevents every career panel from being shown.
    a.expr(PATH(*CLASS));a.expr(PATH('game','components','FluxCore','FluxComponent'));a.op(105)
    a.function('Initialize',1,lambda a:(a.set(R(1),'m_oData',R(2)),a.set(R(1),'_visible',False),a.do(R(1),'Install')))
    a.function('IsLoaded',0,lambda a:a.ret(True))
    a.function('IsReady',0,lambda a:a.ret(True))
    a.function('LocalEventHandler',2,lambda a:a.ret(False))
    def shutdown(a):
        a.set(R(1),'onEnterFrame',None);a.set(R(1),'m_oDataHelper',None)
        a.do(R(1),'UnregisterForData')
    a.function('Shutdown',0,shutdown)
    def install(a):
        def ready(a):
            def apply(a):
                a.set(HELPER,'Server16MarketOriginalProcessData',P(HELPER,'ProcessData'))
                a.set(HELPER,'ProcessData',PATH(*CLASS,'prototype','ProcessScoutData'))
                a.set(HELPER,'Server16MarketInstalled',True)
            a.when(P(HELPER,'Server16MarketInstalled'),lambda a:None,apply)
            a.set(R(1),'onEnterFrame',None)
        a.when(P(HELPER,'ProcessData'),ready)
    a.function('Install',0,install)
    def wrapper(a):
        scout=('bin',16,EQ(P(P(R(2),'header'),'dpId'),PATH('game','uif','UIFDataProviderList','CM_SCOUT_REPORT_DP')),EQ(P(R(3),'ID'),208))
        a.when(('not',scout),lambda a:a.ret(CALL(R(1),'Server16MarketOriginalProcessData',R(2),R(3),R(4))))
        for slot in range(1,6):
            prefix=f'SUBTILE_{slot}_';cache=P(R(3),'Server16MarketOriginal'+str(slot))
            def restore(a,slot=slot,prefix=prefix,cache=cache):
                for key in ('DESTINATION','ID','SUBTILE_TYPE','FG_PATH','PARAM'):a.set(R(3),prefix+key,P(cache,prefix+key))
                for field in FIELDS:
                    for prop in PROPERTIES:
                        key=original_key(slot,field,prop);a.set(R(3),key,P(cache,key))
            a.when(EQ(P(R(3),'Server16MarketLastSlot'),slot),restore)
        a.do(R(1),'Server16MarketOriginalProcessData',R(2),R(3),R(4))
        count=P(('index',P(R(2),'data'),0),'LENGTH')
        # For zero reports FIFA uses the separate XML fallback; ignore invalid
        # or unexpected payloads instead of fabricating roster report counts.
        for slot in range(1,7):
            def append(a,slot=slot):
                if slot==6:
                    # XML already provides the complete seventh slide.
                    a.set(R(3),'LENGTH',6);a.set(R(3),'Server16MarketLastSlot',0);a.ret(R(3));return
                prefix=f'SUBTILE_{slot}_';cache=P(R(3),'Server16MarketOriginal'+str(slot))
                def remember(a):
                    a.set(R(3),'Server16MarketOriginal'+str(slot),('object',))
                    for key in ('DESTINATION','ID','SUBTILE_TYPE','FG_PATH','PARAM'):a.set(cache,prefix+key,P(R(3),prefix+key))
                    for field in FIELDS:
                        for prop in PROPERTIES:
                            key=original_key(slot,field,prop);a.set(cache,key,P(R(3),key))
                a.when(cache,lambda a:None,remember)
                a.set(R(3),'LENGTH',slot)
                a.set(R(3),'Server16MarketLastSlot',slot)
                for key,value in dict(DESTINATION='Server16EnterTransferMarket',ID=1902,SUBTILE_TYPE='TILE',FG_PATH='',PARAM='').items():a.set(R(3),prefix+key,value)
                for field in FIELDS:a.set(R(3),original_key(slot,field,'VISIBLE'),'FALSE')
                for field,text,y,size,height in (('TITLE','MERCADO DE TRANSFERÊNCIAS',24,'HS',58),('SUBTITLE','Compras, vendas e empréstimos de jogadores',104,'SM',58),('MESSAGE','Ligas · Clubes · Negócios · Minha liga',210,'SM',52),('DESCRIPTION','Consultar o mercado da sua carreira',324,'SM',42)):
                    attrs=dict(TYPE='text',PARAM=text,FORMAT=size,WIDTH=790,HEIGHT=height,X=24,Y=y,REL_TARGET='',REL_X=0,REL_Y=0,VISIBLE='TRUE',TRANSLATE='FALSE')
                    for key,value in attrs.items():a.set(R(3),original_key(slot,field,key),value)
                a.ret(R(3))
            a.when(EQ(count,slot),append)
        a.ret(R(3))
    a.function('ProcessScoutData',3,wrapper);a.op(0);a.finish()
    a.align();registration=len(data);data.extend(dictionaries[1]);a.string(FULL);a.op(28);a.string(FULL);a.expr(2);a.expr(PATH('Object'));a.method('registerClass');a.op(23);a.op(0);a.finish()
    return start,registration

def build(game,output):return build_apt(game,output,[],{},script_factory=script,full_name=FULL)
