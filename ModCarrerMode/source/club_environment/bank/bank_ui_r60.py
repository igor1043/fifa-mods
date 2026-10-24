import portable_paths as portable
"""Small native FIFA form: one focus model for pad, keyboard and pointer."""
import sys,json,struct
import build_screen as b
sys.path.insert(0,str(b.HERE.parent/'career_match_preview_20261022'))
from build_preview import Code
from loans import BANKS,OFFERED_BANKS,AMOUNTS,TERMS,quote,next_month,next_day,parse_date,offered,response_date as bank_response_date,response_days
b.Code=Code
R=b.reg;T=b.this;P=b.prop;M=b.MANAGER;EQ=b.equal;ADD=b.plus;CALL=b.call
ORIGINAL=b.make_script;VIEW={}
FIELDS=(('title',130,155,1640,58,42),('subtitle',132,218,1630,42,25),('section',130,280,1640,48,32),('status',130,890,1640,40,24),('pageInfo',1040,748,690,40,24),('emptyState',150,445,1520,65,29))
FIELDS+=tuple((f'detail{i}',960,350+i*45,780,43,25) for i in range(11))
FIELDS+=tuple((f'cell{i}_{j}',x,348+i*47,w,43,24) for i in range(7) for j,(x,w) in enumerate(((150,220),(400,310),(750,350),(1160,530))))

def label(a,name,value):a.set(T(name),'text',value)
def show(a,name,value):a.set(T(name),'_visible',value)
def go(a,page,focus=0):a.set(R(1),'page',page);a.set(R(1),'focus',focus);a.do(R(1),'Refresh')
def datestr(value):
 try:return parse_date(value).strftime('%d/%m/%Y')
 except (ValueError,TypeError):return 'Não disponível'

def due_date(value,count):
 try:return datestr(next_month(value,count))
 except (ValueError,TypeError):return 'Não disponível'

def response_date(value,bank=0):
 try:return bank_response_date(value,bank)
 except (ValueError,TypeError):return None

def script(data,dictionaries):
 old=b.Code.function
 def emit(self,name,count,body,constructor=False):
  result=old(self,name,count,REPLACE.get(name,body),constructor)
  if name=='InitComponents':
   for n,c,f in EXTRA:old(self,n,c,f)
  return result
 b.Code.function=emit
 try:return ORIGINAL(data,dictionaries)
 finally:b.Code.function=old

def init(a):
 for key,value in (('page',0),('focus',0 if VIEW.get('can_borrow') else 1),('bank',OFFERED_BANKS[0]),('amountIndex',0),('termIndex',1),('statementPage',0),('action',0)):a.set(R(1),key,value)
 a.when(b.G('Server16BankSequenceV2'),lambda a:None,lambda a:a.set(b.GLOBAL,'Server16BankSequenceV2',0))
 a.when(b.G('Server16BankPollAttempts'),lambda a:None,lambda a:a.set(b.GLOBAL,'Server16BankPollAttempts',0))
 # Keep the constructor bounded. Materialize only the selected plan when
 # entering its view, never a flat 585-element array on the native APT stack.
 a.set(R(1),'simulationPlan',None)
 # Sequence zero warms the bounded request scanner while the proposal is read.
 a.set(b.GLOBAL,'Server16BankHelloV2',ADD('S16BANK_V2|'+b.NONCE+'|','0|0|0|0|0|END_S16BANK'))
 a.when(EQ(b.G('Server16BankPendingNonce'),b.NONCE),lambda a:a.set(R(1),'page',5))
 if VIEW.get('result'):
  a.when(EQ(b.G('Server16BankPendingSequence'),VIEW['result']['sequence']),lambda a:a.set(b.GLOBAL,'Server16BankPendingNonce',None))
 a.set(R(1),'_visible',True);a.set(R(1),'_alpha',100);show(a,'mcGridControl',False);a.do(R(1),'Refresh');a.set(R(1),'onEnterFrame',T('WaitButtons'))

def load_plan(a):
 # Nested dispatch evaluates only one institution, amount and term. The largest
 # materialized array has 48 rows; the screen can open before any plan exists.
 for bank in range(len(BANKS)):
  def choose_bank(a,bank=bank):
   for ai,amount in enumerate(AMOUNTS):
    def choose_amount(a,ai=ai,amount=amount):
     for ti,months in enumerate(TERMS):
      if not offered(bank,amount,months):continue
      q=quote(bank,amount,months)
      rows=('array',tuple(('array',(str(p['number']).zfill(2),due_date(response_date(VIEW.get('date'),bank),p['number']),b.money(p['amount']),'Prevista')) for p in q['payments']))
      a.when(EQ(T('termIndex'),ti),lambda a,rows=rows:a.set(R(1),'simulationPlan',rows))
    a.when(EQ(T('amountIndex'),ai),choose_amount)
  a.when(EQ(T('bank'),bank),choose_bank)

BUTTONS=[('row'+str(i),i,'RowClick','RowOver') for i in range(5)]+[('payNext',0,'PaymentClick','PaymentOver'),('payAll',1,'PaymentClick','PaymentOver'),('ledgerBack',2,'PaymentClick','PaymentOver'),('previousStatement',-1,'PageClick',None),('nextStatement',1,'PageClick',None)]+[('tableRow'+str(i),i,'RowClick','RowOver') for i in range(6)]
def wait(a):
 def bind(a):
  for name,index,click,over in BUTTONS:
   obj=T(name);a.set(obj,'owner',R(1));a.set(obj,'index',index);a.set(obj,'onRelease',T(click))
   if over:a.set(obj,'onRollOver',T(over))
  for i in range(3):
   for side,delta in (('less',-1),('more',1)):
    obj=P(T('row'+str(i)),side);a.set(obj,'owner',R(1));a.set(obj,'index',i);a.set(obj,'delta',delta);a.set(obj,'onRelease',T('AdjustClick'))
  a.do(R(1),'Refresh');a.set(R(1),'pollFrames',0);a.set(R(1),'onEnterFrame',T('PollResult'))
 a.when(T('row0'),bind)
def row_over(a):a.set(P(R(1),'owner'),'focus',P(R(1),'index'));a.do(P(R(1),'owner'),'Refresh')
def row_click(a):a.do(R(1),'onRollOver');a.do(P(R(1),'owner'),'Select')
def adjust_click(a):a.set(P(R(1),'owner'),'focus',P(R(1),'index'));a.do(P(R(1),'owner'),'Shift',P(R(1),'delta'))
def page_click(a):a.do(P(R(1),'owner'),'StatementPage',P(R(1),'index'))

# Native text boxes are centered within their own button, not in a neighboring
# arrow hit area. Back is deliberately a single-line action in every view.
BUTTON_TEXT_LAYOUT={**{'row'+str(i):(74,34,6) for i in range(5)},
 **{name:(60,34,6) for name in ('payNext','payAll','ledgerBack')},
 **{name:(54,34,6) for name in ('previousStatement','nextStatement')}}

def draw_row(a,name,index,text,hint='',arrows=False):
 if isinstance(text,str) and text.startswith('Voltar'):text='Voltar';hint=''
 obj=T(name);show(a,name,True)
 if name in BUTTON_TEXT_LAYOUT:
  height,label_height,top=BUTTON_TEXT_LAYOUT[name]
  a.set(P(obj,'label'),'_y',top if hint else (height-label_height)/2)
 a.set(P(obj,'hint'),'_visible',bool(hint));a.set(P(obj,'label'),'text',text);a.set(P(obj,'hint'),'text',hint)
 a.set(P(obj,'selected'),'_alpha',0);a.set(P(obj,'label'),'textColor',0x334b56);a.set(P(obj,'hint'),'textColor',0x536874)
 a.when(EQ(T('focus'),index),lambda a:(a.set(P(obj,'selected'),'_alpha',100),a.set(P(obj,'label'),'textColor',0xffffff),a.set(P(obj,'hint'),'textColor',0xe1edf3)))
 if name.startswith('row'):
  for side in ('less','more'):a.set(P(obj,side),'_visible',arrows)

def refresh(a):
 # Individual statements reposition these shared native rows. Restore the
 # simulation grid before its own draw when returning from a contract.
 for i in range(7):
  for j in range(4):a.set(T(f'cell{i}_{j}'),'_y',348+i*47)
 for i in range(6):a.set(T('tableRow'+str(i)),'_y',393+i*47)
 a.set(T('pageInfo'),'_y',748)
 for name,*_ in FIELDS:label(a,name,'')
 for name,*_ in BUTTONS:show(a,name,False)
 show(a,'mcGridControl',False);label(a,'title','EMPRÉSTIMOS DO CLUBE')
 for name in ('summaryCard','tableHeader','scrollTrack','scrollThumb')+tuple('tableRow'+str(i) for i in range(6)):show(a,name,False)
 for i in range(len(BANKS)):show(a,'bankLogo'+str(i),False)
 for name,*_ in FIELDS:a.set(T(name),'textColor',0x334b56)
 wage=VIEW.get('wage_budget');wage_text=b.money(wage) if wage is not None else 'Não informado'
 budget_text=b.money(VIEW.get('budget',0)) if VIEW.get('ready') else 'Carregando...'
 year=str(VIEW['date'])[:4] if VIEW.get('date') else 'Não disponível'
 label(a,'subtitle',f"{VIEW.get('used',0)}/2 empréstimos em {year}")
 label(a,'status','')
 active=VIEW.get('active');application=VIEW.get('application');today=VIEW.get('date')
 expected=application['decision_date'] if application else response_date(today)
 def home(a):
  label(a,'section','Gerencie os empréstimos do clube')
  draw_row(a,'row0',0,'Novo empréstimo','Escolher banco, valor e prazo' if VIEW.get('can_borrow') else 'Solicitação em análise' if application else 'Indisponível: contrato ativo ou limite anual atingido')
  draw_row(a,'row1',1,'Parcelas e pagamentos','Consultar vencimentos, antecipar parcela ou quitar')
  label(a,'detail0','ORÇAMENTO ATUAL');label(a,'detail1','Transferências: '+budget_text);label(a,'detail2','Salários: '+(wage_text if VIEW.get('ready') else 'Carregando...'))
  if not VIEW.get('ready'):
   label(a,'section','Carregando os empréstimos do clube...');label(a,'detail5','Aguardando os dados confirmados do clube.');label(a,'detail7','Nenhuma contratação pode ser enviada enquanto os dados carregam.')
  if active:
   remaining=sum(p['amount'] for p in active['payments'][active['paid']:]);next_payment=active['payments'][active['paid']]
   values=['EMPRÉSTIMO ATIVO',active.get('bank_name',BANKS[active['bank']]['name']),'Falta pagar: '+b.money(remaining),'Parcelas pagas: '+str(active['paid'])+' / '+str(active['months']),
      'Próximo vencimento: '+datestr(next_payment['date']),'Próxima parcela: '+b.money(next_payment['amount']),
      'Crédito contratado: '+b.money(active['principal']),'Solicitado em: '+datestr(active.get('application_date',active['date'])),
      'Aprovado em: '+datestr(active['date']),'Total do contrato: '+b.money(active['total']),'Aviso na caixa de mensagens um dia antes.']
   for i,value in enumerate(values):label(a,'detail'+str(i),value)
   a.set(T('detail0'),'textColor',0x26744a);a.set(T('detail2'),'textColor',0x26744a)
  elif application:
   label(a,'detail4','SOLICITAÇÃO EM ANÁLISE');label(a,'detail5',BANKS[application['bank']]['name']+' · '+b.money(application['principal']))
   label(a,'detail6','Enviada em: '+datestr(application['date']));label(a,'detail7','Resposta prevista: '+datestr(application['decision_date']))
   label(a,'detail8','Análise vencida: aguardando uma tela segura.' if today>=application['decision_date'] else 'Aguardando a data de resposta registrada.');label(a,'detail9','A resposta chegará à caixa de mensagens.');label(a,'detail10','Crédito somente após aprovação.')
  elif VIEW.get('last_decision'):
   decision=VIEW['last_decision'];label(a,'detail4','ÚLTIMA SOLICITAÇÃO');label(a,'detail5',BANKS[decision['bank']]['name'])
   label(a,'detail6','Enviada em: '+datestr(decision['date']));label(a,'detail7','Resposta prevista: '+datestr(decision['decision_date']))
   label(a,'detail8','Concluída em: '+datestr(decision['decided_date']));label(a,'detail9','Aprovada' if decision['status']=='approved' else 'Não aprovada');label(a,'detail10','Confira o e-mail na caixa de mensagens.')
  elif VIEW.get('ready'):label(a,'detail5','Nenhum empréstimo em aberto.')
  if VIEW.get('error'):label(a,'status',VIEW['error'])
 a.when(EQ(T('page'),0),home)
 show(a,'summaryCard',('bin',17,('bin',17,EQ(T('page'),0),EQ(T('page'),1)),EQ(T('page'),2)))
 for i in range(len(BANKS)):
  def logo(a,i=i):
   show(a,'bankLogo'+str(i),True);a.set(T('bankLogo'+str(i)),'_x',650);a.set(T('bankLogo'+str(i)),'_y',350)
  a.when(('bin',16,('bin',17,EQ(T('page'),1),EQ(T('page'),2)),EQ(T('bank'),i)),logo)
  if active and active['bank']==i:a.when(EQ(T('page'),0),lambda a,i=i:(show(a,'bankLogo'+str(i),True),a.set(T('bankLogo'+str(i)),'_x',1635),a.set(T('bankLogo'+str(i)),'_y',335)))

 def form(a):
  label(a,'section','Novo empréstimo')
  draw_row(a,'row0',0,ADD('Banco: ',('index',('array',tuple(bank['name'] for bank in BANKS)),T('bank'))),'Seis instituições · taxas simuladas para o jogo',True)
  draw_row(a,'row1',1,ADD('Valor: ',('index',('array',tuple(b.money(n) for n in AMOUNTS)),T('amountIndex'))),'Crédito no orçamento de transferências',True)
  draw_row(a,'row2',2,ADD(ADD('Prazo: ',('index',('array',TERMS),T('termIndex'))),' meses'),'Parcelas mensais na data da carreira',True)
  draw_row(a,'row3',3,'Revisar proposta','Ver condições antes de confirmar');draw_row(a,'row4',4,'Voltar','Retornar aos empréstimos')
 a.when(EQ(T('page'),1),form)
 def proposal(a):
  label(a,'section','Confira a proposta antes de solicitar')
  draw_row(a,'row0',0,'Enviar solicitação','Conferir prazo de análise abaixo');draw_row(a,'row1',1,'Alterar proposta','Voltar ao banco, valor e prazo');draw_row(a,'row2',2,'Ver plano de parcelas','Consultar mês a mês sem solicitar')
 a.when(EQ(T('page'),2),proposal)
 def terms(a):
  for bank in range(len(BANKS)):
   for ai,amount in enumerate(AMOUNTS):
    for ti,months in enumerate(TERMS):
     if not offered(bank,amount,months):continue
     q=quote(bank,amount,months);cond=('bin',16,('bin',16,EQ(T('bank'),bank),EQ(T('amountIndex'),ai)),EQ(T('termIndex'),ti))
     planned=response_date(today,bank)
     values=['SIMULAÇÃO · '+BANKS[bank]['name'],'Saldo atual: '+b.money(VIEW.get('budget',0)),'Crédito se aprovado: +'+b.money(amount),'Saldo após aprovação: '+b.money(VIEW.get('budget',0)+amount),'Resposta prevista: '+datestr(planned),'Parcela mensal: '+b.money(q['payment']),'Primeira cobrança prevista: '+due_date(planned,1),'Última cobrança prevista: '+due_date(planned,months),'Total contratado: '+b.money(q['total']),'Juros totais: '+b.money(q['total']-amount),'Taxa simulada: '+str(q['rate_bps']/100).replace('.',',')+'% ao mês']
     def fill(a,values=values,bank=bank):
      for i,text in enumerate(values):label(a,'detail'+str(i),text)
      days=response_days(bank)
      a.when(EQ(T('page'),2),lambda a:a.set(P(T('row0'),'hint'),'text','Resposta em '+str(days)+(' dia da carreira' if days==1 else ' dias da carreira')))
     a.when(cond,fill)
 a.when(('bin',17,EQ(T('page'),1),EQ(T('page'),2)),terms)
 def ledger(a):
  schedule=VIEW.get('schedule',[]);count=len(schedule)
  label(a,'section','Parcelas do empréstimo');show(a,'tableHeader',True)
  for j,text in enumerate(('PARCELA','VENCIMENTO','VALOR','SITUAÇÃO')):label(a,f'cell0_{j}',text)
  for f in range(count+3):
   a.when(EQ(T('focus'),f),lambda a,f=f:a.set(R(1),'statementOffset',max(0,min(f-5,count-6))))
  if not schedule:label(a,'emptyState','Nenhuma parcela contratada. Escolha Novo empréstimo para simular.')
  for offset in range(max(1,count-5)):
   def fill(a,offset=offset):
    for i,p in enumerate(schedule[offset:offset+6],1):
     obj=T('tableRow'+str(i-1));show(a,'tableRow'+str(i-1),True);a.set(obj,'index',offset+i-1)
     paid=p['status']=='Paga';late=p['status']=='Vencida'
     a.set(obj,'_alpha',100);a.set(obj,'_visible',True)
     values=(str(p['number']).zfill(2)+' / '+str(count),datestr(p['date']),b.money(p['amount']),p['status']+(' em '+datestr(p['paid_date']) if p.get('paid_date') else ''))
     for j,value in enumerate(values):
      label(a,f'cell{i}_{j}',value);a.set(T(f'cell{i}_{j}'),'textColor',0x26744a if paid else 0xae3448 if late else 0x536874)
     a.set(P(obj,'selection'),'_visible',EQ(T('focus'),offset+i-1))
    label(a,'pageInfo',f'{offset+1 if count else 0}–{min(offset+6,count)} de {count} parcelas')
    if count>6:
     show(a,'scrollTrack',True);show(a,'scrollThumb',True);a.set(T('scrollThumb'),'_height',max(26,282*6/count));a.set(T('scrollThumb'),'_y',393+(282-max(26,282*6/count))*offset/(count-6))
   a.when(EQ(T('statementOffset'),offset),fill)
  buttons=(('payNext',count,'Pagar próxima parcela','Antecipar a próxima parcela'),('payAll',count+1,'Quitar empréstimo','Pagar todo o saldo devedor'),('ledgerBack',count+2,'Voltar','Empréstimos do clube')) if active else (('ledgerBack',count,'Voltar','Empréstimos do clube'),)
  for name,index,title,hint in buttons:
   a.set(T(name),'index',index);draw_row(a,name,index,title,hint)
  if active:label(a,'status','Empréstimo ativo · Falta pagar: '+b.money(sum(p['amount'] for p in active['payments'][active['paid']:]))+' · '+str(active['paid'])+'/'+str(active['months'])+' pagas')
  else:label(a,'status','Contrato quitado.' if schedule else 'Sem dívida em aberto.')
 a.when(EQ(T('page'),3),ledger)

 def plan(a):
  label(a,'section','Plano previsto de parcelas · simulação');show(a,'tableHeader',True);a.set(T('tableHeader'),'_y',341)
  for j,text in enumerate(('PARCELA','VENCIMENTO','VALOR','SITUAÇÃO')):label(a,f'cell0_{j}',text)
  a.do(R(1),'LoadPlan');items=T('simulationPlan')
  for i in range(6):
   at=ADD(('bin',12,T('statementPage'),6),i);entry=('index',items,at)
   def fill(a,i=i,entry=entry):
    show(a,'tableRow'+str(i),True);a.set(P(T('tableRow'+str(i)),'selection'),'_visible',False)
    for j in range(4):label(a,f'cell{i+1}_{j}',('index',entry,j))
   a.when(('bin',72,at,P(items,'length')),fill)
  a.set(T('ledgerBack'),'index',0);draw_row(a,'ledgerBack',0,'Voltar à proposta','Retornar sem contratar')
  for name in ('previousStatement','nextStatement'):show(a,name,('bin',103,T('termIndex'),0))
  label(a,'pageInfo',ADD(ADD(ADD('Página ',ADD(T('statementPage'),1)),'/'),('index',('array',tuple((months+5)//6 for months in TERMS)),T('termIndex'))));label(a,'status','Simulação: nenhum crédito ou cobrança foi aplicado.')
 a.when(EQ(T('page'),6),plan)
 def payment(a):
  label(a,'section','Confirme o pagamento');draw_row(a,'row0',0,'Confirmar pagamento','Descontar do orçamento de transferências');draw_row(a,'row1',1,'Voltar às parcelas','Voltar sem pagar')
  if active:
   total=sum(p['amount'] for p in active['payments'][active['paid']:]);next_value=active['payments'][active['paid']]['amount']
   label(a,'detail0','ORÇAMENTO ATUAL: '+b.money(VIEW.get('budget',0)))
   a.when(EQ(T('action'),1),lambda a:(label(a,'detail2','Próxima parcela: '+b.money(next_value)),label(a,'detail4','Saldo após pagamento: '+b.money(VIEW.get('budget',0)-next_value))),lambda a:(label(a,'detail2','Quitação: '+b.money(total)),label(a,'detail4','Saldo após pagamento: '+b.money(VIEW.get('budget',0)-total))))
   label(a,'detail6','Salários permanecem: '+wage_text);label(a,'detail8','Antecipação pelos valores contratados.');label(a,'detail9','A operação exige saldo suficiente.')
 a.when(EQ(T('page'),4),payment)
 def result(a):
  def pending(a):
   a.when(EQ(T('action'),0),lambda a:(label(a,'section','Registrando solicitação...'),label(a,'detail0',ADD('Pedido enviado em: ',b.G('Server16BankSubmittedText'))),label(a,'detail6',ADD('Resposta prevista: ',b.G('Server16BankResponseText')))),lambda a:(label(a,'section','Conferindo pagamento...'),label(a,'detail0','Aguarde a conferência do orçamento nesta carreira.')))
   label(a,'detail2','O resultado aparecerá aqui automaticamente.');label(a,'detail4','Não é necessário enviar o pedido novamente.')
   draw_row(a,'row0',0,'Voltar ao Escritório','O pedido enviado continua sendo verificado')
  def finished(a):
   result=VIEW.get('result') or {};ok=result.get('ok',False)
   if ok and result.get('kind')=='loan_requested':
    label(a,'section','Solicitação registrada');label(a,'detail0','Enviada em: '+datestr(result.get('submitted_date',(application or {}).get('date'))))
    label(a,'detail2','Resposta prevista: '+datestr(result['decision_date']));label(a,'detail4','Aprovação ou recusa na caixa de mensagens.')
    label(a,'detail6','Orçamento atual: '+budget_text);label(a,'detail8','O valor será creditado somente após aprovação.');label(a,'detail10','Salve a carreira no FIFA para guardar a solicitação.')
    draw_row(a,'row0',0,'Voltar aos empréstimos','Consultar a solicitação em análise');return
   label(a,'section','Operação aplicada' if ok else 'Operação não aplicada')
   if ok:
    # Backend feedback also carries persistence/delivery diagnostics. Keep the
    # native confirmation concise: each line has its own edit-text rectangle.
    credit=result.get('action',0)==0
    label(a,'detail0','Empréstimo aprovado. Crédito disponível.' if credit else 'Pagamento confirmado no orçamento.')
    label(a,'detail1','Confira a confirmação na caixa de mensagens.')
   else:label(a,'detail0',result.get('message','Não foi possível confirmar esta solicitação.'))
   label(a,'detail2','Transferências agora: '+b.money(VIEW.get('budget',0)))
   selected=next((c for c in VIEW.get('contracts',[]) if c['id']==result.get('contract_id')),active)
   if selected:
    remaining=sum(p['amount'] for p in selected['payments'][selected['paid']:])
    label(a,'detail4','Saldo deste contrato: '+b.money(remaining))
    label(a,'detail6','Próxima cobrança: '+datestr(selected['payments'][selected['paid']]['date']) if remaining else 'Contrato quitado.')
   else:label(a,'detail4','Nenhum empréstimo em aberto.')
   label(a,'detail8','Salve a carreira no FIFA para guardar a operação.' if ok else 'Confira o motivo antes de tentar novamente.')
   draw_row(a,'row0',0,'Ver parcelas e pagamentos' if ok else 'Voltar aos empréstimos','Consultar o extrato atualizado' if ok else 'Retornar sem reenviar o pedido')
  seq=(VIEW.get('result') or {}).get('sequence',-1)
  a.when(EQ(b.G('Server16BankPendingSequence'),seq),finished,pending)
 a.when(EQ(T('page'),5),result);a.do(M('HelpManager'),'Update')

def submit(a):
 a.set(b.GLOBAL,'Server16BankSequenceV2',ADD(b.G('Server16BankSequenceV2'),1));value='S16BANK_V3|'+b.NONCE+'|'
 for item in (b.G('Server16BankSequenceV2'),'|',T('action'),'|',T('bank'),'|',T('amountIndex'),'|',T('termIndex'),'|',VIEW.get('date',0),'|END_S16BANK'):value=ADD(value,item)
 a.set(b.GLOBAL,'Server16BankPendingNonce',b.NONCE);a.set(b.GLOBAL,'Server16BankPendingSequence',b.G('Server16BankSequenceV2'));a.set(b.GLOBAL,'Server16BankSubmittedText',datestr(VIEW.get('date')));a.set(b.GLOBAL,'Server16BankResponseText',datestr(response_date(VIEW.get('date'))));a.set(b.GLOBAL,'Server16BankPollAttempts',0)
 for bank in range(len(BANKS)):
  a.when(EQ(T('bank'),bank),lambda a,bank=bank:a.set(b.GLOBAL,'Server16BankResponseText',datestr(response_date(VIEW.get('date'),bank))))
 payment='S16BANK_V4|'+b.NONCE+'|'
 for item in (b.G('Server16BankSequenceV2'),'|',T('action'),'|',T('bank'),'|',T('amountIndex'),'|',T('termIndex'),'|',VIEW.get('date',0),'|',T('selectedPaymentId'),'|END_S16BANK'):payment=ADD(payment,item)
 a.when(EQ(T('action'),0),lambda a:a.set(b.GLOBAL,'Server16BankRequestV2',value),lambda a:a.set(b.GLOBAL,'Server16BankRequestV2',payment))
 # Native capture happens inside this call, before the user can leave Loans.
 a.do(b.ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16SubmitBank',b.G('Server16BankRequestV2'))
 go(a,5)

def poll_result(a):
 a.when(T('exiting'),lambda a:a.ret())
 def pending(a):
  a.set(R(1),'pollFrames',ADD(T('pollFrames'),1))
  def reload(a):
   a.set(R(1),'pollFrames',0);a.set(b.GLOBAL,'Server16BankPollAttempts',ADD(b.G('Server16BankPollAttempts'),1))
   def refresh_view(a):
    # OnExit clears this callback when the native navigation consumes the event.
    # If a foreign navigation file rejects it, retry up to the visible timeout.
    a.do(b.ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16RefreshBank','')
   def timeout(a):
    label(a,'section','Aguardando confirmação');label(a,'detail2','A confirmação demorou mais que o esperado.');label(a,'detail4','Volte ao Escritório e consulte os empréstimos antes de reenviar.');a.set(R(1),'onEnterFrame',None)
   a.when(('bin',72,b.G('Server16BankPollAttempts'),21),refresh_view,timeout)
  a.when(('bin',103,T('pollFrames'),89),reload)
 condition=('bin',16,EQ(T('page'),5),EQ(b.G('Server16BankPendingNonce'),b.NONCE))
 a.when(condition if VIEW.get('ready') else True,pending)

def leave(a):a.do(b.ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),P(T('navEvents'),'BACK'),'');a.do(M('InputManager'),'DisableCurrentLocalEventHandler')
def select(a):
 if not VIEW.get('ready'):
  a.do(b.ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16RefreshBank','');a.ret();return
 def home(a):
  def new(a):
   if VIEW.get('can_borrow'):go(a,1)
   else:label(a,'status',VIEW.get('error') or ('Resposta prevista: '+datestr(VIEW['application']['decision_date']) if VIEW.get('application') else 'Quite a dívida atual ou aguarde o próximo ano da carreira.'))
  a.when(EQ(T('focus'),0),new,lambda a:go(a,3,0 if VIEW.get('active') else len(VIEW.get('schedule',[]))));a.ret()
 a.when(EQ(T('page'),0),home)
 def form(a):
  a.when(('bin',72,T('focus'),3),lambda a:(a.do(R(1),'Shift',1),a.ret()));a.when(EQ(T('focus'),3),lambda a:go(a,2),lambda a:go(a,0));a.ret()
 a.when(EQ(T('page'),1),form)
 def review(a):
  a.when(EQ(T('focus'),0),lambda a:(a.set(R(1),'action',0),a.do(R(1),'Submit'),a.ret()))
  a.when(EQ(T('focus'),1),lambda a:go(a,1,3),lambda a:(a.set(R(1),'statementPage',0),go(a,6)));a.ret()
 a.when(EQ(T('page'),2),review)
 def ledger(a):
  count=len(VIEW.get('schedule',[]))
  a.when(('bin',72,T('focus'),count),lambda a:(label(a,'status','Use Pagar próxima parcela ou Quitar empréstimo para confirmar uma operação.'),a.ret()))
  a.when(EQ(T('focus'),count+2 if VIEW.get('active') else count),lambda a:(go(a,0,1),a.ret()))
  if VIEW.get('active'):a.set(R(1),'action',ADD(ADD(T('focus'),-count),1));go(a,4)
  else:label(a,'status','Não há empréstimo em aberto para pagar.')
  a.ret()
 a.when(EQ(T('page'),3),ledger)
 a.when(EQ(T('page'),4),lambda a:(a.when(EQ(T('focus'),0),lambda a:a.do(R(1),'Submit'),lambda a:go(a,3)),a.ret()))
 def result(a):
  seq=(VIEW.get('result') or {}).get('sequence',-1)
  result=VIEW.get('result') or {}
  a.when(EQ(b.G('Server16BankPendingSequence'),seq),lambda a:go(a,3 if result.get('ok') and result.get('kind')!='loan_requested' else 0),leave)
 a.when(EQ(T('page'),5),result)
 a.when(EQ(T('page'),6),lambda a:go(a,2,2))

def back(a):
 a.when(('bin',17,EQ(T('page'),0),EQ(T('page'),5)),lambda a:(leave(a),a.ret()))
 a.when(EQ(T('page'),2),lambda a:(go(a,1,3),a.ret()));a.when(EQ(T('page'),4),lambda a:(go(a,3),a.ret()));a.when(EQ(T('page'),6),lambda a:(go(a,2,2),a.ret()));go(a,0)
def focus(a):
 count=('index',('array',(2,5,3,len(VIEW.get('schedule',[]))+(3 if VIEW.get('active') else 1),2,1,1)),T('page'));a.set(R(1),'focus',('bin',63,ADD(ADD(T('focus'),R(2)),count),count));a.do(R(1),'Refresh')
def statement(a):
 a.when(EQ(T('page'),3),lambda a:(a.do(R(1),'MoveFocus',('bin',12,R(2),6)),a.ret()))
 a.set(R(1),'statementPages',max(1,(len(VIEW.get('schedule',[]))+7)//8));a.when(EQ(T('page'),6),lambda a:a.set(R(1),'statementPages',('index',('array',tuple((months+5)//6 for months in TERMS)),T('termIndex'))));pages=T('statementPages');a.set(R(1),'statementPage',('bin',63,ADD(ADD(T('statementPage'),R(2)),pages),pages));a.do(R(1),'Refresh')
def shift(a):
 def wrap(field,count):a.set(R(1),field,('bin',63,ADD(ADD(T(field),R(2)),count),count))
 a.when(EQ(T('page'),1),lambda a:(a.when(EQ(T('focus'),0),lambda a:a.set(R(1),'bank',ADD(3,('bin',63,ADD(ADD(ADD(T('bank'),-3),R(2)),len(OFFERED_BANKS)),len(OFFERED_BANKS))))),a.when(EQ(T('focus'),1),lambda a:wrap('amountIndex',len(AMOUNTS))),a.when(EQ(T('focus'),2),lambda a:wrap('termIndex',len(TERMS)))))
 a.when(('bin',17,EQ(T('page'),3),EQ(T('page'),6)),lambda a:a.do(R(1),'StatementPage',R(2)));a.do(R(1),'Refresh')
def key(a):
 for code,method,arg in (('BACK','Back',None),('ADVANCE','Select',None),('PRIMARY_SELECT','Select',None),('UP','MoveFocus',-1),('DOWN','MoveFocus',1),('LEFT','Shift',-1),('RIGHT','Shift',1),('L1','StatementPage',-1),('R1','StatementPage',1)):
  def invoke(a,method=method,arg=arg):
   a.do(R(1),method,*(() if arg is None else (arg,)));a.ret(True)
  a.when(('bin',16,P(M('InputCodes'),code),EQ(R(2),P(M('InputCodes'),code))),invoke)
 a.ret(True)
def animate(a):a.do(M('ScreenManager'),'BeginAnimateIn',CALL(b.path('cafe','utility','Delegate'),'Create',R(1),T('OnAnimateInComplete')));a.do(R(1),'OnAnimateInComplete')
def shutdown(a):
 a.when(T('exiting'),lambda a:a.ret());a.set(R(1),'exiting',True);a.set(R(1),'onEnterFrame',None)
 for name,*_ in BUTTONS:
  for event in ('onRelease','onRollOver'):a.set(T(name),event,None)
 a.do(M('InputManager'),'DisableCurrentLocalEventHandler');a.do(M('HelpManager'),'Clear');a.do(R(1),'Shutdown')
REPLACE={'InitComponents':init,'InitBankCards':lambda a:None,'Refresh':refresh,'Submit':submit,'Select':select,'Back':back,'Shift':shift,'LocalEventHandler':key,'AnimateIn':animate,'OnExitScreen':shutdown,
 'getHelpContext':lambda a:a.ret(('array',(CALL(b.path('ion','manager','HelpItem'),'CreateHelpTickerItem','ADVANCE','Selecionar'),CALL(b.path('ion','manager','HelpItem'),'CreateHelpTickerItem','BACK','Voltar'))))}
EXTRA=[('LoadPlan',0,load_plan),('WaitButtons',0,wait),('PollResult',0,poll_result),('RowOver',0,row_over),('RowClick',0,row_click),('PaymentOver',0,row_over),('PaymentClick',0,row_click),('AdjustClick',0,adjust_click),('PageClick',0,page_click),('MoveFocus',1,focus),('StatementPage',1,statement)]

def graphics(data,apt,template,shape,append,new_chars,controls,count,additions):
 def character(raw):cid=count+len(new_chars);new_chars.append(append(raw));return cid
 def place(cid,depth,x,y,sx=1,sy=1,name=None,color=0xffffffff):
  raw=bytearray(data[template.offset:template.offset+80]);struct.pack_into('<iii6f',raw,8,46 if name else 14,depth,cid,sx,0,0,sy,x,y);struct.pack_into('<II',raw,44,color,0);struct.pack_into('<Q',raw,56,append(name.encode()+b'\0') if name else 0);return append(raw)
 def text(value,w,h,size,color):
  raw=bytearray(data[apt.characters[3].offset:apt.characters[3].offset+96]);struct.pack_into('<4f',raw,32,0,0,w,h);struct.pack_into('<If',raw,56,color,size);struct.pack_into('<QQ',raw,80,append(value.encode('utf8')+b'\0'),0);return character(raw)
 def clip(parts):
  raw=bytearray(data[apt.characters[9].offset:apt.characters[9].offset+56]);frame=append(struct.pack('<I4xQ',len(parts),append(struct.pack('<'+'Q'*len(parts),*parts))));struct.pack_into('<I4xQ',raw,32,1,frame);struct.pack_into('<Q',raw,48,0);return character(raw)
 def button(name,x,y,w,h,label='',arrows=False):
  selected=clip([place(shape,1,0,0,w,h,color=0xff075a9e)])
  parts=[place(shape,1,0,0,w,h,color=0xffd9e0e3),place(selected,2,0,0,name='selected'),place(text(label,w-170 if arrows else w-30,34,28,0xff334b56),3,16,6,name='label'),place(text('',w-32,22,18,0xff536874),4,16,36,name='hint')]
  for side,glyph,xpos in ((('less','<',w-122),('more','>',w-62)) if arrows else ()):
   arrow=clip([place(shape,1,0,0,46,42,color=0xffbac9d3),place(text(glyph,42,38,29,0xff173d54),2,12,1)])
   parts.append(place(arrow,5 if side=='less' else 6,xpos,11,name=side))
  cid=clip(parts);controls.append(place(cid,100+len(controls),x,y,name=name))
 # Underlays are added after text but below it in native depth order.
 controls.append(place(clip([place(shape,1,0,0,840,510,color=0xffe5eae8),place(shape,2,0,0,6,510,color=0xff81b737)]),2,930,330,name='summaryCard'))
 controls.append(place(clip([place(shape,1,0,0,1620,47,color=0xffd1d9dc)]),3,130,341,name='tableHeader'))
 for i in range(6):
  selected=clip([place(shape,1,0,0,1620,47,color=0xffbcdce4)])
  row=clip([place(shape,1,0,0,1620,47,color=0xffe8eeeb if i%2==0 else 0xfff9faf8),place(selected,2,0,0,name='selection')])
  controls.append(place(row,4+i,130,393+i*47,name='tableRow'+str(i)))
 controls.append(place(clip([place(shape,1,0,0,8,282,color=0xffd3dbde)]),4,1762,393,name='scrollTrack'))
 controls.append(place(clip([place(shape,1,0,0,8,40,color=0xff4a6570)]),5,1762,393,name='scrollThumb'))
 from bank_art import embed_logos
 embed_logos(data,apt,append,new_chars,controls,count,additions,place,clip,character)
 for i in range(5):button('row'+str(i),130,345+i*85,760,74,arrows=True)
 for name,x in (('payNext',130),('payAll',680),('ledgerBack',1230)):button(name,x,815,520,60)
 button('previousStatement',130,750,240,54,'< Anterior');button('nextStatement',390,750,240,54,'Próxima >')

def build(view=None):
 global VIEW
 VIEW=dict(view if view is not None else json.loads((b.HERE/'runtime/finance_view.json').read_text(encoding='utf8')))
 try:parse_date(VIEW.get('date'))
 except (ValueError,TypeError):VIEW.update(date=None,ready=False,can_borrow=False,nonce='DISABLED',active=None,schedule=[])
 b.NONCE=VIEW.get('nonce','DISABLED');b.FIELDS=FIELDS;b.make_script=script;b.USE_R57=True;b.USE_R60=True;b.build()

# Keep the economic protocol independent from the native visual layout.
import bank_design as _bank_design
_bank_design.install(sys.modules[__name__])

import bank_contract_views as _bank_contract_views
_bank_contract_views.install(sys.modules[__name__])
