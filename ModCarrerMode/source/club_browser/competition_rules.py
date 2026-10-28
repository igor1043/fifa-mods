"""Read the installed competition's colour slots; never infer zones by team count."""
from pathlib import Path
from collections import defaultdict
import csv

COLORS={'champion':'#c2a345','continental':'#2c86ce','secondary':'#d4aa45','extra':'#4fa18a','promotion':'#36a2bb','highlight':'#91a7b2','relegation':'#d45f64','playoff':'#bd8f48','advance':'#2c86ce'}
def read_rules(game,asset,group,labels):
 folder=Path(game)/'dlc/dlc_FootballCompEng/dlc/FootballCompEng/data/compdata'
 def read(name):return list(csv.reader((folder/(name+'.txt')).read_text(encoding='utf-8-sig').splitlines()))
 objects={int(r[0]):r for r in read('compobj') if len(r)>=5 and r[0].isdigit()};settings=read('settings');advancement=read('advancement')
 roots=[n for n,r in objects.items() if r[1]=='3' and r[2]=='C'+str(asset)]
 if len(roots)!=1:return [],{}
 root=roots[0]
 def ancestor(node,kind):
  seen=set()
  while node in objects and node not in seen:
   seen.add(node);r=objects[node]
   if r[1]==str(kind):return node
   node=int(r[4])
  return None
 if group not in objects or ancestor(group,3)!=root:return [],{}
 confed=ancestor(root,1);confed_key=objects[confed][2] if confed is not None else ''
 confed_assets=[int(r[2][1:]) for n,r in objects.items() if r[1]=='3' and r[2].startswith('C') and r[2][1:].isdigit() and ancestor(n,1)==confed]
 def named(part,fallback):
  return next((labels.get(a,'').replace('CONMEBOL ','').replace('UEFA ','') for a in confed_assets if part in labels.get(a,'').casefold() and 'recopa' not in labels.get(a,'').casefold()),fallback)
 main=named('libertadores','Competição continental principal') if confed_key=='CNBL' else named('champions','Competição continental principal')
 secondary=named('sudamericana','Competição continental adicional') if confed_key=='CNBL' else named('europa','Competição continental adicional')
 root_settings={r[1]:r[2] for r in settings if len(r)==3 and r[0]==str(root)}
 promo=root_settings.get('info_league_promo');releg=root_settings.get('info_league_releg')
 definitions={
  'info_color_slot_champ':('champion','Campeão'),
  'info_color_slot_champ_cup':('continental',main),
  'info_color_slot_euro_league':('extra',secondary),
  'info_color_slot_promo':('promotion','Acesso') if promo else ('highlight','Destaque da liga'),
  'info_color_slot_promo_poss':('playoff','Play-off de acesso'),
  'info_color_slot_releg':('relegation','Rebaixamento'),
  'info_color_slot_releg_poss':('playoff','Play-off de permanência'),
  'info_color_slot_adv_group':('advance','Classificação à próxima fase')}
 legend=[];zones={}
 for key,(kind,label) in definitions.items():
  ranks=sorted({int(r[2]) for r in settings if len(r)==3 and r[0]==str(group) and r[1]==key and r[2].isdigit()})
  if not ranks:continue
  # A cup group can send its third club into another continental competition.
  destinations={ancestor(int(r[2]),3) for r in advancement if len(r)>=4 and r[0]==str(group) and r[1].isdigit() and int(r[1]) in ranks and r[2].isdigit()}
  destination_assets={int(objects[n][2][1:]) for n in destinations if n in objects and objects[n][2].startswith('C') and objects[n][2][1:].isdigit() and n!=root}
  if len(destination_assets)==1:label=labels.get(next(iter(destination_assets)),label).replace('CONMEBOL ','').replace('UEFA ','')
  item=dict(key=kind,label=label,color=COLORS[kind],ranks=ranks,source=f'settings.txt · {group} · {key}')
  legend.append(item)
  for rank in ranks:zones[rank]=item
 return legend,zones
