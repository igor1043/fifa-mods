"""Annual statements using the same native controls and career currency."""
from layout import INK,BLUE,MUTED,WHITE,LIGHT


def pages(view,shell,money):
    years=view.get('annual_history',[]);result=[];count=max(1,(len(years)+5)//6)
    def amount(s,x,y,w,h,value,size=23,color=BLUE):
        if value is None:s.text(x,y,w,h,'Não registrado',18,MUTED,1)
        else:money(s,x,y,w,h,value,size,color)
    for page in range(count):
        key='history' if page==0 else 'history:'+str(page);s=shell(view,key,'overview')
        s.text(120,304,1550,42,'HISTÓRICO FINANCEIRO ANUAL',29)
        s.text(120,348,1550,31,'Receitas, despesas e orçamento observado em cada ano desta carreira.',21,MUTED)
        for i,r in enumerate(years[page*6:page*6+6]):
            y=398+i*69;s.action(110,y,1700,62,'','year:'+str(r['year']),WHITE,INK)
            s.text(132,y+12,140,37,str(r['year']),27,BLUE)
            s.text(300,y+5,400,23,'RECEITAS REGISTRADAS',15,MUTED);amount(s,300,y+27,400,29,r['income'])
            s.text(760,y+5,400,23,'DESPESAS OPERACIONAIS',15,MUTED);amount(s,760,y+27,400,29,r['expenses'])
            s.text(1250,y+5,430,23,'RESULTADO OPERACIONAL',15,MUTED);amount(s,1250,y+27,430,29,r['result'])
        if not years:s.text(130,465,1660,60,'O histórico aparecerá conforme os lançamentos forem registrados.',25,MUTED)
        if page:s.action(1260,830,80,35,'‹','history' if page==1 else 'history:'+str(page-1))
        if page+1<count:s.action(1730,830,80,35,'›','history:'+str(page+1))
        result.append(s.pack())
    for index,r in enumerate(years):
        year=r['year'];s=shell(view,'year:'+str(year),'overview')
        from finance_prizes import entries
        prize_rows=entries(r.get('native_finance'),view.get('club'),year)
        s.text(120,304,1350,40,'EXTRATO ANUAL · '+str(year),29)
        if prize_rows:s.action(1500,305,300,35,'Ver premiações','prizes' if year==(view.get('date') or 0)//10000 else 'prizes:year:'+str(year),LIGHT,INK,20)
        cards=[('Receitas registradas',r['income']),('Despesas operacionais',r['expenses']),('Resultado operacional',r['result']),('Último orçamento observado',r.get('closing_budget'))]
        for i,(label,value) in enumerate(cards):
            x=110+i*430;s.rect(x,354,415,79,WHITE);s.text(x+13,360,389,26,label,20,MUTED);amount(s,x+13,388,389,37,value,27)
        months={m['month']%100:m for m in r['months']}
        for label,x,w in [('MÊS',130,170),('RECEITAS',310,250),('DESPESAS',600,250),('RESULTADO',890,250)]:s.text(x,450,w,29,label,19,MUTED)
        labels=('JAN','FEV','MAR','ABR','MAI','JUN','JUL','AGO','SET','OUT','NOV','DEZ')
        for month in range(1,13):
            y=486+(month-1)*28;m=months.get(month,{})
            income=sum(m.get(k,0) for k in ('tv','tickets','sponsor','members'))+sum(p['amount'] for p in prize_rows if p['date']//100%100==month);expense=-sum(m.get(k,0) for k in ('coach','staff','facilities','match_costs','interest'))
            s.rect(110,y,1040,27,WHITE if month%2 else LIGHT);s.text(132,y+2,150,24,labels[month-1],18,INK)
            for x,value in ((310,income),(600,expense),(890,income-expense)):amount(s,x,y+1,250,25,value,18)
        s.rect(1180,450,630,368,WHITE);s.text(1200,464,590,31,'MOVIMENTAÇÕES DO PERÍODO',23)
        total=lambda k:sum(m.get(k,0) for m in r['months'])
        rows=[('Direitos de TV',total('tv')),('Bilheteria bruta',total('tickets')),('Patrocínio',total('sponsor')),('Sócio-torcedor',total('members')),('Premiações',sum(p['amount'] for p in prize_rows)),
              ('Salário do técnico',-total('coach')),('Comissão técnica',-total('staff')),('Estrutura e jogos',-total('facilities')-total('match_costs')),
              ('Juros dos empréstimos',-total('interest')),('Amortização bancária',-total('loans')+total('interest'))]
        for i,(label,value) in enumerate(rows):
            y=507+i*29;s.text(1202,y,335,27,label,18,MUTED);amount(s,1540,y,248,27,value,19)
        date=r.get('last_date');stamp=f'{date%100:02d}/{date//100%100:02d}/{date//10000}' if date else 'não registrada'
        s.text(120,840,1130,27,'Orçamento: última leitura em '+stamp+'. Resultado usa os lançamentos por data de origem.',17,MUTED)
        s.action(1260,832,310,39,'Voltar ao histórico','history')
        if index+1<len(years):s.action(1600,832,80,39,'‹','year:'+str(years[index+1]['year']))
        if index:s.action(1730,832,80,39,'›','year:'+str(years[index-1]['year']))
        result.append(s.pack())
    return result
