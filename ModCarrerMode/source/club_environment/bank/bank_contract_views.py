"""Loan overview, contract history and an individual statement in native APT."""
from loans import BANKS,MAX_ACTIVE,MAX_PER_YEAR

# A compact native array keeps statement navigation independent from APT builds.
ID,BANK,NAME,PRINCIPAL,TOTAL,REMAINING,PAID,MONTHS,DATE,SUBMITTED,STATUS,PAYABLE,SCHEDULE,LIST_TITLE,LIST_HINT,META=range(16)

def contracts(view):
    rows=view.get('contracts')
    if rows is not None:return rows
    active=view.get('active')
    if not active:return []
    return [dict(active,schedule=view.get('schedule',[]),remaining=sum(p['amount'] for p in active['payments'][active['paid']:]),status='Ativo')]

def blocked_reason(view):
    if not view.get('ready'):return 'Aguardando os dados do clube.'
    application=view.get('application')
    if application:return 'Solicitação em análise. Aguarde a resposta do banco.'
    if sum(c['paid']<c['months'] for c in contracts(view))>=MAX_ACTIVE:return 'Limite de quatro empréstimos ativos atingido.'
    if view.get('next_borrow_date',0)>view.get('date',0):
        from loans import parse_date
        return 'Próximo pedido em '+parse_date(view['next_borrow_date']).strftime('%d/%m/%Y')+' · intervalo de dois meses.'
    return view.get('credit_error') or 'Limite de quatro contratações no ano atingido.'

def install(ui):
    u=ui;T=u.T;R=u.R;P=u.P;EQ=u.EQ;ADD=u.ADD
    original={name:getattr(u,name) for name in ('init','refresh','select','focus','shift','back','graphics')}
    u.EXTRA.append(('RefreshDesign',0,original['refresh']))
    extra_fields=(('overviewTitle',820,330,900,48,32),('overviewState',820,395,900,42,30),
        ('overviewBudgetLabel',820,465,500,36,24),('overviewBudget',1350,465,380,36,28),
        ('overviewWageLabel',820,515,500,36,24),('overviewWage',1350,515,380,36,28),
        ('overviewLine0',820,590,900,40,26),('overviewLine1',820,640,900,40,24),('overviewLine2',820,690,900,40,24),
        ('contractHeading',920,345,600,45,32),('contractStatus',920,405,780,40,29),
        ('contractLine0',920,470,780,42,26),('contractLine1',920,525,780,42,26),('contractLine2',920,580,780,42,26),('contractLine3',920,635,780,42,24),
        ('contractLine4',920,690,800,36,22),('contractListInfo',140,825,670,34,23),
        ('statementHeading',160,320,1370,42,30),('statementMeta',160,365,1500,40,23),
        ('statementBalance',160,401,1500,35,23))
    u.FIELDS+=extra_fields
    u.BUTTON_TEXT_LAYOUT.update({
        **{name:(112,42,16) for name in ('homeNew','homeContracts')},
        **{'contractTile'+str(i):(86,34,10) for i in range(5)},
        **{name:(72,34,8) for name in ('contractNew','contractBack')}})
    u.BUTTONS.extend((('homeNew',0,'RowClick','RowOver'),('homeContracts',1,'RowClick','RowOver'),
        ('contractNew',0,'RowClick','RowOver'),('contractBack',1,'RowClick','RowOver')))
    u.BUTTONS.extend(('contractTile'+str(i),i,'ContractClick','ContractOver') for i in range(5))

    def record(contract,active):
        name=contract.get('bank_name',BANKS[contract['bank']]['name']);rows=contract.get('schedule',[])
        if not rows:
            rows=[dict(p,status='Paga' if p['number']<=contract['paid'] else 'Vencida' if p['date']<=u.VIEW['date'] else 'A vencer') for p in contract['payments']]
        remaining=sum(p['amount'] for p in contract['payments'][contract['paid']:]);paid=contract['paid'];months=contract['months']
        schedule=tuple(('array',(str(p['number']).zfill(2)+' / '+str(months),u.datestr(p['date']),u.b.money(p['amount']),
            p['status']+(' em '+u.datestr(p['paid_date']) if p.get('paid_date') else ''),p['status']=='Paga',p['status']=='Vencida')) for p in rows)
        status='Ativo' if paid<months else 'Quitado';payable=paid<months
        title=name+' · '+u.b.money(contract['principal'])
        hint=status+' · '+u.datestr(contract['date'])+' · '+str(paid)+'/'+str(months)+' parcelas pagas'
        meta='Solicitado em '+u.datestr(contract.get('application_date',contract['date']))+' · Resposta prevista: '+u.datestr(contract.get('decision_date',contract['date']))+' · Aprovado em '+u.datestr(contract['date'])
        return ('array',(contract['id'],contract['bank'],name,u.b.money(contract['principal']),u.b.money(contract['total']),u.b.money(remaining),paid,months,u.datestr(contract['date']),u.datestr(contract.get('application_date',contract['date'])),status,payable,('array',schedule),title,hint,meta))

    def item(index):return ('index',('index',T('loanContracts'),T('contractIndex')),index)
    def field(row,index):return ('index',row,index)
    def set_focus(a,value):a.set(R(1),'focus',value);a.do(R(1),'Refresh')

    def init(a):
        original['init'](a)
        rows=contracts(u.VIEW);active=u.VIEW.get('active')
        target=(u.VIEW.get('result') or {}).get('contract_id') or (active or {}).get('id')
        selected=next((i for i,c in enumerate(rows) if c['id']==target),0)
        a.set(R(1),'loanContracts',('array',tuple(record(c,active) for c in rows)))
        a.set(R(1),'contractIndex',selected);a.set(R(1),'selectedPaymentId',rows[selected]['id'] if rows else '');a.set(R(1),'statementRow',0);a.set(R(1),'contractOffset',0);a.set(R(1),'individualOffset',0);a.do(R(1),'Refresh')

    def contract_over(a):
        owner=P(R(1),'owner');index=P(R(1),'index')
        a.set(owner,'focus',index);a.set(owner,'contractIndex',index);a.do(owner,'Refresh')
    def contract_click(a):a.do(R(1),'onRollOver');a.do(P(R(1),'owner'),'Select')

    def hide_old(a):
        for name in ('summaryCard','tableHeader','scrollTrack','scrollThumb','bankHero','optionsPanel','simulationPanel','ratePanel'):
            u.show(a,name,False)
        for name,*_ in u.BUTTONS:u.show(a,name,False)
        for name,*_ in u.FIELDS:
            if name not in ('title','subtitle','section'):u.label(a,name,'')
        for i in range(len(BANKS)):
            u.show(a,'bankLogo'+str(i),False);u.show(a,'bankHeaderLogo'+str(i),False)

    def selected_logo(a,x,y):
        for bank in range(len(BANKS)):
            def show(a,bank=bank):
                name='bankHeaderLogo'+str(bank);u.show(a,name,True);a.set(T(name),'_x',x);a.set(T(name),'_y',y)
            a.when(EQ(item(BANK),bank),show)

    def refresh(a):
        a.do(R(1),'RefreshDesign')
        for name in ('overviewPanel','contractsPanel','statementPanel'):u.show(a,name,False)
        # All views share the same safe header and leave the FIFA footer clear.
        for name,x,y in (('title',120,125),('subtitle',122,190),('section',120,245),('status',130,850)):
            a.set(T(name),'_x',x);a.set(T(name),'_y',y)
        for name,x,y in (('contractHeading',920,345),('contractStatus',920,405),('contractLine0',920,470),('contractLine1',920,525)):
            a.set(T(name),'_x',x);a.set(T(name),'_y',y)
        a.set(T('contractsPanel'),'_x',875);a.set(T('contractsPanel'),'_width',900)
        rows=contracts(u.VIEW);count=len(rows);active=u.VIEW.get('active')
        application=u.VIEW.get('application')
        active_rows=[c for c in rows if c['paid']<c['months']]
        unavailable=blocked_reason(u.VIEW)
        def home(a):
            hide_old(a);u.label(a,'section','Gerencie os empréstimos do clube');u.show(a,'overviewPanel',True)
            u.draw_row(a,'homeNew',0,'Novo empréstimo','Escolher instituição, valor e prazo' if u.VIEW.get('can_borrow') else 'Solicitação em análise' if u.VIEW.get('application') else unavailable)
            u.draw_row(a,'homeContracts',1,'Meus empréstimos',str(count)+' contrato(s) · consultar parcelas e pagamentos')
            u.label(a,'overviewTitle','Situação dos empréstimos')
            u.label(a,'overviewBudgetLabel','Orçamento de transferências');u.label(a,'overviewBudget',u.b.money(u.VIEW.get('budget',0)))
            wage=u.VIEW.get('wage_budget');u.label(a,'overviewWageLabel','Orçamento de salários');u.label(a,'overviewWage',u.b.money(wage) if wage is not None else 'Não informado')
            if not u.VIEW.get('ready'):
                u.label(a,'overviewState','Aguardando os dados do clube');u.label(a,'overviewLine0',u.VIEW.get('error') or 'Carregando a carreira em execução...')
            elif active:
                remaining=sum(p['amount'] for c in active_rows for p in c['payments'][c['paid']:])
                next_day=min(c['payments'][c['paid']]['date'] for c in active_rows)
                next_amount=sum(c['payments'][c['paid']]['amount'] for c in active_rows if c['payments'][c['paid']]['date']==next_day)
                u.label(a,'overviewState',str(len(active_rows))+' de 4 empréstimos ativos')
                u.label(a,'overviewLine0','Total a pagar: '+u.b.money(remaining));a.set(T('overviewLine0'),'textColor',0x26744a)
                u.label(a,'overviewLine1','Próxima cobrança: '+u.datestr(next_day)+' · '+u.b.money(next_amount))
                u.label(a,'overviewLine2','Escolha o contrato em Meus empréstimos.')
            elif u.VIEW.get('application'):
                app=u.VIEW['application'];u.label(a,'overviewState','Solicitação em análise')
                u.label(a,'overviewLine0','Pedido enviado em '+u.datestr(app['date']));u.label(a,'overviewLine1','Resposta prevista: '+u.datestr(app['decision_date']))
                u.label(a,'overviewLine2','A resposta chegará à caixa de mensagens.')
            else:
                u.label(a,'overviewState','Nenhuma dívida ativa');a.set(T('overviewState'),'textColor',0x26744a)
                u.label(a,'overviewLine0',str(u.VIEW.get('used',0))+' de 4 contratações utilizadas neste ano')
                u.label(a,'overviewLine1','Intervalo mínimo de dois meses entre contratações.')
                u.label(a,'overviewLine2',('Crédito total do clube: '+u.b.money(u.VIEW['credit']['capacity'])) if u.VIEW.get('credit') else 'Consulte o histórico em Meus empréstimos.')
        a.when(EQ(T('page'),0),home)

        def listing(a):
            hide_old(a);u.label(a,'section','Meus empréstimos');u.show(a,'contractsPanel',True)
            if not count:
                a.set(T('contractsPanel'),'_x',130);a.set(T('contractsPanel'),'_width',1620)
                for name,y in (('contractHeading',370),('contractStatus',430),('contractLine0',505),('contractLine1',560)):
                    a.set(T(name),'_x',210);a.set(T(name),'_y',y)
                u.label(a,'contractHeading','Solicitação em análise' if application else 'Nenhum contrato registrado');u.label(a,'contractStatus','Aguardando a resposta do banco' if application else 'Sem dívida em aberto')
                u.label(a,'contractLine0','Pedido enviado em '+u.datestr(application['date']) if application else 'Simule um empréstimo para conhecer as condições.')
                u.label(a,'contractLine1','Resposta prevista: '+u.datestr(application['decision_date']) if application else 'Os contratos ativos e quitados aparecerão nesta lista.')
            else:
                a.when(('bin',72,T('focus'),count),lambda a:a.set(R(1),'contractIndex',T('focus')))
                a.when(('bin',72,T('contractIndex'),T('contractOffset')),lambda a:a.set(R(1),'contractOffset',T('contractIndex')))
                a.when(('bin',72,ADD(T('contractOffset'),4),T('contractIndex')),lambda a:a.set(R(1),'contractOffset',ADD(T('contractIndex'),-4)))
                for i in range(min(count,5)):
                    index=ADD(T('contractOffset'),i);row=('index',T('loanContracts'),index);name='contractTile'+str(i)
                    a.set(T(name),'index',index);u.draw_row(a,name,index,field(row,LIST_TITLE),field(row,LIST_HINT))
                selected_logo(a,1540,335)
                u.label(a,'contractHeading',item(NAME));u.label(a,'contractStatus',item(STATUS))
                u.label(a,'contractLine0',ADD('Crédito contratado: ',item(PRINCIPAL)))
                u.label(a,'contractLine1',ADD('Falta pagar: ',item(REMAINING)))
                u.label(a,'contractLine2',ADD(ADD(ADD('Parcelas pagas: ',item(PAID)),' / '),item(MONTHS)))
                u.label(a,'contractLine3',ADD('Aprovado em ',item(DATE)))
                u.label(a,'contractLine4',ADD('Pedido enviado em ',item(SUBMITTED)))
                u.label(a,'contractListInfo',ADD(ADD(ADD(T('contractIndex'),1),' de '),str(count)+' contratos'))
            a.set(T('contractNew'),'index',count);a.set(T('contractBack'),'index',count+1)
            u.draw_row(a,'contractNew',count,'Novo empréstimo','Simular e consultar condições')
            u.draw_row(a,'contractBack',count+1,'Voltar','Resumo dos empréstimos')
        a.when(EQ(T('page'),7),listing)

        def statement(a):
            hide_old(a);u.label(a,'section','Extrato do contrato');u.show(a,'statementPanel',True)
            if not count:
                u.label(a,'statementHeading','Nenhum contrato selecionado')
                a.set(T('ledgerBack'),'index',0);u.draw_row(a,'ledgerBack',0,'Voltar','Meus empréstimos');return
            schedule=item(SCHEDULE);length=P(schedule,'length')
            selected_logo(a,1570,322)
            u.label(a,'statementHeading',ADD(ADD(item(NAME),' · '),item(STATUS)))
            u.label(a,'statementMeta',item(META))
            u.label(a,'statementBalance',ADD(ADD(ADD(ADD(ADD('Total contratado: ',item(TOTAL)),' · Falta pagar: '),item(REMAINING)),' · Parcelas pagas: '),ADD(ADD(item(PAID),' / '),item(MONTHS))))
            u.show(a,'tableHeader',True);a.set(T('tableHeader'),'_y',445)
            for j,label in enumerate(('PARCELA','VENCIMENTO','VALOR','SITUAÇÃO')):u.label(a,'cell0_'+str(j),label)
            maximum=('call',u.b.path('Math'),'max',(0,ADD(length,-6)))
            def ensure_visible(a):
                a.when(('bin',72,T('focus'),T('individualOffset')),lambda a:a.set(R(1),'individualOffset',('call',u.b.path('Math'),'min',(T('focus'),maximum))))
                a.when(('bin',72,ADD(T('individualOffset'),5),T('focus')),lambda a:a.set(R(1),'individualOffset',('call',u.b.path('Math'),'min',(ADD(T('focus'),-5),maximum))))
            a.when(('bin',72,T('focus'),length),lambda a:(a.set(R(1),'statementRow',T('focus')),ensure_visible(a)))
            a.set(R(1),'statementOffset',T('individualOffset'))
            for i in range(6):
                index=ADD(T('statementOffset'),i);entry=('index',schedule,index);name='tableRow'+str(i)
                def fill(a,i=i,index=index,entry=entry,name=name):
                    u.show(a,name,True);a.set(T(name),'_y',492+i*47);a.set(T(name),'index',index)
                    for j in range(4):
                        field_name=f'cell{i+1}_{j}';u.label(a,field_name,field(entry,j))
                        a.when(field(entry,4),lambda a,field_name=field_name:a.set(T(field_name),'textColor',0x26744a),lambda a,field_name=field_name:a.when(field(entry,5),lambda a:a.set(T(field_name),'textColor',0xae3448)))
                    a.set(P(T(name),'selection'),'_visible',EQ(T('focus'),index))
                a.when(('bin',72,index,length),fill)
            for i in range(7):
                for j in range(4):a.set(T(f'cell{i}_{j}'),'_y',450 if i==0 else 492+(i-1)*47)
            a.set(T('pageInfo'),'_y',780);u.label(a,'pageInfo',ADD(ADD(ADD(ADD(T('statementOffset'),1),'–'),('call',u.b.path('Math'),'min',(ADD(T('statementOffset'),6),length))),ADD(' de ',ADD(length,' parcelas'))))
            def can_pay(a):
                for name,delta,title,hint in (('payNext',0,'Pagar próxima parcela','Antecipar a próxima parcela'),('payAll',1,'Quitar empréstimo','Pagar o saldo devedor')):
                    index=ADD(length,delta);a.set(T(name),'index',index);u.draw_row(a,name,index,title,hint)
                a.set(T('ledgerBack'),'index',ADD(length,2));u.draw_row(a,'ledgerBack',ADD(length,2),'Voltar','Meus empréstimos')
            a.when(item(PAYABLE),can_pay,lambda a:(a.set(T('ledgerBack'),'index',length),u.draw_row(a,'ledgerBack',length,'Voltar','Meus empréstimos')))
            # No track, no thumb on an empty or short statement.
            def scrollbar(a):
                u.show(a,'scrollTrack',True);u.show(a,'scrollThumb',True);a.set(T('scrollTrack'),'_y',492)
                height=('call',u.b.path('Math'),'max',(26,('bin',13,1692,length)))
                a.set(T('scrollThumb'),'_height',height)
                a.set(T('scrollThumb'),'_y',ADD(492,('bin',12,('bin',13,T('statementOffset'),ADD(length,-6)),('bin',11,282,height))))
            a.when(('bin',103,length,6),scrollbar)
        a.when(EQ(T('page'),3),statement)

        def payment(a):
            if not count:return
            u.label(a,'detail0',ADD('Contrato: ',item(NAME)))
            for index,c in enumerate(rows):
                if c['paid']>=c['months']:continue
                next_value=c['payments'][c['paid']]['amount']
                remaining=sum(p['amount'] for p in c['payments'][c['paid']:])
                def details(a,c=c,next_value=next_value,remaining=remaining):
                    u.label(a,'detail1','Crédito contratado: '+u.b.money(c['principal']))
                    a.when(EQ(T('action'),1),lambda a:(u.label(a,'detail2','Próxima parcela: '+u.b.money(next_value)),u.label(a,'detail4','Saldo após pagamento: '+u.b.money(u.VIEW['budget']-next_value))),
                        lambda a:(u.label(a,'detail2','Quitação deste contrato: '+u.b.money(remaining)),u.label(a,'detail4','Saldo após pagamento: '+u.b.money(u.VIEW['budget']-remaining))))
                a.when(EQ(T('contractIndex'),index),details)
        a.when(EQ(T('page'),4),payment)

    def select(a):
        if not u.VIEW.get('ready'):original['select'](a);return
        count=len(contracts(u.VIEW))
        def home(a):
            def new(a):
                if u.VIEW.get('can_borrow'):u.go(a,1,0)
                else:u.label(a,'overviewLine2',blocked_reason(u.VIEW))
            a.when(EQ(T('focus'),0),new,lambda a:u.go(a,7,T('contractIndex')));a.ret()
        a.when(EQ(T('page'),0),home)
        def listing(a):
            a.when(('bin',72,T('focus'),count),lambda a:(a.set(R(1),'contractIndex',T('focus')),a.set(R(1),'individualOffset',0),u.go(a,3),a.ret()))
            def new(a):
                if u.VIEW.get('can_borrow'):u.go(a,1,0)
                else:u.label(a,'contractLine3',('Resposta prevista: '+u.datestr(u.VIEW['application']['decision_date'])) if u.VIEW.get('application') else blocked_reason(u.VIEW))
            a.when(EQ(T('focus'),count),new,lambda a:u.go(a,0,1));a.ret()
        a.when(EQ(T('page'),7),listing)
        def statement(a):
            if not count:u.go(a,7);a.ret();return
            length=P(item(SCHEDULE),'length')
            a.when(('bin',72,T('focus'),length),lambda a:a.ret())
            a.when(('bin',16,item(PAYABLE),('bin',72,T('focus'),ADD(length,2))),lambda a:(a.set(R(1),'selectedPaymentId',item(ID)),a.set(R(1),'action',ADD(ADD(T('focus'),('bin',12,length,-1)),1)),u.go(a,4),a.ret()))
            u.go(a,7,T('contractIndex'));a.ret()
        a.when(EQ(T('page'),3),statement);original['select'](a)

    def focus(a):
        count=len(contracts(u.VIEW))
        def listing(a):
            if count:
                a.when(('bin',72,T('focus'),count),
                    lambda a:set_focus(a,('call',u.b.path('Math'),'max',(0,('call',u.b.path('Math'),'min',(count,ADD(T('focus'),R(2))))))),
                    lambda a:a.when(('bin',72,R(2),0),lambda a:set_focus(a,T('contractIndex'))))
            a.ret()
        a.when(EQ(T('page'),7),listing)
        def statement(a):
            if not count:set_focus(a,0);a.ret();return
            length=P(item(SCHEDULE),'length')
            a.when(('bin',72,T('focus'),length),
                lambda a:set_focus(a,('call',u.b.path('Math'),'max',(0,('call',u.b.path('Math'),'min',(length,ADD(T('focus'),R(2))))))),
                lambda a:a.when(('bin',72,R(2),0),lambda a:set_focus(a,T('statementRow'))))
            a.ret()
        a.when(EQ(T('page'),3),statement);original['focus'](a)

    def shift(a):
        count=len(contracts(u.VIEW))
        def listing(a):
            a.when(('bin',103,T('focus'),count-1),lambda a:set_focus(a,ADD(count,('bin',63,ADD(ADD(ADD(T('focus'),-count),R(2)),2),2))))
            a.ret()
        a.when(EQ(T('page'),7),listing)
        def statement(a):
            if not count:a.ret();return
            length=P(item(SCHEDULE),'length')
            a.set(R(1),'footerCount',1)
            a.when(item(PAYABLE),lambda a:a.set(R(1),'footerCount',3))
            footer=T('footerCount')
            a.when(('bin',103,T('focus'),ADD(length,-1)),lambda a:set_focus(a,ADD(length,('bin',63,ADD(ADD(ADD(T('focus'),('bin',12,length,-1)),R(2)),footer),footer))))
            a.ret()
        a.when(EQ(T('page'),3),statement);original['shift'](a)

    def back(a):
        a.when(EQ(T('page'),3),lambda a:(u.go(a,7,T('contractIndex')),a.ret()))
        a.when(EQ(T('page'),7),lambda a:(u.go(a,0,1),a.ret()))
        original['back'](a)

    def graphics(data,apt,template,shape,append,new_chars,controls,count,additions):
        original['graphics'](data,apt,template,shape,append,new_chars,controls,count,additions)
        import struct
        from bank_art import texture_writer
        from bank_skin import textures
        def character(raw):cid=count+len(new_chars);new_chars.append(append(raw));return cid
        def place(cid,depth,x,y,sx=1,sy=1,name=None):
            raw=bytearray(data[template.offset:template.offset+80]);struct.pack_into('<iii6f',raw,8,46 if name else 14,depth,cid,sx,0,0,sy,x,y);struct.pack_into('<II',raw,44,0xffffffff,0);struct.pack_into('<Q',raw,56,append(name.encode()+b'\0') if name else 0);return append(raw)
        def clip(parts):
            raw=bytearray(data[apt.characters[9].offset:apt.characters[9].offset+56]);frame=append(struct.pack('<I4xQ',len(parts),append(struct.pack('<'+'Q'*len(parts),*parts))));struct.pack_into('<I4xQ',raw,32,1,frame);struct.pack_into('<Q',raw,48,0);return character(raw)
        def text(w,h,size):
            raw=bytearray(data[apt.characters[3].offset:apt.characters[3].offset+96]);struct.pack_into('<4f',raw,32,0,0,w,h);struct.pack_into('<If',raw,56,0xff203b55,size);struct.pack_into('<QQ',raw,80,append(b'\0'),0);return character(raw)
        write=texture_writer(data,append,new_chars,count,additions,character);images=textures()
        skin={k:(write(images[k]),images[k].size) for k in ('action_idle','action_selected','summary')}
        def tile(key,w,h):cid,(iw,ih)=skin[key];return place(cid,1,0,0,w/iw,h/ih)
        def panel(name,x,y,w,h):controls.append(place(clip([tile('summary',w,h)]),20,x,y,name=name))
        def button(name,x,y,w,h,big=False):
            label_height=42 if big else 34
            hint_top=63 if big else 42
            parts=[tile('action_idle',w,h),place(clip([tile('action_selected',w,h)]),2,0,0,name='selected'),place(text(w-44,label_height,32 if big else 28),3,22,16 if big else 8,name='label'),place(text(w-44,26,23 if big else 19),4,22,hint_top,name='hint')]
            controls.append(place(clip(parts),100,x,y,name=name))
        panel('overviewPanel',785,310,995,450);panel('contractsPanel',875,315,900,420);panel('statementPanel',130,310,1620,128)
        button('homeNew',120,325,625,112,True);button('homeContracts',120,453,625,112,True)
        for i in range(5):button('contractTile'+str(i),120,315+i*96,710,86)
        button('contractNew',875,780,430,72);button('contractBack',1325,780,450,72)

    u.init=init;u.refresh=refresh;u.select=select;u.focus=focus;u.shift=shift;u.back=back;u.graphics=graphics
    u.REPLACE.update(InitComponents=init,Refresh=refresh,Select=select,Shift=shift,Back=back)
    u.EXTRA[:]=[(name,count,focus if name=='MoveFocus' else body) for name,count,body in u.EXTRA]
    u.EXTRA.extend((('ContractOver',0,contract_over),('ContractClick',0,contract_click)))
