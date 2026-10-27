import portable_paths as portable
"""Use installed career competition artwork, embedding it in the native APT."""
from pathlib import Path
import hashlib,io,struct
from PIL import Image


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
