from ui_theme import ACCENT, ACCENT_SOFT
"""Supersampled chart textures embedded in the native APT, no web layer."""
from pathlib import Path
from functools import lru_cache
import os,math
from PIL import Image,ImageDraw,ImageFont

GREEN='#289b80';RED='#e44868';BLUE=ACCENT;GRID='#e5edf4';MUTED='#768ca1'
MONTHS=('JAN','FEV','MAR','ABR','MAI','JUN','JUL','AGO','SET','OUT','NOV','DEZ')

def font(size):
 return ImageFont.truetype(str(Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts/arial.ttf'),size)

@lru_cache(maxsize=40)
def panel(width,height):
 scale=2;w=int(width)*scale;h=int(height)*scale
 im=Image.new('RGBA',(w,h));draw=ImageDraw.Draw(im)
 draw.rounded_rectangle((1,1,w-2,h-2),radius=18*scale,fill='#fafdff',outline='#e2ebf4',width=scale)
 return im.resize((int(width),int(height)),Image.Resampling.LANCZOS)

def compact(number):
 value=abs(number)
 if value>=1_000_000:return ('-' if number<0 else '')+f'{value/1_000_000:.1f}'.replace('.',',')+' mi'
 if value>=1000:return ('-' if number<0 else '')+f'{value/1000:.0f}'+' mil'
 return str(int(number))

def chart_scale(series,observed):
 peak=max(1,max([max(r[:2]) for r in series[:observed]]+[0]));unit=10**math.floor(math.log10(peak))
 return math.ceil(peak/unit)*unit

def evolution(series,width=876,height=178,observed=12,labels=True):
 """Two comparable monthly bars. Net result is shown in the monthly table."""
 scale=2;im=Image.new('RGBA',(width*scale,height*scale));d=ImageDraw.Draw(im)
 left,top,right,bottom=65*scale,9*scale,(width-12)*scale,(height-29)*scale
 high=chart_scale(series,observed)
 def yy(v):return bottom-max(0,v)/high*(bottom-top)
 for i in range(4):
  value=high*i/3;y=yy(value);d.line((left,y,right,y),fill=GRID,width=scale)
  if labels:d.text((left-9*scale,y),compact(round(value)),font=font(14*scale),fill=MUTED,anchor='rm')
 step=(right-left)/12
 for i,(income,expense,result) in enumerate(series):
  x=left+(i+.5)*step;zero=yy(0);bar=step*.24
  if i<observed and income:d.rounded_rectangle((x-bar-2*scale,yy(income),x-2*scale,zero),radius=2*scale,fill=GREEN)
  if i<observed and expense:d.rounded_rectangle((x+2*scale,yy(expense),x+bar+2*scale,zero),radius=2*scale,fill=RED)
  d.text((x,bottom+12*scale),MONTHS[i],font=font(14*scale),fill=MUTED,anchor='mt')
 if not any(any(r[:2]) for r in series[:observed]):d.text(((left+right)/2,(top+bottom)/2),'Aguardando lançamentos',font=font(16*scale),fill=MUTED,anchor='mm')
 return im

def switch(enabled,width=92,height=36):
 scale=3;im=Image.new('RGBA',(width*scale,height*scale));d=ImageDraw.Draw(im)
 d.rounded_rectangle((0,0,width*scale-1,height*scale-1),radius=height*scale/2,fill=GREEN if enabled else '#aebecb')
 center=(width-height/2 if enabled else height/2)*scale;r=(height/2-4)*scale
 d.ellipse((center-r,height*scale/2-r,center+r,height*scale/2+r),fill='white')
 return im

def progress(fraction,color=GREEN,width=309,height=9):
 im=Image.new('RGBA',(width*3,height*3));d=ImageDraw.Draw(im);end=round(width*3*max(0,min(1,fraction)))
 d.rounded_rectangle((0,0,width*3-1,height*3-1),radius=height*1.5,fill='#e3ecf3')
 if end>height*3:d.rounded_rectangle((0,0,end-1,height*3-1),radius=height*1.5,fill=color)
 elif end:d.rectangle((0,0,end-1,height*3-1),fill=color)
 return im

@lru_cache(maxsize=80)
def glyph(kind,size=28,color='#163e67'):
 """Small category pictograms, drawn at 3x for the native white cards."""
 im=Image.new('RGBA',(96,96));d=ImageDraw.Draw(im);c=color
 if kind=='tv':
  d.rounded_rectangle((12,23,84,70),6,outline=c,width=7);d.line((36,12,48,23,60,12),fill=c,width=5);d.line((48,70,48,82,28,82,68,82),fill=c,width=5)
 elif kind=='ticket':
  d.rounded_rectangle((12,23,84,73),6,fill=c);d.ellipse((4,39,25,58),fill=(0,0,0,0));d.ellipse((71,39,92,58),fill=(0,0,0,0));d.line((61,30,61,67),fill='white',width=3)
 elif kind in ('coach','salary','staff'):
  d.ellipse((35,12,61,38),fill=c);d.rounded_rectangle((26,44,70,82),9,fill=c)
  if kind in ('salary','staff'):
   for x in (7,66):d.ellipse((x,24,x+21,45),fill=c);d.rounded_rectangle((x-2,50,x+24,79),7,fill=c)
 elif kind=='interest':
  d.line((29,74,68,20),fill=c,width=7);d.ellipse((15,15,40,40),outline=c,width=6);d.ellipse((56,56,81,81),outline=c,width=6)
 elif kind=='transfer':
  d.line((12,30,80,30,64,14),fill=c,width=7);d.line((80,30,64,46),fill=c,width=7)
  d.line((84,65,16,65,32,49),fill=c,width=7);d.line((16,65,32,81),fill=c,width=7)
 elif kind=='budget':
  d.rounded_rectangle((17,20,79,84),5,outline=c,width=6);d.line((34,8,34,29,62,29,62,8),fill=c,width=6)
  for x,h in ((30,17),(44,28),(58,40)):d.rectangle((x,75-h,x+8,75),fill=c)
 elif kind=='settings':
  for x,cy in ((23,33),(48,65),(73,38)):
   d.line((x,12,x,84),fill=c,width=5);d.rounded_rectangle((x-8,cy-9,x+8,cy+9),3,fill=c)
 elif kind=='sponsor':
  d.rounded_rectangle((12,20,84,77),6,outline=c,width=6);d.line((20,36,76,36),fill=c,width=5)
  d.polygon(((48,43),(52,52),(63,53),(55,61),(58,71),(48,66),(38,71),(41,61),(33,53),(44,52)),fill=c)
 elif kind=='match_costs':
  d.polygon(((14,40),(48,20),(82,40),(82,76),(14,76)),outline=c,width=5)
  for x in (28,47,66):d.rectangle((x,47,x+5,76),fill=c)
 else:
  d.rounded_rectangle((15,27,81,75),6,outline=c,width=6);d.rectangle((52,40,85,61),fill=c)
 return im.resize((max(96,size*3),max(96,size*3)),Image.Resampling.LANCZOS)

def donut(values,size=170):
 scale=3;im=Image.new('RGBA',(size*scale,size*scale));d=ImageDraw.Draw(im);box=(7*scale,7*scale,(size-7)*scale,(size-7)*scale)
 d.ellipse(box,outline='#e6edf5',width=25*scale);total=sum(max(0,v) for v in values)
 if total:
  angle=-90
  for value,color in zip(values,(BLUE,GREEN,'#8672bc')):
   end=angle+max(0,value)*360/total
   if end>angle:d.arc(box,start=angle,end=end,fill=color,width=25*scale)
   angle=end
 return im

def spark(values,color=BLUE,width=90,height=24):
 im=Image.new('RGBA',(width*2,height*2));d=ImageDraw.Draw(im)
 if len(values)<2:return im
 low=min(values);high=max(values);span=max(1,high-low)
 points=[(4+i*(width*2-8)/(len(values)-1),height*2-4-(v-low)/span*(height*2-8)) for i,v in enumerate(values)]
 d.line(points,fill=color,width=3)
 return im

def icon(kind,size=34):
 im=Image.new('RGBA',(size*3,size*3));d=ImageDraw.Draw(im);c=BLUE if kind in ('wallet','income') else RED if kind=='expense' else GREEN
 d.rounded_rectangle((0,0,size*3-1,size*3-1),radius=21,fill='#e5f1ff' if kind in ('wallet','income') else '#ffedf1' if kind=='expense' else '#e6f5f0')
 if kind=='wallet':
  d.rounded_rectangle((23,28,80,73),radius=6,fill=c);d.rectangle((61,42,83,61),fill=ACCENT_SOFT);d.ellipse((68,48,73,53),fill=c)
 elif kind=='result':
  for i,h in enumerate((19,30,43,59)):d.rectangle((21+i*15,77-h,29+i*15,77),fill=c)
 else:
  cy=46;d.line((51,22,51,79),fill=c,width=7)
  d.line((33,40,51,22,69,40) if kind=='income' else (33,61,51,79,69,61),fill=c,width=7)
 return im
