"""Monthly income/expense dashboards, reporting only; no posting or payout."""
from finance_report import composition,period_months
from finance_pages import panel,pack
from layout import INK,BLUE,MUTED,WHITE,LIGHT
import finance_art as art

MONTH_NAMES=('Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro')

def pages(view,shell,money):
 result=[];year=(view.get('date') or 0)//10000;periods=[None]+period_months(view)
 def key(side,month):return side if month is None else f'{side}:month:{month}'
 for side,title in (('receipts','RECEITAS'),('expenses','DESPESAS')):
  for index,month in enumerate(periods):
   rows=composition(view,side,month);total=sum(r['value'] for r in rows);count=max(1,(len(rows)+6)//7)
   period=f'Ano {year}' if month is None else MONTH_NAMES[month%100-1]+' / '+str(month//100)
   root=key(side,month)
   for page in range(count):
    scene_key=root if page==0 else root+':page:'+str(page);s=shell(view,scene_key,side);assets={}
    s.text(120,304,900,39,title+' · '+('ANO COMPLETO' if month is None else 'HISTÓRICO MENSAL'),28)
    s.action(1080,304,172,36,'Ano completo',side,LIGHT,BLUE,17)
    s.action(1270,304,60,36,'‹',key(side,periods[max(0,index-1)]),LIGHT,BLUE,22)
    s.text(1340,307,392,32,period,23,INK,2)
    s.action(1748,304,60,36,'›',key(side,periods[min(len(periods)-1,index+1)]),LIGHT,BLUE,22)
    panel(s,assets,'compositionCard',100,358,528,456)
    s.text(126,375,476,32,'Distribuição das '+title.lower(),24)
    values=[r['value'] for r in rows];colors=[art.category_color(r['key']) for r in rows]
    donut_key='periodDonut_'+root.replace(':','_')
    assets[donut_key]=art.donut(values,size=292,colors=colors);s.image(donut_key,218,427,292,292)
    s.text(259,536,210,25,'Total registrado',19,MUTED,2)
    money(s,241,572,246,42,total,29,art.GREEN if side=='receipts' else art.RED,2)
    s.text(126,756,476,42,'Percentual de cada origem no período selecionado.',18,MUTED,2)
    panel(s,assets,'categoryCard',644,358,1176,456)
    s.text(671,375,600,31,'Origens das receitas' if side=='receipts' else 'Destino das despesas',24)
    s.text(1257,380,280,24,'VALOR',17,MUTED,1);s.text(1604,380,188,24,'% DO TOTAL',17,MUTED,1)
    s.rect(670,414,1125,1,'#dce6ee')
    for i,row in enumerate(rows[page*7:page*7+7]):
     y=423+i*49;s.action(660,y,1144,47,'',row['target'],WHITE,BLUE,21)
     name='periodIcon_'+row['key'];assets[name]=art.glyph(row['key'],29,art.category_color(row['key']));s.image(name,678,y+7,29,29)
     s.text(727,y+1,500,28,row['label'],22);s.text(727,y+27,500,19,row['source'],14,MUTED)
     money(s,1235,y+4,300,32,row['value'],24,INK,1)
     share=row['value']/total if total else 0
     name='periodShare_'+root.replace(':','_')+'_'+row['key'];assets[name]=art.progress(share,art.category_color(row['key']),width=110,height=8);s.image(name,1571,y+14,110,8)
     s.text(1692,y+3,97,29,str(round(share*100))+'%',21,MUTED,1)
     s.rect(671,y+47,1123,1,'#e5edf4')
    if not rows:s.text(690,507,1070,130,'Nenhuma movimentação confirmada neste período.',28,MUTED,2)
    s.text(670,782,1125,23,'Negócios do save: valores acordados. Empréstimos bancários ficam em Dívidas.',15,MUTED)
    links=(('Direitos de TV','tv'),('Bilheteria','tickets'),('Patrocínio','sponsors'),('Sócio-torcedor','members'),('Transferências','transfers')) if side=='receipts' else (('Salários','salaries'),('Transferências','transfers:in'),('Dívidas e juros','loans'))
    for i,(label,target) in enumerate(links):s.action(100+i*284,829,272,35,label,target,LIGHT,BLUE,18)
    if count>1:s.action(1560,829,250,35,'Mais categorias',root if page else root+':page:1',LIGHT,BLUE,18)
    result.append(pack(s,assets))
 # A member receipt has a real, separately switchable posting each month.
 entries=sorted((r for r in view.get('entries',[]) if r['kind']=='members'),key=lambda r:r['date'],reverse=True)
 count=max(1,(len(entries)+5)//6)
 for page in range(count):
  root='members' if page==0 else 'members:'+str(page);s=shell(view,root,'receipts');assets={}
  s.text(120,306,1660,39,'SÓCIO-TORCEDOR · HISTÓRICO MENSAL',28)
  s.text(120,357,1660,58,'Receita mensal estimada pelo prestígio do clube e pela força da liga. A configuração pode desativar os próximos créditos.',22,MUTED)
  for i,row in enumerate(entries[page*6:page*6+6]):
   y=445+i*53;s.rect(100,y,1720,49,WHITE if i%2==0 else LIGHT)
   stamp=row['date']//100;s.text(123,y+8,520,31,MONTH_NAMES[stamp%100-1]+' / '+str(stamp//100),23)
   s.text(700,y+8,500,31,{'applied':'Recebido','pending':'Pendente','disabled':'Desativado'}.get(row['status'],row['status']),22,MUTED)
   money(s,1330,y+8,460,32,row['amount'] if row['status']=='applied' else 0,24,art.GREEN)
  if not entries:s.text(120,502,1660,80,'Os recebimentos aparecem após o fechamento do mês, sem créditos retroativos.',25,MUTED)
  from finance_pages import pager
  pager(s,'members',page,count,len(entries),6);result.append(pack(s,assets))
 return result
