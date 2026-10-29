"""Execute the shipped APT payload, then render its actual named clip state."""
from pathlib import Path
import argparse,io,json,os,struct,sys

def main():
 p=argparse.ArgumentParser();p.add_argument('--game',required=True);p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);repo=Path(__file__).resolve().parents[4];source=repo/'ModCarrerMode/source';env=source/'club_environment';os.environ['SERVER16_GAME_ROOT']=a.game
 sys.path[:0]=[str(source),str(env),str(env/'vendor'),str(env/'bank'),str(env/'preview'),str(env/'market')]
 from screen import FULL,assets_for,scenes_for
 from native_review_vm import open_native
 from formats import Placement
 from PIL import Image,ImageDraw,ImageFont
 model=json.loads((out/'preview.json').read_text(encoding='utf8'));vm,state,apt,calls=open_native(out/'managermarket-review.big',full=FULL)
 frames=0;peak_steps=0
 for _ in range(1000):
  if state.get('dataReady'):break
  vm.invoke(state.get('DataFrame'),state);frames+=1;peak_steps=max(peak_steps,vm.steps)
 else:raise RuntimeError('Carregamento nativo não terminou')
 if vm.errors:raise RuntimeError(str(vm.errors))
 assets=assets_for(repo,model);scenes=scenes_for(model,assets)
 # Review the DDS pixels actually shipped in the BIG, including compression
 # and transparent block padding, rather than the pre-encoding source PNGs.
 textures=[e.data for e in apt.big.entries.values() if e.data.startswith(b'DDS ')]
 if len(textures)!=len(assets)+2:raise RuntimeError('Texture catalogue/order mismatch')
 invalid=[]
 for i,blob in enumerate(textures):
  height,width=struct.unpack_from('<II',blob,12)
  if width%4 or height%4:invalid.append(i)
 if invalid:raise RuntimeError('Native DXT block dimensions: '+str(invalid))
 def decoded(cid):
  char=apt.characters[cid]
  while char.type==5:
   cid=next(p.character for p in char.frames[0] if isinstance(p,Placement));char=apt.characters[cid]
  return apt.texture(char.texture)
 root={p.name:p.character for p in apt.characters[9].frames[0] if isinstance(p,Placement)}
 for i,scene in enumerate(scenes):
  placed=[p for p in apt.characters[root['scene'+str(i)]].frames[0] if isinstance(p,Placement)];placements={p.depth:p.character for p in placed};named={p.name:p.character for p in placed if p.name}
  for depth,node in enumerate(scene['nodes'],1):
   key=node.get('asset') if node['type']=='image' else node.get('background_asset') if node['type']=='action' else None
   cid=named.get(node.get('name')) if node.get('name') else named.get('action'+str(node['index'])) if node['type']=='action' else placements.get(depth)
   if key and cid is not None:
    image=decoded(cid)
    if image is None:raise RuntimeError('Native texture missing: '+key)
    assets[key]=image
 def render(filename,profile=False):
  scale=.7;im=Image.new('RGB',(1344,756),'#302b23');draw=ImageDraw.Draw(im);index=1 if profile else (0,3,4)[state.get('tab')];scene=scenes[index];clip=state.get('scene'+str(index))
  for n in scene['nodes']:
   c=None
   if n.get('name'):c=clip.get(n['name'])
   if n['type']=='action':c=clip.get('action'+str(n['index']))
   if c is not None and c.get('_visible') in (False,0):continue
   x=n['x'];y=n['y'];w=n['w'];h=n['h']
   if c is not None:
    for key in ('_width','_height'):
     value=c.get(key)
     if isinstance(value,(int,float)):
      if key=='_width':w=value
      else:h=value
    for key,old in (('_x',x),('_y',y)):
     value=c.get(key)
     if isinstance(value,(int,float)):
      if key=='_x':x=value
      else:y=value
   if w<=0 or h<=0:continue
   box=tuple(round(v*scale) for v in (x,y,x+w,y+h))
   if n['type'] in ('rect','action'):
    if n.get('background_asset') in assets:
     src=assets[n['background_asset']].resize((box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS);im.paste(src,(box[0],box[1]),src)
    else:draw.rectangle(box,fill=n['color'])
    if n['type']=='action' and c and c.get('selected').get('_alpha')==100:draw.rectangle(box,outline='#b9a274',width=2)
   if n['type'] in ('text','action'):
    value=n['text'];value=c.get('text') if n['type']=='text' and c is not None and isinstance(c.get('text'),str) else value
    if n['type']=='text' and c is not None and isinstance(c.get('text'),str):
     try:value=value.encode('latin1').decode('utf8')
     except (UnicodeEncodeError,UnicodeDecodeError):pass
    if not value:continue
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',max(9,round(n['size']*scale)));color=n.get('ink',n.get('color','#233847'));align=n.get('align',2 if n['type']=='action' else 0);tw=max(font.getlength(line) for line in str(value).split('\n'));tx=box[0]+((box[2]-box[0]-tw)/2 if align==2 else box[2]-box[0]-tw if align==1 else 0);draw.multiline_text((tx,box[1]+1),str(value),font=font,fill=color,spacing=2,align='center' if align==2 else 'right' if align==1 else 'left')
   if n['type']=='image' and n['asset'] in assets:
    src=assets[n['asset']].resize((max(1,box[2]-box[0]),max(1,box[3]-box[1])),Image.Resampling.LANCZOS);im.paste(src,(box[0],box[1]),src)
  im.save(out/filename)
 render('clubes.png');club_count=len(state.get('filtered'))
 vm.invoke(state.get('Command'),state,(40,));render('perfil.png',True)
 target=next((i for i,p in enumerate(model['people']) if p['name']=='Abel Braga'),0);state.set('person',target);vm.invoke(state.get('Refresh'),state);render('perfil-abel.png',True)
 for code,name in ((81,'passagens.png'),(82,'titulos.png')):vm.invoke(state.get('Command'),state,(code,));render(name,True)
 vm.invoke(state.get('Command'),state,(83,));render('estilo.png',True);vm.invoke(state.get('Command'),state,(80,));vm.invoke(state.get('Command'),state,(90,));render('perfil-casa.png',True)
 vm.invoke(state.get('Command'),state,(60,));vm.invoke(state.get('Command'),state,(1,));render('movimentacoes.png');vm.invoke(state.get('Command'),state,(2,));free_count=len(state.get('filtered'));render('livres.png');vm.invoke(state.get('Command'),state,(35,));age_count=len(state.get('filtered'));vm.invoke(state.get('Command'),state,(37,));nationality_count=len(state.get('filtered'))
 report=dict(class_name=FULL,apt_characters=len(apt.characters),club_rows_in_initial_league=club_count,free_available=free_count,age_filter_count=age_count,nationality_filter_count=nationality_count,vm_errors=vm.errors,unknown_opcodes=list(vm.unknown),loader_frames=frames,loader_peak_instructions=peak_steps,textures_checked=len(textures),native_dds_pixels_reviewed=True);(out/'native_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
