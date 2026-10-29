from ui_theme import ACCENT, ACCENT_INK, ACCENT_TEXT, rgb
"""Native white FIFA finance screen and original keyboard/pad help ticker."""
from pathlib import Path
import json,sys
import portable_paths as portable
local_market=Path(__file__).resolve().parents[1]/'market'
sys.path.insert(0,str(local_market if (local_market/'native_screen.py').is_file() else portable.SOURCES/'market'))
import build_screen as b
from build_preview import Code
from native_screen import build as build_native,neighbors,arr
from layout import Scene,INK,BLUE,MUTED,WHITE,PAPER,LIGHT
from club_finance import monthly,SWITCHES
from loans import parse_date

CLASS=('game','screens','career','server16','ClubFinance');FULL='.'.join(CLASS);PAGE='/'.join(CLASS)
TABS=(('overview','Visão geral'),('receipts','Receitas'),('expenses','Despesas'),('transfers','Transferências'),('salaries','Salários'),('loans','Dívidas'),('budget','Orçamento'),('settings','Configurações'))
ROOT_TABS={'contracts':'receipts','tickets':'receipts','statement':'budget','monthly':'overview'}

def root_tab(key):return ROOT_TABS.get(key.split(':')[0],key.split(':')[0])
R=b.reg;T=b.this;P=b.prop;EQ=b.equal;CALL=b.call;M=b.MANAGER;ION=b.ION
def day(value):
 try:return parse_date(value).strftime('%d/%m/%Y')
 except (ValueError,TypeError):return 'Aguardando carreira'

def money(s,x,y,w,h,value,size=27,color=BLUE,align=1,compact=False):
 name='money'+str(sum(n.get('name','').startswith('money') for n in s.nodes))
 s.text(x,y,w,h,'',size,color,align);s.nodes[-1].update(name=name,amount=int(value),compact=compact)

def shell(view,key,tab):
 s=Scene(key,'Finanças do clube');s.rect(60,90,1800,828,PAPER)
 s.text(100,120,1720,58,'FINANÇAS DO CLUBE',40)
 s.text(102,182,1720,34,f"{view.get('club_name','Clube')} · {day(view.get('date'))} · Acompanhamento desde {day(view.get('start'))}",23,MUTED)
 for i,(target,label) in enumerate(TABS):s.action(100+i*216,234,208,50,label,target,ACCENT if target==tab else LIGHT,ACCENT_TEXT if target==tab else INK,22)
 s.text(100,876,1715,30,view.get('message','Receitas adicionais do mod · Valores aplicados à verba de transferências.'),19,MUTED)
 return s

def scenes(view):
 from finance_dashboard import summary
 from finance_pages import pages as detail_pages
 rows=view.get('months',[]);result=[summary(view,shell,money)]+detail_pages(view,shell,money)
 contracts=view.get('agreements',[]);pages=max(1,(len(contracts)+5)//6)
 for page in range(pages):
  key='contracts' if page==0 else 'contracts:'+str(page);s=shell(view,key,'receipts');assets={}
  s.text(120,310,1320,40,'TV · CONTRATO POR COMPETIÇÃO',28)
  s.text(1450,315,350,35,'VALOR POR PARTIDA',21,MUTED,1)
  for i,c in enumerate(contracts[page*6:page*6+6]):
   y=367+i*72;s.rect(100,y,1720,65,WHITE)
   from finance_pages import picture
   from club_finance import match_terms
   picture(s,assets,'crest',view.get('club',0),119,y+9,42,46);picture(s,assets,'competition',c['asset'],175,y+7,46,49)
   s.text(240,y+4,1090,33,c['name'],25);s.text(240,y+37,1090,24,'Vigência: temporada da carreira · Somente partidas efetivamente disputadas',18,MUTED)
   money(s,1400,y+15,400,36,match_terms(c,view.get('date') or 0)['per_match'],27)
  if not contracts:s.text(120,390,1600,55,'Os contratos aparecem ao confirmar as competições da carreira.',25,MUTED)
  if pages>1:
   s.action(100,811,155,42,'‹','contracts' if page<=1 else 'contracts:'+str(page-1));s.action(270,811,155,42,'›','contracts:'+str(page+1) if page+1<pages else key)
  packed=s.pack();packed['assets']=assets;result.append(packed)
 months=rows[:24];pages=max(1,(len(months)+6)//7)
 for page in range(pages):
  key='statement' if page==0 else 'statement:'+str(page);s=shell(view,key,'budget')
  s.text(120,310,1700,40,'EXTRATO MENSAL · MOVIMENTAÇÕES EFETIVADAS',28)
  for x,w,label in ((120,150,'MÊS'),(285,230,'TV'),(530,230,'BILHETERIA'),(775,230,'PATROCÍNIO'),(1020,230,'EQUIPE'),(1265,230,'JOGOS'),(1510,290,'PARCELAS')):s.text(x,366,w,30,label,20,MUTED,0 if x==120 else 1)
  for i,row in enumerate(months[page*7:page*7+7]):
   y=410+i*53;s.rect(100,y,1720,47,WHITE if i%2==0 else LIGHT)
   text=str(row['month']);s.text(120,y+6,150,34,text[4:]+'/'+text[:4],22)
   for x,w,value in ((285,230,row.get('tv',0)),(530,230,row.get('tickets',0)),(775,230,row.get('sponsor',0)),(1020,230,row.get('coach',0)+row.get('staff',0)),(1265,230,row.get('match_costs',0)),(1510,290,row.get('loans',0))):money(s,x,y+6,w,35,value,22)
  if not months:s.text(120,450,1640,65,'Ainda não há lançamentos. Acompanhe após disputar jogos e avançar o calendário.',25,MUTED)
  if pages>1:
   s.action(100,811,155,42,'‹','statement' if page<=1 else 'statement:'+str(page-1));s.action(270,811,155,42,'›','statement:'+str(page+1) if page+1<pages else key)
  result.append(s.pack())
 import finance_art as art
 s=shell(view,'settings','settings');assets={}
 s.text(120,308,1670,42,'MODO FINANCEIRO · OPÇÕES DESTA CARREIRA E CLUBE',28)
 labels=('Sistema financeiro · chave geral','Receitas de TV por partida','Bilheteria dos jogos em casa','Salário mensal do técnico','Cobrança automática dos empréstimos','Patrocínio do clube','Comissão técnica','Custos das partidas em casa')
 descriptions=('Controla os acréscimos e débitos do sistema financeiro.',
  'Recebe o contrato da competição por partida concluída.',
  'Receita adicional calculada para jogos como mandante.',
  'Desconta a remuneração do técnico ao fechar o mês.',
  'Mantém as parcelas e cobra os vencimentos pelo calendário.',
  'Um contrato por clube e temporada, proporcional à reputação.',
  'Equipe de apoio estimada pelo porte do clube, descontada ao mês.',
  'Operação e taxas estimadas, cobradas junto à renda do jogo em casa.')
 for i,(kind,label) in enumerate(zip(SWITCHES,labels)):
  enabled=view.get('settings',{}).get(kind,True);y=354+i*56
  s.action(100,y,1720,52,'','toggle:'+kind,WHITE,INK,25)
  s.actions[-1].update(setting=i,value=not enabled)
  s.text(125,y+3,1270,27,label,23);s.text(125,y+29,1270,21,descriptions[i],17,MUTED)
  s.text(1420,y+12,230,30,'Ativado' if enabled else 'Desativado',22,BLUE if enabled else MUTED,1);s.nodes[-1]['name']='switchState'+str(i)
  for state in (False,True):
   asset='switch'+str(int(state));assets[asset]=art.switch(state)
   s.image(asset,1686,y+8,92,36);s.nodes[-1]['name']=('switchOn' if state else 'switchOff')+str(i)
 s.text(120,809,1670,24,'A chave geral bloqueia novos créditos e débitos. Desativar mantém o histórico e as dívidas existentes.',18,MUTED)
 s.text(120,840,1670,28,'',20,BLUE);s.nodes[-1]['name']='settingsFeedback'
 packed=s.pack();packed['assets']=assets;result.append(packed)
 # Page chunks keep bounded APT work and original native help/input handling.
 for scene in result:
  scene['back']='overview'
  buttons=scene['actions']
  scene['scrollPrevious']=next((b['target'] for b in buttons if b['label']=='‹'),scene['key'])
  scene['scrollNext']=next((b['target'] for b in buttons if b['label']=='›'),scene['key'])
 return result

def script(data,dictionaries,items,view):
 b.CLASS=CLASS;b.FULL=FULL
 a=Code(data);a.align();start=len(data);data.extend(dictionaries[0]);keys={s['key']:i for i,s in enumerate(items)}
 focus_for_page=arr(next((j for j,(key,_) in enumerate(TABS) if root_tab(s['key'])==key),0) for s in items)
 settings_clip=T('scene'+str(keys['settings']))
 pending=('bin',16,EQ(b.G('Server16FinanceNonce'),view.get('nonce','DISABLED')),('bin',103,b.G('Server16FinancePending'),view.get('ack',0)))
 for i,name in enumerate(CLASS[:-1]):
  parent=b.GLOBAL if not i else b.path(*CLASS[:i]);a.when(P(parent,name),lambda a:None,lambda a,parent=parent,name=name:a.set(parent,name,('object',)))
 def ctor(a):
  a.op(89);a.reg(2);a.op(118);a.op(93)
  a.do(M('ScreenManager'),'SetOnExitScreenCallback',CALL(b.path('cafe','utility','Delegate'),'Create',R(1),T('OnExitScreen')))
  a.do(R(1),'Initialize',FULL,None,True);a.set(R(1),'staticData',CALL(ION,'GetScreenStaticData'));a.set(R(1),'navEvents',CALL(ION,'GetEvents','Navigation'))
  a.set(R(1),'page',0);a.set(R(1),'focus',0)
  def restore(a):
   for i,s in enumerate(items):a.when(EQ(b.G('Server16FinancePageKey'),s['key']),lambda a,i=i:a.set(R(1),'page',i))
  a.when(b.G('Server16FinanceReloading'),restore)
  a.set(R(1),'focus',('index',focus_for_page,T('page')))
  a.set(R(1),'waitingSetting',False);a.set(R(1),'settingsFeedback',(view.get('setting_result') or {}).get('message',''))
  for i,kind in enumerate(SWITCHES):a.set(R(1),'setting'+str(i),view.get('settings',{}).get(kind,True))
  def waiting(a):
   a.set(R(1),'waitingSetting',True);a.set(R(1),'settingsFeedback','Aplicando configuração...')
   for i in range(len(SWITCHES)):
    a.when(EQ(b.G('Server16FinanceSetting'),i),lambda a,i=i:a.set(R(1),'setting'+str(i),b.G('Server16FinanceValue')))
  a.when(pending,waiting)
  def restore_focus(a):
   a.when(('bin',16,('bin',103,b.G('Server16FinanceFocus'),len(TABS)-1),('bin',72,b.G('Server16FinanceFocus'),len(TABS)+len(SWITCHES))),lambda a:a.set(R(1),'focus',b.G('Server16FinanceFocus')))
  a.when(EQ(T('page'),keys['settings']),restore_focus)
  a.set(b.GLOBAL,'Server16FinanceReloading',False);a.set(R(1),'_visible',True);a.set(R(1),'_alpha',100)
  a.set(R(1),'onEnterFrame',T('WaitClips'));a.do(R(1),'WaitClips')
 a.function(CLASS[-1],0,ctor,True);a.expr(b.path(*CLASS));a.expr(b.path('ion','screen','BaseScreen'));a.op(105)
 def bind(a):
  last=P(settings_clip,'switchOn'+str(len(SWITCHES)-1))
  a.when(('not',('bin',16,P(T('scene0'),'action0'),last)),lambda a:a.ret())
  for i,s in enumerate(items):
   for j,action in enumerate(s['actions']):
    obj=P(T('scene'+str(i)),'action'+str(j));a.set(obj,'owner',R(1));a.set(obj,'index',j);a.set(obj,'onRelease',T('Click'));a.set(obj,'onRollOver',T('Over'))
  a.set(R(1),'onEnterFrame',None);a.set(R(1),'pollFrames',0)
  a.when(pending,lambda a:a.set(R(1),'onEnterFrame',T('Poll')))
  if not view.get('ready'):a.set(R(1),'onEnterFrame',T('Poll'))
  a.do(M('InputManager'),'SetLocalEventHandler',CALL(b.path('cafe','utility','Delegate'),'Create',R(1),T('LocalEventHandler')))
  a.do(R(1),'Refresh')
  a.do(M('ScreenManager'),'BeginAnimateIn',CALL(b.path('cafe','utility','Delegate'),'Create',R(1),T('OnAnimateInComplete')))
  a.do(R(1),'OnAnimateInComplete')
 a.function('WaitClips',0,bind)
 def complete(a):
  a.when(T('screenReady'),lambda a:a.ret());a.set(R(1),'screenReady',True)
  a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'SCREEN_READY','');a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'DONE_LOADING','')
 a.function('OnAnimateInComplete',0,complete)
 def refresh(a):
  for i,s in enumerate(items):
   clip=T('scene'+str(i));a.set(clip,'_visible',EQ(T('page'),i))
   for j,_ in enumerate(s['actions']):a.set(P(P(clip,'action'+str(j)),'selected'),'_alpha',('bin',12,EQ(T('focus'),j),100))
   a.when(EQ(T('page'),i),lambda a,i=i:a.do(R(1),'Money'+str(i)))
  a.do(R(1),'RefreshSwitches')
  a.do(M('HelpManager'),'Update')
 a.function('Refresh',0,refresh)
 def switches(a):
  for i in range(len(SWITCHES)):
   state=T('setting'+str(i));a.set(P(settings_clip,'switchOn'+str(i)),'_visible',state);a.set(P(settings_clip,'switchOff'+str(i)),'_visible',('not',state))
   field=P(settings_clip,'switchState'+str(i))
   a.when(state,lambda a,field=field:(a.set(field,'text','Ativado'),a.set(field,'textColor',rgb(ACCENT_INK))),lambda a,field=field:(a.set(field,'text','Desativado'),a.set(field,'textColor',0x6b818d)))
  a.set(P(settings_clip,'settingsFeedback'),'text',T('settingsFeedback'))
 a.function('RefreshSwitches',0,switches)
 for i,s in enumerate(items):
  def values(a,i=i,s=s):
   for n in s['nodes']:
    if 'amount' in n:a.set(P(T('scene'+str(i)),n['name']),'text',CALL(b.path('ION_Localization'),'LocalizeCurrencyWithType',n.get('compact',False),n['amount'],view.get('currency',0)))
  a.function('Money'+str(i),0,values)
 def go(a):
  a.set(R(1),'page',R(2));a.set(R(1),'focus',('index',focus_for_page,R(2)));a.do(R(1),'Refresh')
 a.function('Go',1,go)
 def select(a):
  for i,s in enumerate(items):
   def choose(a,i=i,s=s):
    for j,action in enumerate(s['actions']):
     def handle(a,action=action):
      if 'setting' in action:
       if not view.get('ready'):return
       a.when(T('waitingSetting'),lambda a:a.ret())
       index=action['setting'];a.set(R(1),'setting'+str(index),('not',T('setting'+str(index))))
       a.set(R(1),'waitingSetting',True);a.set(R(1),'settingsFeedback','Aplicando configuração...')
       a.do(R(1),'RefreshSwitches')
       a.when(b.G('Server16BankSequenceV2'),lambda a:None,lambda a:a.set(b.GLOBAL,'Server16BankSequenceV2',0))
       a.set(b.GLOBAL,'Server16BankSequenceV2',b.plus(b.G('Server16BankSequenceV2'),1))
       a.set(b.GLOBAL,'Server16FinancePending',b.G('Server16BankSequenceV2'));a.set(b.GLOBAL,'Server16FinanceNonce',view['nonce'])
       a.set(b.GLOBAL,'Server16FinanceSetting',index);a.set(b.GLOBAL,'Server16FinanceValue',T('setting'+str(index)));a.set(b.GLOBAL,'Server16FinanceFocus',T('focus'))
       value=b.plus(b.plus('S16BANK_V3|'+view['nonce']+'|',b.G('Server16BankSequenceV2')),f'|2|{index}|')
       wire=b.plus(b.plus(value,('bin',12,T('setting'+str(index)),1)),f"|0|{view['date']}|END_S16BANK")
       a.do(ION,'SendSystemEvent','Calendar','Server16SubmitBank',wire)
       a.set(R(1),'pollFrames',0);a.set(R(1),'onEnterFrame',T('Poll'))
      else:a.do(R(1),'Go',keys.get(action['target'],0))
      # Go changes page/focus. End this APT dispatch before the loop reaches
      # another scene and accidentally handles its newly selected first tab.
      a.ret()
     a.when(EQ(T('focus'),j),handle)
   a.when(EQ(T('page'),i),choose)
 a.function('Select',0,select)
 def over(a):a.set(P(R(1),'owner'),'focus',P(R(1),'index'));a.do(P(R(1),'owner'),'Refresh')
 def click(a):a.do(R(1),'onRollOver');a.do(P(R(1),'owner'),'Select')
 a.function('Over',0,over);a.function('Click',0,click)
 def move(a):
  table=arr(arr(arr(r) for r in neighbors(s['actions'])) for s in items)
  a.set(R(1),'focus',('index',('index',('index',table,T('page')),T('focus')),R(2)));a.do(R(1),'Refresh')
 a.function('Move',1,move)
 roots=[keys[k] for k,_ in TABS]
 def tab(a):
  selected=arr(next((i for i,(key,_) in enumerate(TABS) if root_tab(s['key'])==key),0) for s in items)
  at=('bin',63,b.plus(b.plus(('index',selected,T('page')),R(2)),len(roots)),len(roots));a.do(R(1),'Go',('index',arr(roots),at))
 a.function('ChangeTab',1,tab)
 def scroll(a):
  previous=arr(keys.get(s['scrollPrevious'],keys[s['key']]) for s in items)
  following=arr(keys.get(s['scrollNext'],keys[s['key']]) for s in items)
  a.when(EQ(R(2),-1),lambda a:a.do(R(1),'Go',('index',previous,T('page'))),lambda a:a.do(R(1),'Go',('index',following,T('page'))))
 a.function('Scroll',1,scroll)
 def back(a):
  def leave(a):
   a.set(R(1),'leaving',True);a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),P(T('navEvents'),'BACK'),'')
  a.when(EQ(T('page'),0),leave,lambda a:a.do(R(1),'Go',0))
 a.function('Back',0,back)
 def poll(a):
  a.set(R(1),'pollFrames',b.plus(T('pollFrames'),1))
  def slow(a):
   a.set(R(1),'settingsFeedback','Aguardando confirmação do serviço. A opção ainda não foi confirmada.');a.do(R(1),'RefreshSwitches');a.set(R(1),'onEnterFrame',None)
  a.when(('bin',103,T('pollFrames'),1799),slow)
 a.function('Poll',0,poll)
 def key(a):
  for name,method,argument in (('BACK','Back',None),('ADVANCE','Select',None),('PRIMARY_SELECT','Select',None),('LEFT','Move',0),('RIGHT','Move',1),('UP','Move',2),('DOWN','Move',3),('LAS_LEFT','Move',0),('LAS_RIGHT','Move',1),('LAS_UP','Move',2),('LAS_DOWN','Move',3),('RAS_UP','Scroll',-1),('RAS_DOWN','Scroll',1),('L2','ChangeTab',-1),('R2','ChangeTab',1)):
   code=P(M('InputCodes'),name)
   def handle(a,method=method,argument=argument):a.do(R(1),method,*(() if argument is None else (argument,)));a.ret(True)
   a.when(('bin',16,code,EQ(R(2),code)),handle)
  a.ret(True)
 a.function('LocalEventHandler',2,key)
 a.function('getHelpContext',0,lambda a:a.ret(arr(CALL(b.path('ion','manager','HelpItem'),'CreateHelpTickerItem',code,label) for code,label in (('ADVANCE','Selecionar'),('BACK','Voltar'),('L2R2','Abas'),('RAS_UD','Rolar lista')))))
 def shutdown(a):
  a.set(b.GLOBAL,'Server16FinanceReloading',('not',T('leaving')))
  a.set(b.GLOBAL,'Server16FinancePageKey',('index',arr(s['key'] for s in items),T('page')));a.set(b.GLOBAL,'Server16FinanceFocus',T('focus'))
  a.set(R(1),'onEnterFrame',None);a.do(M('InputManager'),'DisableCurrentLocalEventHandler');a.do(M('HelpManager'),'Clear');a.do(R(1),'Shutdown')
 a.function('OnExitScreen',0,shutdown);a.op(0);a.finish();a.align();registration=len(data);data.extend(dictionaries[1])
 a.string(FULL);a.op(28);a.string(FULL);a.expr(2);a.expr(b.path('Object'));a.method('registerClass');a.op(23);a.op(0);a.finish()
 return start,registration

def build(view,output):
 saved={k:getattr(b,k) for k in ('CLASS','FULL')}
 items=scenes(view);assets={k:v for s in items for k,v in s.get('assets',{}).items()}
 # The shared native builder pads BC3 surfaces to 4px blocks without resampling
 # icons/charts. Fast lossless archive compression avoids delaying live updates.
 try:return build_native(portable.GAME,output,items,assets,script_factory=lambda data,dictionaries,items:script(data,dictionaries,items,view),full_name=FULL,compression_level=1)
 finally:
  for key,value in saved.items():setattr(b,key,value)
