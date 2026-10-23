"""Build an extraction-only dressing-room repair for an installed V12 base."""
from pathlib import Path,PurePosixPath
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import zipfile


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def build(root,output,stamp):
    root=Path(root).resolve();output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    assets=json.loads((root/'ModCarrerMode/source/club_environment/assets-manifest.json').read_text(encoding='utf8'))['files']
    assert len(assets)==33
    files={}
    def add(relative,source=None):
        path=PurePosixPath(relative)
        if path.is_absolute() or '..' in path.parts or ':' in relative:raise ValueError(relative)
        if path.suffix.casefold() in ('.cmd','.bat','.ps1','.pyc','.log'):raise ValueError('Not a runtime dependency: '+relative)
        if relative.startswith(('runtime/','ModCarrerMode/runtime/')):raise ValueError('Live session data: '+relative)
        source=Path(source) if source else root/relative
        if not source.is_file():raise FileNotFoundError(source)
        files[relative]=source
    for row in assets:
        source=root/row['path']
        assert source.stat().st_size==row['bytes'] and sha(source)==row['sha256'],row['path']
        add(row['path'])
    # The session supervisor imports all three helper groups. Their source
    # dependencies must remain together even in a room-only repair package.
    source=root/'ModCarrerMode/source/club_environment'
    for file in source.rglob('*.py'):
        if '__pycache__' not in file.parts and not file.name.startswith('test_'):
            add(file.relative_to(root).as_posix())
    for relative in (
        'ModCarrerMode/source/club_environment/assets-manifest.json',
        'ModCarrerMode/data/club_environment/room/runtime/medical_room_r57.json',
        'ModCarrerMode/data/club_environment/room/runtime/room_roles_r57.json',
        'ModCarrerMode/mods/club_environment/native_dressing_room.dll',
        'ModCarrerMode/mods/mod_host.dll','Server16Python.exe','dinput8.dll','winmm.dll',
        'data/ui/game/components/careercomponents/careerhubwidget.big',
        'data/ui/layout/careermanagerhubcfg.xml',
        'data/ui/nav/careermode/mainmenuhubflow.nav',
        'data/ui/nav/careermode/server16dressingroomflow.nav',
        'data/ui/nav/careermode/server16bankloansflow.nav',
        'data/ui/nav/careermode/server16matchpreviewflow.nav',
        'ModCarrerMode/source/club_environment/bank/careertype.big'):
        add(relative)
    # Exercise the exact frozen Python environment shipped to the recipient,
    # in a fresh Unicode path with no developer caches, DBs, saves or indices.
    stage=Path(tempfile.mkdtemp(prefix='FIFA Vestiário pacote '))
    for relative,source in files.items():
        target=stage/relative;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(source.read_bytes())
    result=subprocess.run([str(stage/'Server16Python.exe'),'--club-environment-install',
        '--game-root',str(stage)],cwd=stage,capture_output=True,timeout=120)
    log=(result.stdout+result.stderr).decode('utf8',errors='replace')
    (output/'vestiario-package-check.log').write_text(log,encoding='utf8')
    if result.returncode:raise RuntimeError('Isolated bundled-runtime check failed: '+log[-5000:])
    checked=json.loads((stage/'ModCarrerMode/runtime/club_environment/check.json').read_text(encoding='utf8'))
    assert checked['ready'] and set(checked['workers'])=={'room','bank','preview'}
    for name in ('dressingroom','bankloansv2','matchpreview'):
        relative=f'data/ui/game/screens/career/server16/{name}.big'
        add(relative,stage/relative)
    records=[{'path':name,'bytes':source.stat().st_size,'sha256':sha(source)}
             for name,source in sorted(files.items())]
    manifest={'format':1,'purpose':'Vestiario repair for an installed FIFA Friends V12 base',
        'base_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        'static_model_texture_pose_files':len(assets),'bundled_runtime_check':checked,
        'files':records}
    # The check's game path is disposable, not part of the installed package.
    manifest['bundled_runtime_check'].pop('game',None)
    readme='''VESTIÁRIO COMPLETO — FIFA FRIENDS V12

Pacote de reposição para a base V12 já instalada, onde o botão Vestiário existe.

1. Feche FIFA e Server16.
2. Extraia o conteúdo deste ZIP diretamente na pasta que contém fifa16.exe.
3. Mescle as pastas data e ModCarrerMode e substitua os arquivos solicitados.
4. Abra o FIFA pelo Server16 e carregue sua carreira normalmente.

Contém os 33 modelos, texturas e poses estáticos do ambiente, a DLL do
Vestiário, os auxiliares, o runtime do Server16 e telas iniciais genéricas.
Os recursos específicos do elenco e do clube serão gerados no computador.
Este pacote inclui código e arquivos que também estão no GitHub.

Não há instalador. Não contém saves, empréstimos contratados, caches de outra
carreira, índices BH ou lista enabled.txt. A base V12 e seus arquivos originais
continuam necessários. O mod já estava habilitado no diagnóstico do Robson.
O manifesto em ModCarrerMode/docs/vestiario-package-manifest.json relaciona
todos os arquivos de execução com seus tamanhos e hashes SHA256.
'''
    target=output/f'FIFA-Friends-Vestiario-Completo-{stamp}.zip';temp=target.with_suffix('.zip.new')
    with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for relative,source in sorted(files.items()):archive.write(source,relative)
        archive.writestr('LEIA-ME-VESTIARIO.txt',readme.encode('utf8'))
        archive.writestr('ModCarrerMode/docs/vestiario-package-manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf8'))
    with zipfile.ZipFile(temp) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist())==len(files)+2
        for row in records:
            with archive.open(row['path']) as stream:
                assert hashlib.file_digest(stream,'sha256').hexdigest()==row['sha256'],row['path']
    os.replace(temp,target)
    report={'zip':str(target),'bytes':target.stat().st_size,'MB':round(target.stat().st_size/1e6,2),
        'sha256':sha(target),'files':len(files)+2,'static_assets':33,'bundled_runtime_verified':True,
        'neutral_screens_generated_in_isolation':True,'installers':0,'saves_or_session_data':0,
        'stage':str(stage)}
    target.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output',type=Path);parser.add_argument('--date',default='20261023')
    args=parser.parse_args();print(json.dumps(build(args.root,args.output or args.root/'code-release',args.date),ensure_ascii=False,indent=2))
