"""Native, white-and-gold loading card using the dressing room's visual language."""
from pathlib import Path
import sys
from PIL import Image,ImageDraw
if __package__ is None:
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]));__package__='trophy_room'
from . import assets

def quad(x,y,z,w,h):
    return dict(positions=[[x-w/2,y-h/2,z],[x+w/2,y-h/2,z],[x+w/2,y+h/2,z],[x-w/2,y+h/2,z]],
                normals=[[0,0,1]]*4,uvs=[[0,1],[1,1],[1,0],[0,0]],indices=[0,1,2,0,2,3])

def build(game):
    game=Path(game);out=game/assets.PREFIX;seed=game/'ModCarrerMode/data/trophy_room'
    im=Image.new('RGBA',(1920,1080),'#f7f9fa');d=ImageDraw.Draw(im)
    d.rounded_rectangle((178,244,1758,882),27,fill='#dce2e6')
    d.rounded_rectangle((170,232,1750,870),27,fill='white',outline='#dae3e9',width=2)
    d.rectangle((194,232,1726,242),fill='#b9a274')
    d.rounded_rectangle((256,256,454,454),38,fill='#fafaf8',outline='#e7e1d3',width=2)
    for xy,text,size,color in [((480,292),'SALA DE TROFÉUS',23,'#5e7582'),
                              ((480,337),'Preparando a sala de troféus',49,'#19303c'),
                              ((280,485),'Organizando o ambiente e as conquistas do clube.',29,'#5e7582'),
                              ((280,768),'A entrada será automática quando a cena estiver pronta.',25,'#5e7582')]:
        d.text(xy,text,font=assets.font(size,True),fill=color)
    for i,label in enumerate(('Conquistas do clube','Modelos e materiais','Montagem da sala')):
        x=280+i*470;d.rounded_rectangle((x,540,x+420,645),14,fill='#f9fafb',outline='#dce5ea',width=2)
        d.ellipse((x+20,566,x+68,614),fill='#f2ecde')
        d.text((x+35,574),str(i+1),font=assets.font(24,True),fill='#b9a274')
        d.text((x+86,577),label,font=assets.font(23,True),fill='#19303c')
    d.rounded_rectangle((280,716,1640,730),7,fill='#e3e9ec')
    im.save(out/'loading.png');assets.rx_texture(im,seed/'texture-template.rx3','gallery_cm',out/'loading-texture.rx3')
    for name,shape in [('loading-panel',quad(0,166,100,1296,729)),
                       ('loading-backdrop',quad(0,166,99,5000,3000)),
                       ('loading-progress',quad(0,42.475,101,918,9.45)),
                       ('loading-badge',quad(-408.375,290.875,102,78.3,78.3))]:
        assets.mesh_file([shape],seed/'prop-template.rx3',out/(name+'.rx3'))
    for name,color in [('loading-white',(247,249,250,255)),('loading-gold',(185,162,116,255))]:
        assets.rx_texture(Image.new('RGBA',(4,4),color),seed/'texture-template.rx3','gallery_cm',out/(name+'.rx3'))
    return out

if __name__=='__main__':print(build(sys.argv[1]))
