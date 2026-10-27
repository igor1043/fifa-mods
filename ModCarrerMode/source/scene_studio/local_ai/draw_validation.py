from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
ROOT=Path(__file__).resolve().parent.parent;capture=json.loads((ROOT/'build/tests/ai-reference.json').read_text());image=Image.open(ROOT/'reference.png').convert('RGB');draw=ImageDraw.Draw(image)
edges=[(5,6),(5,7),(7,9),(6,8),(8,10),(5,11),(6,12),(11,12),(11,13),(13,15),(12,14),(14,16),(15,17),(16,20)]
colors=['#77e3ca','#f4ca7b','#95c3ff','#f9a7cb','#c3e684','#d0b0ff']
font=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',18)
for i,p in enumerate(capture['people']):
 color=colors[i%len(colors)];x,y,r,b=p['bbox'];draw.rectangle((x,y,r,b),outline=color,width=2);draw.text((x+3,max(0,y-20)),str(i+1),fill=color,font=font)
 for a,b in edges:
  if min(p['keypoints2d'][a][2],p['keypoints2d'][b][2])<.3:continue
  draw.line((*p['keypoints2d'][a][:2],*p['keypoints2d'][b][:2]),fill=color,width=3)
 for x,y,s in p['keypoints2d'][:23]:
  if s>=.3:draw.ellipse((x-3,y-3,x+3,y+3),fill='#ffffff')
image.save(ROOT/'build/tests/ai-detection-preview.png')
