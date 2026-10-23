"""Build explicit, hash-checked club and panorama addons for an installed V12."""
from pathlib import Path
import argparse,hashlib,json,zipfile

COMMON={
 'Server16Python.exe','dinput8.dll','dinput8_l9_chain.dll','winmm.dll',
 'ModCarrerMode/mods/mod_host.dll','ModCarrerMode/tools/frontend_stadium_prepare.exe',
 'ModCarrerMode/mods/frontend_stadium/frontend_stadium_native_v11.dll',
 'ModCarrerMode/mods/panorama_drone/panorama_drone_v5.dll',
 'ModCarrerMode/mods/career_ui_assets/career_ui_assets.dll',
 'ModCarrerMode/config/frontend_stadium.ini','ModCarrerMode/config/panorama_drone.ini',
 'ModCarrerMode/config/stadium_metadata.ini','ModCarrerMode/data/catalogs/club_stadium_fallback.tsv',
 'data/ui/game/background/backgroundfifa.big','data/ui/game/screens/misc/stadiumpan.big',
 'data/ui/imgAssets/backgroundstadiums/st_server16_frontend_clear.dds',
 *('data/fifarna/lua/assets/'+n+'.lua' for n in ('stadium','crowd','server16_frontend_stadium','server16_frontend_176','server16_frontend_261')),
}
ENABLED=['frontend_stadium\\frontend_stadium_native_v11.dll','panorama_drone\\panorama_drone_v5.dll','career_ui_assets\\career_ui_assets.dll']
NAV=[{'path':'data/ui/nav/mainfeflow.nav','state':'mainMenuWithStadium'},{'path':'data/ui/nav/careermode/mainmenuhubflow.nav','state':'MainMenuHub'}]

def evidence(root,relative):
 data=(root/relative).read_bytes()
 return {'path':relative,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def build(root,out,kind,stamp):
 source=root/'ModCarrerMode/source/club_environment';files=set(COMMON);enabled=list(ENABLED)
 if kind=='club':
  # Private runtime, generated career art and experimental revisions never enter the archive.
  files.update(p.relative_to(root).as_posix() for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py','.md','.json','.h','.cpp','.cmd','.big') and not p.name.startswith('test'))
  files.update(p.relative_to(root).as_posix() for p in (root/'ModCarrerMode/data/club_environment').rglob('*') if p.is_file())
  files.update(e['path'] for e in json.loads((source/'assets-manifest.json').read_text(encoding='utf8'))['files'])
  files.update(('SubsOn.dll','SubsOn.ini','data/ant.cbac','ModCarrerMode/mods/subson/subson_bridge.dll','ModCarrerMode/mods/substitution_all7_rulescan_native/substitution_all7_rulescan_native.dll','ModCarrerMode/mods/club_environment/native_dressing_room.dll',
   'data/ui/game/components/careercomponents/careerhubwidget.big','data/ui/layout/careermanagerhubcfg.xml','data/ui/nav/careermode/mainmenuhubflow.nav'))
  files.update('data/ui/nav/careermode/server16'+n+'flow.nav' for n in ('bankloans','dressingroom','matchpreview'))
  files.update('data/ui/game/screens/career/server16/'+n+'.big' for n in ('bankloansv2','dressingroom','matchpreview'))
  enabled+=['club_environment\\native_dressing_room.dll','subson\\subson_bridge.dll','substitution_all7_rulescan_native\\substitution_all7_rulescan_native.dll']
 label='Ambiente-Clube' if kind=='club' else 'Panoramica'
 name=f'FIFA-Friends-{label}-{stamp}';out.mkdir(parents=True,exist_ok=True)
 rows=[]
 for relative in sorted(files):
  if Path(relative).is_absolute() or '..' in Path(relative).parts:raise ValueError(relative)
  row=evidence(root,relative);row['policy']='preserve' if relative.startswith('ModCarrerMode/config/') else 'subson_options' if relative=='SubsOn.ini' else 'replace';rows.append(row)
 manifest={'version':1,'kind':kind,'requires':'FIFA Friends V12','files':rows,'enabled':enabled,'navigation':NAV}
 readme=(f'FIFA Friends V12 - {label}\r\n\r\n'
  '1. Feche FIFA e Server16. Extraia este ZIP na raiz do jogo.\r\n'
  f'2. Execute Instalar-{label}.cmd e aguarde a mensagem de conclusao.\r\n'
  '3. Abra o Server16 atualizado e inicie o jogo. A opcao de estadio personalizado fica no F12.\r\n\r\n'
  'O instalador confere SHA-256, cria backup, preserva configuracoes de estadio e altera apenas entradas proprias em enabled.txt.\r\n'
  'As rotas de fundo sao mescladas com a navegacao local. Os BHs sao ativados no proprio PC; nao copie BHs de outro jogo.\r\n'
  'A panoramica inclui interface nativa, texto para continuar, escudo, Lua, catalogo, DLLs e auxiliar de preparo.\r\n'
  'Capacidade/publico customizados vem dos INIs do pacote, FSW/settings.ini ou ModCarrerMode/config/stadium_metadata.ini; ausentes ficam vazios.\r\n'
  'Os estadios personalizados de StadiumGBD e a base V12 nao estao neste ZIP. Pacotes RAR precisam de um extrator disponivel (WinRAR/7-Zip ou tar compativel).\r\n'
  'Se houver crash no outro PC, envie runtime/diagnostics da nova sessao e crash.dmp. O pacote nao foi testado no PC do Robson.\r\n')
 if kind=='club':readme+=('O ambiente inclui os modelos/texturas estaticos e a animacao SubsOn. Camisas, nomes, cores e quadros sao gerados pela carreira.\r\n'
  'Emprestimos: aguarde o resultado na propria tela e salve a carreira no FIFA. Banco de reservas: maximo 12, minimo de jogadores aptos 11.\r\n'
  'Historico anual desativado. Saves, caches, fotos geradas e livros financeiros pessoais nao sao distribuidos.\r\n')
 cmd=f'@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0{name}\\Install.ps1" -GameDirectory "%~dp0."\r\nif errorlevel 1 echo A instalacao falhou. Leia a mensagem acima.\r\npause\r\n'
 target=out/(name+'.zip')
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for relative in sorted(files):z.write(root/relative,name+'/payload/'+relative)
  z.writestr(name+'/manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf8'))
  z.writestr(name+'/Install.ps1',(root/'ModCarrerMode/tools/Install-PortablePackage.ps1').read_text(encoding='utf8').encode('utf-8-sig'))
  z.writestr('Instalar-'+label+'.cmd',cmd.encode('ascii'));z.writestr('LEIA-ME-'+label+'.txt',readme.encode('utf-8-sig'))
 with zipfile.ZipFile(target) as z:
  assert z.testzip() is None
  for row in rows:assert hashlib.sha256(z.read(name+'/payload/'+row['path'])).hexdigest()==row['sha256']
 report={'zip':str(target),'kind':kind,'payload_files':len(rows),'zip_bytes':target.stat().st_size,'zip_MB':round(target.stat().st_size/1e6,3),'uncompressed_bytes':sum(r['bytes'] for r in rows),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
 target.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf8');return report

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);parser.add_argument('--output',type=Path);parser.add_argument('--date',default='20261023');args=parser.parse_args()
 root=args.root.resolve();out=args.output or root/'code-release'
 print(json.dumps([build(root,out,k,args.date) for k in ('club','panorama')],indent=2))
if __name__=='__main__':main()
