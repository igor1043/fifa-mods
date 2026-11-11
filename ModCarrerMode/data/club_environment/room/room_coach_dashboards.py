"""Office monitor artwork from validated career data; no simulation or save writes."""
import io,json
from PIL import Image,ImageDraw,ImageOps
from room_interior_r71 import font,palette

W,H=2048,1024
TEXT=(30,44,53);MUTED=(105,120,129);DARK=(24,32,39);PAPER=(238,241,242);LINE=(218,225,229)
TITLES=('QUADRO TÁTICO','ANÁLISE DE DESEMPENHO','CLASSIFICAÇÃO DA LIGA','DESTAQUES DO ELENCO',
        'JOGADORES OBSERVADOS','REDE DE OLHEIROS')


def label(d,xy,value,size=32,color=TEXT,width=None):
    value=str(value);f=font(size)
    if width:
        while d.textlength(value,font=f)>width and f.size>24:f=font(f.size-1)
        while d.textlength(value,font=f)>width and len(value)>1:value=value[:-2].rstrip()+'…'
    d.text(xy,value,font=f,fill=color)


def date(value):
    s=str(value)
    return s[6:8]+'/'+s[4:6]+'/'+s[:4] if len(s)==8 else '—'


def image(im,read_asset,path,box):
    try:
        art=Image.open(io.BytesIO(read_asset(path))).convert('RGBA')
        art.thumbnail((box[2],box[3]),Image.Resampling.LANCZOS)
        im.alpha_composite(art,(round(box[0]+(box[2]-art.width)/2),round(box[1]+(box[3]-art.height)/2)))
        return True
    except (OSError,ValueError,FileNotFoundError):return False


def card(d,box):d.rounded_rectangle(box,radius=18,fill='white',outline=LINE,width=2)


def television(context,read_asset):
    im=Image.new('RGBA',(W,H),DARK+(255,));d=ImageDraw.Draw(im)
    label(d,(80,65),'PRÓXIMA PARTIDA',62,(245,248,250))
    label(d,(83,151),context.get('league_name',''),35,(181,195,203),width=1850)
    fixture=context.get('fixture',[]);user=context.get('user',{});opponent=context.get('opponent',{})
    if len(fixture)>4 and fixture[0]>0:
        when=date(fixture[3]);time=f'{fixture[4]//100:02d}:{fixture[4]%100:02d}'
        label(d,(790,260),when+' · '+time,38,(211,222,228),width=1100)
    else:label(d,(790,260),'Próxima partida a definir',38,(211,222,228),width=1100)
    for x,ident,name,formation in ((240,context['club'],context['club_name'],user.get('formation','')),
                                  (1450,opponent.get('team_id',0),opponent.get('name') or 'A definir',opponent.get('formation',''))):
        if ident:image(im,read_asset,f'data/ui/imgassets/crest/light/l{ident}.dds',(x,310,350,350))
        label(d,(x-100,710),name,52,(245,248,250),width=565)
        label(d,(x,800),formation,38,(181,195,203),width=450)
    d.text((1024,535),'×',font=font(150),fill=(238,242,243),anchor='mm')
    d.line((80,920,1968,920),fill=(76,94,105),width=3)
    label(d,(80,954),'PREPARAÇÃO TÁTICA · COMISSÃO TÉCNICA',28,(181,195,203))
    return im


def observed(context,read_asset,accent):
    c=context.get('coach',{}).get('scouting',{});reports=c.get('reports',[])
    im=Image.new('RGBA',(W,H),PAPER+(255,));d=ImageDraw.Draw(im)
    label(d,(62,158),'Relatórios da rede global · '+context['club_name'],30,MUTED,width=1850)
    for i,(name,value) in enumerate((('EM OBSERVAÇÃO',len(reports)),('CLUBES',len({r['club'] for r in reports if r['club']})),('MOSTRANDO',min(4,len(reports))))):
        x=60+i*665;card(d,(x,220,x+640,348));label(d,(x+25,238),name,26,MUTED);label(d,(x+25,276),value,51)
    for i,p in enumerate(reports[:4]):
        x=60+(i%2)*1000;y=384+(i//2)*270;card(d,(x,y,x+960,y+246))
        d.rounded_rectangle((x+18,y+18,x+208,y+228),radius=14,fill=(229,235,238))
        if not image(im,read_asset,f'data/ui/imgassets/heads/p{p["id"]}.dds',(x+21,y+27,184,197)):
            d.ellipse((x+75,y+53,x+150,y+128),fill=(155,170,180));d.rounded_rectangle((x+48,y+139,x+178,y+225),radius=24,fill=(155,170,180))
        image(im,read_asset,f'data/ui/imgassets/crest/light/l{p["club"]}.dds',(x+843,y+26,83,83))
        label(d,(x+240,y+27),p['name'],42,width=580)
        label(d,(x+241,y+87),p['club_name'],30,MUTED,width=670)
        nation=p.get('nationality',{})
        image(im,read_asset,f'data/ui/imgAssets/flags512x512/f_{nation.get("id",0)}.dds',(x+238,y+143,48,37))
        label(d,(x+303,y+141),nation.get('name',''),27,MUTED,width=560)
        label(d,(x+241,y+192),'Registro · '+date(p.get('date')),25,MUTED)
        d.rectangle((x+18,y+224,x+208,y+229),fill=accent)
    if not reports:
        card(d,(60,395,1980,888))
        label(d,(125,520),'Nenhum jogador observado registrado.' if c.get('recognized') else 'Relatórios indisponíveis para este formato de carreira.',44,width=1740)
        label(d,(125,610),'Adicione jogadores à lista de observação no FIFA.',31,MUTED)
    return im


def network(context,read_asset,accent):
    c=context.get('coach',{}).get('scouting',{});scouts=c.get('scouts',[]);assigned=[s for s in scouts if s.get('country',{}).get('id',0)>0]
    country_order={ident:i+1 for i,ident in enumerate(dict.fromkeys(s['country']['id'] for s in assigned))}
    im=Image.new('RGBA',(W,H),PAPER+(255,));d=ImageDraw.Draw(im)
    label(d,(62,158),'Destinos registrados da rede global · '+context['club_name'],30,MUTED,width=1850)
    for i,(title,value) in enumerate((('OLHEIROS CONTRATADOS',len(scouts)),('DESTINOS ATUAIS',len({s['country']['id'] for s in assigned})),('MISSÕES DA BASE',len(c.get('youth',[]))))):
        x=60+i*665;card(d,(x,220,x+640,348));label(d,(x+25,238),title,26,MUTED);label(d,(x+25,276),value,51)
    card(d,(60,383,1195,947));card(d,(1225,383,1980,947))
    label(d,(88,401),'DISTRIBUIÇÃO DA REDE',26,MUTED)
    try:
        earth=Image.open(io.BytesIO(read_asset('ModCarrerMode/data/club_browser/assets/globe/earth.png'))).convert('L')
        earth=ImageOps.colorize(earth,(191,203,207),(240,244,244)).resize((1080,470),Image.Resampling.LANCZOS)
        im.paste(earth,(87,455));geo=json.loads(read_asset('ModCarrerMode/data/club_browser/world_geography.json'))
        used=set();pins=[]
        for s in assigned:
            country=s['country'];g=geo.get(country.get('iso'))
            if not g or country['id'] in used:continue
            used.add(country['id']);x=87+(g['lon']+180)/360*1080;y=455+(90-g['lat'])/180*470
            px,py=x,y
            while any((px-a)**2+(py-b)**2<42**2 for a,b in pins):py-=43
            py=max(475,py);pins.append((px,py))
            if abs(py-y)>1:d.line((x,y,px,py),fill=accent,width=2)
            d.ellipse((px-18,py-18,px+18,py+18),fill='white',outline=accent,width=3)
            d.text((px,py),str(country_order[country['id']]),font=font(24),fill=TEXT,anchor='mm')
    except (OSError,ValueError,KeyError,FileNotFoundError):
        label(d,(115,590),'Rede de observação do clube',39,width=1000)
    for i,s in enumerate(scouts[:5]):
        y=403+i*102
        if i:d.line((1250,y-8,1955,y-8),fill=LINE,width=2)
        country=s.get('country',{})
        if country.get('id'):image(im,read_asset,f'data/ui/imgAssets/flags512x512/f_{country["id"]}.dds',(1253,y+8,65,45))
        label(d,(1340,y+2),s['name'],29,width=595)
        destination=f"{country_order[country['id']]:02d} · {country['name']}" if country.get('id') else 'Sem destino registrado'
        label(d,(1340,y+43),destination,28,MUTED,width=595)
    if not scouts:
        label(d,(1260,500),'Nenhum olheiro contratado.' if c.get('recognized') else 'Rede indisponível.',36,width=665)
        label(d,(1260,568),'Contrate e envie olheiros pelo FIFA.',27,MUTED,width=665)
    return im


def enhance(context,pages,read_asset):
    primary,_=palette(context['colors']);accent=primary if max(primary)-min(primary)>25 and min(primary)<190 else (159,130,74)
    pages[4]=observed(context,read_asset,accent);pages[5]=network(context,read_asset,accent)
    pages[6]=television(context,read_asset)
    for i,im in enumerate(pages[:6]):
        d=ImageDraw.Draw(im);d.rectangle((0,0,W,132),fill=DARK)
        d.rectangle((0,0,12,132),fill=accent)
        label(d,(55,15),'COMISSÃO TÉCNICA',21,(172,185,194))
        label(d,(55,47),TITLES[i],53,(248,250,251),width=1770)
        image(im,read_asset,f'data/ui/imgassets/crest/light/l{context["club"]}.dds',(1890,24,92,92))
        d.rectangle((0,985,W,H),fill=DARK)
        label(d,(36,990),'CARREIRA · '+date(context['date']),21,(198,209,216))
        label(d,(1480,990),f'{i+1:02d} / CENTRO DE ANÁLISE',21,(198,209,216),width=530)
        d.rectangle((2,2,W-3,H-3),outline=DARK,width=6)
    return pages
