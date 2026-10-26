"""Build one flat asset complement, excluding every file published in Git."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,zipfile,importlib.util

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def build(root,out,stamp,reuse_archive=None):
    root=Path(root).resolve();out=Path(out);out.mkdir(parents=True,exist_ok=True)
    tracked={p.decode('utf8').casefold() for p in subprocess.check_output(['git','ls-files','-z'],cwd=root).split(b'\0') if p}
    assets=json.loads((root/'ModCarrerMode/source/club_environment/assets-manifest.json').read_text(encoding='utf8'))
    rows=[dict(row) for row in assets['files']]
    globe=json.loads((root/'ModCarrerMode/data/club_browser/assets-manifest.json').read_text(encoding='utf8'))
    rows.extend(dict(row) for row in globe['files'])
    presentation=json.loads((root/'ModCarrerMode/data/catalogs/presentation_assets.json').read_text(encoding='utf8'))
    rows.extend(dict(row) for row in presentation['files'])
    animation='data/ant.cbac'
    rows.append({'path':animation,'bytes':(root/animation).stat().st_size,'sha256':sha(root/animation)})
    paths=set()
    for row in rows:
        relative=row['path'];path=Path(relative)
        if path.is_absolute() or '..' in path.parts or ':' in relative:raise ValueError('Unsafe asset path: '+relative)
        if relative.casefold() in tracked:raise ValueError('Already published in Git: '+relative)
        if relative.casefold() in paths:raise ValueError('Duplicate asset: '+relative)
        paths.add(relative.casefold())
        if path.suffix.casefold() not in ('.rx3','.npz','.cbac','.dds','.png','.bin','.ini'):raise ValueError('Not a static asset: '+relative)
        source=root/path
        if source.stat().st_size!=row['bytes'] or sha(source)!=row['sha256']:raise ValueError('Asset differs from manifest: '+relative)
    target=out/f'FIFA-Friends-Assets-Complementares-{stamp}.zip';temporary=target.with_suffix('.zip.new')
    if reuse_archive is None:
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
            for row in sorted(rows,key=lambda r:r['path']):archive.write(root/row['path'],row['path'])
    elif Path(reuse_archive).resolve()!=temporary.resolve():
        import shutil
        shutil.copy2(reuse_archive,temporary)
    with zipfile.ZipFile(temporary) as archive:
        if archive.testzip() is not None:raise ValueError('ZIP failed CRC verification')
        if set(archive.namelist())!={r['path'] for r in rows}:raise ValueError('Unexpected ZIP entries')
        for row in rows:
            with archive.open(row['path']) as stream:
                if hashlib.file_digest(stream,'sha256').hexdigest()!=row['sha256']:raise ValueError('ZIP asset hash mismatch')
    verifier_path=Path(__file__).with_name('Verify-PortablePackage.py')
    spec=importlib.util.spec_from_file_location('verify_portable_package',verifier_path)
    verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    checked=verifier.verify(root,temporary,out/('verificacao-'+stamp))
    os.replace(temporary,target)
    report={'zip':str(target),'zip_bytes':target.stat().st_size,'zip_MB':round(target.stat().st_size/1e6,3),'uncompressed_bytes':sum(r['bytes'] for r in rows),'asset_files':len(rows),'tracked_files_in_zip':0,'installers_in_zip':0,'layout':'game-relative paths; extract directly into FIFA root','code_source':'GitHub fifa-friends-v12 branch','code_commit':checked['commit'],'server16_sha256':checked['server16_sha256'],'clean_github_plus_zip_verified':True,'sha256':sha(target),'files':rows}
    target.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return {k:v for k,v in report.items() if k!='files'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);parser.add_argument('--output',type=Path);parser.add_argument('--date',default='20261024');parser.add_argument('--reuse-archive',type=Path,help='Recheck every entry and the clean installation using an already compressed complement');args=parser.parse_args()
    print(json.dumps(build(args.root,args.output or args.root/'code-release',args.date,args.reuse_archive),indent=2))
if __name__=='__main__':main()
