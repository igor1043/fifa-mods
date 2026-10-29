"""Build the editable SQL catalogue from the researched workbook intermediate."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,sqlite3,unicodedata
from engine import DEFAULTS

def key(name):
 n=''.join(c for c in unicodedata.normalize('NFKD',str(name)) if not unicodedata.combining(c)).casefold()
 n=re.sub(r'\b\d+\b',' ',n);n=re.sub('[^a-z ]',' ',n);n=' '.join(n.split())
 return {'adenor tite':'tite','xavi':'xavi hernandez','renato gaucho':'renato portaluppi','ze ricardo':'jose ricardo'}.get(n,n)
def ident(name):return 'COACH-'+hashlib.sha256(key(name).encode()).hexdigest()[:16]
# Gameplay calibration, not a claim of an official real-world rating.
RATINGS={'zinedine zidane':9,'carlo ancelotti':10,'jurgen klopp':10,'joachim low':8,
 'hansi flick':9,'xavi hernandez':8,'jose mourinho':9,'antonio conte':9,'diego simeone':9,
 'arsene wenger':9,'alex ferguson':10,'vanderlei luxemburgo':7,'abel braga':7,
 'roger machado':6,'renato portaluppi':7,'andre villas boas':7,'frank lampard':6,
 'steven gerrard':6,'ole gunnar solskjaer':7,'gareth southgate':8,'tite':8,
 'dorival junior':8,'marcelo gallardo':8,'ramon diaz':7,'luiz felipe scolari':8,'dunga':7}
def region(country):
 if country in ('Brazil','Argentina','Uruguay','Paraguay','Chile','Peru','Bolivia','Ecuador','Colombia','Venezuela'):return 'América do Sul'
 if country in ('United States','Canada','Mexico','Costa Rica','Honduras','Panama','Jamaica','El Salvador','Guatemala','Trinidad and Tobago','Haiti','Cuba'):return 'América do Norte'
 if country in ('Australia','New Zealand','Fiji','Papua New Guinea'):return 'Oceania'
 if country in ('Japan','China PR','Korea Republic','Saudi Arabia','India','Qatar','Iran','Iraq','Thailand','Indonesia','Malaysia','United Arab Emirates','Uzbekistan','Vietnam','Singapore'):return 'Ásia'
 if country in ('South Africa','Egypt','Morocco','Algeria','Tunisia','Nigeria','Ghana','Cameroon','Senegal','Ivory Coast','Côte d’Ivoire','DR Congo','Angola','Zambia','Guinea','Mali','Gabon'):return 'África'
 return 'Europa' if country else 'Outras regiões'

def build(source,portraits,destination):
 d=json.loads(Path(source).read_text(encoding='utf8'));destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
 target=destination/'catalog.sqlite3';db=sqlite3.connect(target)
 db.executescript('''DROP TABLE IF EXISTS coaches; DROP TABLE IF EXISTS clubs; DROP TABLE IF EXISTS club_seed; DROP TABLE IF EXISTS aliases; DROP TABLE IF EXISTS rules;
 DROP TABLE IF EXISTS metadata;
 CREATE TABLE coaches(coach_id TEXT PRIMARY KEY,name TEXT,nationality TEXT,birth_date TEXT,reputation REAL,salary INT,style TEXT,image TEXT,eligible INT,fictional INT);
 CREATE TABLE clubs(club_id INT PRIMARY KEY,name TEXT,league_id INT,league_name TEXT,country TEXT,region TEXT,reputation REAL,budget INT,level INT);
 CREATE TABLE club_seed(club_id INT PRIMARY KEY,coach_id TEXT,priority INT,source TEXT);
 CREATE TABLE aliases(source_id TEXT PRIMARY KEY,coach_id TEXT,name TEXT);
 CREATE TABLE rules(key TEXT PRIMARY KEY,value REAL);
 CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);''')
 clubs={x['team_id']:x for x in d['clubs'] if not x['special_team_no_manager']};people={};aliases={}
 reputations={}
 for c in clubs.values():reputations[key(c.get('manager_current_input') or c['base_fifa16_manager'])]=max(reputations.get(key(c.get('manager_current_input') or c['base_fifa16_manager']),1),c.get('club_reputation_suggested') or 4)
 for m in d['manager_id_images']:
  k=key(m['display_name']);cid=ident(k);aliases[m['manager_id']]=(cid,m['display_name'])
  image='minifaces/'+(m.get('file_name') or 'NOTFOUND_DEFAULT.png')
  rep=reputations.get(k,RATINGS.get(k,4));bio=m;eligible=1
  age=bio.get('age_as_of_date')
  if bio.get('age_at_death') or (age and age>85):eligible=0
  display=re.sub(r'\s+\d{2,}$','',m['display_name']).strip()
  person=dict(coach_id=cid,name=display,nationality=bio.get('nationality') or '',birth_date=bio.get('birth_date'),reputation=rep,salary=int(2500*rep*rep),style='Equilibrado',image=image,eligible=eligible,fictional=0)
  old=people.get(k)
  if old:
   if old['image'].endswith('NOTFOUND_DEFAULT.png') and not image.endswith('NOTFOUND_DEFAULT.png'):old['image']=image
   if not old['nationality'] and person['nationality']:old['nationality']=person['nationality']
   if not old['birth_date'] and person['birth_date']:old['birth_date']=person['birth_date']
   old['reputation']=max(old['reputation'],rep)
  else:people[k]=person
 # Current supplied names take precedence over legacy duplicate team slots.
 used=set();seeds=[];fictitious=0
 for c in sorted(clubs.values(),key=lambda x:(x.get('manager_csv_id') is not None,x.get('club_reputation_suggested') or 1),reverse=True):
  name=c.get('manager_current_input') or c.get('base_fifa16_manager') or '';k=key(name);person=people.get(k)
  if person is None or person['coach_id'] in used:
   cid='GEN-'+str(c['team_id']);fictitious+=1
   first=('Rafael','Carlos','André','Paulo','Bruno','Marcos')[c['team_id']%6];last=('Almeida','Costa','Moreira','Mendes','Ribeiro','Castro')[(c['team_id']//6)%6]
   person=dict(coach_id=cid,name=first+' '+last,nationality=c.get('country_name') or '',birth_date=f"{1970+c['team_id']%20}-01-01",reputation=c.get('club_reputation_suggested') or 3,salary=10000,style='Equilibrado',image='minifaces/NOTFOUND_DEFAULT.png',eligible=1,fictional=1)
   people[cid]=person
  used.add(person['coach_id']);seeds.append((c['team_id'],person['coach_id'],int(c.get('manager_csv_id') is not None),'CSV fornecido / base instalada' if not person['fictional'] else 'Nome fictício para clube sem técnico único'))
  # Budget is a generic calibration until the saved club row supplies its value.
  budget=int(1_000_000*(max(1,c.get('club_reputation_suggested') or 4)**2))
  db.execute('INSERT INTO clubs VALUES(?,?,?,?,?,?,?,?,?)',(c['team_id'],c['team_name'],c.get('league_id') or 0,c.get('league_name') or 'Outras competições',c.get('country_name') or '',region(c.get('country_name')),c.get('club_reputation_suggested') or 4,budget,c.get('league_level') or 1))
 for p in people.values():db.execute('INSERT INTO coaches VALUES(?,?,?,?,?,?,?,?,?,?)',tuple(p.values()))
 db.executemany('INSERT INTO aliases VALUES(?,?,?)',[(k,*v) for k,v in aliases.items()]);db.executemany('INSERT INTO club_seed VALUES(?,?,?,?)',seeds);db.executemany('INSERT INTO rules VALUES(?,?)',DEFAULTS.items())
 db.executemany('INSERT INTO metadata VALUES(?,?)',[('reference_date',d['date']),('nationality_source','Wikidata; correspondências incertas permanecem vazias'),('salary_basis','Modelo simulado em moeda da carreira; não representa salário real'),('source_db_hash',d['game_db_sha256'])]);db.commit();db.close()
 photos=destination/'minifaces';photos.mkdir(exist_ok=True);copied=0
 for p in Path(portraits).glob('*.png'):
  if re.fullmatch(r'\d{6}\.png',p.name) or p.name=='NOTFOUND_DEFAULT.png':shutil.copy2(p,photos/p.name);copied+=1
 return dict(catalog=str(target),coaches=len(people),clubs=len(clubs),fictional=fictitious,free=len(people)-len(seeds),portrait_files=copied)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--portraits',required=True);p.add_argument('--destination',required=True);a=p.parse_args();print(json.dumps(build(a.source,a.portraits,a.destination),ensure_ascii=False))
