"""Editable graphic layouts for independent cabinet and corner materials.

These are club-color joinery graphics, not replacements for FIFA kit, face or
crest assets. The latter continue to be referenced from the game's catalog.
"""
from PIL import Image,ImageDraw
import numpy as np
from room_fascia import font


def palette(club):
    return [tuple(club[f'teamcolor{n}{c}'] for c in 'rgb') for n in (1,2)]


def structural(club,size=1024):
    primary,secondary=palette(club)
    # The structure is intentionally restrained: no full backing illustration
    # repeated on the four faces and every horizontal shelf.
    rng=np.random.default_rng(int(club['teamid']))
    grain=rng.integers(-3,4,(size,size,1))
    pixels=np.empty((size,size,4),dtype=np.uint8)
    base=np.array([25,27,29]) if sum(primary)<480 else np.array([39,40,41])
    pixels[:,:,:3]=np.clip(base+grain,0,255);pixels[:,:,3]=255
    image=Image.fromarray(pixels);d=ImageDraw.Draw(image)
    for x in range(0,size,72):d.line((x,0,x,size),fill=(49,49,49),width=1)
    shade=tuple(round(c*.28+20) for c in primary)
    for offset in range(-size,size*2,280):
        d.polygon([(offset,0),(offset+24,0),(offset-size+24,size),(offset-size,size)],fill=shade)
    d.rectangle((0,0,12,size),fill=primary);d.rectangle((size-5,0,size,size),fill=secondary)
    return image


def corner(club,size=(768,1536)):
    primary,secondary=palette(club);w,h=size;team=int(club['teamid'])
    image=Image.new('RGBA',size,(18,20,22,255));d=ImageDraw.Draw(image)
    # Each club has its own graphic rhythm. This panel is an architectural
    # corner sign, rather than a copy of the locker/niche backing artwork.
    family={1043:'bands',598:'tricolor',383:'chevron',517:'star',567:'tricolor',
            568:'stars',569:'sash',1041:'bands',1048:'circle',1053:'bands',
            1598:'tricolor',1629:'bands',1719:'bands',1035:'bands',1039:'sash',
            111044:'chevron',112476:'chevron',113163:'circle',123921:'circle',130026:'star'}.get(team,'chevron')
    accent=secondary if sum(primary)<100 else primary
    if family in ('bands','tricolor','sash'):
        for i in range(4):
            y=120+i*210
            ink=primary if i%2==0 else secondary
            d.polygon([(0,y),(w,y+190),(w,y+260),(0,y+70)],fill=ink)
        if family=='tricolor':d.polygon([(0,220),(w,410),(w,445),(0,255)],fill=(245,245,239))
    elif family in ('star','stars'):
        for x,y,r in ((w//2,320,175),(w//3,850,50),(2*w//3,920,42)):
            points=[]
            import math
            for i in range(10):
                a=-math.pi/2+i*math.pi/5;rr=r if i%2==0 else r*.42
                points.append((x+math.cos(a)*rr,y+math.sin(a)*rr))
            d.polygon(points,fill=accent)
    elif family=='circle':
        for r in (310,230,150):d.ellipse((w//2-r,440-r,w//2+r,440+r),outline=accent,width=28)
    else:
        for i in range(4):
            y=120+i*180;d.line([(80,y),(w//2,y+160),(w-80,y)],fill=accent,width=38)
    # Name typography supplies identity even where a club's badge is not in
    # the user's base installation. No copied badge is baked into this PNG.
    d.rectangle((30,1130,w-30,h-85),fill=(18,20,22))
    words=club['teamname'].upper().split();lines=['']
    face=font(76)
    for word in words:
        candidate=(lines[-1]+' '+word).strip()
        if d.textlength(candidate,font=face)>w-110 and lines[-1]:lines.append(word)
        else:lines[-1]=candidate
    for i,line in enumerate(lines):d.text((w/2,1190+i*88),line,font=face,fill=(244,244,239),anchor='mm')
    d.rectangle((30,h-78,w-30,h-68),fill=primary)
    d.rectangle((30,h-58,w-30,h-51),fill=secondary)
    return image
