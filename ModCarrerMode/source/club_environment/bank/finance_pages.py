from ui_theme import ACCENT, ACCENT_TEXT
"""Native finance drill-downs, with original installed player/club artwork."""
from functools import lru_cache
from io import BytesIO
from PIL import Image,ImageDraw,ImageChops
import portable_paths as portable
from layout import INK,BLUE,MUTED,WHITE,LIGHT
import finance_art as art

@lru_cache(maxsize=256)
def artwork(game,kind,ident):
 candidates=(f'ModCarrerMode/data/club_environment/bank/assets/{ident}.png',) if kind=='bank' and str(ident).replace('_','').isalnum() else (f'data/ui/imgAssets/heads/p{ident}.dds',) if kind=='head' else (
  (f'data/ui/imgAssets/careerCompetitionIcons/{ident}.png',f'data/ui/imgAssets/league/light/l{ident}.dds',f'data/ui/imgAssets/league/dark/l{ident}.dds') if kind=='competition' else
  (f'data/ui/imgAssets/crest/light/l{ident}.dds',f'data/ui/imgAssets/crest/dark/l{ident}.dds'))
 image=None
 for path in candidates:
  try:image=Image.open(BytesIO(portable.read_asset(path))).convert('RGBA');break
  except (OSError,ValueError):pass
 canvas=Image.new('RGBA',(256,256))
 if image is not None:
  if kind=='bank':
   # The installed bank marks include large white margins. Fit the visible
   # logo rather than shrinking that whole source canvas into the debt row.
   opaque=Image.new('RGBA',image.size,'white');opaque.alpha_composite(image)
   bounds=ImageChops.difference(opaque.convert('RGB'),Image.new('RGB',image.size,'white')).convert('L').point(lambda v:255 if v>16 else 0).getbbox()
   if bounds:image=image.crop(bounds)
  image.thumbnail((248,248),Image.Resampling.LANCZOS);canvas.alpha_composite(image,((256-image.width)//2,(256-image.height)//2))
 else:
  d=ImageDraw.Draw(canvas)
  if kind=='head':d.ellipse((42,12,86,57),fill='#aabac4');d.rounded_rectangle((22,64,106,124),22,fill='#aabac4')
  elif kind=='bank':
   icon=art.glyph('match_costs',72);icon.thumbnail((190,190),Image.Resampling.LANCZOS);canvas.alpha_composite(icon,((256-icon.width)//2,(256-icon.height)//2))
 return canvas

def picture(s,assets,kind,ident,x,y,w,h):
 key=kind+'_'+str(ident);assets[key]=artwork(str(portable.GAME),kind,ident);s.image(key,x,y,w,h)

def panel(s,assets,key,x,y,w,h):
 assets[key]=art.panel(w,h);s.image(key,x,y,w,h)

def pack(s,assets):
 result=s.pack();result['assets']=assets;return result

def match_revenue_rows(view,kind,venue='all'):
 """Display joins only; historical amounts and states are never rewritten."""
 fixtures={}
 for m in view.get('fixtures',[]):fixtures.setdefault(m['id'],[]).append(m)
 entries={r['id']:r for r in view.get('entries',[])};rows=[]
 for e in entries.values():
  if e['kind']!=kind:continue
  choices=[m for m in fixtures.get(e.get('fixture'),[]) if m.get('date')==e.get('date') and (e.get('home') is None or m.get('home')==e['home']) and (e.get('away') is None or m.get('away')==e['away'])]
  m=choices[0] if len(choices)==1 else {}
  home=e.get('home',m.get('home'));away=e.get('away',m.get('away'))
  if home is None:
   try:home,away=map(int,e['id'].split(':')[-2:])
   except (ValueError,TypeError):continue
  club=view.get('club')
  if club not in (home,away) or venue=='home' and home!=club or venue=='away' and away!=club:continue
  if kind=='tickets' and home!=club:continue
  cost=entries.get('match_costs:'+e['id'].split(':',1)[1]);actual=e['amount'] if e['status']=='applied' else 0
  charge=-cost['amount'] if cost and cost['status']=='applied' else 0
  opponent=away if home==club else home;name_key='away_name' if home==club else 'home_name'
  rows.append(dict(id=e['id'],date=e['date'],opponent=opponent,name=e.get(name_key,m.get(name_key,'Clube '+str(opponent))),
   competition=e['description'],asset=e.get('competition_asset',m.get('asset',0)),venue='Casa' if home==club else 'Fora',attendance=e.get('attendance'),crowd_percent=e.get('crowd_percent'),crowd_source=e.get('crowd_source'),gross=actual,cost=charge,net=actual-charge,status=e['status']))
 return sorted(rows,key=lambda r:(r['date'],r['id']),reverse=True)

def ticket_rows(view):
 from club_finance import ticket_operation_cost
 rows=match_revenue_rows(view,'tickets','home');entries={e['id']:e for e in view.get('entries',[])}
 for row in rows:
  expense=entries.get('match_costs:'+row['id'].split(':',1)[1])
  row.update(display_cost=row['cost'],display_net=row['net'],cost_estimated=False,cost_note='Debitada' if expense and expense['status']=='applied' else '')
  if row['status']!='applied':continue
  if expense:
   if expense['status']=='pending':row.update(display_cost=-expense['amount'],display_net=row['gross']+expense['amount'],cost_note='Pendente')
   elif expense['status']=='disabled':row['cost_note']='Desativada'
  else:
   # Old receipts have no operation posting. Show a labelled comparison, not
   # a fabricated payment or a new mutation of the historical ledger.
   estimate=ticket_operation_cost(row['gross'],view.get('rules'))
   row.update(display_cost=estimate,display_net=row['gross']-estimate,cost_estimated=True,cost_note='Estimativa · não debitada')
 return rows

SPONSOR_PARTS=(('Patrocinador master',60),('Patrocinadores secundários',25),('Fornecedor de material esportivo',15))
def sponsor_parts(total):
 """Temporary display allocation; the sum is exactly the one existing posting."""
 amounts=[int(total)*share//100 for _,share in SPONSOR_PARTS[:-1]]
 amounts.append(int(total)-sum(amounts))
 return [(label,share,amount) for (label,share),amount in zip(SPONSOR_PARTS,amounts)]

def pager(s,key,page,count,total,limit):
 first=key if page<=1 else key+':'+str(page-1)
 last=key+':'+str(page+1) if page+1<count else (key if page==0 else key+':'+str(page))
 if count>1:
  s.action(100,814,110,40,'‹',first);s.action(222,814,110,40,'›',last)
 s.text(370,822,1425,26,f'{page*limit+1 if total else 0}–{min((page+1)*limit,total)} de {total}',20,MUTED,1)

def pages(view,shell,money):
 from finance_dashboard import model
 from finance_ui import day
 m=model(view);result=[];months=view.get('months',[])
 observed=(view.get('date') or 0)//100%100
 count=max(1,(observed+5)//6)
 for page in range(count):
  key='monthly' if page==0 else 'monthly:'+str(page);s=shell(view,key,'overview');assets={}
  s.text(120,304,1660,36,'EVOLUÇÃO MENSAL · '+str(m['year']),28)
  for x,w,label in ((120,330,'MÊS'),(500,390,'RECEITAS'),(940,390,'DESPESAS'),(1370,430,'RESULTADO')):s.text(x,364,w,30,label,22,MUTED,0 if x==120 else 1)
  for i,(income,expense,net) in enumerate(m['series'][page*6:min(observed,page*6+6)]):
   y=414+i*62;s.rect(100,y,1720,55,WHITE if i%2==0 else LIGHT)
   s.text(120,y+11,330,33,art.MONTHS[page*6+i]+' / '+str(m['year']),24)
   for x,w,value,color in ((500,390,income,art.GREEN),(940,390,expense,art.RED),(1370,430,net,BLUE)):
    money(s,x,y+10,w,36,value,26,color)
  s.text(120,792,1240,25,'Mês de origem dos lançamentos. Pagamentos atrasados mantêm a data efetiva de aplicação no histórico.',18,MUTED)
  pager(s,'monthly',page,count,observed,6);result.append(pack(s,assets))
 # Revenue and expense pages keep operating income distinct from financing.
 for root,title,fields in (('receipts','RECEITAS ADICIONAIS',(('tv','Direitos de TV'),('tickets','Bilheteria bruta'),('sponsor','Patrocínio'))),
                            ('expenses','DESPESAS ADICIONAIS',(('coach','Técnico'),('staff','Comissão técnica'),('match_costs','Custos dos jogos'),('interest','Juros')))):
  count=max(1,(len(months)+6)//7)
  for page in range(count):
   key=root if page==0 else root+':'+str(page);s=shell(view,key,root);assets={}
   s.text(120,302,1250,36,title,27)
   if root=='receipts':s.action(1480,300,320,42,'Contratos de TV','contracts',LIGHT,BLUE,22)
   cw=1720/len(fields)
   for j,(field,label) in enumerate(fields):
    x=100+j*cw;panel(s,assets,'total'+field,x,353,int(cw-12),88)
    if root=='receipts':s.action(x,353,cw-12,88,'',{'tv':'tv','tickets':'tickets','sponsor':'sponsors'}[field],WHITE,BLUE,22)
    s.text(x+20,362,cw-45,28,label,22);money(s,x+20,397,cw-45,35,m[field],27,art.GREEN if root=='receipts' else art.RED,0)
   sw=1420/len(fields);s.text(120,464,220,30,'MÊS',22,MUTED)
   for j,(field,label) in enumerate(fields):s.text(380+j*sw,464,sw-25,30,label,21,MUTED,1)
   for i,r in enumerate(months[page*7:page*7+7]):
    y=506+i*40;s.rect(100,y,1720,37,WHITE if i%2==0 else LIGHT)
    stamp=str(r['month']);s.text(120,y+4,320,31,stamp[4:]+'/'+stamp[:4],22)
    for j,(field,_) in enumerate(fields):money(s,380+j*sw,y+4,sw-25,31,abs(r.get(field,0)),22)
   if not months:s.text(120,540,1600,70,'Nenhum lançamento adicional registrado. Os valores surgem após a ativação do mod.',25,MUTED)
   pager(s,root,page,count,len(months),7);result.append(pack(s,assets))
 # Matchday receipts: only home fixtures, paged without rebuilding the UI.
 rows=ticket_rows(view);count=max(1,(len(rows)+3)//4)
 estimated=any(r['cost_estimated'] for r in rows);rate=int(view.get('rules',{}).get('match_cost_bps',4000))/100
 for page in range(count):
  key='tickets' if page==0 else 'tickets:'+str(page);s=shell(view,key,'receipts');assets={}
  s.text(120,302,1660,36,'BILHETERIA · PARTIDAS EM CASA',28)
  s.text(120,347,1660,27,f'Operação de referência: {rate:g}% da renda · Histórico sem custo: estimativa, sem débito retroativo',19,MUTED)
  for j,(label,total,color) in enumerate((('RENDA BRUTA RECEBIDA',sum(r['gross'] for r in rows),INK),('OPERAÇÃO · REAL + ESTIMADA' if estimated else 'CUSTOS DE OPERAÇÃO',sum(r['display_cost'] for r in rows),art.RED),('RENDA LÍQUIDA ESTIMADA' if estimated else 'RENDA LÍQUIDA',sum(r['display_net'] for r in rows),art.GREEN))):
   x=100+j*576;panel(s,assets,'ticketTotal'+str(j),x,387,560,79)
   s.text(x+18,394,524,24,label,18,MUTED);money(s,x+18,423,524,36,total,28,color,0)
  for x,w,label in ((120,165,'DATA'),(305,500,'ADVERSÁRIO / COMPETIÇÃO'),(830,170,'PÚBLICO'),(1015,240,'BRUTA'),(1280,240,'OPERAÇÃO'),(1540,260,'LÍQUIDA')):s.text(x,480,w,29,label,20,MUTED,0 if x<830 else 1)
  for i,row in enumerate(rows[page*4:page*4+4]):
   y=521+i*66;s.rect(100,y,1720,61,WHITE if i%2==0 else LIGHT)
   s.text(120,y+9,165,28,day(row['date']),21);s.text(120,y+35,165,22,{'applied':'Aplicada','pending':'Pendente','disabled':'Desativada'}.get(row['status'],row['status']),16,MUTED)
   picture(s,assets,'crest',row['opponent'],305,y+9,42,44);s.text(362,y+5,440,30,row['name'],22)
   picture(s,assets,'competition',row['asset'],362,y+35,23,23);s.text(393,y+35,405,23,row['competition'],17,MUTED)
   s.text(830,y+5,170,30,f"{row['attendance']:,}".replace(',','.') if row['attendance'] is not None else '—',22,MUTED,1)
   if row.get('crowd_percent') is not None:
    origin='partida' if row.get('crowd_source')=='crowd_match_applied' else 'estimado'
    s.text(810,y+35,190,22,f"{row['crowd_percent']}% · {origin}",16,MUTED,1)
   for x,w,k,color in ((1015,240,'gross',INK),(1280,240,'display_cost',art.RED),(1540,260,'display_net',art.GREEN)):money(s,x,y+5,w,31,row[k],22,color)
   s.text(1260,y+35,260,22,row['cost_note'],15,MUTED,1)
   if row['cost_estimated']:s.text(1540,y+35,260,22,'Estimativa',15,MUTED,1)
   elif row['cost_note']=='Pendente':s.text(1540,y+35,260,22,'Após custo pendente',15,MUTED,1)
  if not rows:s.text(120,565,1660,70,'Nenhuma renda de jogo em casa registrada desde a ativação.',26,MUTED)
  pager(s,'tickets',page,count,len(rows),4);result.append(pack(s,assets))
 # TV is a distinct query: home fixtures by default, away/all remain visible
 # because the existing contract also pays the club for away appearances.
 for venue,title in (('home','Casa'),('away','Fora'),('all','Todos')):
  root='tv' if venue=='home' else 'tv:'+venue
  rows=match_revenue_rows(view,'tv',venue);count=max(1,(len(rows)+4)//5)
  for page in range(count):
   key=root if page==0 else root+':'+str(page);s=shell(view,key,'receipts');assets={}
   s.text(120,302,1000,36,'DIREITOS DE TV · RECEITA POR PARTIDA',28)
   s.action(1490,300,310,40,'Contratos de TV','contracts',LIGHT,BLUE,21)
   for j,(v,label) in enumerate((('home','Casa'),('away','Fora'),('all','Todos'))):
    s.action(100+j*200,352,190,40,label,'tv' if v=='home' else 'tv:'+v,ACCENT if v==venue else LIGHT,ACCENT_TEXT if v==venue else INK,22)
   s.text(760,356,560,29,'Recebido · '+title.lower(),21,MUTED,1);money(s,1330,351,470,38,sum(r['gross'] for r in rows),27,art.GREEN)
   for x,w,label in ((120,165,'DATA'),(305,900,'ADVERSÁRIO / COMPETIÇÃO'),(1210,200,'MANDO'),(1440,360,'RECEBIDO')):s.text(x,411,w,29,label,20,MUTED,0 if x<1440 else 1)
   for i,row in enumerate(rows[page*5:page*5+5]):
    y=452+i*66;s.rect(100,y,1720,60,WHITE if i%2==0 else LIGHT)
    s.text(120,y+6,165,28,day(row['date']),21);s.text(120,y+33,165,22,{'applied':'Aplicada','pending':'Pendente','disabled':'Desativada'}.get(row['status'],row['status']),16,MUTED)
    picture(s,assets,'crest',row['opponent'],305,y+6,44,46);s.text(364,y+2,810,29,row['name'],23)
    picture(s,assets,'competition',row['asset'],364,y+31,23,23);s.text(395,y+31,782,23,row['competition'],17,MUTED)
    s.text(1210,y+15,200,30,row['venue'],22,MUTED);money(s,1440,y+12,360,36,row['gross'],26,art.GREEN)
   if not rows:s.text(120,490,1660,70,'Nenhuma receita de TV registrada para este filtro desde a ativação.',26,MUTED)
   pager(s,root,page,count,len(rows),5);result.append(pack(s,assets))
 # Sponsorship is still one financial agreement. These categories only split
 # its display value and never create contracts, sponsors or extra credits.
 entries=[e for e in view.get('entries',[]) if e['kind']=='sponsor'];entries.sort(key=lambda e:(e['date'],e['id']),reverse=True)
 total=sum(e['amount'] for e in entries if e['status']=='applied');count=max(1,(len(entries)+3)//4)
 for page in range(count):
  key='sponsors' if page==0 else 'sponsors:'+str(page);s=shell(view,key,'receipts');assets={}
  s.text(120,302,1660,36,'PATROCÍNIO · COMPOSIÇÃO DAS RECEITAS',28)
  s.text(120,347,1660,27,'Distribuição provisória do patrocínio atual · Sem patrocinadores ou contratos individuais nesta versão',19,MUTED)
  for j,(label,share,amount) in enumerate(sponsor_parts(total)):
   x=100+j*576;panel(s,assets,'sponsor'+str(j),x,393,560,114)
   picture(s,assets,'crest',view.get('club',0),x+18,410,46,50)
   s.text(x+82,406,458,29,label,22);s.text(x+82,438,138,24,str(share)+'% do total',17,MUTED);money(s,x+229,441,306,36,amount,26,art.GREEN)
  s.text(120,534,990,30,'LANÇAMENTOS DO PATROCÍNIO ÚNICO',22,MUTED);s.text(1320,534,480,30,'VALOR RECEBIDO',21,MUTED,1)
  for i,e in enumerate(entries[page*4:page*4+4]):
   y=579+i*52;s.rect(100,y,1720,47,WHITE if i%2==0 else LIGHT)
   s.text(120,y+7,215,30,day(e['date']),22);s.text(350,y+7,790,30,e.get('description','Patrocínio do clube'),22)
   s.text(1140,y+9,290,27,{'applied':'Aplicado','pending':'Pendente','disabled':'Desativado'}.get(e['status'],e['status']),20,MUTED)
   money(s,1440,y+6,360,33,e['amount'] if e['status']=='applied' else 0,24,art.GREEN)
  if not entries:s.text(120,600,1660,65,'Nenhum recebimento de patrocínio registrado desde a ativação.',25,MUTED)
  pager(s,'sponsors',page,count,len(entries),4);result.append(pack(s,assets))
 # Confirmed deals are information only, not another budget posting.
 transfers=view.get('transfers',[])
 for mode,label in (('all','Todas'),('in','Chegadas'),('out','Saídas')):
  root='transfers' if mode=='all' else 'transfers:'+mode
  rows=[r for r in transfers if mode=='all' or r['direction']==mode];count=max(1,(len(rows)+5)//6)
  for page in range(count):
   key=root if page==0 else root+':'+str(page);s=shell(view,key,'transfers');assets={}
   s.text(120,304,1660,35,'TRANSFERÊNCIAS CONFIRMADAS NA TEMPORADA',27)
   for j,(value,text) in enumerate((('all','Todas'),('in','Chegadas'),('out','Saídas'))):
    s.action(100+j*250,353,238,40,text,'transfers' if value=='all' else 'transfers:'+value,ACCENT if mode==value else LIGHT,ACCENT_TEXT if mode==value else INK,22)
   s.text(920,359,880,30,'Negócios confirmados no save · Sem novo lançamento de verba',19,MUTED,1)
   for i,row in enumerate(rows[page*6:page*6+6]):
    y=410+i*65;s.rect(100,y,1720,60,WHITE if i%2==0 else LIGHT)
    s.text(118,y+7,148,26,day(row['date']),20);s.text(118,y+33,148,23,'Empréstimo' if row['loan'] else 'Transferência',17,MUTED)
    picture(s,assets,'head',row['player'],280,y+2,60,57);s.text(354,y+13,480,36,row['name'],25)
    s.text(850,y+14,130,30,'Chegada' if row['direction']=='in' else 'Saída',21,art.RED if row['direction']=='in' else art.GREEN)
    picture(s,assets,'crest',row['other']['id'],996,y+9,40,42);s.text(1050,y+15,390,32,row['other']['name'],23)
    money(s,1455,y+12,340,36,row['fee'],25,art.RED if row['direction']=='in' else art.GREEN)
   if not rows:s.text(120,470,1650,90,'Não foi possível consultar os negócios deste save.' if view.get('transfer_error') else 'Nenhum negócio confirmado para este filtro na temporada.',26,MUTED)
   pager(s,root,page,count,len(rows),6);result.append(pack(s,assets))
 # Individual active contracts, never offered wages or departed players.
 players=view.get('players',[]);count=max(1,(len(players)+6)//7)
 for page in range(count):
  key='salaries' if page==0 else 'salaries:'+str(page);s=shell(view,key,'salaries');assets={}
  s.text(120,302,1000,36,'FOLHA DOS JOGADORES · CONTRATOS DO SAVE',27)
  if view.get('player_weekly') is not None:
   s.text(1150,307,270,30,'Total semanal',22,MUTED);money(s,1430,302,370,38,view['player_weekly'],27)
  for x,w,label in ((120,680,'JOGADOR'),(815,170,'IDADE / GER'),(1010,240,'SEMANAL'),(1265,250,'MENSAL EST.'),(1530,265,'CONTRATO ATÉ')):s.text(x,356,w,30,label,21,MUTED,0 if x==120 else 1)
  for i,p in enumerate(players[page*7:page*7+7]):
   y=395+i*54;s.rect(100,y,1720,50,WHITE if i%2==0 else LIGHT)
   picture(s,assets,'head',p['id'],116,y,50,50);s.text(182,y+3,615,28,p['name'],23)
   s.text(182,y+29,615,21,p['position']+(' · Titular' if p.get('starter')==1 else ''),17,MUTED)
   s.text(815,y+10,170,31,(str(p['age'])+' / ' if p.get('age',-1)>=0 else '— / ')+str(p['overall']),21,MUTED,1)
   for x,w,field in ((1010,240,'weekly'),(1265,250,'monthly')):
    if p[field] is None:s.text(x,y+9,w,30,'Não informado',19,MUTED,1)
    else:money(s,x,y+8,w,33,p[field],23)
   expiry=p.get('expiry');s.text(1530,y+10,265,31,str(expiry) if isinstance(expiry,int) and 1900<expiry<2200 else '—',22,MUTED,1)
  if not players:s.text(120,440,1660,75,'Aguardando os contratos dos jogadores deste clube.',26,MUTED)
  s.text(120,782,1130,27,'Mensal estimado = semanal × 52/12 · A folha mantém a cobrança nativa do FIFA.',19,MUTED)
  pager(s,'salaries',page,count,len(players),7);result.append(pack(s,assets))
 debts=view.get('debts',[]);count=max(1,(len(debts)+3)//4)
 for page in range(count):
  key='loans' if page==0 else 'loans:'+str(page);s=shell(view,key,'loans');assets={}
  s.text(120,304,1300,36,'DÍVIDAS E EMPRÉSTIMOS DO CLUBE',27);s.text(1420,306,380,30,str(sum(d['balance']>0 for d in debts))+' ativo(s)',23,BLUE,1)
  for i,d in enumerate(debts[page*4:page*4+4]):
   y=364+i*102;panel(s,assets,'debt'+str(i),100,y,1720,94)
   from loans import BANKS
   bank_id=d.get('bank_id') or next((b['id'] for b in BANKS if b['name']==d['bank']),'')
   picture(s,assets,'bank',bank_id,116,y+14,106,64)
   s.text(238,y+9,540,30,d['bank']+' · '+('Ativo' if d['balance'] else 'Quitado'),26)
   s.text(238,y+49,540,28,f"{d['paid']}/{d['total']} parcelas · {day(d['date'])}",20,MUTED)
   s.text(800,y+8,440,26,'SALDO DEVEDOR',18,MUTED);money(s,800,y+39,440,39,d['balance'],28)
   s.text(1330,y+8,465,26,'PRÓXIMA · '+(day(d['next_date']) if d['next_date'] else 'Quitado'),18,MUTED,1);money(s,1330,y+39,465,39,d['next_amount'],28)
  if not debts:s.text(120,420,1650,60,'Nenhum empréstimo contratado neste clube e carreira.',26,MUTED)
  s.text(120,788,1660,27,'Consulte parcelas e pagamentos no card Empréstimos do clube.',21,MUTED)
  pager(s,'loans',page,count,len(debts),4);result.append(pack(s,assets))
 s=shell(view,'budget','budget');assets={}
 s.text(120,304,1660,36,'ORÇAMENTO E FOLHA SALARIAL',27)
 for x,label,value in ((100,'Transferências · inicial registrado',view.get('budget_initial')),(968,'Transferências · disponível agora',view.get('budget'))):
  panel(s,assets,'budget'+str(x),x,366,852,120);s.text(x+24,380,800,33,label,26)
  if value is not None:money(s,x+24,424,800,43,value,35,BLUE,0)
  else:s.text(x+24,428,800,35,'Não informado',24,MUTED)
 for x,label,value in ((100,'Jogadores · folha semanal',view.get('player_weekly')),(968,'Salários · margem semanal disponível',view.get('wage_margin'))):
  panel(s,assets,'payroll'+str(x),x,506,852,120);s.text(x+24,522,800,33,label,26)
  if value is not None:money(s,x+24,566,800,43,value,35,BLUE,0)
  else:s.text(x+24,566,800,35,'Não informado',24,MUTED)
 s.action(100,668,852,62,'Ver extrato mensal','statement',LIGHT,BLUE,26);s.action(968,668,852,62,'Ver folha por jogador','salaries',LIGHT,BLUE,26)
 last=view.get('last_cash_change')
 if last and last.get('verified'):
  s.text(120,738,1640,30,'Última movimentação do mod · '+day(last['date'])+' · '+('+' if last['delta']>=0 else '')+__import__('career_currency').format_money(last['delta'],view.get('currency')),22,MUTED)
 s.text(120,784,1640,49,'O saldo do FIFA já contém as operações nativas e as movimentações confirmadas do mod. As consultas não reaplicam valores.',23,MUTED)
 result.append(pack(s,assets));return result
