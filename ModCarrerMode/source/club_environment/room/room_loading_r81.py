"""Sharp, compact native loading slate and a separate live progress surface."""
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


def artwork(error=False):
    im=Image.new('RGBA',(1920,1080),(24,39,48,255));d=ImageDraw.Draw(im)
    ink=(22,49,63);muted=(104,127,143);gold=rgba(ACCENT)[:3]
    def text(pos,value,size,fill=ink):
        d.text(pos,value,font=ImageFont.truetype(str(portable.FONTS/'arialbd.ttf'),size),fill=fill)
    d.rectangle((0,0,1919,9),fill=gold)
    d.rounded_rectangle((170,235,1750,870),radius=24,fill=(255,255,255),outline=(218,227,233),width=2)
    d.rounded_rectangle((260,300,344,384),radius=16,fill=(242,236,222))
    # Locker silhouette uses clean lines instead of another raster logo.
    d.rounded_rectangle((282,316,323,371),radius=4,outline=gold,width=4)
    d.line((302,318,302,369),fill=gold,width=3)
    for y in (326,333):d.line((287,y,297,y),fill=gold,width=2);d.line((308,y,318,y),fill=gold,width=2)
    text((370,302),'VESTIÁRIO 3D',24,muted)
    text((370,345),'Não foi possível preparar a cena' if error else 'Preparando o vestiário',56)
    text((280,443),'Volte e entre novamente para tentar carregar os recursos.' if error else 'Organizando o elenco e os recursos visuais do clube.',29,muted)
    labels=('Recursos do clube','Modelos e texturas','Montagem da cena')
    for i,label in enumerate(labels):
        x=280+i*470
        d.rounded_rectangle((x,540,x+420,645),radius=12,fill=(246,248,250),outline=(229,235,239),width=2)
        d.ellipse((x+20,566,x+68,614),fill=(242,236,222))
        text((x+35,574),str(i+1),24,gold);text((x+86,577),label,25)
    d.rounded_rectangle((BAR_LEFT,BAR_TOP,BAR_RIGHT,BAR_BOTTOM),radius=7,fill=(224,232,237))
    text((280,768),'Use Voltar para sair desta tela.' if error else 'A cena abre automaticamente quando todos os recursos estiverem prontos.',25,muted)
    return im


def stage(game,output):
    game,output=Path(game),Path(output);output.mkdir(parents=True,exist_ok=True)
    template=game/(PREFIX+'shared/loading_slate_r56.rx3')
    for name,shape in (
        ('loading_panel_r81.rx3',panel([0,CENTER_Y,400],WIDTH,HEIGHT)),
        ('loading_progress_r81.rx3',panel([BAR_WIDTH/2,BAR_Y,400.2],BAR_WIDTH,(BAR_BOTTOM-BAR_TOP)*HEIGHT/1080))):
        rx=Rx3(template.read_bytes());replace_mesh(rx,0,*shape);(output/name).write_bytes(rx.build())
    for name,error in (('loading_panel_texture_r81.rx3',False),('loading_error_texture_r81.rx3',True)):
        im=artwork(error);texture_package(im,output/name,'slate_cm')
    texture_package(Image.new('RGBA',(8,8),rgba(ACCENT)),output/'loading_progress_texture_r81.rx3','slate_cm')
    return dict(revision=81,bar_x=BAR_X,bar_width=BAR_WIDTH,bar_y=BAR_Y,progress='loaded native resources / requested native resources')


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    print(json.dumps(stage(portable.GAME,args.output),indent=2))
