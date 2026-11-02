"""Competition economics from installed FCE hierarchy, never competition names."""
import csv
from pathlib import Path


def profiles(game):
 folder=Path(game)/'dlc/dlc_FootballCompEng/dlc/FootballCompEng/data/compdata'
 objects={int(r[0]):r for r in csv.reader((folder/'compobj.txt').read_text(encoding='utf-8-sig').splitlines()) if len(r)>=5 and r[0].isdigit()}
 settings={}
 for row in csv.reader((folder/'settings.txt').read_text(encoding='utf-8-sig').splitlines()):
  if len(row)==3 and row[0].isdigit():settings.setdefault(int(row[0]),{})[row[1]]=row[2]
 result={}
 for ident,row in objects.items():
  if row[1]!='3':continue
  options=settings.get(ident,{});mode=options.get('comp_type','');asset=int(options.get('asset_id',row[2][1:] if row[2][1:].isdigit() else 0))
  parent=objects.get(int(row[4]),[])
  importance=int(options.get('match_matchimportance',80))
  category='league' if mode=='LEAGUE' else 'supercup' if mode=='SUPERCUP' else 'cup'
  if parent and parent[1] in ('0','1'):category='world' if parent[1]=='0' else 'continental'
  result[ident]=dict(asset=asset,category=category,importance=importance,parent=int(row[4]),mode=mode)
 return result


def enrich(profile,metadata,league_asset):
 data=metadata.get(profile['root'],{})
 result=dict(profile,**{k:v for k,v in data.items() if k!='asset'})
 domestic=next((v for v in metadata.values() if v['asset']==league_asset and v['mode']=='LEAGUE'),None)
 if data.get('category') in ('cup','league') and domestic and data['parent']!=domestic['parent']:
  result['category']='regional'
 return result
