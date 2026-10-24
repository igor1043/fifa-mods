"""One FIFA-style display model shared by the native APT and review preview."""
from math import ceil
import re

INK='#334b56';BLUE='#0063b1';MUTED='#6b818d';PAPER='#f4f6f7';LIGHT='#e6ebed';WHITE='#ffffff'
TABS=(('overview','Resumo'),('leagues','Ligas'),('clubs','Clubes'),('deals','Negócios'),('mine','Minha liga'))
def money(n):return f'{int(n or 0):,}'.replace(',','.')
def compact(n):return (f'{n/1_000_000:.1f}'.replace('.',',')+' mi') if abs(n)>=1_000_000 else money(n)
def day(value):return '/'.join(str(value)[:10].split('-')[::-1]) if value else 'Não informado'
def league_name(value):return re.sub(r'\s*\(\d+\)$','',str(value or 'Liga não identificada')).strip()

class Scene:
    def __init__(self,key,title):self.key=key;self.title=title;self.nodes=[];self.actions=[]
    def rect(self,x,y,w,h,color=WHITE):self.nodes.append(dict(type='rect',x=x,y=y,w=w,h=h,color=color))
    def text(self,x,y,w,h,value,size=24,color=INK,align=0,bold=False):
        self.nodes.append(dict(type='text',x=x,y=y,w=w,h=h,text=str(value),size=size,color=color,align=align,bold=bold))
    def image(self,key,x,y,w,h):self.nodes.append(dict(type='image',asset=key,x=x,y=y,w=w,h=h))
    def action(self,x,y,w,h,label,target,fill=LIGHT,ink=INK,size=23):
        index=len(self.actions);self.actions.append(dict(x=x,y=y,w=w,h=h,label=label,target=target))
        self.nodes.append(dict(type='action',x=x,y=y,w=w,h=h,text=label,target=target,color=fill,ink=ink,size=size,index=index))
    def pack(self):
        result=dict(key=self.key,title=self.title,nodes=self.nodes,actions=self.actions)
        if hasattr(self,'pagination'):result['pagination']=self.pagination
        return result

def shell(data,key,tab,title=None):
    s=Scene(key,title or 'Mercado de Transferências');s.rect(0,0,1920,1080,'#034067')
    s.rect(60,90,1800,828,PAPER);s.image('crest_'+str(data['clubId']),96,112,66,70)
    s.text(184,112,1510,54,'MERCADO DE TRANSFERÊNCIAS',40,bold=True)
    s.text(186,174,1220,34,data['clubName']+'  ·  '+day(data['careerDate'])+'  ·  Temporada '+str(data['careerDate'])[:4],25)
    for i,(target,label) in enumerate(TABS):
        s.action(96+i*346,224,338,47,label,target,BLUE if tab==target else '#dbe2e5',WHITE if tab==target else INK,25)
    s.text(96,936,1300,30,'↵ Selecionar     Esc Voltar     ← → Navegar',23,WHITE)
    s.text(96,976,1728,28,'PRÉVIA · Dados do save gravado · Nenhuma alteração no jogo ou na carreira',18,'#c6d7e0')
    return s

def kpis(s,items,y=292):
    width=(1728-14*(len(items)-1))/len(items)
    for i,(title,value,note) in enumerate(items):
        x=96+i*(width+14);s.rect(x,y,width,90,WHITE);s.rect(x,y,5,90,BLUE)
        s.text(x+18,y+9,width-32,23,title,18,MUTED,bold=True)
        s.text(x+18,y+32,width-32,36,value,30,BLUE,bold=True)
        s.text(x+18,y+69,width-32,19,note,15,MUTED)

def club_rank(s,rows,x,y,w,heading,kind='purchases'):
    s.rect(x,y,w,198,WHITE);s.text(x+15,y+10,w-30,30,heading,25,bold=True)
    if not rows:s.text(x+18,y+74,w-36,30,'Nenhum negócio confirmado.',22,MUTED);return
    ordered=sorted(rows,key=lambda r:r.get(kind,0),reverse=True)[:5]
    for i,r in enumerate(ordered):
        yy=y+48+i*28;s.text(x+14,yy,30,26,str(i+1),21,MUTED)
        s.image('crest_'+str(r['id']),x+49,yy-1,27,27)
        s.text(x+89,yy,w-320,26,r['name'],21)
        s.text(x+w-218,yy,60,26,str(r.get(kind,0)),21,align=1)
        s.text(x+w-146,yy,126,26,compact(r.get('revenue' if kind=='sales' else 'investment',0)),21,BLUE,1)

def deals(s,rows,top=352,limit=5):
    for i,item in enumerate(rows[:limit]):
        y=top+i*91;s.rect(96,y,1728,84,WHITE if i%2==0 else '#e9eef0')
        s.text(114,y+14,168,28,day(item['date']),23)
        s.text(114,y+45,168,24,'Empréstimo' if item['loan'] else 'Compra',18,MUTED)
        s.image('head_'+str(item['playerId']),294,y+9,64,64)
        s.text(376,y+12,352,30,item['playerName'],24,bold=True)
        s.text(376,y+47,352,24,f"{item['position']} · GER {item['overall']} · POT {item['potential']}",19,MUTED)
        for prefix,x in (('from',748),('to',1162)):
            team=item[prefix];s.image('crest_'+str(team['id']),x,y+20,43,43)
            s.text(x+54,y+14,294,28,team['name'],22)
            s.text(x+54,y+47,294,23,league_name(team['leagueName']),17,MUTED)
        s.text(1104,y+25,43,35,'→',29,BLUE)
        s.text(1530,y+13,270,36,money(item['fee']),28,BLUE,1,bold=True)
        s.text(1530,y+51,270,22,'Taxa do empréstimo' if item['loan'] else 'Valor da transferência',17,MUTED,1)
    if not rows:
        height=limit*91-7;s.rect(96,top,1728,height,WHITE)
        middle=top+max(20,(height-98)/2)
        s.text(240,middle,1440,43,'Nenhum negócio concluído nesta carreira.',30,align=2)
        s.text(240,middle+53,1440,38,'Compras e empréstimos aparecem após a conclusão da negociação.',22,MUTED,2)

def entry(data):
    s=shell(data,'entry','overview','Card no carrossel de olheiros')
    s.text(96,293,1700,39,'CARROSSEL DE OLHEIROS',30,bold=True)
    s.rect(96,350,846,418,WHITE);s.rect(96,350,846,11,BLUE)
    s.text(122,388,780,52,'MERCADO DE TRANSFERÊNCIAS',37,bold=True)
    s.text(122,449,760,40,'Compras, vendas e empréstimos da carreira',27)
    for i,(label,value) in enumerate((('NEGÓCIOS',str(data['summary']['completedDeals'])),('INVESTIMENTO',compact(data['summary']['investment'])),('LIGAS',str(len(data['leagues']))))):
        x=126+i*262;s.text(x,549,245,30,label,19,MUTED);s.text(x,590,245,57,value,38,BLUE,bold=True)
    s.action(120,686,794,56,'Entrar no Mercado de Transferências','overview',BLUE,WHITE,26)
    s.rect(964,350,418,418,'#e4e9eb');s.text(990,390,360,50,'BUSCAR JOGADORES',30,bold=True)
    s.text(990,457,360,64,'Encontre reforços para o clube',23,MUTED)
    s.rect(1404,350,420,418,'#e4e9eb');s.text(1430,390,360,50,'NEGOCIAÇÕES',30,bold=True)
    s.text(1430,457,360,64,'Acompanhe suas propostas',23,MUTED)
    s.text(106,807,1700,34,'Explore as movimentações de jogadores, clubes e ligas da sua carreira.',25,MUTED)
    return s

def make_scenes(data):
    result=[entry(data)];summary=data['summary'];rows=data['transfers']
    s=shell(data,'overview','overview')
    kpis(s,[('VALOR INVESTIDO',compact(summary['investment']),'Compras permanentes'),('VOLUME DO MERCADO',compact(summary['feeVolume']),'Inclui taxas de empréstimos'),('COMPRAS CONCLUÍDAS',str(summary['purchases']),'Confirmadas na carreira'),('EMPRÉSTIMOS',str(summary['loans']),'Negócios de jogadores'),('NEGÓCIOS CONFIRMADOS',str(summary['completedDeals']),str(summary['buyers'])+' clubes compradores')])
    window=data['window'];period=window.get('current') or window.get('next')
    s.rect(96,398,1728,64,'#e0e8ec')
    if period:
        opened=bool(window.get('current'));status=('Fecha em '+str(period['daysRemaining'])+' dias') if opened else ('Abre em '+str(period['daysUntilOpen'])+' dias')
        s.text(116,407,650,29,'JANELA DE TRANSFERÊNCIAS '+('ABERTA' if opened else 'FECHADA'),25,BLUE,bold=True)
        s.text(116,437,960,22,day(period['startDate'])+' a '+day(period['endDate'])+' · '+str(period['durationDays'])+' dias de duração',19)
        s.text(1320,415,475,33,status,26,BLUE,1)
    else:s.text(118,413,1660,32,'Período da janela não informado neste save.',25,MUTED)
    s.rect(96,480,846,198,WHITE);s.text(111,490,640,30,'LIGAS QUE MAIS INVESTIRAM',25,bold=True)
    s.action(758,488,168,30,'Ver ligas','leagues',LIGHT,INK,19)
    maximum=max((r['investment'] for r in data['leagues']),default=1) or 1
    for i,row in enumerate(data['leagues'][:5]):
        yy=528+i*28;s.image('league_'+str(row['id']),111,yy-2,26,26)
        s.text(150,yy,390,26,league_name(row['name']),21)
        s.rect(552,yy+10,210,8,LIGHT);s.rect(552,yy+10,max(2,210*row['investment']/maximum),8,BLUE)
        s.text(775,yy,146,26,compact(row['investment']),21,BLUE,1)
    if not data['leagues']:s.text(116,557,790,33,'Sem compras confirmadas por liga.',23,MUTED)
    club_rank(s,data['buyers'],978,480,846,'CLUBES QUE MAIS CONTRATARAM')
    s.text(96,694,1240,33,'ÚLTIMOS NEGÓCIOS',28,bold=True)
    s.action(1510,689,314,37,'Ver todos ('+str(len(rows))+')','deals',LIGHT,INK,22)
    deals(s,rows,736,2);result.append(s)
    # League rankings keep long careers paged instead of squeezing rows.
    for page in range(max(1,ceil(len(data['leagues'])/7))):
        key='leagues' if not page else 'leagues:'+str(page)
        s=shell(data,key,'leagues');s.text(96,294,1450,38,'INVESTIMENTO POR LIGA',30,bold=True)
        s.rect(96,342,1728,42,'#d4dfe4')
        for x,w,label in ((114,740,'LIGA'),(890,180,'COMPRAS'),(1090,220,'EMPRÉSTIMOS'),(1350,450,'INVESTIMENTO')):s.text(x,350,w,29,label,21)
        for i,row in enumerate(data['leagues'][page*7:page*7+7]):
            y=390+i*61;s.rect(96,y,1728,55,WHITE if i%2==0 else '#e7edef')
            s.action(96,y,1728,55,'','league:'+str(row['id']),fill='#f8fafb')
            s.text(114,y+12,40,31,str(page*7+i+1),24,MUTED);s.image('league_'+str(row['id']),170,y+7,40,40)
            s.text(231,y+12,620,32,league_name(row['name']),25)
            s.text(890,y+12,180,32,row['purchases'],25);s.text(1090,y+12,220,32,row['loans'],25)
            s.text(1350,y+10,450,35,money(row['investment']),28,BLUE,1,bold=True)
        if not data['leagues']:s.text(200,470,1500,45,'Nenhuma compra concluída para classificar.',30,MUTED,2)
        pagination(s,page,max(1,ceil(len(data['leagues'])/7)),'leagues',len(data['leagues']),'ligas');result.append(s)
    s=shell(data,'clubs','clubs');s.text(96,295,1500,38,'DESTAQUES DO MERCADO · TOP 5',30,bold=True)
    for x,title,source,kind in ((96,'QUEM MAIS GASTOU',data['buyers'],'investment'),(682,'QUEM MAIS COMPROU',data['buyers'],'purchases'),(1268,'QUEM MAIS VENDEU',data['sellers'],'sales')):
        s.rect(x,352,556,460,WHITE);s.text(x+18,367,520,36,title,27,BLUE,bold=True)
        selected=sorted((r for r in source if r.get('sales' if kind=='sales' else 'purchases',0)>0),key=lambda r:r.get(kind,0),reverse=True)[:5]
        for i,r in enumerate(selected):
            y=423+i*74;s.image('crest_'+str(r['id']),x+16,y+4,45,45)
            s.text(x+77,y,450,30,r['name'],24,bold=True)
            s.text(x+77,y+35,450,25,str(r.get('sales' if kind=='sales' else 'purchases',0))+' negócios · '+money(r.get('revenue' if kind=='sales' else 'investment',0)),21,MUTED)
    result.append(s)
    append_deal_pages(result,data,rows,'deals','NEGÓCIOS CONCLUÍDOS','deals')
    for league in data['leagues']:
        subset=[r for r in rows if r['from']['leagueId']==league['id'] or r['to']['leagueId']==league['id']]
        append_deal_pages(result,data,subset,'league:'+str(league['id']),'NEGÓCIOS · '+league_name(league['name']),'leagues',back='leagues')
    mine=data['myLeague'];s=shell(data,'mine','mine');s.text(96,294,1650,40,'MINHA LIGA · '+league_name(mine['name']),30,bold=True)
    ms=mine['summary'];kpis(s,[('INVESTIMENTO',compact(ms['investment']),str(ms['purchases'])+' compras'),('ARRECADAÇÃO',compact(ms['revenue']),str(ms['sales'])+' vendas'),('SALDO LÍQUIDO',compact(ms['netSpend']),'Compras menos vendas'),('NEGÓCIOS NA LIGA',str(ms['deals']),'Entradas e saídas')],350)
    club_rank(s,mine['clubs'],96,468,846,'MAIORES COMPRADORES DA LIGA','purchases');club_rank(s,mine['clubs'],978,468,846,'MAIORES VENDEDORES DA LIGA','sales')
    s.text(96,695,1500,32,'ÚLTIMAS MOVIMENTAÇÕES DA LIGA',28,bold=True);deals(s,mine['transfers'],735,2);result.append(s)
    packed=[s.pack() for s in result]
    keys={s['key'] for s in packed}
    assert len(keys)==len(packed)
    for scene in packed:
        scene['back']='entry' if scene['key']=='overview' else 'leagues' if scene['key'].startswith('league:') else 'overview'
        for a in scene['actions']:assert a['target'] in keys or a['target']=='refresh',a
    return packed

def pagination(s,page,count,prefix,total,unit):
    previous=(page-1)%count;following=(page+1)%count
    s.pagination=dict(index=page,count=count,previous=prefix if previous==0 else prefix+':'+str(previous),next=prefix if following==0 else prefix+':'+str(following))
    if count>1:
        s.action(96,854,68,42,'‹',s.pagination['previous'],size=28)
        s.action(172,854,68,42,'›',s.pagination['next'],size=28)
        # Keep large careers compact while still indicating the current page.
        first=max(0,min(page-3,count-7));last=min(count,first+7)
        for i in range(first,last):
            s.nodes.append(dict(type='dot',x=270+(i-first)*27,y=870,w=12,h=12,color=BLUE if i==page else '#a8b6bd'))
    s.text(1080,859,744,32,f'Página {page+1} de {count} · {total} {unit}',22,MUTED,1)

def append_deal_pages(result,data,rows,prefix,title,tab,back=None):
    count=max(1,ceil(len(rows)/5))
    for page in range(count):
        key=prefix if not page else prefix+':'+str(page)
        s=shell(data,key,tab);s.text(96,295,1580,40,title,30,bold=True)
        deals(s,rows[page*5:page*5+5],350,5)
        pagination(s,page,count,prefix,len(rows),'negócios')
        if back:s.action(560,854,255,42,'Voltar às ligas',back)
        result.append(s)
