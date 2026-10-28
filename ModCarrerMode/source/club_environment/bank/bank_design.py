"""Reference-inspired bank list and proposal cards on the native FIFA screen."""
from loans import BANKS,AMOUNTS,TERMS,quote,offered,amount_indices,term_indices,product_limits

ORDER=(7,9,10,11,12,3,4,5,6,8)
N=len(ORDER)
ROWS=(469,504,539,585,639,673,707,747,781,818)

def install(ui):
    global u,T,R,P,EQ,ADD
    u=ui;T=u.T;R=u.R;P=u.P;EQ=u.EQ;ADD=u.ADD
    original={name:getattr(u,name) for name in ('init','refresh','select','shift','focus','back','wait','graphics')}
    # Keep each native APT method bounded even with localized money expressions.
    u.EXTRA.append(('RefreshBase',0,original['refresh']))
    def fields():
        return (('bankHeading',845,312,920,46,32),('bankCaption',845,356,910,34,24),
            ('amountCaption',710,430,425,36,27),('amountHint',710,538,430,34,19),
            ('termCaption',710,578,425,36,27),('termHint',710,684,430,34,19),
            ('simulationHeading',1208,425,560,40,28),('responseHint',1550,614,225,30,18),('bankListInfo',300,823,280,36,20)) \
            +tuple((f'summaryLabel{i}',1208,y,360,34,22) for i,y in enumerate(ROWS)) \
            +tuple((f'summaryValue{i}',1570,y,208,34,24) for i,y in enumerate(ROWS))
    u.FIELDS+=fields()
    u.BUTTON_TEXT_LAYOUT.update({
        'amountControl':(60,36,12),'termControl':(60,36,12),
        'reviewControl':(64,36,6),'formBack':(64,36,6),
        'bankPrevious':(36,36,0),'bankNext':(36,36,0)})
    u.BUTTONS.extend([('bankTile'+str(i),i,'BankClick','BankOver') for i in range(6)])
    u.BUTTONS.extend((('bankPrevious',-1,'BankPageClick',None),('bankNext',1,'BankPageClick',None)))
    u.BUTTONS.extend((('amountControl',N,'RowClick','RowOver'),('termControl',N+1,'RowClick','RowOver'),('reviewControl',N+2,'RowClick','RowOver'),('formBack',N+3,'RowClick','RowOver')))

    def init(a):
        original['init'](a);a.set(R(1),'bankIndex',0);a.set(R(1),'bankOffset',0);a.set(R(1),'bank',ORDER[0]);a.do(R(1),'Refresh')

    def bank_over(a):
        owner=P(R(1),'owner');index=P(R(1),'index')
        a.set(owner,'focus',index);a.set(owner,'bankIndex',index);a.do(owner,'Refresh')

    def bank_click(a):
        a.do(R(1),'onRollOver');a.do(P(R(1),'owner'),'Select')

    def bank_page(a):
        owner=P(R(1),'owner')
        for index in range(N):
            def jump(a,index=index):
                a.when(EQ(P(R(1),'index'),1),lambda a:a.set(owner,'focus',min(N-1,index+6)),lambda a:a.set(owner,'focus',max(0,index-6)))
                a.do(owner,'Refresh');a.ret()
            a.when(EQ(P(owner,'bankIndex'),index),jump)

    def wait(a):
        original['wait'](a)
        def bind(a):
            for name,index in (('amountControl',N),('termControl',N+1)):
                for side,delta in (('less',-1),('more',1)):
                    obj=P(T(name),side);a.set(obj,'owner',R(1));a.set(obj,'index',index);a.set(obj,'delta',delta);a.set(obj,'onRelease',T('AdjustClick'))
        a.when(T('amountControl'),bind)
        for name in ('amountControl','termControl'):
            for side,glyph in (('less','−'),('more','+')):a.set(P(P(T(name),side),'glyph'),'text',glyph)

    def refresh(a):
        # Restore the positions used by the other pages before their own draw.
        for name,x,y in (('title',130,155),('subtitle',132,218),('section',130,280),('status',130,900)):
            a.set(T(name),'_x',x);a.set(T(name),'_y',y)
        a.do(R(1),'RefreshBase')
        for name in ('bankHero','optionsPanel','simulationPanel','ratePanel'):
            u.show(a,name,False)
        for index in range(len(BANKS)):
            u.show(a,'bankHeaderLogo'+str(index),False);a.set(T('bankHeaderLogo'+str(index)),'_x',695);a.set(T('bankHeaderLogo'+str(index)),'_y',320)
        def form(a):
            for name,x,y in (('title',80,125),('subtitle',82,188),('section',80,245)):
                a.set(T(name),'_x',x);a.set(T(name),'_y',y)
            u.show(a,'summaryCard',False)
            for i in range(11):u.label(a,'detail'+str(i),'')
            for i in range(5):u.show(a,'row'+str(i),False)
            for i in range(len(BANKS)):u.show(a,'bankLogo'+str(i),False)
            for name in ('bankHero','optionsPanel','simulationPanel','ratePanel'):u.show(a,name,True)
            # Focus traverses the list and then the four explicit form controls.
            a.when(('bin',72,T('focus'),N),lambda a:a.set(R(1),'bankIndex',T('focus')))
            a.set(R(1),'bank',('index',('array',ORDER),T('bankIndex')))
            for bank in ORDER:
                def normalize(a,bank=bank):
                    for key,allowed,values in (('amountIndex',amount_indices(bank),AMOUNTS),('termIndex',term_indices(bank),TERMS)):
                        clamped=tuple(max((i for i in allowed if values[i]<=value),default=allowed[0]) for value in values)
                        a.set(R(1),key,('index',('array',clamped),T(key)))
                a.when(EQ(T('bank'),bank),normalize)
            for selected in range(N):
                def visible(a,selected=selected):
                    a.when(('bin',72,selected,T('bankOffset')),lambda a:a.set(R(1),'bankOffset',min(selected,N-6)))
                    a.when(('bin',72,ADD(T('bankOffset'),5),selected),lambda a:a.set(R(1),'bankOffset',max(0,min(selected-5,N-6))))
                a.when(EQ(T('bankIndex'),selected),visible)
            for offset in range(N-5):
                def rows(a,offset=offset):
                    for visible,index in enumerate(range(offset,offset+6)):
                        bank=ORDER[index];item=BANKS[bank];name='bankTile'+str(visible);obj=T(name)
                        a.set(obj,'index',index);u.show(a,name,True)
                        a.set(P(obj,'label'),'text',item['name']);a.set(P(obj,'hint'),'text','Até '+u.b.money(product_limits(bank)[0])+' · a partir de '+str(item['rate_bps']/100).replace('.',',')+'% a.m.')
                        a.set(P(obj,'label'),'textColor',0x203b55);a.set(P(obj,'hint'),'textColor',0x536b80);a.set(P(obj,'selected'),'_alpha',0)
                        a.when(EQ(T('bankIndex'),index),lambda a,obj=obj:(a.set(P(obj,'selected'),'_alpha',100),a.set(P(obj,'label'),'textColor',0xffffff),a.set(P(obj,'hint'),'textColor',0xe8f3fc)))
                        logo=T('bankLogo'+str(bank));u.show(a,'bankLogo'+str(bank),True)
                        for key,value in (('_x',100),('_y',304+visible*86),('_xscale',75),('_yscale',100)):a.set(logo,key,value)
                a.when(EQ(T('bankOffset'),offset),rows)
            u.draw_row(a,'bankPrevious',-1,'‹');u.draw_row(a,'bankNext',-1,'›')
            u.label(a,'bankListInfo',ADD(ADD(ADD(ADD(T('bankOffset'),1),'–'),ADD(T('bankOffset'),6)),' de '+str(N)+' bancos'))
            for bank in ORDER:
                def chosen(a,bank=bank):
                    u.show(a,'bankHeaderLogo'+str(bank),True)
                    u.label(a,'bankHeading','Banco: '+BANKS[bank]['name']);u.label(a,'bankCaption','SIMULAÇÃO · Até '+u.b.money(product_limits(bank)[0])+' em '+str(product_limits(bank)[1])+' meses')
                a.when(EQ(T('bank'),bank),chosen)
            u.label(a,'amountCaption','Valor do empréstimo');u.label(a,'amountHint','Crédito no orçamento de transferências')
            u.label(a,'termCaption','Prazo');u.label(a,'termHint','Valores e prazos maiores aumentam os juros')
            u.draw_row(a,'amountControl',N,('index',('array',tuple(u.b.money(v) for v in AMOUNTS)),T('amountIndex')))
            u.draw_row(a,'termControl',N+1,ADD(('index',('array',TERMS),T('termIndex')),' meses'))
            u.draw_row(a,'reviewControl',N+2,'Revisar proposta','Ver condições antes de confirmar')
            u.draw_row(a,'formBack',N+3,'Voltar','Selecionar outra instituição')
            u.label(a,'simulationHeading','Resumo da simulação');u.label(a,'responseHint','')
            budget=u.VIEW.get('budget',0)
            labels=('Saldo atual','Crédito se aprovado','Saldo após aprovação','Resposta prevista','Parcela mensal','Primeira cobrança prevista','Última cobrança prevista','Total contratado','Juros totais','Taxa simulada')
            for i,label in enumerate(labels):u.label(a,'summaryLabel'+str(i),label)
            for bank in ORDER:
                for ai,amount in enumerate(AMOUNTS):
                    for ti,months in enumerate(TERMS):
                        if not offered(bank,amount,months):continue
                        q=quote(bank,amount,months)
                        expected=u.response_date(u.VIEW.get('date'),bank)
                        condition=('bin',16,('bin',16,EQ(T('bank'),bank),EQ(T('amountIndex'),ai)),EQ(T('termIndex'),ti))
                        values=(u.b.money(budget),'+'+u.b.money(amount),u.b.money(budget+amount),u.datestr(expected),u.b.money(q['payment']),u.due_date(expected,1),u.due_date(expected,months),u.b.money(q['total']),u.b.money(q['total']-amount),str(q['rate_bps']/100).replace('.',',')+'% ao mês')
                        def fill(a,values=values):
                            for i,value in enumerate(values):u.label(a,'summaryValue'+str(i),value)
                        a.when(condition,fill)
            a.set(T('summaryValue1'),'textColor',0x13883b);a.set(T('summaryValue4'),'textColor',0xdf8c00)
            for name in ('summaryLabel9','summaryValue9'):a.set(T(name),'textColor',0x005eae)
            u.label(a,'status','')
        a.when(EQ(T('page'),1),form)

    def select(a):
        def form(a):
            a.when(('bin',72,T('focus'),N),lambda a:(u.go(a,1,N),a.ret()))
            a.when(('bin',72,T('focus'),N+2),lambda a:(a.do(R(1),'Shift',1),a.ret()))
            a.when(EQ(T('focus'),N+2),lambda a:u.go(a,2),lambda a:u.go(a,1,T('bankIndex')));a.ret()
        a.when(EQ(T('page'),1),form)
        a.when(('bin',16,EQ(T('page'),2),EQ(T('focus'),1)),lambda a:(u.go(a,1,N+2),a.ret()))
        original['select'](a)

    def focus(a):
        a.when(EQ(T('page'),1),lambda a:(a.set(R(1),'focus',('bin',63,ADD(ADD(T('focus'),R(2)),N+4),N+4)),a.do(R(1),'Refresh'),a.ret()))
        original['focus'](a)

    def shift(a):
        def form(a):
            a.when(('bin',72,T('focus'),N),lambda a:a.set(R(1),'focus',('bin',63,ADD(ADD(T('focus'),R(2)),N),N)))
            for bank in ORDER:
                def bank_values(a,bank=bank):
                    for index,field,allowed,values in ((N,'amountIndex',amount_indices(bank),AMOUNTS),(N+1,'termIndex',term_indices(bank),TERMS)):
                        positions=tuple(allowed.index(max((i for i in allowed if values[i]<=value),default=allowed[0])) for value in values)
                        position=('index',('array',positions),T(field))
                        target=('index',('array',allowed),('bin',63,ADD(ADD(position,R(2)),len(allowed)),len(allowed)))
                        a.when(EQ(T('focus'),index),lambda a,field=field,target=target:a.set(R(1),field,target))
                a.when(EQ(T('bank'),bank),bank_values)
            a.do(R(1),'Refresh');a.ret()
        a.when(EQ(T('page'),1),form);original['shift'](a)

    def back(a):
        a.when(EQ(T('page'),1),lambda a:(a.when(('bin',103,T('focus'),N-1),lambda a:u.go(a,1,T('bankIndex')),lambda a:u.go(a,0)),a.ret()))
        a.when(EQ(T('page'),2),lambda a:(u.go(a,1,N+2),a.ret()));original['back'](a)

    def graphics(data,apt,template,shape,append,new_chars,controls,count,additions):
        original['graphics'](data,apt,template,shape,append,new_chars,controls,count,additions)
        # The factory is shared with the logo textures and uses the same proven
        # DDS/geometry conventions as the rest of the native screen.
        import struct
        from bank_art import texture_writer
        from bank_skin import textures
        def character(raw):cid=count+len(new_chars);new_chars.append(append(raw));return cid
        def place(cid,depth,x,y,sx=1,sy=1,name=None):
            raw=bytearray(data[template.offset:template.offset+80]);struct.pack_into('<iii6f',raw,8,46 if name else 14,depth,cid,sx,0,0,sy,x,y);struct.pack_into('<II',raw,44,0xffffffff,0);struct.pack_into('<Q',raw,56,append(name.encode()+b'\0') if name else 0);return append(raw)
        def clip(parts):
            raw=bytearray(data[apt.characters[9].offset:apt.characters[9].offset+56]);frame=append(struct.pack('<I4xQ',len(parts),append(struct.pack('<'+'Q'*len(parts),*parts))));struct.pack_into('<I4xQ',raw,32,1,frame);struct.pack_into('<Q',raw,48,0);return character(raw)
        def text(width,height,size,alignment=0):
            raw=bytearray(data[apt.characters[3].offset:apt.characters[3].offset+96]);struct.pack_into('<4f',raw,32,0,0,width,height);struct.pack_into('<I',raw,52,alignment);struct.pack_into('<If',raw,56,0xff203b55,size);struct.pack_into('<QQ',raw,80,append(b'\0'),0);return character(raw)
        write=texture_writer(data,append,new_chars,count,additions,character);skin={k:(write(v),v.size) for k,v in textures().items()}
        def textured(key,depth,w,h,name=None):
            cid,(width,height)=skin[key];return place(cid,depth,0,0,w/width,h/height,name)
        def panel(key,name,x,y,w,h,depth=2):controls.append(place(clip([textured(key,1,w,h)]),depth,x,y,name=name))
        panel('header','bankHero',675,293,1130,104)
        panel('options','optionsPanel',675,410,490,306)
        panel('summary','simulationPanel',1180,410,625,454)
        # Native underlays provide separators and a small blue rate strip.
        def colored(name,x,y,w,h,color):
            raw=bytearray(data[template.offset:template.offset+80]);struct.pack_into('<iii6f',raw,8,46,6,shape,w,0,0,h,0,0);struct.pack_into('<II',raw,44,color,0);struct.pack_into('<Q',raw,56,0);struct.pack_into('<i',raw,8,14);child=append(raw);controls.append(place(clip([child]),6,x,y,name=name))
        colored('ratePanel',1195,815,595,38,0xffdcecfb)
        def button(name,x,y,w,h,index,bank=False,arrows=False):
            idle='bank_idle' if bank else 'action_idle';selected='bank_selected' if bank else 'action_selected'
            parts=[textured(idle,1,w,h),place(clip([textured(selected,1,w,h)]),2,0,0,name='selected')]
            paging=name in ('bankPrevious','bankNext')
            tx=0 if paging else 134 if bank else 18
            label_width=w-148 if arrows else w-tx-34
            if paging:label_width=w
            parts.extend((place(text(label_width,36,26 if paging else 27 if bank else 29,2 if arrows or paging else 0),3,tx,0 if paging else 12 if bank else 6,name='label'),place(text(w-tx-30,24,19),4,tx,46 if bank else 37,name='hint')))
            if arrows:
                for side,glyph,off in (('less','−',w-108),('more','+',w-54)):
                    # Equal square hit areas, with each glyph centered inside.
                    glyph_id=text(44,38,30,2);parts.append(place(clip([textured('action_idle',1,44,44),place(glyph_id,2,0,3,name='glyph')]),5 if side=='less' else 6,off,8,name=side))
            controls.append(place(clip(parts),2000+index,x,y,name=name))
        for i in range(6):button('bankTile'+str(i),80,295+i*86,570,82,i,bank=True)
        button('amountControl',700,471,450,60,10,arrows=True);button('termControl',700,619,450,60,11,arrows=True)
        button('reviewControl',675,726,490,64,12);button('formBack',675,800,490,64,13)
        button('bankPrevious',80,820,90,36,14);button('bankNext',180,820,90,36,15)

    u.init=init;u.refresh=refresh;u.select=select;u.shift=shift;u.focus=focus;u.back=back;u.wait=wait;u.graphics=graphics
    u.REPLACE.update(InitComponents=init,Refresh=refresh,Select=select,Shift=shift,Back=back)
    u.EXTRA[:]=[(name,count,wait if name=='WaitButtons' else focus if name=='MoveFocus' else body) for name,count,body in u.EXTRA]
    u.EXTRA.extend((('BankOver',0,bank_over),('BankClick',0,bank_click),('BankPageClick',0,bank_page)))
