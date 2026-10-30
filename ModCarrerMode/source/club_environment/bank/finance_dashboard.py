"""Dashboard composition following the user's four-KPI/charts/tables reference."""
import finance_art as art
from layout import INK,BLUE,MUTED,WHITE,PAPER,LIGHT

def model(view):
 year=(view.get('date') or 0)//10000
 rows={r['month']%100:r for r in view.get('months',[]) if r['month']//100==year}
 series=[]
 for month in range(1,13):
  row=rows.get(month,{});income=sum(row.get(k,0) for k in ('tv','tickets','sponsor'))
  expense=-sum(row.get(k,0) for k in ('coach','staff','match_costs','interest'))
  series.append((income,expense,income-expense))
 tv=sum(r.get('tv',0) for r in rows.values());tickets=sum(r.get('tickets',0) for r in rows.values())
 coach=-sum(r.get('coach',0) for r in rows.values());interest=-sum(r.get('interest',0) for r in rows.values())
 sponsor=sum(r.get('sponsor',0) for r in rows.values());staff=-sum(r.get('staff',0) for r in rows.values());costs=-sum(r.get('match_costs',0) for r in rows.values())
 return dict(year=year,series=series,tv=tv,tickets=tickets,coach=coach,interest=interest,sponsor=sponsor,staff=staff,match_costs=costs,
  income=tv+tickets+sponsor,expense=coach+interest+staff+costs,result=tv+tickets+sponsor-coach-interest-staff-costs)

def budget_metrics(view):
 initial=view.get('budget_initial');current=view.get('budget');payroll=view.get('player_weekly');margin=view.get('wage_margin')
 return dict(initial=initial,current=current,variation=current-initial if initial is not None and current is not None else None,
  budget_ratio=current/initial if initial is not None and initial>0 and current is not None else None,
  salary_limit=payroll+margin if payroll is not None and margin is not None else None,
  salary_ratio=payroll/(payroll+margin) if payroll is not None and margin is not None and payroll+margin>0 else None)

def summary(view,shell,money):
 s=shell(view,'overview','overview');m=model(view);assets={}
 def image(name,im,x,y,w,h):assets[name]=im;s.image(name,x,y,w,h)
 def card(name,x,y,w,h):image(name,art.panel(w,h),x,y,w,h)
 for i,(label,value,kind,note,values) in enumerate((
  ('Orçamento disponível',view.get('budget',0),'wallet','Verba de transferências validada',[]),
  ('Receitas extras',m['income'],'income','TV, bilheteria e patrocínio',[r[0] for r in m['series']]),
  ('Despesas extras',m['expense'],'expense','Equipe, jogos e juros',[r[1] for r in m['series']]),
  ('Resultado do ano',m['result'],'result','Receitas menos despesas extras',[r[2] for r in m['series']]))):
  x=100+i*432;card('kpi'+str(i),x,294,418,106);image('icon'+kind,art.icon(kind),x+18,309,34,34)
  s.text(x+67,307,328,27,label,23,INK);money(s,x+67,334,330,38,value,31,'#173951',0)
  s.text(x+18,376,294,21,note,17,MUTED)
  if values:image('spark'+str(i),art.spark(values[:((view.get('date') or 0)//100%100)],art.RED if kind=='expense' else art.GREEN if kind=='result' else art.BLUE),x+313,372,90,24)
 # Charts, income composition and the two native budget cards.
 card('evolutionCard',100,414,926,241);image('monthlyIcon',art.glyph('budget',28,BLUE),120,426,28,28);s.text(159,426,600,29,'Evolução mensal',25,INK)
 s.action(843,426,160,30,'Ver mês a mês','monthly',WHITE,BLUE,17)
 s.text(122,457,510,24,'Receitas e despesas por mês de origem · '+str(m['year']),18,MUTED)
 for x,color,label in ((742,art.GREEN,'Receitas'),(870,art.RED,'Despesas')):
  s.nodes.append(dict(type='dot',x=x,y=462,w=9,h=9,color=color));s.text(x+14,455,100,24,label,17,MUTED)
 observed=(view.get('date') or 0)//100%100
 image('evolution',art.evolution(m['series'],height=169,observed=observed,labels=False),122,480,876,169)
 high=art.chart_scale(m['series'],observed)
 for i in range(4):
  # Axis amounts are native text too: currency conversion/abbreviation must
  # match the selected save, rather than baking accounting units into a PNG.
  money(s,112,610-i*(131/3),67,22,round(high*i/3),13,MUTED,1,compact=True)
 card('distributionCard',1040,414,421,241);image('distributionIcon',art.glyph('budget',25,BLUE),1058,428,25,25);s.text(1091,426,348,30,'Distribuição das receitas',23,INK)
 s.text(1060,458,380,24,'Participação no total registrado',17,MUTED)
 image('distribution',art.donut((m['tv'],m['tickets'],m['sponsor'])),1055,483,164,164)
 s.text(1080,548,114,27,'Total',19,MUTED,2)
 money(s,1070,576,136,26,m['income'],18,BLUE,2)
 for y,color,label,value in ((493,art.BLUE,'Direitos de TV',m['tv']),(542,art.GREEN,'Bilheteria',m['tickets']),(591,'#8672bc','Patrocínio',m['sponsor'])):
  s.nodes.append(dict(type='dot',x=1230,y=y+7,w=9,h=9,color=color));s.text(1248,y,190,25,label,19,INK)
  s.text(1248,y+24,190,23,str(round(value*100/m['income']))+'%' if m['income'] else 'Sem receita registrada',17,MUTED)
 metrics=budget_metrics(view)
 for key,y,title,kind,ratio,values in (
  ('budgetCard',414,'Orçamento da temporada','budget',metrics['budget_ratio'],(('Inicial',metrics['initial']),('Variação',metrics['variation']),('Disponível',metrics['current']))),
  ('wagesCard',543,'Limite salarial semanal','salary',metrics['salary_ratio'],(('Limite',metrics['salary_limit']),('Folha',view.get('player_weekly')),('Margem',view.get('wage_margin'))))):
  card(key,1475,y,345,112 if key=='wagesCard' else 116)
  image(key+'Icon',art.glyph(kind,25,BLUE),1491,y+12,25,25);s.text(1526,y+12,260,27,title,21,INK)
  image(key+'Mark',art.glyph('settings',16,BLUE),1790,y+16,16,16)
  image(key+'Bar',art.progress(ratio or 0,art.RED if kind=='salary' else art.GREEN,width=216),1493,y+48,216,9)
  s.text(1718,y+43,84,21,(str(round(ratio*100))+'%') if ratio is not None else '—',15,MUTED,1)
  for j,(label,value) in enumerate(values):
   xx=1493+j*104
   if j:s.rect(xx-7,y+71,1,30,'#dce6ee')
   s.text(xx,y+68,99,20,label,15,MUTED)
   if value is not None:money(s,xx,y+88,99,23,value,15,art.GREEN if j==2 else INK,0)
   else:s.text(xx,y+88,99,22,'—',17,MUTED)
 # Simulated commercial/staff categories have their own configurable ledger.
 for x,w,title,entries,total,tint in ((100,548,'Principais receitas',(('Direitos de TV',m['tv'],'tv'),('Bilheteria bruta',m['tickets'],'ticket'),('Patrocínio',m['sponsor'],'sponsor')),m['income'],art.GREEN),
    (662,548,'Principais despesas',(('Salário do técnico',m['coach'],'coach'),('Comissão técnica',m['staff'],'staff'),('Custos dos jogos',m['match_costs'],'match_costs'),('Juros',m['interest'],'interest')),m['expense'],art.RED)):
  card('table'+str(x),x,669,w,185);image('tableIcon'+str(x),art.icon('income' if tint==art.GREEN else 'expense',28),x+17,682,28,28);s.text(x+56,681,w-76,30,title,25,INK)
  s.text(x+17,718,30,22,'#',16,MUTED);s.text(x+72,718,180,22,'DESCRIÇÃO',16,MUTED);s.text(x+252,718,140,22,'VALOR',16,MUTED,1);s.text(x+448,718,78,22,'% TOTAL',16,MUTED,1);s.rect(x+16,742,w-32,1,'#dce6ee')
  for j,(label,value,kind) in enumerate(entries):
   yy=747+j*25
   if x==100:s.action(x+14,yy,w-28,25,'',{'tv':'tv','ticket':'tickets','sponsor':'sponsors'}[kind],WHITE,BLUE,17)
   s.text(x+17,yy,24,27,str(j+1),18,MUTED);image('category'+str(x)+str(j),art.glyph(kind,22),x+43,yy+1,22,22)
   s.text(x+72,yy,176,25,label,17,INK);money(s,x+252,yy,140,25,value,17,INK)
   percent=round(value*100/total) if total else 0;image('share'+str(x)+str(j),art.progress(percent/100,tint,width=70,height=9),x+404,yy+8,70,9)
   s.text(x+481,yy,45,26,str(percent)+'%',17,MUTED,1)
   if j<len(entries)-1:s.rect(x+16,yy+24,w-32,1,'#e5edf4')
 from finance_pages import picture
 card('transferCard',1224,669,596,185);image('transferIcon',art.glyph('transfer',27,BLUE),1242,683,27,27);s.text(1282,681,320,30,'Transferências',25,INK)
 s.action(1648,680,150,31,'Ver todas','transfers',WHITE,BLUE,18)
 transfers=view.get('transfers',[])
 for j,row in enumerate(transfers[:3]):
  yy=720+j*42;picture(s,assets,'head',row['player'],1243,yy,38,39)
  s.text(1290,yy,262,25,row['name'],19,INK)
  s.text(1290,yy+23,262,18,('Chegada' if row['direction']=='in' else 'Saída')+(' · Empréstimo' if row['loan'] else ''),15,MUTED)
  picture(s,assets,'crest',row['other']['id'],1560,yy+3,29,31)
  money(s,1602,yy+6,195,31,row['fee'],21,art.RED if row['direction']=='in' else art.GREEN)
 if not transfers:s.text(1244,741,556,66,'Nenhum negócio confirmado para este clube no save.' if not view.get('transfer_error') else 'Aguardando os negócios deste save.',22,MUTED)
 if not view.get('ready'):
  s.rect(100,294,1720,560,PAPER);s.text(130,410,1660,60,'Carregando as finanças desta carreira...',32)
  s.text(130,485,1660,70,view.get('message','Aguardando dados atuais do clube e das competições.'),23,MUTED)
 result=s.pack();result['assets']=assets
 return result
