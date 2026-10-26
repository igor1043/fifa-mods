"""Read the existing career save; all outputs stay in this separate workspace."""
from pathlib import Path
import sys,json,hashlib
root=Path(__file__).resolve().parent;game=Path(json.loads((root/'settings.json').read_text(encoding='utf8'))['game_root'])
sys.path.insert(0,str(game/'ModCarrerMode/source/club_browser'))
from lineup_data import project
snapshot=json.loads((game/'ModCarrerMode/runtime/career_fce_snapshot.json').read_text(encoding='utf8'))
save=Path(snapshot['savePath']);before=hashlib.sha256(save.read_bytes()).hexdigest()
result=project(game,save,1043)
(root/'fixture.bin').write_bytes(result['fixture'])
(root/'roster.json').write_text(json.dumps(result['roster'],ensure_ascii=False,indent=2),encoding='utf8')
assert hashlib.sha256(save.read_bytes()).hexdigest()==before
print('READ_ONLY_FLAMENGO_XI',len(result['roster']))
