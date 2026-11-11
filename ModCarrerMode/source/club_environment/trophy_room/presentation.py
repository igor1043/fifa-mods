"""Current-page camera cues and one atlas for the selected title's details."""
import math
from PIL import Image,ImageDraw
from . import assets
from .loading import quad


def visit(slot,cup):
    height=cup['display_dimensions_cm'][1]
    side=1 if slot['side']=='left' else -1
    target=[slot['x'],slot['y']+height*.50,slot['z']]
    # Stand in the aisle, outside the glass, at the trophy's actual height.
    eye=[slot['x']+side*235,max(140,target[1]+13),slot['z']+35]
    close=[slot['x']+side*190,target[1]+8,slot['z']+14]
    # Keep the authored cue centred on the actual cup. The runtime frames it
    # inside the viewport beside the history panel, at the current aspect.
    close_target=target.copy()
    return dict(slot=slot['index'],eye=eye,target=target,fov=54,
                detail_eye=close,detail_target=close_target,detail_fov=55)


def detail_card(game,identity,row,cup):
    im=Image.new('RGBA',(512,512),'#f8fafb');d=ImageDraw.Draw(im)
    d.rectangle((0,0,511,8),fill='#b9a274')
    logo=assets.crest(game,identity['club'],64);im.alpha_composite(logo,(28,28))
    d.text((112,37),'CONQUISTA DO CLUBE',font=assets.font(21,True),fill='#4d6571')
    name=row['name'].replace(' · DEMONSTRAÇÃO','').replace('DEMONSTRAÇÃO · ','')
    # Bounded line wrapping instead of squeezing a long league into tiny text.
    words=name.split();lines=[];line=''
    for word in words:
        candidate=(line+' '+word).strip()
        if d.textbbox((0,0),candidate,font=assets.font(29,True))[2]>440 and line:lines.append(line);line=word
        else:line=candidate
    lines.append(line)
    for i,text in enumerate(lines[:3]):d.text((28,128+i*36),text,font=assets.font(29,True),fill='#19303c')
    y=255
    d.line((28,y,484,y),fill='#dce4e8',width=2)
    d.text((28,y+24),'TEMPORADA',font=assets.font(19,True),fill='#70848e')
    d.text((28,y+53),str(row['year']),font=assets.font(43,True),fill='#8b7041')
    d.text((212,y+24),'CLUBE',font=assets.font(19,True),fill='#70848e')
    assets.center(d,(339,y+75),identity['name'],25,'#19303c',True,267)
    preview=row.get('origin')=='preview'
    d.rounded_rectangle((28,386,484,440),9,fill='#f1ebdd' if preview else '#e2efe9')
    assets.center(d,(256,413),'DEMONSTRAÇÃO' if preview else 'TÍTULO CONFIRMADO',23,'#71582d' if preview else '#27694d',True,430)
    assets.center(d,(256,474),'Modelo original do FIFA · '+('tamanho nativo' if cup['scale']==1 else 'ajustado à vitrine'),17,'#70848e',False,458)
    return im


def atlas_geometry(count):
    parts=[]
    for i in range(count):
        p=quad(0,0,0,150,150);x,y=i%8,i//8
        p['uvs']=[[(x+u)/8,(y+v)/4] for u,v in p['uvs']];parts.append(p)
    return parts
