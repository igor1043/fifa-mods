"""Read actual stage format (LEAGUE / KO1LEG / KO2LEGS) for any installed cup."""
from pathlib import Path
import csv,re

def read_formats(game):
 folder=Path(game)/'dlc/dlc_FootballCompEng/dlc/FootballCompEng/data/compdata'
 def rows(name):return csv.reader((folder/(name+'.txt')).read_text(encoding='utf-8-sig').splitlines())
 objects={int(r[0]):r for r in rows('compobj') if len(r)>=5 and r[0].isdigit()}
 settings={int(r[0]):r[2] for r in rows('settings') if len(r)==3 and r[0].isdigit() and r[1]=='match_stagetype'}
 result={}
 for identifier,row in objects.items():
  if row[1]!='4':continue
  mode=settings.get(identifier,'');name=row[3].strip();kind=0;label='Fase'
  if mode=='LEAGUE':kind=2;label='Fase de grupos'
  elif mode.startswith('KO'):
   ordinal=int(row[2][1:]) if row[2][1:].isdigit() else identifier
   key=name.casefold()
   if 'quarter' in key:kind=7;label='Quartas de final'
   elif 'semi' in key:kind=8;label='Semifinais'
   elif 'third' in key:kind=9;label='Terceiro lugar'
   elif 'round_of_16' in key:kind=6;label='Oitavas de final'
   elif 'round_of_32' in key:kind=5;label='32 avos de final'
   elif 'final' in key:kind=10;label='Final'
   else:
    kind=100+ordinal;number=re.search(r'(?:round|stage)_(\d+)',key)
    label=(number.group(1)+'ª fase') if number else 'Eliminatória '+str(ordinal)
  result[identifier]=dict(kind=kind,name=label,mode=mode,root=int(row[4]),groups=[n for n,r in objects.items() if r[1]=='5' and int(r[4])==identifier])
 return result
