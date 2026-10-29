"""Stage and inspect the package against a copied sidecar, never the save."""
from pathlib import Path
import argparse,hashlib,json,os,sys

def main():
 p=argparse.ArgumentParser();p.add_argument('--game',required=True);p.add_argument('--output',required=True);a=p.parse_args();game=Path(a.game).resolve();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True)
 repo=Path(__file__).resolve().parents[4];source=repo/'ModCarrerMode/source';env=source/'club_environment';os.environ['SERVER16_GAME_ROOT']=str(game)
 sys.path[:0]=[str(source),str(env),str(env/'vendor'),str(env/'bank'),str(env/'preview'),str(env/'market')]
 from inputs import Inputs
 from engine import Market
 from model import project
 from screen import build,waiting
 from package import stage
 snapshot=json.loads((game/'ModCarrerMode/runtime/career_fce_snapshot.json').read_text(encoding='utf8'));save=Path(snapshot['savePath']);before=hashlib.sha256(save.read_bytes()).hexdigest()
 stat=save.stat();observed=dict(save=dict(path=str(save),size=stat.st_size,mtime_ns=stat.st_mtime_ns),date=snapshot['date'],profile=dict(club_id=snapshot['club']))
 inputs=Inputs(game);context=inputs.read(observed,offline=True)
 from catalog_meta import populate
 populate(repo/'ModCarrerMode/data/manager_market/catalog.sqlite3',inputs.cache.base,game/'ModCarrerMode/data/club_browser/catalog.tsv')
 market=Market(out/'preview_world_v3.sqlite3',repo/'ModCarrerMode/data/manager_market/catalog.sqlite3');market.open_save(context['digest'],save,context)
 with market.db:market.advance(context)
 model=project(market);market.close();(out/'preview.json').write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding='utf8')
 ready=build(repo,out/'managermarket-review.big',model);placeholder=build(repo,out/'package/data/ui/game/screens/career/server16/managermarket.big',waiting());files=stage(repo,out/'package')
 after=hashlib.sha256(save.read_bytes()).hexdigest()
 if before!=after:raise RuntimeError('Arquivo do save mudou durante a validação')
 report=dict(ready_package=ready,placeholder=placeholder,navigation_files=files,clubs=len(model['clubRows']),free=len(model['freeRows']),people=len(model['people']),source_save_sha256=before,source_save_unchanged=before==after)
 (out/'stage_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
