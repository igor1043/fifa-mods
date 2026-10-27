import portable_paths as portable
"""Native FIFA kit asset precedence; reads declarative RM assignments as data."""
import re,csv

def rules(text,club,league,info):
 # Conditional Lua is not evaluated by this read-only exporter.
 text=re.sub(r'--\[\[.*?\]\]','',text,flags=re.S)
 lines=[line.split('--',1)[0].strip() for line in text.splitlines()]
 if any(re.match(r'(if|for|while|function|repeat)\b',line) for line in lines):
  return {'default_league':league,'assignments':'complex Lua: database fallback'}
 regular={};tournament={};default=league
 for line in lines:
  m=re.fullmatch(r'(assignTeamTournament|assignKitDetails|assignTournamentKitDetails)\s*\((.*)\)\s*;?',line)
  if not m:continue
  fields=next(csv.reader([m[2]],skipinitialspace=True))
  if not fields or not fields[0].strip().isdigit() or int(fields[0])!=club:continue
  if m[1]=='assignTeamTournament':
   if len(fields)==2 and fields[1].strip().isdigit():default=int(fields[1]);continue
  if len(fields)!=(11 if m[1]=='assignTournamentKitDetails' else 10):continue
  try:
   kit=int(fields[1]);offset=3 if m[1]=='assignTournamentKitDetails' else 2
   values={'name_font':int(fields[offset]),'name_color':fields[offset+1].strip(),'layout':int(fields[offset+2]),'font':int(fields[offset+3]),'color':int(fields[offset+4])}
   target=tournament if offset==3 else regular
   if offset==2 or int(fields[2])==league:target[kit]=values
  except ValueError:continue
 for kit,base in info.items():
  for override in (regular.get(kit,{}),tournament.get(kit,{})):
   for key,value in override.items():
    if key=='name_color':
     if re.fullmatch('[0-9a-fA-F]{6}',value):base[key]=[int(value[i:i+2],16) for i in (0,2,4)]
    elif value>=0:base[key]=value
 return {'default_league':default,'assignments':'native declarative team rules'}

def number_candidates(club,typ,league,default,font,color):
 paths=[]
 for competition in dict.fromkeys((league,default,0)):
  paths.append(f'data/sceneassets/kitnumbers/specifickitnumbers_{club}_1_{competition}_{typ}.rx3')
 paths += [f'data/sceneassets/kitnumbers/specifickitnumbers_{club}_0_{league}_{color}.rx3',f'data/sceneassets/kitnumbers/specifickitnumbers_0_0_{league}_{color}.rx3',f'data/sceneassets/kitnumbers/specifickitnumbers_{club}_0_0_{color}.rx3',f'data/sceneassets/kitnumbers/specifickitnumbers_0_0_{default}_{color}.rx3',f'data/sceneassets/kitnumbers/specifickitnumbers_0_0_0_{color}.rx3',f'data/sceneassets/kitnumbers/kitnumbers_{font}_{color}.rx3','data/sceneassets/kitnumbers/kitnumbers_0_0.rx3']
 return list(dict.fromkeys(paths))

def name_candidates(club,typ,league,default,font):
 paths=[f'data/sceneassets/jerseyfonts/specificfont_{club}_1_{competition}_{typ}.ttf' for competition in dict.fromkeys((league,default,0))]
 paths += [f'data/sceneassets/jerseyfonts/specificfont_{club}_0_{league}_0.ttf',f'data/sceneassets/jerseyfonts/specificfont_0_0_{league}_0.ttf',f'data/sceneassets/jerseyfonts/specificfont_{club}_0_0_0.ttf',f'data/sceneassets/jerseyfonts/specificfont_0_0_0_{default}.ttf' if league==-1 else f'data/sceneassets/jerseyfonts/specificfont_0_0_{league}_{default}.ttf',f'data/sceneassets/jerseyfonts/specificfont_0_0_{default}_0.ttf','data/sceneassets/jerseyfonts/specificfont_0_0_0_0.ttf',f'data/sceneassets/jerseyfonts/font_{font}.ttf']
 return list(dict.fromkeys(paths))
