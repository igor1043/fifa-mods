"""Native loading card, overscan backing, club badge and animated activity ring."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
import portable_paths as portable
from ui_theme import ACCENT,rgba
from rx3 import Rx3
from room_visual_r68 import replace_mesh
from room_interior_r71 import panel
from room_native_hanging_20261022 import texture_package

PREFIX='data/sceneassets/server16_dressing_room_v3/'
WIDTH,HEIGHT=900.,506.25
CENTER_Y=1184.
BAR_LEFT=280;BAR_RIGHT=1640;BAR_TOP=716;BAR_BOTTOM=730
BAR_WIDTH=(BAR_RIGHT-BAR_LEFT)*WIDTH/1920
BAR_X=(BAR_LEFT-960)*WIDTH/1920
BAR_Y=CENTER_Y+(540-(BAR_TOP+BAR_BOTTOM)/2)*HEIGHT/1080
BADGE_X=(355-960)*WIDTH/1920
BADGE_Y=CENTER_Y+(540-355)*HEIGHT/1080
BADGE_SIZE=94*WIDTH/1920
REVISION=82


def artwork(error=False):
    # Keep the loading state legible over the full-screen native backing. The
    # old navy backdrop and pale card made the scene feel dim before the room
    # had even finished loading.
    im=Image.new('RGBA',(1920,1080),(247,249,250,255));d=ImageDraw.Draw(im)
    ink=(25,48,60);muted=(94,117,130);gold=rgba(ACCENT)[:3]
    def text(pos,value,size,fill=ink):
        d.text(pos,value,font=ImageFont.truetype(str(portable.FONTS/'arialbd.ttf'),size),fill=fill)
    # Soft card shadow, crisp white surface, and a restrained gold header.
    d.rounded_rectangle((178,244,1758,882),radius=27,fill=(218,225,229))
    d.rounded_rectangle((170,232,1750,870),radius=27,fill=(255,255,255),outline=(218,227,233),width=2)
    d.rounded_rectangle((170,232,1750,244),radius=6,fill=gold)
    d.rounded_rectangle((280,280,430,430),radius=30,fill=(250,250,248),outline=(231,225,211),width=3)
    text((480,292),'VESTIÁRIO 3D',23,muted)
    text((480,337),'Falha ao preparar a cena' if error else 'Preparando o vestiário',54)
    text((280,443),'Volte e entre novamente para tentar carregar os recursos.' if error else 'Organizando o elenco e os recursos visuais do clube.',29,muted)
    labels=('Recursos do clube','Modelos e texturas','Montagem da cena')
    for i,label in enumerate(labels):
        x=280+i*470
        d.rounded_rectangle((x,540,x+420,645),radius=14,fill=(249,250,251),outline=(220,229,234),width=2)
        d.rounded_rectangle((x,540,x+420,548),radius=4,fill=(238,232,219))
        d.ellipse((x+20,566,x+68,614),fill=(242,236,222),outline=(225,214,190),width=2)
        text((x+35,574),str(i+1),24,gold);text((x+86,577),label,25)
    d.rounded_rectangle((BAR_LEFT,BAR_TOP,BAR_RIGHT,BAR_BOTTOM),radius=7,fill=(227,233,236))
    text((280,768),'Use Voltar para sair desta tela.' if error else 'A entrada será automática quando a cena estiver pronta.',25,muted)
    return im


def stage(game,output):
    game,output=Path(game),Path(output);output.mkdir(parents=True,exist_ok=True)
    template=game/(PREFIX+'shared/loading_slate_r56.rx3')
    for name,shape in (
        ('loading_backdrop_r82.rx3',panel([0,CENTER_Y,399],4000,2500)),
        ('loading_panel_r82.rx3',panel([0,CENTER_Y,400],WIDTH,HEIGHT)),
        ('loading_badge_r82.rx3',panel([0,0,0],BADGE_SIZE,BADGE_SIZE)),
        ('loading_ring_r82.rx3',panel([0,0,0],144*WIDTH/1920,144*HEIGHT/1080)),
        ('loading_progress_r82.rx3',panel([BAR_WIDTH/2,BAR_Y,400.2],BAR_WIDTH,(BAR_BOTTOM-BAR_TOP)*HEIGHT/1080))):
        rx=Rx3(template.read_bytes());replace_mesh(rx,0,*shape);(output/name).write_bytes(rx.build())
    for name,error in (('loading_panel_texture_r82.rx3',False),('loading_error_texture_r82.rx3',True)):
        im=artwork(error);texture_package(im,output/name,'slate_cm')
    texture_package(Image.new('RGBA',(8,8),(247,249,250,255)),output/'loading_backdrop_texture_r82.rx3','slate_cm')
    texture_package(Image.new('RGBA',(8,8),rgba(ACCENT)),output/'loading_progress_texture_r82.rx3','slate_cm')
    ring=Image.new('RGBA',(512,512));d=ImageDraw.Draw(ring)
    d.ellipse((26,26,486,486),outline=(222,228,231,255),width=18)
    d.arc((26,26,486,486),-90,65,fill=rgba(ACCENT),width=22)
    d.ellipse((36,36,476,476),outline=(255,255,255,110),width=2)
    texture_package(ring,output/'loading_ring_texture_r82.rx3','slate_cm')
    return dict(revision=REVISION,bar_x=BAR_X,bar_width=BAR_WIDTH,bar_y=BAR_Y,
                badge_x=BADGE_X,badge_y=BADGE_Y,badge_size=BADGE_SIZE,
                backdrop='overscan, behind card, all supported camera aspect ratios',
                progress='loaded native resources / requested native resources')


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    print(json.dumps(stage(portable.GAME,args.output),indent=2))
