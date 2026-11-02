"""Medical room dashboards and crisp illustrative sports-medicine posters."""
import io,math
from PIL import Image,ImageDraw
from room_interior_r71 import font,palette,club_sign
from room_coach_decor_r76 import SWATCHES

TEXT=(26,45,56);MUTED=(93,112,124);BG=(239,243,245);GREEN=(36,151,112);RED=(203,69,83)


def atlas(context,read_asset):
    data=context['medical'];primary,secondary=palette(context['colors']);ink=TEXT if sum(a*b for a,b in zip(primary,(.2126,.7152,.0722)))>145 else (255,255,255)
    pages=[]
    def text(d,xy,s,size=34,color=TEXT):d.text(xy,str(s),font=font(size),fill=color)
    def fit(d,xy,s,width,size=34,color=TEXT):
        f=font(size)
        while d.textlength(str(s),font=f)>width and f.size>18:f=font(f.size-1)
        d.text(xy,str(s),font=f,fill=color)
    def new(title,subtitle):
        image=Image.new('RGBA',(2048,1024),BG+(255,));d=ImageDraw.Draw(image);d.rectangle((0,0,2048,132),fill=primary)
        text(d,(55,28),title,61,ink);text(d,(58,161),subtitle,29,MUTED);pages.append(image);return image,d
    date=str(context['date']);date=f'{date[6:8]}/{date[4:6]}/{date[:4]}'
    im,d=new('SITUAÇÃO MÉDICA DO ELENCO',context['club_name']+' · '+date)
    total=data.get('rosterCount',0);out=data.get('unavailableCount',len(data['players']));available=data.get('availableCount',max(0,total-out))
    d.ellipse((90,260,570,740),fill=GREEN)
    if total and out:d.pieslice((90,260,570,740),-90,-90+360*out/total,fill=RED)
    d.ellipse((175,345,485,655),fill=BG);d.text((330,465),str(available),font=font(110),anchor='mm',fill=TEXT);d.text((330,560),'disponíveis',font=font(37),anchor='mm',fill=MUTED)
    text(d,(100,800),f'{available} disponíveis',42,GREEN);text(d,(100,870),f'{out} em tratamento',42,RED)
    injured=data['players'];step=min(121,720/max(6,len(injured)));scale=step/121
    if not injured:text(d,(690,430),'Nenhum atleta na lista de lesões.',48,GREEN)
    for i,p in enumerate(injured):
        y=248+i*step;d.rounded_rectangle((655,y,1995,y+step-8),radius=10,fill='white');fit(d,(683,y+9*scale),p['name'],600,max(20,int(39*scale)))
        fit(d,(683,y+61*scale),p.get('injury','Tipo não informado'),850,max(18,int(26*scale)),MUTED);fit(d,(1560,y+30*scale),p.get('return','—'),390,max(20,int(34*scale)),RED)

    im,d=new('RECUPERAÇÃO · ACOMPANHAMENTO','Evolução observada pelo prazo restante · '+date)
    text(d,(65,236),'PRAZO E EVOLUÇÃO ACOMPANHADA',33)
    for i,p in enumerate(data['players'][:3]):
        y=310+i*115;fit(d,(65,y),p['name'],750,35);progress=p.get('recovery')
        label=f'{progress}%' if progress is not None else '—';text(d,(790,y),label,36,GREEN)
        d.rectangle((70,y+61,960,y+78),fill=(207,218,223))
        if progress is not None:d.rectangle((70,y+61,70+890*progress/100,y+78),fill=GREEN)
    if not data['players']:text(d,(70,400),'Sem afastamentos atuais.',42,GREEN)
    text(d,(65,690),'ACOMPANHAMENTOS ANTERIORES',29)
    history=data.get('observedHistory',[])[-2:]
    for i,p in enumerate(history):
        fit(d,(65,750+i*74),p['name']+' · '+p.get('injury',''),900,29,MUTED)
    if not history:text(d,(65,765),'Histórico ainda sem registros.',29,MUTED)
    text(d,(1080,236),'RESISTÊNCIA · ATRIBUTO DO ELENCO',30)
    for i,p in enumerate(sorted(data.get('condition',[]),key=lambda p:(p['available'],p['name']))[:7]):
        y=310+i*78;fit(d,(1080,y),p['name'],630,31);value=p.get('stamina');text(d,(1810,y),value if value is not None else '—',34)
        if value is not None:
            d.rectangle((1080,y+43,1950,y+55),fill=(207,218,223));d.rectangle((1080,y+43,1080+870*value/100,y+55),fill=GREEN)
    text(d,(65,935),'Carga física  —     Fadiga  —     Risco de lesão  —     Sem registro disponível',28,MUTED)

    # Simplified illustrative posters; they do not diagnose injuries or prescribe therapy.
    im,d=new('FISIOTERAPIA ESPORTIVA','Musculatura · Referência visual para o ambiente')
    cx=680;d.ellipse((cx-75,245,cx+75,395),fill=(235,224,211),outline=TEXT,width=7)
    d.rounded_rectangle((cx-130,405,cx+130,695),radius=58,fill=(209,111,105),outline=TEXT,width=6)
    for side in (-1,1):
        x=cx+side*155;d.line((cx+side*100,440,x+side*55,665,x+side*70,820),fill=(199,81,87),width=65)
        d.line((cx+side*68,690,cx+side*80,835,cx+side*100,972),fill=(198,80,83),width=78)
        for y in (465,525,585):d.ellipse((cx+side*65-50,y-24,cx+side*65+50,y+24),outline=(247,218,207),width=6)
    text(d,(1140,340),'FORÇA',65);text(d,(1140,485),'MOBILIDADE',65);text(d,(1140,630),'RECUPERAÇÃO',65)
    for y in (440,585,730):d.line((1140,y,1880,y),fill=primary,width=8)

    im,d=new('ARTICULAÇÃO DO JOELHO','Medicina esportiva · Referência visual')
    d.rounded_rectangle((610,240,770,530),radius=67,fill=(226,226,213),outline=TEXT,width=7)
    d.ellipse((540,470,700,630),fill=(228,226,212),outline=TEXT,width=7);d.ellipse((680,470,840,630),fill=(228,226,212),outline=TEXT,width=7)
    d.rounded_rectangle((610,625,760,960),radius=50,fill=(230,227,215),outline=TEXT,width=7)
    d.rounded_rectangle((795,630,850,960),radius=24,fill=(217,220,208),outline=TEXT,width=5)
    for points in [[(585,555),(640,690)],[(795,555),(735,690)],[(630,560),(755,670)],[(770,560),(640,670)]]:d.line(points,fill=(72,135,170),width=19)
    for y,label in [(350,'ESTABILIDADE'),(550,'MOVIMENTO'),(750,'FORTALECIMENTO')]:
        d.line((890,y+35,1140,y+35),fill=MUTED,width=4);text(d,(1170,y),label,49)

    im,d=new('COLUNA VERTEBRAL','Postura, mobilidade e controle · Referência visual')
    for i in range(16):
        y=250+i*42;x=700+25*math.sin(i*.38);w=57+i*2
        d.rounded_rectangle((x-w,y,x+w,y+30),radius=9,fill=(228,227,212),outline=TEXT,width=4)
        d.line((x-w-25,y+13,x+w+25,y+13),fill=(212,204,185),width=7)
    for y,label in [(320,'CONTROLE'),(530,'MOBILIDADE'),(740,'RECUPERAÇÃO FUNCIONAL')]:text(d,(1100,y),label,46);d.line((1100,y+83,1930,y+83),fill=primary,width=8)

    im=Image.new('RGBA',(2048,1024));crest=None
    try:crest=Image.open(io.BytesIO(read_asset(f'data/ui/imgassets/crest/light/l{context["club"]}.dds'))).convert('RGBA')
    except (OSError,ValueError,FileNotFoundError):pass
    im.paste(club_sign(context,'DEPARTAMENTO MÉDICO','medical',crest),(0,0));im.paste(club_sign(context,'COMISSÃO TÉCNICA','coach',crest),(0,512));pages.append(im)

    im,d=new('FISIOTERAPIA','Equipamento · Painel ilustrativo')
    d.rounded_rectangle((100,265,1960,850),radius=30,fill=(20,45,56));text(d,(160,320),'PRONTO',80,(78,200,147))
    line=[(x,570+60*math.sin(x*.022)) for x in range(160,1880,12)];d.line(line,fill=(80,195,201),width=9)
    text(d,(160,720),'CONTROLE DE SESSÃO',41,(221,234,235))

    im,d=new('ACOMPANHAMENTO DO ATLETA',context['club_name']+' · '+date)
    for i,label in enumerate(('Avaliação e evolução','Registro do atendimento','Retorno aos treinamentos','Planejamento da recuperação')):
        y=280+i*155;d.rectangle((80,y,120,y+40),outline=MUTED,width=4);text(d,(160,y-5),label,46);d.line((160,y+82,1940,y+82),fill=(181,196,202),width=3)
    # Medical products add restrained natural colors alongside the club identity.
    swatch=ImageDraw.Draw(im)
    for i,rgb in enumerate(SWATCHES):swatch.rectangle((i*128,960,(i+1)*128-1,1023),fill=rgb+(255,))
    result=Image.new('RGBA',(4096,4096))
    for i,page in enumerate(pages):result.paste(page,((i%2)*2048,(i//2)*1024))
    return result
