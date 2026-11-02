"""Build portable native geometry/art once, outside the interactive load."""
from pathlib import Path
import argparse,hashlib,json,time

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--game-root',type=Path,required=True);parser.add_argument('--model',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--probe',type=Path,required=True);args=parser.parse_args()
 import screen,asset_cache,prepared_catalogue
 model=json.loads(args.model.read_bytes());start=time.perf_counter();result=screen.build(args.game_root,args.probe,model)
 keys=[]
 for group in ('clubRows','freeRows','moveRows','hireRows'):keys.append((group,sorted({r[4] for r in model['clubRows']}|{p['head'] for p in model['people']}),sorted(asset_cache.flag_keys(args.game_root,model))))
 revision=asset_cache.revision(args.game_root,model);token=hashlib.sha256((screen.GEOMETRY_SIGNATURE+revision).encode()+json.dumps(keys,sort_keys=True).encode()).hexdigest()
 template=args.game_root/'ModCarrerMode/runtime/manager_market/native_templates'/('template_'+token+'.big')
 recipe=prepared_catalogue.export(args.game_root,model,screen.GEOMETRY_SIGNATURE,revision,template,args.output)
 print(json.dumps(dict(seconds=round(time.perf_counter()-start,3),template_bytes=(args.output/'catalogue.big').stat().st_size,recipe=recipe,build=result)),flush=True)

if __name__=='__main__':main()
