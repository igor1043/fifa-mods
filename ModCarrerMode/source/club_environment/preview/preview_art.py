import portable_paths as portable
"""Use installed career competition artwork, embedding it in the native APT."""
from pathlib import Path
import hashlib,io,struct,re,unicodedata
from PIL import Image,ImageDraw,ImageOps


def competition_art(ui,ident,cache):
    if ident<=0:return None
    paths=(ui/f'careerCompetitionIcons/{ident}.png',
           ui/f'league/light/l{ident}.dds',ui/f'league/dark/l{ident}.dds',
           ui/f'league/{ident}.dds',
           ui/f'cmCalendarCompetitions/cmCalendarCompetitions{ident}.dds')
    source=None
    for candidate in paths:
        try:source=portable.materialize(candidate.relative_to(portable.GAME).as_posix());break
        except FileNotFoundError:continue
    if source is None:return None
    if source.suffix.lower()=='.dds':return source
    raw=source.read_bytes();stamp=hashlib.sha256(raw).hexdigest()[:20]
    target=Path(cache)/f'competition_{ident}_{stamp}.dds'
    if not target.exists():
        image=Image.open(io.BytesIO(raw)).convert('RGBA')
        image.thumbnail((256,256),Image.Resampling.LANCZOS)
        size=((image.width+3)//4*4,(image.height+3)//4*4)
        canvas=Image.new('RGBA',size);canvas.alpha_composite(image,((size[0]-image.width)//2,(size[1]-image.height)//2))
        output=io.BytesIO();canvas.save(output,format='DDS',pixel_format='DXT5')
        dds=bytearray(output.getvalue());struct.pack_into('<I',dds,20,len(dds)-128);struct.pack_into('<I',dds,88,0)
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(dds)
    return target


def _stadium_key(value):
    value=unicodedata.normalize('NFKD',str(value or '')).encode('ascii','ignore').decode('ascii').casefold()
    return ' '.join(re.findall(r'[a-z0-9]+',value))


def _fallback_stadium_art(cache):
    """Create a neutral stadium backdrop when the game has no exact thumbnail."""
    target=Path(cache)/'stadium_generic_v1.dds'
    if target.exists():return target
    scale=2;width,height=1050*scale,404*scale
    image=Image.new('RGB',(width,height));pixels=image.load()
    for y in range(height):
        t=y/max(1,height-1)
        if t<.68:
            blend=t/.68;top=(12,29,48);bottom=(66,93,103)
            color=tuple(int(top[i]*(1-blend)+bottom[i]*blend) for i in range(3))
        else:
            blend=(t-.68)/.32;top=(40,91,49);bottom=(24,75,36)
            color=tuple(int(top[i]*(1-blend)+bottom[i]*blend) for i in range(3))
        for x in range(width):pixels[x,y]=color
    draw=ImageDraw.Draw(image,'RGBA')
    # Distant roof and grandstand silhouette.
    draw.polygon(((0,128*scale),(150*scale,93*scale),(525*scale,72*scale),(900*scale,93*scale),(1050*scale,128*scale),
                  (1050*scale,152*scale),(0,152*scale)),fill=(10,20,30,230))
    draw.polygon(((0,150*scale),(1050*scale,150*scale),(940*scale,277*scale),(110*scale,277*scale)),fill=(75,91,96,255))
    draw.polygon(((0,157*scale),(1050*scale,157*scale),(965*scale,191*scale),(85*scale,191*scale)),fill=(24,43,58,255))
    # Seat bands with alternating club-neutral colors, not a fabricated venue identity.
    for row,y in enumerate(range(164,244,7)):
        left=78+(y-164)//3;right=1050-left
        for x in range(left,right,11):
            shade=(49,94,126,220) if (x//11+row)%4 else (166,151,102,220)
            draw.rectangle((x*scale,y*scale,(x+6)*scale,(y+3)*scale),fill=shade)
        draw.line((left*scale,(y+5)*scale,right*scale,(y+5)*scale),fill=(215,223,220,90),width=scale)
    draw.polygon(((0,247*scale),(1050*scale,247*scale),(1050*scale,284*scale),(0,284*scale)),fill=(24,35,40,255))
    # Floodlights and warm glow.
    for x in (48,1002):
        draw.line((x*scale,60*scale,x*scale,157*scale),fill=(172,187,188,230),width=3*scale)
        draw.rounded_rectangle(((x-25)*scale,54*scale,(x+25)*scale,65*scale),radius=4*scale,fill=(245,230,186,255))
        for dx in range(-18,19,9):
            draw.ellipse(((x+dx-2)*scale,57*scale,(x+dx+2)*scale,61*scale),fill=(255,246,208,255))
    # Foreground pitch and subtle markings.
    draw.polygon(((0,277*scale),(1050*scale,277*scale),(1050*scale,404*scale),(0,404*scale)),fill=(35,91,42,255))
    draw.line((0,278*scale,1050*scale,278*scale),fill=(200,220,174,190),width=2*scale)
    draw.rectangle((340*scale,304*scale,710*scale,403*scale),outline=(210,227,190,135),width=2*scale)
    draw.ellipse((450*scale,326*scale,600*scale,404*scale),outline=(210,227,190,135),width=2*scale)
    image=image.resize((1050,404),Image.Resampling.LANCZOS).convert('RGBA')
    output=io.BytesIO();image.save(output,format='DDS',pixel_format='DXT5')
    dds=bytearray(output.getvalue());struct.pack_into('<I',dds,20,len(dds)-128);struct.pack_into('<I',dds,88,0)
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(dds)
    return target


def stadium_source(game,venue_key,venue_name=''):
    """Mirror Central: exact FSW key, stripped render digits, then native DB art.

    Central accepts DDS/BMP as well as JPEG/PNG and can use built-in stadium
    movies. A fuzzy name match may show a different venue, so it is not used.
    """
    game=Path(game);key=str(venue_key or '').strip();values=[]
    if not key:key=str(venue_name or '').strip()
    if not key or any(c in key for c in '/\\:') or key in ('.','..'):return None
    candidate=key
    while candidate:
        values.append(candidate)
        if not candidate[-1].isdigit():break
        candidate=candidate[:-1].strip()
    for value in values:
        # Reuse Central's already-converted thumbnail first.
        paths=[game/'data/ui/imgAssets/stadium'/('stadium_'+value+'.dds')]
        paths.extend(game/'StadiumGBD/render/thumbnail/stadium'/(value+ext) for ext in ('.dds','.jpg','.jpeg','.png','.bmp','.jepg'))
        for path in paths:
            if path.is_file():
                try:
                    raw=path.read_bytes();Image.open(io.BytesIO(raw)).load()
                    return str(path),raw
                except (OSError,ValueError):continue
    if key.isdigit():
        from formats import BigFile
        for variant in (0,1,3,4):
            path=game/'data/ui/artAssets/stadium'/f'stadium_{int(key)}_{variant}.big'
            try:
                movie=BigFile(path)
                for member in movie.entries.values():
                    raw=bytes(member.data)
                    if raw[:4]==b'DDS ':
                        Image.open(io.BytesIO(raw)).load();return str(path),raw
            except (OSError,ValueError,KeyError):continue
    return None


def stadium_art(game,venue_key,venue_name,cache):
    """Embed the same real photo used by Central, with block-aligned DDS size."""
    source=stadium_source(game,venue_key,venue_name)
    if source is None:return None
    _,raw=source;stamp=hashlib.sha256(raw+b'|next-match-stadium-v2-1052x404').hexdigest()[:20]
    target=Path(cache)/f'stadium_{stamp}.dds'
    if target.exists():return target
    image=Image.open(io.BytesIO(raw)).convert('RGB')
    image=ImageOps.fit(image,(1052,404),method=Image.Resampling.LANCZOS,centering=(.5,.42)).convert('RGBA')
    output=io.BytesIO();image.save(output,format='DDS',pixel_format='DXT5')
    dds=bytearray(output.getvalue());struct.pack_into('<I',dds,20,len(dds)-128);struct.pack_into('<I',dds,88,0)
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(dds)
    return target
