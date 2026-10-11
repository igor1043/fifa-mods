"""Export both institutional RGB colors from this installation's FIFA database."""
from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,r'J:\mods\fifa 16\01_Projetos\mascotes\visualizador\tools')
from fifa_db import FifaDatabase
p=Path(__file__).parent
game=Path(r'U:\fifa 16')
db=FifaDatabase(game)
fields=['teamid','teamname']+[f'teamcolor{n}{c}' for n in (1,2) for c in ('r','g','b')]
rows=sorted(db.rows('teams',fields),key=lambda row:row['teamid'])
palette=[]
for row in rows:
    colors=[[row[f'teamcolor{n}{c}'] for c in ('r','g','b')] for n in (1,2)]
    assert all(isinstance(v,int) and 0<=v<=255 for rgb in colors for v in rgb),row
    palette.append({'team':row['teamid'],'name':row['teamname'],'primary':colors[0],'secondary':colors[1]})
assert len({r['team'] for r in palette})==len(palette)
lines=['// Generated from the installed FIFA database; no per-frame database reads.', 'static const TeamPalette teamPalettes[]={']
for r in palette:
    lines.append('    {%d,{%s},{%s}},'%(r['team'],','.join(map(str,r['primary'])),','.join(map(str,r['secondary']))))
lines.append('};')
(p/'team_palettes.h').write_text('\n'.join(lines)+'\n',encoding='utf-8')
out=p/'build/team_palettes.json'
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({'database':str(game/'data/db/fifa_ng_db.db'),'sha256':hashlib.sha256((game/'data/db/fifa_ng_db.db').read_bytes()).hexdigest(),'teams':palette},ensure_ascii=False,indent=2),encoding='utf-8')
print('Exported two RGB colors for',len(palette),'teams')
print(json.dumps([r for r in palette if r['team'] in (1041,1043,113163)],ensure_ascii=True))
