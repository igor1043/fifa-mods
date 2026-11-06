"""Create a verified asset-only delta against an earlier public manifest."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,os,subprocess,zipfile

def digest(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def build(root,base,output,name):
 root=Path(root).resolve();base=Path(base);output=Path(output);output.mkdir(parents=True,exist_ok=True)
 current=json.loads((root/'ModCarrerMode/data/catalogs/asset_complement.json').read_text(encoding='utf-8'))
 baseline=json.loads(base.read_text(encoding='utf-8'));before={r['path']:r for r in baseline['files']};rows=current['files'];tracked=set(subprocess.check_output(['git','ls-files','-z'],cwd=root).decode('utf-8').split('\0'));seen=set();delta=[]
 for row in rows:
  rel=row['path'];path=PurePosixPath(rel)
  if path.is_absolute() or '..' in path.parts or ':' in rel or '\\' in rel:raise ValueError('Unsafe asset path: '+rel)
  if rel in tracked or rel in seen:raise ValueError('Tracked or duplicate asset: '+rel)
  if path.suffix.lower() in ('.exe','.dll','.py','.pyc','.log','.sqlite','.sqlite3'):raise ValueError('Not a static external asset: '+rel)
  if rel.startswith(('runtime/','ModCarrerMode/runtime/','data/sceneassets/server16_dressing_room_20261022/')):raise ValueError('Session or retired room asset: '+rel)
  seen.add(rel);source=root/rel
  if source.stat().st_size!=row['bytes'] or digest(source)!=row['sha256']:raise ValueError('Changed asset: '+rel)
  if before.get(rel,{}).get('sha256')!=row['sha256']:delta.append(row)
 target=output/name;temporary=target.with_suffix('.zip.new')
 with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
  for row in delta:z.write(root/row['path'],row['path'])
 with zipfile.ZipFile(temporary) as z:
  assert z.testzip() is None
  assert set(z.namelist())=={r['path'] for r in delta}
  for row in delta:
   with z.open(row['path']) as f:assert hashlib.file_digest(f,'sha256').hexdigest()==row['sha256']
 os.replace(temporary,target)
 report=dict(zip=target.name,bytes=target.stat().st_size,sha256=digest(target),base=baseline.get('release',base.name),base_manifest_sha256=digest(base),code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),files=delta,files_count=len(delta),unchanged_files=len(rows)-len(delta),retired_assets=sorted(set(before)-seen),room_version=3,contains_saves=False,contains_runtime=False,contains_legacy_room=False)
 target.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 return {k:v for k,v in report.items() if k not in ('files','retired_assets')}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--base-manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--name',default='FIFA-Friends-Assets-Delta-20261104-sobre-20261102-R2.zip');a=p.parse_args();print(json.dumps(build(a.root,a.base_manifest,a.output,a.name),indent=2))
