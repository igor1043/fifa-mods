"""Framed home/away minikits from FIFA's existing per-club assets."""
import io
from PIL import Image,ImageDraw
from room_interior_r71 import font


def texture(club,read_asset):
    im=Image.new('RGBA',(1024,1024),(243,240,234,255));d=ImageDraw.Draw(im)
    for kit in (0,1):
        x=kit*512
        d.rectangle((x+12,12,x+500,756),outline=(74,79,81),width=3)
        try:
            shirt=Image.open(io.BytesIO(read_asset(f'data/ui/imgassets/kits/j{kit}_{club}_0.dds'))).convert('RGBA')
            shirt.thumbnail((430,430),Image.Resampling.LANCZOS)
            # Enlarge the original transparent minikit uniformly; never replace
            # the actual away strip with the home strip or a made-up jersey.
            factor=min(430/shirt.width,430/shirt.height)
            shirt=shirt.resize((round(shirt.width*factor),round(shirt.height*factor)),Image.Resampling.LANCZOS)
            im.alpha_composite(shirt,(x+(512-shirt.width)//2,135+(430-shirt.height)//2))
        except (OSError,ValueError,FileNotFoundError):
            d.text((x+256,340),'Uniforme indisponível',font=font(25),fill=(109,113,116),anchor='mm')
        d.line((x+122,620,x+390,620),fill=(150,151,146),width=2)
        d.text((x+256,668),f'UNIFORME {kit+1}',font=font(29),fill=(46,56,61),anchor='mm')
    return im
