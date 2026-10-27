"""Verify Git archive + the asset complement in a new Unicode directory.

Development tool; not an installer. Never reads the developer's runtime/cache,
connects to FIFA, modifies a save, activates BHs or installs a driver.
"""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,os,subprocess,sys,tempfile,zipfile

def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def safe(name):
    p=PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or ':' in name or '\\' in name:raise ValueError('Unsafe archive member: '+name)
    return p

def verify(root,complement,output):
    root,complement,output=map(lambda p:Path(p).resolve(),(root,complement,output));output.mkdir(parents=True,exist_ok=True)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    tracked={p.decode() for p in subprocess.check_output(['git','ls-files','-z'],cwd=root).split(b'\0') if p}
    report={'commit':commit,'complement':str(complement),'complement_sha256':digest(complement)}
    with tempfile.TemporaryDirectory(prefix='FIFA limpo verificação á ',dir=output) as temp:
        temp=Path(temp);assert temp.resolve().is_relative_to(output)
        archive=temp/'github.zip';stage=temp/'FIFA';stage.mkdir()
        subprocess.run(['git','archive','--format=zip','--output='+str(archive),'HEAD'],cwd=root,check=True)
        with zipfile.ZipFile(archive) as z:
            for name in z.namelist():safe(name)
            z.extractall(stage)
        expected={}
        for rel in ('ModCarrerMode/source/club_environment/assets-manifest.json','ModCarrerMode/data/club_browser/assets-manifest.json','ModCarrerMode/data/catalogs/presentation_assets.json'):
            for row in json.loads((stage/rel).read_text(encoding='utf8'))['files']:
                safe(row['path']);assert row['path'] not in expected;expected[row['path']]=row
        pose='ModCarrerMode/data/club_browser/poses/starting_eleven.pose'
        profile=stage/pose.replace('.pose','.json')
        if profile.is_file():
            metadata=json.loads(profile.read_text(encoding='utf8'))
            expected[pose]={'path':pose,'bytes':metadata['recipe_bytes'],'sha256':metadata['recipe_sha256']}
        with zipfile.ZipFile(complement) as z:
            names=z.namelist();assert len(names)==len(set(names))
            assert set(names)==set(expected)|{'data/ant.cbac'},'Complement has missing or unexpected assets'
            assert not set(names)&tracked,'Complement duplicates the Git payload'
            assert z.testzip() is None
            for name in names:
                safe(name);p=stage/name;p.parent.mkdir(parents=True,exist_ok=True)
                with z.open(name) as incoming,p.open('wb') as dest:
                    import shutil
                    shutil.copyfileobj(incoming,dest)
                if name in expected:
                    row=expected[name];assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256'],name
        for row in json.loads((stage/'ModCarrerMode/source/club_environment/release-manifest.json').read_text(encoding='utf8'))['files']:
            p=stage/row['path'];assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256'],row['path']
        enabled=[]
        for line in (stage/'ModCarrerMode/mods/enabled.txt').read_text(encoding='utf8').splitlines():
            line=line.strip()
            if not line or line.startswith('#'):continue
            p=stage/'ModCarrerMode/mods'/line;assert p.is_file(),line;enabled.append(line)
        assert not (stage/'ModCarrerMode/runtime').exists(),'Git/ZIP leaked a developer runtime'
        assert not (stage/'data/sceneassets/var_room').exists(),'Rejected internal VAR room leaked into assets'
        assert not (stage/'ModCarrerMode/mods/var_room').exists(),'Rejected internal VAR room DLL leaked into release'
        assert 'var_cabin\\var_cabin.dll' in enabled,'Existing pitchside VAR cabin must remain enabled'
        env={k:v for k,v in os.environ.items() if not k.startswith(('SERVER16_','PYINSTALLER_')) and k!='PYTHONPATH'}
        env['PYINSTALLER_RESET_ENVIRONMENT']='1'
        def run(args,label,environment=env):
            p=subprocess.run(args,cwd=stage,env=environment,capture_output=True,timeout=120,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (output/(label+'.log')).write_bytes(p.stdout+p.stderr)
            if p.returncode:raise RuntimeError(label+' failed; see '+str(output/(label+'.log')))
        exe=stage/'Server16Python.exe'
        # Inspect our own bundled module: checking a loose source file alone
        # would miss an older executable shipped beside corrected sources.
        from PyInstaller.archive.readers import CArchiveReader
        frozen_archive=CArchiveReader(str(exe)).open_embedded_archive('PYZ.pyz')
        assert 'server16_py.var_room_panel' not in frozen_archive.toc,'Rejected internal VAR panel remains embedded'
        frozen=frozen_archive.extract('server16_py.club_environment')
        expected_module=compile((stage/'ModCarrerMode/source/server16_py/club_environment.py').read_bytes(),frozen.co_filename,'exec',optimize=0)
        assert frozen==expected_module,'Server16 executable does not contain the published worker source'
        run([str(exe),'--server16-selftest',str(stage/'selftest.json')],'frozen-selftest')
        run([str(exe),'--club-environment-check','--game-root',str(stage)],'first-boot')
        checked=json.loads((stage/'ModCarrerMode/runtime/club_environment/check.json').read_text(encoding='utf8'))
        assert checked['ready'] and checked['bank_icons']==10
        source=stage/'ModCarrerMode/source';common=source/'club_environment';runtime=stage/'ModCarrerMode/runtime/club_environment'
        pyenv=dict(env,SERVER16_GAME_ROOT=str(stage),PYTHONPATH=os.pathsep.join(map(str,(source,common,common/'vendor',runtime/'room',runtime/'bank',runtime/'preview',source/'tests',source/'club_browser'))))
        # These entries run the published worker function from a completely
        # absent runtime and execute safe fixture scripts, not FIFA APIs.
        methods=('test_direct_worker_prepares_missing_runtime_before_entry',
                 'test_direct_worker_recovers_deleted_entry_and_preserves_ledger',
                 'test_paths_with_spaces_and_loan_upgrade_preserves_private_ledger',
                 'test_invalid_inherited_stdout_cannot_abort_the_worker')
        run([sys.executable,'-B','-m','unittest',*('test_club_environment.PortableRuntimeTest.'+name for name in methods)],'direct-worker-tests',pyenv)
        run([sys.executable,'-B','-m','unittest','test_exporter'],'exporter-failure-tests',pyenv)
        run([sys.executable,'-B','-m','unittest','test_room_material_install_r59'],'room-assets-tests',pyenv)
        runtime_entries={kind:(runtime/kind/entry).is_file() for kind,entry in {'room':'prepare_native_room_components_r46_20261022.py','bank':'watch_r57.py','preview':'prepare.py'}.items()}
        assert all(runtime_entries.values())
        report.update(github_files=len(tracked),enabled_dlls=len(enabled),asset_files=len(names),release_files_verified=len(json.loads((stage/'ModCarrerMode/source/club_environment/release-manifest.json').read_text())['files']),
                      runtime_initially_absent=True,runtime_entries=runtime_entries,server16_sha256=digest(exe),
                      frozen=json.loads((stage/'selftest.json').read_text()),pose_and_bank_check=True,
                      frozen_worker_matches_published_source=True,
                      direct_worker_tests=True,invalid_stdout_cannot_abort_worker=True,exporter_failure_tests=True,room_geometry_textures_mips_and_lighting_tests=True,
                      runtime_or_save_copied=False,drivers_installed=False,fifa_started=False)
    (output/'clean-package.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);p.add_argument('--zip',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(verify(a.root,a.zip,a.output),ensure_ascii=False,indent=2))
