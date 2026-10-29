"""Local display metadata. FIFA's tables are read; only our catalogue is written."""
from pathlib import Path
from contextlib import closing
import sqlite3,unicodedata

def key(value):return ''.join(c for c in unicodedata.normalize('NFKD',str(value or '')) if not unicodedata.combining(c)).casefold().strip()

TRANSLATIONS={'Brazil':'Brasil','Italy':'Itália','France':'França','Germany':'Alemanha','Spain':'Espanha','England':'Inglaterra','Uruguay':'Uruguai','Colombia':'Colômbia','Bolivia':'Bolívia','Mexico':'México','Belgium':'Bélgica','Holland':'Países Baixos','Switzerland':'Suíça','Denmark':'Dinamarca','Sweden':'Suécia','Austria':'Áustria','Scotland':'Escócia','Wales':'País de Gales','Japan':'Japão','Korea Republic':'Coreia do Sul','United States':'Estados Unidos','South Africa':'África do Sul','Cameroon':'Camarões','Egypt':'Egito','Nigeria':'Nigéria','Russia':'Rússia','Greece':'Grécia','Croatia':'Croácia','Serbia':'Sérvia','Australia':'Austrália','Republic of Ireland':'Irlanda','Czech Republic':'Chéquia','Poland':'Polônia','Turkey':'Turquia','Ukraine':'Ucrânia','Romania':'Romênia','Norway':'Noruega','Paraguay':'Paraguai','Peru':'Peru','Ecuador':'Equador','Venezuela':'Venezuela','China PR':'China','Saudi Arabia':'Arábia Saudita','Catar':'Catar','Algeria':'Argélia','Tunisia':'Tunísia','Morocco':'Marrocos','Senegal':'Senegal','Finland':'Finlândia','Slovenia':'Eslovênia','Slovakia':'Eslováquia','Bulgaria':'Bulgária','Belarus':'Bielorrússia','Iran':'Irã','Bosnia and Herzegovina':'Bósnia e Herzegovina','Canada':'Canadá','Hungary':'Hungria','Iceland':'Islândia','New Zealand':'Nova Zelândia','Trinidad and Tobago':'Trindade e Tobago','Côte d\'Ivoire':'Costa do Marfim','Congo DR':'RD Congo','Zimbabwe':'Zimbábue','Ghana':'Gana','Thailand':'Tailândia','United Arab Emirates':'Emirados Árabes Unidos','International':'Internacional','Rest of World':'Resto do mundo'}
ALIASES={'reino dos paises baixos':'Holland','netherlands':'Holland','reino da dinamarca':'Denmark','checoslovaquia':'Czech Republic','republica tcheca':'Czech Republic','coreia do sul':'Korea Republic','irao':'Iran','costa do marfim':'Côte d\'Ivoire'}

def populate(catalog,base,browser):
 """Refresh expandable league/country IDs without changing the game database."""
 labels={};countries={};league_countries={};levels={}
 try:
  for line in Path(browser).read_text(encoding='utf-8-sig').splitlines():
   r=line.split('\t')
   if len(r)==18:countries[int(r[2])]=r[1];labels[int(r[5])]=r[6];league_countries[int(r[5])]=int(r[2]);levels[int(r[5])]=int(r[7])
 except OSError:pass
 with closing(sqlite3.connect(catalog)) as db,db:
  db.executescript('CREATE TABLE IF NOT EXISTS country_catalog(nation_id INT PRIMARY KEY,name TEXT,source_name TEXT); CREATE TABLE IF NOT EXISTS league_catalog(league_id INT PRIMARY KEY,name TEXT,country_id INT,level INT); CREATE TABLE IF NOT EXISTS coach_preferences(coach_id TEXT PRIMARY KEY,formation TEXT,secondary_style TEXT);')
  db.executemany('INSERT OR REPLACE INTO country_catalog VALUES(?,?,?)',[(r['nationid'],countries.get(r['nationid'],TRANSLATIONS.get(r['nationname'],r['nationname'])),r['nationname']) for r in base.rows('nations',['nationid','nationname'])])
  db.executemany('INSERT OR REPLACE INTO league_catalog VALUES(?,?,?,?)',[(r['leagueid'],labels.get(r['leagueid'],r['leaguename']),league_countries.get(r['leagueid'],r['countryid']),levels.get(r['leagueid'],r['level'])) for r in base.rows('leagues',['leagueid','leaguename','countryid','level'])])

class Labels:
 def __init__(self,catalog):
  self.countries={};self.leagues={};self.aliases={};self.preferences={}
  with closing(sqlite3.connect(catalog)) as db:
   db.row_factory=sqlite3.Row;tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
   if 'country_catalog' in tables:
    for row in db.execute('SELECT * FROM country_catalog'):
     r=dict(row);self.countries[r['nation_id']]=r
     for name in (r['name'],r['source_name']):self.aliases[key(name)]=r
   if 'league_catalog' in tables:self.leagues={r['league_id']:dict(r) for r in db.execute('SELECT * FROM league_catalog')}
   if 'coach_preferences' in tables:self.preferences={r['coach_id']:dict(r) for r in db.execute('SELECT * FROM coach_preferences')}
  for alias,name in ALIASES.items():
   if key(name) in self.aliases:self.aliases[alias]=self.aliases[key(name)]
 def nationality(self,value):
  names=[];flags=[]
  for part in str(value or '').split(';'):
   part=part.strip()
   if not part:continue
   if key(part) in ('reino unido','united kingdom'):
    if 'Reino Unido' not in names:names.append('Reino Unido');flags.append('flag_uk')
    continue
   # Regional Brazilian leagues are not different coach nationalities.
   if part.startswith('Brasil '):part='Brasil'
   row=self.aliases.get(key(part));label=row['name'] if row else TRANSLATIONS.get(part,part)
   if label not in names:names.append(label);flags.append('flag_'+str(row['nation_id']) if row else 'flag_0')
  return (' / '.join(names) or 'Não informada',flags[0] if flags else 'flag_0')
 def country(self,value):
  row=self.aliases.get(key(value))
  return (row['name'],row['nation_id']) if row else (TRANSLATIONS.get(value,value) or 'Outros países',0)
