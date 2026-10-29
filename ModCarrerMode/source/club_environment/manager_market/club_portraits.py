"""Read club RGBs only; add team-coloured corners to display copies of heads."""
from functools import lru_cache
from pathlib import Path
from PIL import Image,ImageDraw

def colors(game):
 game=Path(game);db=game/'data/db/fifa_ng_db.db';meta=game/'data/db/fifa_ng_db-meta.xml'
 if not db.exists() or not meta.exists():return {}
 return _colors(str(game),db.stat().st_mtime_ns,meta.stat().st_mtime_ns)

@lru_cache(maxsize=2)
def _colors(game,*revision):
 from fifa_db import FifaDatabase
 base=FifaDatabase(Path(game));fields=['teamid']+['teamcolor'+str(i)+c for i in (1,2) for c in 'rgb']
 return {r['teamid']:tuple('#'+''.join(f'{max(0,min(255,int(r.get("teamcolor"+str(i)+c) or 0))):02x}' for c in 'rgb') for i in (1,2)) for r in base.rows('teams',fields)}

def portrait(source,palette=None):
 size=256;im=Image.new('RGBA',(size,size));d=ImageDraw.Draw(im);d.rounded_rectangle((0,0,255,255),12,fill='#e9eef1')
 primary,secondary=palette or ('#bac6ce','#dce3e8')
 d.polygon(((0,0),(109,0),(0,122)),fill=primary);d.polygon(((109,0),(139,0),(0,155),(0,122)),fill=secondary)
 d.polygon(((203,255),(255,202),(255,255)),fill=primary)
 face=source.convert('RGBA');box=face.getbbox()
 if box:face=face.crop(box)
 face.thumbnail((244,248),Image.Resampling.LANCZOS);im.alpha_composite(face,((size-face.width)//2,size-face.height))
 mask=Image.new('L',im.size);ImageDraw.Draw(mask).rounded_rectangle((0,0,255,255),12,fill=255);im.putalpha(mask)
 return im
