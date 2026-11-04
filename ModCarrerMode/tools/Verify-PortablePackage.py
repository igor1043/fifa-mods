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

FROZEN_SOURCE_MODULES=('server16_py.club_environment','server16_py.app',
    'server16_py.asset_runtime','server16_py.file_tools','server16_py.stadium_runtime',
    'server16_py.d3d_injector','server16_py.first_person_runtime',
    'server16_py.grass_quality_runtime','server16_py.loading_notices',
    'server16_py.match_hub_panel','server16_py.stadium_selector',
    'server16_py.native_asset_cleanup','server16_py.build_check','server16_py.career_options',
    'server16_py.substitution_audio','server16_py.substitution_audio_settings','server16_py.substitution_events')


def check_frozen_sources(frozen_archive,source):
    """Reject an old executable distributed beside newer loose helper files."""
    checked=[]
    for module in FROZEN_SOURCE_MODULES:
        frozen=frozen_archive.extract(module)
        path=Path(source)/Path(*module.split('.')).with_suffix('.py')
        expected=compile(path.read_bytes(),frozen.co_filename,'exec',optimize=0)
        assert frozen==expected,'Server16 executable does not contain published source: '+module
        checked.append(module)
    return checked


def extract_complements(stage,expected,tracked,archives,retired=(),seeded=()):
    retired=set(retired)
    names=set(seeded)
    for archive in archives:
        with zipfile.ZipFile(archive) as z:
            members=z.namelist();assert len(members)==len(set(members))
            assert not set(members)-set(expected)-retired,'Complement has unexpected assets'
            assert not set(members)&tracked,'Complement duplicates the Git payload'
            for name in members:
                safe(name)
                if name in retired:continue
                p=stage/name;p.parent.mkdir(parents=True,exist_ok=True)
                with z.open(name) as incoming,p.open('wb') as dest:
                    import shutil
                    shutil.copyfileobj(incoming,dest)
            names.update(set(members)-retired)
    assert names==set(expected),'Base plus delta has missing assets'
    for name,row in expected.items():
        p=stage/name;assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256'],name
    return names

def verify(root,complement,output,base_zips=(),base_directory=None,base_manifest=None):
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
        expected={};retired=set()
        for rel in ('ModCarrerMode/source/club_environment/assets-manifest.json','ModCarrerMode/data/club_browser/assets-manifest.json','ModCarrerMode/data/catalogs/presentation_assets.json'):
            for row in json.loads((stage/rel).read_text(encoding='utf8'))['files']:
                safe(row['path']);assert row['path'] not in expected;expected[row['path']]=row
        pose='ModCarrerMode/data/club_browser/poses/starting_eleven.pose'
        profile=stage/pose.replace('.pose','.json')
        if profile.is_file():
            metadata=json.loads(profile.read_text(encoding='utf8'))
            expected[pose]={'path':pose,'bytes':metadata['recipe_bytes'],'sha256':metadata['recipe_sha256']}
        full_manifest=stage/'ModCarrerMode/data/catalogs/asset_complement.json'
        if full_manifest.is_file():
            complete=json.loads(full_manifest.read_text(encoding='utf8'))
            assert complete['schema']==1
            external={row['path']:row for row in complete['files']};retired=set(complete.get('retired_assets',[]))
            assert len(external)==len(complete['files'])
            # Older module manifests may reference a small animation already
            # versioned with its code. Every external dependency must be present.
            for name,row in expected.items():
                if name in tracked:
                    assert (stage/name).is_file() and digest(stage/name)==row['sha256'],name
                else:
                    assert name in external and external[name]['sha256']==row['sha256'],name
            expected=external
        if not full_manifest.is_file():
            with zipfile.ZipFile(complement) as z:
                if 'data/ant.cbac' not in expected:
                    blob=z.read('data/ant.cbac');expected['data/ant.cbac']=dict(bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest())
        seeded=set()
        if bool(base_directory)!=bool(base_manifest):raise ValueError('Use --base-directory with --base-manifest')
        if base_directory:
            old={r['path']:r for r in json.loads(Path(base_manifest).read_text(encoding='utf-8'))['files']}
            with zipfile.ZipFile(complement) as z:incoming=set(z.namelist())
            for name,row in expected.items():
                if name in incoming or old.get(name,{}).get('sha256')!=row['sha256']:continue
                safe(name);source=Path(base_directory)/name;dest=stage/name
                assert source.is_file() and digest(source)==old[name]['sha256'],name
                dest.parent.mkdir(parents=True,exist_ok=True)
                try:os.link(source,dest)
                except OSError:
                    import shutil
                    shutil.copy2(source,dest)
                seeded.add(name)
            report['base_manifest_sha256']=digest(Path(base_manifest));report['unchanged_base_files_verified']=len(seeded)
        names=extract_complements(stage,expected,tracked,[*map(Path,base_zips),complement],retired,seeded)
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
        matched_modules=check_frozen_sources(frozen_archive,stage/'ModCarrerMode/source')
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
                      frozen_worker_matches_published_source=True,frozen_source_modules_verified=matched_modules,
                      direct_worker_tests=True,invalid_stdout_cannot_abort_worker=True,exporter_failure_tests=True,room_geometry_textures_mips_and_lighting_tests=True,
                      full_asset_manifest=full_manifest.is_file(),base_complements=[Path(p).name for p in base_zips],
                      runtime_or_save_copied=False,drivers_installed=False,fifa_started=False)
    (output/'clean-package.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);p.add_argument('--zip',type=Path,required=True);p.add_argument('--base-zip',type=Path,action='append',default=[]);p.add_argument('--base-directory',type=Path);p.add_argument('--base-manifest',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(verify(a.root,a.zip,a.output,a.base_zip,a.base_directory,a.base_manifest),ensure_ascii=False,indent=2))
