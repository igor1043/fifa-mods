"""Small, local card textures; all labels and controls remain native APT."""
from PIL import Image,ImageDraw

def panel(width,height,top,bottom,border,radius=10):
    image=Image.new('RGBA',(width,height));draw=ImageDraw.Draw(image)
    first=tuple(bytes.fromhex(top.lstrip('#')));last=tuple(bytes.fromhex(bottom.lstrip('#')))
    for y in range(height):
        t=y/max(1,height-1);draw.line((0,y,width,y),fill=tuple(round(a+(b-a)*t) for a,b in zip(first,last))+(255,))
    mask=Image.new('L',image.size);ImageDraw.Draw(mask).rounded_rectangle((1,1,width-2,height-2),radius,fill=255)
    image.putalpha(mask);ImageDraw.Draw(image).rounded_rectangle((1,1,width-2,height-2),radius,outline=border,width=2)
    return image

def textures():
    header=panel(1152,120,'#e7f1f9','#e7f1f9','#cedce8')
    draw=ImageDraw.Draw(header)
    for x in range(760,1150,60):draw.line((x+100,1,x-80,119),fill='#c8dce9',width=2)
    return {
        'bank_idle':panel(576,96,'#edf3f7','#edf3f7','#cfdbe4'),
        'bank_selected':panel(576,96,'#0877c9','#004b91','#35b8ff'),
        'header':header,
        'options':panel(496,352,'#f7fbff','#f7fbff','#d5e0e8'),
        'summary':panel(640,464,'#f7fbff','#f7fbff','#d5e0e8'),
        'action_idle':panel(496,80,'#edf3f7','#edf3f7','#d0dde7'),
        'action_selected':panel(496,80,'#147fc6','#075a9e','#35b8ff'),
    }
