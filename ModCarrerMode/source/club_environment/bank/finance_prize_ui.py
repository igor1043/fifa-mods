"""Native prize receipts, grouped by competition and dated payment."""
from collections import defaultdict
from finance_prizes import entries
from layout import INK,BLUE,MUTED,WHITE,LIGHT


def groups(rows):
    grouped=defaultdict(list)
    for row in rows:grouped[row['competition']].append(row)
    return sorted((dict(competition=competition,name=items[0].get('name','Competição '+str(competition)),
        asset=items[0].get('asset',0),amount=sum(r['amount'] for r in items),rows=items)
        for competition,items in grouped.items()),key=lambda r:(-r['amount'],r['name']))


def pages(view,shell,money):
    from finance_pages import panel,picture,pack,pager
    from finance_ui import day
    native=dict(view.get('native_finance') or {});all_rows=list(native.get('entries',[]))
    for row in view.get('annual_history',[]):all_rows.extend(row.get('native_finance',{}).get('entries',[]))
    native['entries']=all_rows;club=view.get('club');year=(view.get('date') or 0)//10000
    known=entries(native,club);result=[]
    periods=[('prizes',entries(native,club,year),'Ano '+str(year))]
    for month in sorted({r['date']//100 for r in known if r['date']//10000==year},reverse=True):
        periods.append(('prizes:month:'+str(month),entries(native,club,month=month),f'{month%100:02d}/{month//100}'))
    for older in sorted({r['date']//10000 for r in known if r['date']//10000<year},reverse=True):
        periods.append(('prizes:year:'+str(older),entries(native,club,older),'Ano '+str(older)))
    for root,rows,period in periods:
        competitions=groups(rows);count=max(1,(len(competitions)+3)//4)
        for page in range(count):
            key=root if page==0 else root+':'+str(page);s=shell(view,key,'receipts');assets={}
            s.text(120,303,1120,39,'PREMIAÇÕES · POR COMPETIÇÃO',29)
            s.text(1250,308,550,32,period,23,MUTED,1)
            s.text(120,351,1170,28,'Pagamentos confirmados nos avisos do FIFA e no histórico acompanhado desta carreira.',20,MUTED)
            money(s,1300,346,500,42,sum(r['amount'] for r in rows),30,BLUE)
            for i,row in enumerate(competitions[page*4:page*4+4]):
                y=405+i*96;target=root+':competition:'+str(row['competition'])
                panel(s,assets,'prizeGroup'+str(i),100,y,1720,86);s.action(106,y+3,1708,79,'',target,WHITE,INK,24)
                picture(s,assets,'competition',row['asset'],123,y+10,65,65)
                s.text(215,y+8,1050,32,row['name'],26)
                n=len(row['rows']);s.text(215,y+45,1050,25,f'{n} pagamento'+('s' if n!=1 else '')+' · Último em '+day(max(r['date'] for r in row['rows'])),20,MUTED)
                money(s,1320,y+24,420,39,row['amount'],28,BLUE);s.text(1765,y+24,34,37,'›',30,MUTED)
            if not competitions:s.text(130,465,1640,120,'Nenhum aviso de premiação confirmado neste período.',29,MUTED,2)
            s.text(120,797,1650,27,'Valores já creditados pelo FIFA. Consultar esta tela não altera o orçamento.',19,MUTED)
            pager(s,root,page,count,len(competitions),4);result.append(pack(s,assets))
        for group in competitions:
            detail=root+':competition:'+str(group['competition']);items=group['rows'];count=max(1,(len(items)+4)//5)
            for page in range(count):
                key=detail if page==0 else detail+':'+str(page);s=shell(view,key,'receipts');assets={}
                picture(s,assets,'competition',group['asset'],115,301,66,66)
                s.text(203,303,1190,39,group['name'],29);s.text(203,347,1190,29,'PREMIAÇÕES RECEBIDAS · '+period,20,MUTED)
                money(s,1395,320,395,45,group['amount'],32,BLUE)
                s.text(120,398,260,30,'DATA',20,MUTED);s.text(410,398,870,30,'ORIGEM',20,MUTED);s.text(1350,398,440,30,'VALOR RECEBIDO',20,MUTED,1)
                for i,row in enumerate(items[page*5:page*5+5]):
                    y=447+i*64;s.rect(100,y,1720,58,WHITE if i%2==0 else LIGHT)
                    s.text(120,y+12,260,31,day(row['date']),24)
                    s.text(410,y+2,870,29,'Premiação da competição',23);s.text(410,y+31,870,23,'Crédito nativo confirmado',17,MUTED)
                    money(s,1350,y+9,440,37,row['amount'],27,BLUE)
                s.action(100,795,350,37,'Competições',root,LIGHT,INK,21)
                pager(s,detail,page,count,len(items),5);result.append(pack(s,assets))
    return result
