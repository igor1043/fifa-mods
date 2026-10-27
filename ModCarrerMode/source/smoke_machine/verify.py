from pathlib import Path
import sys,json,re,ctypes,hashlib
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'test_dependencies'))
from lupa.lua51 import LuaRuntime
lua=LuaRuntime(unpack_returned_tuples=True)
installed=Path(r'U:\fifa 16\data\fifarna\lua\assets\sle.lua').read_text(encoding='utf-8-sig')
block=(R/'smoke_machine.lua').read_text()
# Accept the current installed block when checking again after installation.
if block in installed:installed=installed.replace(block,'')
oldBlock=Path(r'J:\mods\fifa 16\estudos fifa 16\48_SMOKE_MACHINE_LOADING_20261014\lua_before.lua').read_text()
if oldBlock in installed:installed=installed.replace(oldBlock,'')
lua.execute(installed);lua.execute(block)
lua.execute('''
db={sle={}};function getTournamentGraphics(x)return x end
function makeRNA(t,i)
 local values={sletype=t,sleindex=i,suittype=0,skintone=0,bodytype=0,suitvariation=0,customcolor=0,
  wvAttribEnvLighting=0,wvAttribStadLightID=0,wvAttribStadID=1,wvAttribStadWeather=0,wvAttribStadClimate=0,
  homeKitTeamID=1043,awayKitTeamID=567,leagueID=7,policeType=0}
 gSportsRNA={GetTable=function()return{}end,GetInt=function(self,row,key)return values[key] or 0 end,
  GetString=function()return "stadium" end,Print=function()end,Assert=function()error("assert")end}
end
counts={};gr={Create=function(self,name,i)return i end,AddSubObject=function(self,batch,sle,t)counts[t]=(counts[t] or 0)+1 end}
CreateSleVariations(gr,{},{});assert(counts[16]==2 and counts[3]==2 and counts[6]==2 and counts[1]==3 and counts[18]==3)
db.sle[1]={};makeRNA(16,1);SleUpdate(1);assert(db.sle[1].isSmokeMachine==0)
FIFA16_SMOKE_MACHINE_HOOK_READY=true;SleUpdate(1)
assert(db.sle[1].isSmokeMachine==1 and db.sle[1].attribmatname=="simple_character_static")
assert(GetTexture(1)=="data/sceneassets/smoke_machine/textures.rx3")
assert(GetRMSle(1,0)=="data/sceneassets/smoke_machine/model.rx3;")
assert(GetRMSle(1,1)=="data/sceneassets/smoke_machine/textures.rx3;")
makeRNA(16,0);SleUpdate(1);assert(db.sle[1].isSmokeMachine==0)
FIFA16_VAR_CABIN_HOOK_READY=true;makeRNA(3,1);SleUpdate(1);assert(db.sle[1].isVarCabin==1 and db.sle[1].isSmokeMachine==0)
FIFA16_ENTRANCE_MODEL_FILE="data/sceneassets/entrance_props/test/model.rx3"
FIFA16_ENTRANCE_TEXTURE_FILE="data/sceneassets/entrance_props/test/textures.rx3"
FIFA16_ENTRANCE_PROPS_HOOK_READY=true;makeRNA(6,1);SleUpdate(1);assert(db.sle[1].isEntranceProps==1 and db.sle[1].isSmokeMachine==0)
FIFA16_MASCOT_PACKAGE_STATUS={[1043]=true};makeRNA(1,2);SleUpdate(1);assert(db.sle[1].isMascot==1 and db.sle[1].isSmokeMachine==0)
gRenderables=gr;gRenderObj={sles={[0]=1,[1]=2,[2]=3},batchSle={}};FIFA16_SMOKE_MACHINE_LIVE_CREATED=nil
nativeRows={}
gSportsRNA={GetTable=function(self,name,i)return i end,GetInt=function(self,i,key)return (nativeRows[i] or {})[key] or 0 end}
gr.AddSubObject=function(self,batch,sle,t)
 counts[t]=(counts[t] or 0)+1;nativeRows[sle]={sletype=t,sleindex=1}
end
counts={};FIFA16_SMOKE_MACHINE_CREATE_LIVE();assert(counts[16]==1)
FIFA16_SMOKE_MACHINE_CREATE_LIVE();assert(counts[16]==1)
-- Replacing the native scene while an old boolean remains true must recreate.
gRenderObj.sles={[0]=1,[1]=2};nativeRows={}
FIFA16_SMOKE_MACHINE_LIVE_CREATED=true;FIFA16_SMOKE_MACHINE_CREATE_LIVE();assert(counts[16]==2)
FIFA16_SMOKE_MACHINE_CREATE_LIVE();assert(counts[16]==2)
gRenderObj.sles={};for i=0,175 do gRenderObj.sles[i]=i end
nativeRows={};FIFA16_SMOKE_MACHINE_LIVE_CREATED=nil;FIFA16_SMOKE_MACHINE_CREATE_LIVE();assert(counts[16]==2)
''')
print('Lua 5.1 reserved static appearance, startup/live deduplication, capacity guard, other officials/VAR/entrance/mascot preserved: PASS')
upgrade=LuaRuntime(unpack_returned_tuples=True)
upgrade.execute(installed);upgrade.execute(oldBlock);upgrade.execute(block)
upgrade.execute('''
db={sle={}};counts={};nativeRows={}
gSportsRNA={GetTable=function(self,name,i)return i end,GetInt=function(self,i,key)return (nativeRows[i] or {})[key] or 0 end}
gr={Create=function(self,name,i)return i end,
 AddSubObject=function(self,batch,sle,t)counts[t]=(counts[t] or 0)+1;nativeRows[sle]={sletype=t,sleindex=counts[t]-1} end}
sles={};CreateSleVariations(gr,{},sles);assert(counts[16]==2)
gRenderables=gr;gRenderObj={sles=sles,batchSle={}}
FIFA16_SMOKE_MACHINE_CREATE_LIVE();assert(counts[16]==2)
''')
print('Upgrade over original Lua bootstrap reserves no duplicate appearance: PASS')
# Compare the physical bases with the actual current emitter formulas.
pyro=(R.parent/'stadium_pyrotechnics/stadium_pyrotechnics.cpp').read_text()
assert 'const auto& site=pyro_site(goalShow,i);' in pyro
assert 'outletX,machineOutletHeightCm,outletZ,1' in pyro
assert 'matrix[16]={1,0,0,0, 0,1,0,0, 0,0,1,0,' in pyro
assert 'cosf(' not in pyro and 'sinf(' not in pyro and 'site.yaw' not in pyro
assert (R/'launch_sites.h').read_bytes()==(R.parent/'stadium_pyrotechnics/launch_sites.h').read_bytes()
sites=set((float(x),float(z)) for x,z in re.findall(r'\{(-?\d+),(-?\d+),[^}]+\}',(R/'launch_sites.h').read_text()))
expected=set()
for x in (-2800,-1400,1400,2800):
    for z in (-3850,3850):expected.add((x,z))
for x in (-5900,5900):
    for z in (-2100,-1800,-700,700,1800,2100):expected.add((x,z))
assert sites==expected and len(sites)==20
assert all(x!=0 for x,z in sites)
assert sum(abs(x)==1400 and abs(z)==3850 for x,z in sites)==4
print('20 bases cover all emitters; four inner sideline bases at -14m/+14m; none at midfield: PASS')
source=(R/'smoke_machine.cpp').read_text()
assert 'SMOKE_MACHINE_LUA_V3' not in source and 'SMOKE_MACHINE_LUA_V2' in source
worker=source[source.index('static DWORD WINAPI worker'):source.index('extern "C" __declspec(dllexport) unsigned')]
assert 'activateLua()' not in worker
assert 'config();scene();refreshLua();' in source
assert 'luaReady&&!hasPrototype' in source
assert 'self+0x30*17' in source and 'self+0x30*(16+0x2f)' in source
assert 'requireVar&&!isVar' in source
assert 'self+0x30*4' not in source and 'self+0x30*(3+0x2f)' not in source
assert 'machineCount*0x50' in source and 'memcpy((void*)list,&saved,sizeof(saved))' in source
assert 'if(now<nextScene)return;nextScene=now+250;' in source
capture=Path(r'J:\mods\fifa 16\01_Projetos\mascotes\mod\diagnostics\20261007_102226_826631_mascot_native_observation\fifa16.image.bin')
with capture.open('rb') as f:
    guards=re.findall(r'\{0x([0-9a-f]+),\{([^}]+)\},(\d+)\}',source)
    for rva,values,length in guards:
        f.seek(int(rva,16));expected=bytes(int(x,16) for x in values.split(','));assert int(length)==len(expected) and f.read(len(expected))==expected
assert len(guards)==6
dll=ctypes.WinDLL(str(R/'build/smoke_machine.dll'))
dll.Fifa16ModGetApiVersion.restype=ctypes.c_uint
dll.Fifa16ModStart.argtypes=[ctypes.c_char_p];dll.Fifa16ModStart.restype=ctypes.c_int
assert dll.Fifa16ModGetApiVersion()==1 and dll.Fifa16ModStart(str(R/'build').encode())==0
print('x64 DLL API, unsupported-process rejection, native guards, temporary placements restored: PASS')
report=json.loads((R/'conversion_validation.json').read_text())
assert report['triangles']<4000 and report['static'] and not report['skeleton']
report['sites']=sorted(sites);report['total_triangles_20_machines']=20*report['triangles']
report['dll_sha256']=hashlib.sha256((R/'build/smoke_machine.dll').read_bytes()).hexdigest()
(R/'validation.json').write_text(json.dumps(report,indent=2))
