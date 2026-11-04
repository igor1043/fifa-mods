"""Native dressing-room fascia layout: text, illustration or a mixed strip.

Authored art is read from the club catalog, and authentic crests are resolved
from the game at render time. No copied crest source or career writes.
"""
from pathlib import Path
import io
from functools import lru_cache
from PIL import Image,ImageDraw,ImageOps,ImageFont
import room_appearance as appearance


def rgb(value,fallback=(18,20,23)):
    try:
        if isinstance(value,str) and len(value)==7 and value.startswith('#'):
            return tuple(int(value[i:i+2],16) for i in (1,3,5))
    except ValueError:pass
    return fallback


@lru_cache(maxsize=24)
def _source(path,modified,size):
    with Image.open(path) as image:
        if image.width*image.height>16_777_216:raise ValueError('Fascia image too large')
        return image.convert('RGBA')


def source(path):
    p=Path(path);s=p.stat();return _source(str(p),s.st_mtime_ns,s.st_size)


@lru_cache(maxsize=8)
def _crest(game,club):
    import portable_paths
    try:return Image.open(io.BytesIO(portable_paths.read_asset(f'data/ui/imgassets/crest/light/l{club}.dds'))).convert('RGBA')
    except (OSError,ValueError,FileNotFoundError):return None


@lru_cache(maxsize=128)
def font(size):
    import os
    for name in ('arialbd.ttf','segoeuib.ttf','arial.ttf'):
        try:return ImageFont.truetype(str(Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/name),size)
        except OSError:pass
    return ImageFont.load_default(size=size)


def text_in_box(image,text,box,ink):
    if not text:return
    x,y,w,h=box;draw=ImageDraw.Draw(image);size=min(330,round(h*.76))
    while size>24 and draw.textlength(text,font=font(size))>w:size-=2
    draw.text((x+w/2,y+h/2),text,font=font(size),fill=ink,anchor='mm')


def _motif(image,art,x,center,height,ratio,focus):
    # Account for the physical plane's aspect, rather than stretching a crest
    # to the raw texture dimensions (the side fascia is 11.7 m wide).
    side=max(8,round(height*ratio))
    tile=ImageOps.fit(art,(side,height),Image.Resampling.LANCZOS,centering=focus)
    mask=Image.new('L',tile.size);d=ImageDraw.Draw(mask)
    d.rounded_rectangle((0,0,side-1,height-1),radius=min(side//8,30),fill=255)
    image.paste(tile,(round(x-side/2),round(center-height/2)),mask)


def _badge(image,crest,x,center,height,ratio):
    badge=crest.copy();badge.thumbnail((height,height),Image.Resampling.LANCZOS)
    badge=badge.resize((max(1,round(badge.width*ratio)),badge.height),Image.Resampling.LANCZOS)
    image.alpha_composite(badge,(round(x-badge.width/2),round(center-badge.height/2)))


def render(game,club,spec,index,width,physical_width,render_text,*,lettering=True):
    """Return a raster consumed by the existing native RX3 texture builder."""
    lines=spec.get('lines') or ['CLUBE'];text=str(lines[index%len(lines)])
    panels=spec.get('panels',[])
    panel=panels[index%len(panels)] if isinstance(panels,list) and panels else {}
    if not isinstance(panel,dict):panel={}
    mode=panel.get('mode','text')
    base=rgb(spec.get('base'));accent=rgb(spec.get('accent'),(230,231,229))
    text=str(panel.get('text',text))
    art_path=appearance.asset(game,club,panel.get('asset_key','fascia'))
    if mode=='image' and art_path:
        # An authored strip is the entire surface, not an illustration cropped
        # into a text template. Keep its pixels and let native UV tiling fit it.
        return source(art_path)
    if mode not in ('mixed','illustration') or not art_path:
        return render_text(text if lettering else '',base,accent,width,club,physical_width)
    try:art=source(art_path)
    except (OSError,ValueError):return render_text(text if lettering else '',base,accent,width,club,physical_width)
    focus=panel.get('focus',[.5,.72])
    if not isinstance(focus,list) or len(focus)!=2:focus=[.5,.72]
    focus=tuple(max(0.,min(1.,float(v))) for v in focus)
    crest=_crest(str(game),club)
    return _render_cached(str(art_path),art_path.stat().st_mtime_ns,club,mode,text,
                          base,accent,width,float(physical_width),focus,
                          art,crest,lettering)


# Cache keys intentionally use the image file identity, not mutable PIL images.
_last={}
def _render_cached(path,modified,club,mode,text,base,accent,width,physical_width,focus,art,crest,lettering=True):
    key=(path,modified,club,mode,text,base,accent,width,physical_width,focus,lettering)
    if key in _last:return _last[key]
    height=1024;image=Image.new('RGBA',(width,height),base+(255,));draw=ImageDraw.Draw(image)
    ratio=(width/physical_width)/(height/45.)
    line=tuple(round(c*.7) for c in accent)
    draw.rectangle((0,0,width-1,7),fill=line+(255,));draw.rectangle((0,height-8,width-1,height-1),fill=line+(255,))
    ink=(247,247,243,255) if .2126*base[0]+.7152*base[1]+.0722*base[2]<145 else (24,28,31,255)
    if mode=='mixed':
        _motif(image,art,width*.115,512,828,ratio,focus)
        if crest is not None:_badge(image,crest,width*.88,512,660,ratio)
        else:_motif(image,art,width*.88,512,828,ratio,focus)
        if lettering:text_in_box(image,text,(width*.21,72,width*.56,880),ink)
    else:
        count=3 if physical_width<700 else 7
        for i in range(count):
            x=(i+.5)*width/count
            if i%2 and crest is not None:_badge(image,crest,x,512,660,ratio)
            else:_motif(image,art,x,512,828,ratio,focus)
        # Fine club-color links unify the image tiles into a single frieze.
        for i in range(count-1):
            a=(i+.5)*width/count+520*ratio;b=(i+1.5)*width/count-520*ratio
            if b>a:draw.line((round(a),512,round(b),512),fill=line+(255,),width=6)
    if len(_last)>=12:_last.pop(next(iter(_last)))
    _last[key]=image
    return image
