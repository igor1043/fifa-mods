"""Read-only complete club roster, sharing the validated career projection cache."""
from pathlib import Path
from lineup_data import ProjectionCache,APPEARANCE,ATTRIBUTES,pack_fixture,starting_sheet
from kit_selection import current_kits
POSITIONS=('GOL','LIB','ALA D','LD','ZAG','ZAG','ZAG','LE','ALA E','VOL','VOL','VOL','MD','MC','MC','MC','ME','MEI','MEI','MEI','SA','SA','SA','PD','ATA','ATA','ATA','PE')

def project(game,save,club,cache=None,season=None):
 cache=cache or ProjectionCache();raw,dbs,base=cache.load(game,save)
 def table(name,fields):
  matches=[db for db in dbs if name in db.tables];db=matches[0] if len(matches)==1 else base
  return cache.table(db,name,fields) if name in db.tables else []
 team=next((r for r in table('teams',['teamid','teamname','captainid','teamcolor1r','teamcolor1g','teamcolor1b']) if r['teamid']==club),None)
 if not team:raise ValueError('Clube indisponível nesta carreira.')
 links=[r for r in table('teamplayerlinks',['teamid','playerid','position','jerseynumber']) if r['teamid']==club]
 if not 1<=len(links)<=100 or len({r['playerid'] for r in links})!=len(links):raise ValueError('Elenco inválido ou duplicado.')
 ids={r['playerid'] for r in links};fields=list(dict.fromkeys(['playerid','commonnameid','firstnameid','lastnameid','playerjerseynameid','preferredposition1','preferredposition2','preferredposition3','preferredposition4','overallrating','nationality','preferredfoot','birthdate',*APPEARANCE,*ATTRIBUTES]))
 players={r['playerid']:r for r in cache.matching(base,'players',fields,'playerid',ids)}
 for db in dbs:
  if 'players' in db.tables:
   for row in cache.matching(db,'players',fields,'playerid',ids):players.setdefault(row['playerid'],{}).update({k:v for k,v in row.items() if v is not None})
 wanted={p.get(k) for p in players.values() for k in ('commonnameid','firstnameid','lastnameid','playerjerseynameid')};wanted.discard(None)
 names={r['nameid']:r['name'] for r in cache.matching(base,'playernames',['nameid','name'],'nameid',wanted)}
 names.update({r['nameid']:r['name'] for r in table('dcplayernames',['nameid','name']) if r['nameid'] in wanted})
 edited={r['playerid']:r for r in table('editedplayernames',['playerid','firstname','surname','commonname','playerjerseyname']) if r['playerid'] in ids}
 translations={'Brazil':'Brasil','Italy':'Itália','France':'França','Germany':'Alemanha','Spain':'Espanha','England':'Inglaterra','Uruguay':'Uruguai','Colombia':'Colômbia','Bolivia':'Bolívia','Mexico':'México','Belgium':'Bélgica','Netherlands':'Países Baixos','Switzerland':'Suíça','Denmark':'Dinamarca','Sweden':'Suécia','Austria':'Áustria','Scotland':'Escócia','Wales':'País de Gales','Japan':'Japão','South Korea':'Coreia do Sul','United States':'Estados Unidos','South Africa':'África do Sul','Cameroon':'Camarões','Egypt':'Egito','Nigeria':'Nigéria','Russia':'Rússia','Greece':'Grécia','Croatia':'Croácia','Serbia':'Sérvia','Australia':'Austrália'}
 nations={r['nationid']:translations.get(r['nationname'],r['nationname']) for r in cache.table(base,'nations',['nationid','nationname'])}
 from season_stats import age,totals
 try:statistics=totals(season,club)
 except ValueError:statistics={}
 try:starters={r['playerid'] for _,r in starting_sheet(table,club,{r['playerid']:r for r in links})}
 except ValueError:starters=None
 kit_fields=['teamtechid','teamid','teamkittypetechid','year','teamkitid','numberfonttype','numbercolor','jerseynamefonttype',*('jerseynamecolor'+c for c in 'rgb'),'jerseynamelayouttype']
 kits=current_kits(table('teamkits',kit_fields),club)
 leagues=[r['leagueid'] for r in table('leagueteamlinks',['teamid','leagueid']) if r['teamid']==club];league=leagues[0] if len(leagues)==1 else 0
 result=[]
 for link in sorted(links,key=lambda l:(l['position'] if l['position'] is not None else 99,l['playerid'])):
  p=players.get(link['playerid'])
  if not p or p.get('height') is None or not 130<=p['height']<=230:continue
  fixture,labels=pack_fixture(club,team['teamname'],team,players,[(link['position'] if link['position'] is not None else 99,link)],names,edited,roster=True)
  row=labels[0];pos=p.get('preferredposition1',-1);row.update(position=POSITIONS[pos] if pos is not None and 0<=pos<28 else '—',height=p['height'],weight=p.get('weight',0),foot={1:'Direito',2:'Esquerdo'}.get(p.get('preferredfoot'),'—'),nationality=nations.get(p.get('nationality'),'—'),attributes={k:p.get(k,-1) for k in ATTRIBUTES},fixture=fixture)
  kit=kits.get(2 if pos==0 else 0,{})
  row.update(club=club,league=league,jersey_name=edited.get(p['playerid'],{}).get('playerjerseyname') or names.get(p.get('playerjerseynameid')) or names.get(p.get('commonnameid')) or names.get(p.get('lastnameid')) or row['name'],kit_rules=dict(font=kit.get('numberfonttype') or 0,color=kit.get('numbercolor') or 0,name_font=kit.get('jerseynamefonttype') or 0,name_color=[kit.get('jerseynamecolor'+c) if kit.get('jerseynamecolor'+c) is not None else 255 for c in 'rgb'],layout=kit.get('jerseynamelayouttype') or 0))
  row.update(age=age(p.get('birthdate'),season.get('date')) if season else -1,starter=int(row['id'] in starters) if starters is not None else -1,performance=statistics.get(row['id'],(0,0,0,0)) if statistics else (-1,-1,-1,-1),secondary=[POSITIONS.get(value,'—') if isinstance(POSITIONS,dict) else POSITIONS[value] if isinstance(value,int) and 0<=value<28 else '—' for value in (p.get('preferredposition2'),p.get('preferredposition3'),p.get('preferredposition4'))])
  result.append(row)
 if not result:raise ValueError('Nenhum jogador com aparência válida neste clube.')
 return dict(club=club,name=team['teamname'],players=result,save_hash=cache.save_hash)

def tsv(data):
 def safe(value):return str(value).replace('\t',' ').replace('\r',' ').replace('\n',' ')[:180]
 rows=['S16ROSTER2\t'+str(data['club'])+'\t'+safe(data['name'])]
 for p in data['players']:
  rows.append('\t'.join(map(safe,[p['id'],p['name'],p['number'],p['position'],p['overall'],p['height'],p['weight'],p['foot'],p['nationality'],*(p['attributes'].get(k,-1) for k in ATTRIBUTES),p.get('age',-1),p.get('starter',-1),*p.get('performance',(-1,-1,-1,-1)),*p.get('secondary',('—','—','—'))])))
 return ('\n'.join(rows)+'\n').encode('utf8')
