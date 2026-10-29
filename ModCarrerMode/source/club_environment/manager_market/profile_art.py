"""Code-drawn profile artwork: antialiased icons, panels and pitch diagrams."""
import math,re
from PIL import Image,ImageDraw
from ui_theme import ACCENT,ACCENT_INK

def panel(w,h,fill='#ffffff',radius=12,stroke='#e2e9ee'):
 scale=2;im=Image.new('RGBA',(w*scale,h*scale));d=ImageDraw.Draw(im)
 d.rounded_rectangle((1,1,w*scale-2,h*scale-2),radius*scale,fill=fill,outline=stroke,width=scale)
 return im.resize((w,h),Image.Resampling.LANCZOS)

def gradient(w,h,left,right,radius=6):
 def rgb(c):return tuple(int(c[i:i+2],16) for i in (1,3,5))
 a,b=rgb(left),rgb(right);im=Image.new('RGBA',(w*2,h*2));d=ImageDraw.Draw(im)
 for x in range(w*2):
  t=x/max(1,w*2-1);d.line((x,0,x,h*2),fill=tuple(round(c*(1-t)+v*t) for c,v in zip(a,b))+(255,))
 mask=Image.new('L',im.size);ImageDraw.Draw(mask).rounded_rectangle((0,0,w*2-1,h*2-1),radius*2,fill=255);im.putalpha(mask)
 return im.resize((w,h),Image.Resampling.LANCZOS)

def glyph(kind,size=128):
 im=Image.new('RGBA',(192,192));d=ImageDraw.Draw(im);c=ACCENT_INK
 if kind=='pitch':
  d.rectangle((24,42,168,150),outline=c,width=9);d.line((96,42,96,150),fill=c,width=7);d.ellipse((78,78,114,114),outline=c,width=7);d.rectangle((24,72,49,120),outline=c,width=7);d.rectangle((143,72,168,120),outline=c,width=7)
 elif kind=='trophy':
  d.polygon(((58,25),(136,25),(128,87),(111,112),(82,112),(66,87)),fill=c);d.line((58,35,28,35,31,65,45,82,67,88),fill=c,width=8);d.line((136,35,165,35,161,65,148,82,126,88),fill=c,width=8);d.rectangle((89,109,105,146),fill=c);d.rounded_rectangle((59,147,137,163),5,fill=c)
 elif kind=='handshake':
  d.line((18,58,49,43,77,59,102,48,139,58,169,44,177,83,155,98,117,134,98,146,81,135,66,131,34,103,19,111,10,72,18,58),fill=c,width=7,joint='curve');d.line((48,44,46,78,30,102),fill=c,width=7);d.line((140,58,143,87,161,98),fill=c,width=7);d.line((76,59,61,80,78,93,104,74,144,111),fill=c,width=7);d.line((71,103,104,132),fill=c,width=5);d.line((87,95,123,122),fill=c,width=5)
 elif kind=='cross':d.line((43,43,149,149),fill=c,width=13);d.line((149,43,43,149),fill=c,width=13)
 elif kind=='ball':
  d.ellipse((22,22,170,170),outline=c,width=8);points=[(96+33*math.sin(i*math.tau/5),94-33*math.cos(i*math.tau/5)) for i in range(5)];d.polygon(points,fill=c)
  for i,(x,y) in enumerate(points):
   a=i*math.tau/5;X,Y=96+72*math.sin(a),96-72*math.cos(a);d.line((x,y,X,Y),fill=c,width=6);d.ellipse((X-12,Y-12,X+12,Y+12),fill=c)
 elif kind=='shield':d.line((97,22,155,41,149,98,128,135,97,169,64,135,43,98,37,41,97,22),fill=c,width=9,joint='curve')
 elif kind=='chevron':d.line((121,38,68,96,121,154),fill=c,width=13,joint='curve')
 elif kind=='arrow':d.line((55,76,96,117,137,76),fill=c,width=10,joint='curve')
 elif kind=='tactics':
  for x,y in ((45,45),(143,45),(96,136)):
   d.ellipse((x-15,y-15,x+15,y+15),outline=c,width=7)
  d.line((45,65,45,126,75,126),fill=c,width=6);d.line((143,65,143,126,116,126),fill=c,width=6);d.line((127,116,143,126,127,136),fill=c,width=6)
 elif kind=='coach':
  d.ellipse((66,26,126,86),fill=c);d.rounded_rectangle((40,101,152,164),20,fill=c);d.polygon(((86,101),(106,101),(96,139)),fill='white')
 return im.resize((size,size),Image.Resampling.LANCZOS)

def assets():
 result={}
 sizes=dict(identity=(366,712),metric=(210,150),venue=(432,180),summary=(1320,226),entry=(1320,166),timeline=(690,120),style=(650,250),pitch=(450,450))
 for name,(w,h) in sizes.items():result['profile_'+name]=panel(w,h)
 result['profile_tab_off']=panel(318,52,'#eaf0f4',7,'#eaf0f4');result['profile_tab_on']=gradient(318,52,'#ac8950',ACCENT,7)
 result['profile_back']=panel(160,48,radius=10);result['profile_filter']=panel(242,36,'#eaf0f4',8,'#eaf0f4');result['profile_clear']=Image.new('RGBA',(4,4))
 result['profile_gold_bar']=gradient(392,12,'#ac8950',ACCENT);result['profile_navy_bar']=gradient(392,12,'#082c46','#163f57');result['profile_track']=gradient(392,12,'#cedae3','#e0e7ec')
 result['profile_tag']=panel(90,30,'#f7f0e2',7,'#f7f0e2')
 for kind in ('pitch','trophy','handshake','cross','ball','shield','chevron','arrow','tactics','coach'):result['profile_icon_'+kind]=glyph(kind)
 for code,fill in (('V','#27a559'),('E','#9daab4'),('D','#ce3042')):
  im=Image.new('RGBA',(72,72));d=ImageDraw.Draw(im);d.ellipse((5,6,67,68),fill='#dce4e7');d.ellipse((4,2,66,64),fill=fill,outline='white',width=3);result['profile_form_'+code]=im
 photo=gradient(322,202,'#e5ebef','#f5f7f9',8);d=ImageDraw.Draw(photo)
 for x in (-180,-70,60,195):d.polygon(((x,202),(x+95,202),(x+300,0),(x+205,0)),fill='#dae1e6')
 d.polygon(((230,202),(271,202),(322,151),(322,110)),fill='#c7b58f');result['profile_photo']=photo
 result['profile_pitch_empty']=pitch('')
 dot=Image.new('RGBA',(36,36));ImageDraw.Draw(dot).ellipse((2,2,33,33),fill=ACCENT,outline='white',width=2);result['profile_dot']=dot
 return result

def formation(value):
 values=[int(v) for v in str(value).replace('–','-').split('-') if v.isdigit()]
 return values if len(values) in (3,4,5) and sum(values)==10 and all(0<n<=5 for n in values) else []

def pitch(value):
 im=panel(440,430,'#edf3f4',12,'#d9e3e7');d=ImageDraw.Draw(im);box=(25,20,415,410);line='#a8bac4'
 d.rectangle(box,outline=line,width=2);d.line((25,215,415,215),fill=line,width=2);d.ellipse((167,177,273,253),outline=line,width=2);d.rectangle((132,20,308,75),outline=line,width=2);d.rectangle((132,355,308,410),outline=line,width=2)
 rows=formation(value)
 if rows:
  points=[(220,382)]+[(25+390*(i+1)/(count+1),345-275*(row+1)/len(rows)) for row,count in enumerate(rows) for i in range(count)]
  for x,y in points:d.ellipse((x-12,y-12,x+12,y+12),fill=ACCENT,outline='white',width=3)
 return im
