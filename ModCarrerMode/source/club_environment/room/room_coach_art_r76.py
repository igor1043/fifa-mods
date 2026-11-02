"""Sharp native atlas: tactics, actual career evidence and planning surfaces."""
import io,math
from PIL import Image,ImageDraw
from room_interior_r71 import font, palette

W,H=2048,1024
TEXT=(26,44,54);MUTED=(94,115,124);BG=(238,242,243);GREEN=(37,142,106)


def paint(context,read_asset):
    c=context.get('coach',{});primary,secondary=palette(context['colors'])
    def light(color):return sum(a*b for a,b in zip(color,(.2126,.7152,.0722)))>145
    ink=(20,26,29) if light(primary) else (255,255,255)
    pages=[]
    def new(title,subtitle):
        im=Image.new('RGBA',(W,H),BG+(255,));d=ImageDraw.Draw(im)
        d.rectangle((0,0,W,132),fill=primary);d.text((55,30),title,font=font(64),fill=ink)
        d.text((58,158),subtitle,font=font(30),fill=MUTED);pages.append(im);return im,d
    def text(d,xy,value,size=35,color=TEXT):d.text(xy,str(value),font=font(size),fill=color)
    def fit(d,xy,label,width,size=36,color=TEXT):
        f=font(size)
        while d.textlength(str(label),font=f)>width and f.size>18:f=font(f.size-1)
        d.text(xy,str(label),font=f,fill=color)
    def head(im,p,box):
        try:
            image=Image.open(io.BytesIO(read_asset(f'data/ui/imgassets/heads/p{p["id"]}.dds'))).convert('RGBA')
            image.thumbnail((box[2],box[3]),Image.Resampling.LANCZOS);im.alpha_composite(image,(box[0],box[1]))
        except (OSError,ValueError,FileNotFoundError):
            d=ImageDraw.Draw(im);x,y,w,h=box;d.ellipse((x+w*.32,y,x+w*.68,y+h*.38),fill=(151,166,174));d.rounded_rectangle((x+w*.15,y+h*.4,x+w*.85,y+h),radius=15,fill=(151,166,174))
    date=str(context['date']);date=f'{date[6:8]}/{date[4:6]}/{date[:4]}'
    im,d=new('QUADRO TÁTICO',context['club_name']+' · '+context.get('user',{}).get('formation','')+' · '+date)
    x0,y0,x1,y1=80,240,1968,940;d.rectangle((x0,y0,x1,y1),fill=(37,88,66),outline='white',width=5)
    d.line((1024,y0,1024,y1),fill='white',width=4);d.ellipse((894,460,1154,720),outline='white',width=4)
    for x in (x0,x1-250):d.rectangle((x,390,x+250,790),outline='white',width=4)
    for p in context.get('user',{}).get('players',[]):
        x=x0+80+max(0,min(1,p['y']))*(x1-x0-160);y=y0+70+max(0,min(1,p['x']))*(y1-y0-140)
        d.ellipse((x-30,y-30,x+30,y+30),fill=secondary,outline=primary,width=6)
        d.text((x,y),str(p.get('number',0)),font=font(31),fill=TEXT if light(secondary) else (255,255,255),anchor='mm')
        fit(d,(x-90,y+35),p.get('name','')[:22],180,23,(255,255,255))

    im,d=new('ANÁLISE DE DESEMPENHO','Partidas e campanhas da carreira · '+date)
    stats=c.get('stats',{});games=stats.get('games',0)
    for i,(label,value) in enumerate([('JOGOS',games),('VITÓRIAS',stats.get('wins',0)),('PONTOS',stats.get('points',0)),('APROVEITAMENTO',f"{stats.get('percentage',0):.1f}%")]):
        x=60+i*495;d.rounded_rectangle((x,230,x+460,420),radius=16,fill='white');text(d,(x+25,250),label,29,MUTED);text(d,(x+25,300),value,70)
    recent=c.get('recent',[])
    text(d,(65,460),'ÚLTIMOS PLACARES REGISTRADOS',31)
    if recent:
        scale=max(3,max(max(m['gf'],m['ga']) for m in recent));points=[[],[]]
        for i,m in enumerate(recent):
            x=130+i*1750/max(1,len(recent)-1)
            for line,key in zip(points,('gf','ga')):line.append((x,770-m[key]*230/scale))
            text(d,(x-35,790),f"{m['gf']}–{m['ga']}",30)
        for line,color in zip(points,(GREEN,(193,65,76))):
            if len(line)>1:d.line(line,fill=color,width=7)
            for x,y in line:d.ellipse((x-8,y-8,x+8,y+8),fill=color)
    else:text(d,(75,615),'Sem placares individuais disponíveis nesta carreira.',36,MUTED)
    for i,key in enumerate(('home','away')):
        own=stats.get(key,{});p=own.get('percentage',0);x=70+i*1000
        text(d,(x,885),('CASA' if key=='home' else 'FORA')+f"  {p:.1f}% · {own.get('games',0)} jogos",31)
        d.rectangle((x,950,x+900,968),fill=(205,215,220));d.rectangle((x,950,x+900*min(100,p)/100,968),fill=GREEN)

    im,d=new('CLASSIFICAÇÃO DA LIGA',c.get('leagueName','Liga da carreira')+' · '+date)
    table=c.get('table',[]);own=next((i for i,r in enumerate(table) if r['club']==context['club']),0);start=max(0,min(own-3,len(table)-8));visible=table[start:start+8]
    for x,label in [(55,'#'),(145,'CLUBE'),(1110,'J'),(1270,'V'),(1420,'E'),(1570,'D'),(1710,'SG'),(1880,'PTS')]:text(d,(x,224),label,30,MUTED)
    for i,r in enumerate(visible):
        y=295+i*80;d.rectangle((40,y-5,2008,y+69),fill=primary if r['club']==context['club'] else (255,255,255));color=ink if r['club']==context['club'] else TEXT
        text(d,(55,y),r['rank'],36,color);fit(d,(145,y),r['name'],900,36,color)
        for x,val in [(1110,r['played']),(1270,r['wins']),(1420,r['draws']),(1570,r['losses']),(1710,r['gf']-r['ga']),(1880,r['points'])]:text(d,(x,y),val,36,color)
    if not visible:text(d,(70,470),'A classificação será exibida quando houver dados da carreira.',38,MUTED)

    im,d=new('ELENCO · DESTAQUES','Indicadores reais disponíveis · '+context['club_name'])
    squad=c.get('squad',[]);rated=[p for p in squad if p.get('rating') is not None]
    cards=[]
    for title,pool,key,display in [('ARTILHEIRO',squad,'goals',lambda p:str(p['goals'])+' gols'),('ASSISTÊNCIAS',squad,'assists',lambda p:str(p['assists'])+' assist.'),('MELHOR MÉDIA',rated,'rating',lambda p:f"{p['rating']:.1f}"),('MAIOR GERAL',squad,'overall',lambda p:str(p['overall']))]:
        p=max(pool,key=lambda p:(p.get(key,0),p.get('games',0)),default=None)
        if p and (p.get(key,0) or key=='overall'):cards.append((title,p,display(p)))
    for i,(title,p,value) in enumerate(cards):
        x=60+(i%2)*1000;y=240+(i//2)*360;d.rounded_rectangle((x,y,x+940,y+320),radius=20,fill='white');head(im,p,(x+22,y+74,210,220));text(d,(x+260,y+30),title,29,MUTED);fit(d,(x+260,y+100),p['name'],650,42);text(d,(x+260,y+180),value,61)
    if not cards:text(d,(70,460),'Aguardando os primeiros indicadores do elenco.',40,MUTED)

    im,d=new('MERCADO · PLANEJAMENTO DO ELENCO','Composição atual e contratos · Análise de apoio, sem negociações simuladas')
    for i,row in enumerate(c.get('coverage',[])):
        y=250+i*106;text(d,(70,y),row['name'],38);text(d,(580,y),f"{row['count']} atletas",34);text(d,(920,y),f"GER {row['overall']:.1f}",34)
        d.rectangle((1210,y+10,1940,y+34),fill=(204,213,218));d.rectangle((1210,y+10,1210+730*min(row['count'],12)/12,y+34),fill=GREEN)
    text(d,(70,720),'VÍNCULOS A ACOMPANHAR',34)
    contracts=c.get('contracts',[])[:4]
    if contracts:
        for i,p in enumerate(contracts):fit(d,(70+(i%2)*1000,790+(i//2)*78),p['name']+' · até '+str(p['contract']),920,33)
    else:text(d,(70,815),'Nenhum contrato próximo do fim identificado no elenco.',33,MUTED)

    im,d=new('GESTÃO ESPORTIVA','Elenco e evolução · '+date)
    for i,p in enumerate(sorted(squad,key=lambda p:(-p.get('overall',0),p['id']))[:7]):
        y=230+i*95;fit(d,(65,y),p['name'],780,36);text(d,(850,y),f"GER {p.get('overall',0)}",34);text(d,(1110,y),f"POT {p.get('potential',0)}",34)
        growth=max(0,p.get('potential',0)-p.get('overall',0));d.rectangle((1440,y+10,1950,y+38),fill=(205,215,220));d.rectangle((1440,y+10,1440+510*min(growth,20)/20,y+38),fill=GREEN)

    im,d=new('ANÁLISE DO PRÓXIMO ADVERSÁRIO',context.get('opponent',{}).get('name','Próxima partida'))
    text(d,(70,250),'FORMAÇÃO PROVÁVEL',36,MUTED);text(d,(70,320),context.get('opponent',{}).get('formation','—'),100)
    for i,(key,value) in enumerate(context.get('opponent_tactics',{}).items()):
        text(d,(850,240+i*115),key,38);text(d,(1510,240+i*115),value,48)
    text(d,(70,850),'Escalação provável e parâmetros registrados na carreira.',32,MUTED)

    im,d=new('PLANEJAMENTO · COMISSÃO TÉCNICA','Prancheta de trabalho · '+context['club_name'])
    for i,label in enumerate(['Análise do adversário','Organização defensiva','Transição e construção','Bolas paradas','Controle de carga e recuperação']):
        y=270+i*130;d.rectangle((75,y,120,y+45),outline=MUTED,width=4);text(d,(160,y-3),label,43);d.line((160,y+80,1940,y+80),fill=(182,196,203),width=2)

    # Share unused page space with the physical decor. These are real club
    # assets, not extra permanent textures/material groups in the scene.
    from room_interior_r71 import make_mural
    from room_coach_decor_r76 import SWATCHES
    decor=Image.new('RGBA',(W,H),primary+(255,));decor.paste(pages[6].resize((1024,512),Image.Resampling.LANCZOS),(0,0))
    d=ImageDraw.Draw(decor);d.rectangle((0,512,511,1023),fill=(235,235,231))
    try:
        kit=Image.open(io.BytesIO(read_asset(f'data/ui/imgassets/kits/j0_{context["club"]}_0.dds'))).convert('RGBA');kit.thumbnail((470,470),Image.Resampling.LANCZOS)
        decor.alpha_composite(kit,((512-kit.width)//2,512+(512-kit.height)//2))
    except (OSError,ValueError,FileNotFoundError):
        d.polygon([(130,620),(190,575),(320,575),(380,620),(350,700),(315,680),(315,950),(195,950),(195,680),(155,700)],fill=primary)
        d.rectangle((195,720,315,760),fill=secondary)
    # Plain analog clock, without decorative illumination.
    cx,cy=768,768;d.ellipse((cx-238,cy-238,cx+238,cy+238),fill=(237,238,231),outline=(93,103,109),width=12)
    for tick in range(60):
        angle=tick*math.tau/60;outer=219;inner=192 if tick%5==0 else 208
        d.line((cx+math.sin(angle)*inner,cy-math.cos(angle)*inner,cx+math.sin(angle)*outer,cy-math.cos(angle)*outer),fill=TEXT,width=7 if tick%5==0 else 3)
    for hour in (12,3,6,9):
        a=hour*math.tau/12;d.text((cx+math.sin(a)*163,cy-math.cos(a)*163),str(hour),font=font(46),anchor='mm',fill=TEXT)
    for angle,length,width in ((-math.pi/3,122,17),(math.pi/3,174,12)):
        d.line((cx,cy,cx+math.sin(angle)*length,cy-math.cos(angle)*length),fill=TEXT,width=width)
    d.ellipse((cx-13,cy-13,cx+13,cy+13),fill=primary)
    mural=make_mural(context,None).resize((1024,341),Image.Resampling.LANCZOS);decor.paste(mural,(1024,512));pages[6]=decor
    swatch=ImageDraw.Draw(pages[7])
    for i,rgb in enumerate(SWATCHES):swatch.rectangle((i*128,960,(i+1)*128-1,1023),fill=rgb+(255,))
    atlas=Image.new('RGBA',(4096,4096))
    for i,page in enumerate(pages):atlas.paste(page,((i%2)*W,(i//2)*H))
    return atlas
