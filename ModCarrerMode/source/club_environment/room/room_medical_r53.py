import portable_paths as portable
"""Club medical presentation from this save and native injury publications."""
from pathlib import Path
import hashlib,json,io,math,numpy as np
from PIL import Image,ImageDraw,ImageFont
from room_native_hanging_20261022 import texture_package
ROOT=portable.ROOM;LIVE=portable.GAME/'data/sceneassets/server16_dressing_room_20261022'

def context_for_room(context,roster,rows):
    known={p['id']:p for p in roster};linked={r.value('playerid'):r for r in rows('teamplayerlinks') if r.value('teamid')==context['club']}
    data=[]
    for pid,p in known.items():
        r=linked.get(pid);weeks=r.value('injury') if r and 'injury' in r.fields else 0
        if 0<weeks<=35:data.append({'player':pid,'name':p['name'],'weeks':weeks,'injury':'Tipo não informado pelo jogo','return':f'{weeks} semana'+('s' if weeks!=1 else ''),'source':'saved_teamplayerlinks'})
    # Native strings are used only for the matching live session, club and day.
    # A stale capture from another career must never become a medical diagnosis.
    (ROOT/'runtime/medical_scope.txt').write_text(f'S16MEDICALSCOPE 1 {context["pid"]} {context["club"]} {context["date"]}\n')
    try:
        lines=(ROOT/'runtime/medical_native_capture.tsv').read_text(encoding='utf8').splitlines();head=lines[0].split()
        valid=len(head)==6 and head[:2]==['S16MEDICAL','1'] and tuple(map(int,head[2:5]))==(context['pid'],context['club'],context['date'])
        # ID-less InjuryList rows are matched only to an unambiguous current
        # roster name, never to a fixed club or to an arbitrary player.
        if valid:
            by_name={}
            for pid,p in known.items():by_name.setdefault(p['name'].strip().casefold(),[]).append(pid)
            existing={p['player']:p for p in data}
            for line in lines[1:]:
                fields=line.split('\t')
                if len(fields)!=4:continue
                ident,name,injury,ret=fields;matches=by_name.get(name.strip().casefold(),[])
                pid=int(ident) if ident.isdigit() and int(ident) in known and known[int(ident)]['name'].strip().casefold()==name.strip().casefold() else (matches[0] if len(matches)==1 else 0)
                if not pid or not ret:continue
                row=existing.get(pid)
                if row is None:row={'player':pid,'name':known[pid]['name'],'weeks':0};data.append(row);existing[pid]=row
                row.update(injury=injury or 'Tipo não informado pelo jogo',**{'return':ret},source='native_InjuryList')
    except (OSError,ValueError,IndexError):pass
    data.sort(key=lambda r:(-r['weeks'],r['name'],r['player']))
    context['medical']={'players':data,'date':context['date'],'source':'career save + validated native InjuryList','type_fallback':'Tipo não informado pelo jogo','pages':max(1,math.ceil(len(data)/6))}
    return context['medical']

def font(size,bold=False):return ImageFont.truetype(str(portable.FONTS/('arialbd.ttf' if bold else 'arial.ttf')),size)
def native_image(read_asset,paths):
    for path in paths:
        try:return Image.open(io.BytesIO(read_asset(path))).convert('RGBA')
        except (FileNotFoundError,OSError,ValueError):pass
    return None

def player_portrait(read_asset,player):
    # Resolve the real FIFA miniface by player ID, including packed assets.
    # No roster index or club badge can accidentally become someone's face.
    for path in (f'data/ui/imgassets/heads/p{player}.dds',f'data/ui/imgassets/heads/p{player}.png',f'data/ui/imgassets/head/p{player}.dds'):
        image=native_image(read_asset,[path])
        if image is not None:return image,path
    return None,''
def paste(im,img,box):
    if img is None:return
    img=img.copy();img.thumbnail((box[2],box[3]),Image.Resampling.LANCZOS);im.alpha_composite(img,(box[0]+(box[2]-img.width)//2,box[1]+(box[3]-img.height)//2))
def fit_text(draw,text,max_width,size,bold=False):
    text=' '.join(str(text).split());f=font(size,bold)
    while draw.textlength(text,font=f)>max_width and f.size>22:f=font(f.size-1,bold)
    while draw.textlength(text,font=f)>max_width and len(text)>1:text=text[:-2].rstrip()+'…'
    return text,f

def board(context,read_asset,page,portraits=None):
    im=Image.new('RGBA',(2048,1280),(239,242,244,255));d=ImageDraw.Draw(im);primary=tuple(round(255*c) for c in context['colors'][0])
    d.rectangle((0,0,2048,168),fill=(17,29,40));d.rectangle((0,164,2048,180),fill=primary)
    crest=native_image(read_asset,[f'data/ui/imgassets/crest/light/l{context["club"]}.dds']);paste(im,crest,(35,22,125,125))
    d.text((190,25),'DEPARTAMENTO MÉDICO',font=font(58,True),fill='white');d.text((192,100),context['club_name'],font=font(34),fill='white')
    medical=context['medical'];players=medical['players'][page*6:page*6+6]
    if not players:d.text((190,540),'Nenhum jogador lesionado',font=font(69,True),fill=(28,50,62))
    for i,p in enumerate(players):
        col=i%2;row=i//2;x=45+col*1000;y=222+row*300
        d.rounded_rectangle((x,y,x+958,y+272),radius=14,fill=(255,255,255),outline=(192,205,214),width=3)
        head=(portraits[p['player']][0] if portraits is not None else player_portrait(read_asset,p['player'])[0])
        if head is not None:paste(im,head,(x+10,y+15,210,240))
        else:
            d.ellipse((x+69,y+34,x+149,y+114),fill=(157,172,184));d.rounded_rectangle((x+42,y+119,x+178,y+239),radius=35,fill=(157,172,184))
        label=p['name'] or ('Jogador '+str(p['player']));f=font(42,True)
        while d.textlength(label,font=f)>710 and f.size>24:f=font(f.size-1,True)
        d.text((x+225,y+28),label,font=f,fill=(18,40,57))
        injury,f=fit_text(d,p['injury'],710,30);d.text((x+225,y+106),injury,font=f,fill=(60,77,86))
        ret,f=fit_text(d,'Retorno previsto: '+p['return'],710,34,True);d.text((x+225,y+175),ret,font=f,fill=(16,92,118))
    date=str(context['date']);d.text((45,1195),f'{date[6:8]}/{date[4:6]}/{date[:4]}  ·  {len(medical["players"])} em recuperação  ·  Página {page+1}/{medical["pages"]}',font=font(30),fill=(55,70,83))
    return im.resize((2048,2048),Image.Resampling.LANCZOS)

def prepare(context,read_asset,add,identity):
    spec=json.loads((ROOT/'runtime/medical_room_r57.json').read_text(encoding='utf8'));prefix='data/sceneassets/server16_dressing_room_20261022/';club=context['club'];medical=context['medical']
    portraits={p['player']:player_portrait(read_asset,p['player']) for p in medical['players']}
    medical['portraits']={str(pid):path or 'silhouette' for pid,(_,path) in portraits.items()}
    palette={'wall':(224,227,228),'charcoal':(26,30,33),'cabinet':(42,47,51),'metal':(159,168,174),'leather':(31,34,36),'rubber':(18,22,24),'towel':(229,228,219),'light':(255,253,243),'glass':(78,126,139),'bottle':(216,225,229),'rehab':(110,120,125),'primary':tuple(round(v*255) for v in context['colors'][0])}
    rng=np.random.default_rng(53022)
    for binding in spec['bindings']:
        material=binding['material'];sub=binding['submesh'];alpha=material in ('crest','glass','shadow')
        if material.startswith('injuries'):
            bank=0 if material=='injuries' else 1
            for page in range(medical['pages']):
                tag=hashlib.sha256(json.dumps([club,context['date'],medical,page,56],sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16];name=f'medical_board_{club}_{tag}_r56.rx3';path=LIVE/name
                if not path.exists():texture_package(board(context,read_asset,page,portraits),path,'medical_cm')
                add(f'medical_{material}_{page}',prefix+'medical_room_r57.rx3',prefix+name,'medical_cm',identity,submesh=sub,page=page,pages=medical['pages'],bank=bank)
            continue
        if material in ('floor','ceiling'):
            texture=prefix+('floor_textures_r44.rx3' if material=='floor' else 'ceiling_r49.rx3');texname='floor_cm' if material=='floor' else 'ceiling_cm'
        elif material=='crest':texture=f'data/ui/imgassets/crest/light/l{club}.dds';texname=''
        elif material=='shadow':texture=prefix+'contact_shadow_r51.rx3';texname='shadow_cm'
        elif material=='brand' or material.startswith('door_sign'):
            im=Image.new('RGBA',(2048,608) if material=='brand' else (2048,288),(24,29,32,255));d=ImageDraw.Draw(im);crest=native_image(read_asset,[f'data/ui/imgassets/crest/light/l{club}.dds'])
            if material=='brand':
                paste(im,crest,(25,10,665,588));d.text((730,57),'DEPARTAMENTO',font=font(96,True),fill='white');d.text((730,190),'MÉDICO',font=font(136,True),fill='white')
                club_text,club_font=fit_text(d,context['club_name'],1230,58,True);d.text((734,365),club_text,font=club_font,fill='white');d.rectangle((730,454,1950,467),fill=palette['primary']);d.text((730,505),'AVALIAÇÃO  ·  RECUPERAÇÃO  ·  DESEMPENHO',font=font(28),fill=(216,224,228))
            else:
                paste(im,crest,(25,20,250,245));title='DEPARTAMENTO MÉDICO' if material.endswith('medical') else 'SALA DO TREINADOR';d.text((320,39),title,font=font(84,True),fill='white');d.text((324,158),context['club_name'],font=font(56),fill=(226,234,239));d.rectangle((0,276,2048,287),fill=palette['primary'])
            im=im.resize((2048,1024 if material=='brand' else 512),Image.Resampling.LANCZOS)
            tag=hashlib.sha256(im.tobytes()).hexdigest()[:12];name=f'medical_brand_{club}_{tag}.rx3';path=LIVE/name
            if not path.exists():texture_package(im,path,'medical_cm')
            texture=prefix+name;texname='medical_cm'
        else:
            rgb=palette[material];noise=rng.integers(-2,3,(128,128)) if material in ('wall','leather','towel','cabinet','rehab') else np.zeros((128,128),dtype=int)
            pixels=np.zeros((128,128,4),dtype=np.uint8)
            for c in range(3):pixels[:,:,c]=np.clip(rgb[c]+noise,0,255)
            pixels[:,:,3]=125 if material=='glass' else 255
            tag=hashlib.sha256(pixels.tobytes()).hexdigest()[:12];name=f'medical_{material}_{tag}.rx3';path=LIVE/name
            if not path.exists():texture_package(Image.fromarray(pixels),path,'medical_cm')
            texture=prefix+name;texname='medical_cm'
        add('medical_'+material,prefix+'medical_room_r57.rx3',texture,texname,identity,alpha,submesh=sub)
