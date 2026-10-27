"""Regression: bind immutable native objects; duplicate assets append in FIFA."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'var_cabin/test_dependencies'))
from lupa.lua51 import LuaRuntime
lua=LuaRuntime(unpack_returned_tuples=True)
lua.execute("""
objects={};contexts=0;reloads=0
function objectFor(name) local o=objects[name];if not o then o={assets={},materials={},textures={},submeshes={}};objects[name]=o end;return o end
gRenderables={
 Find=function(self,name,i) assert(name:match('^server16_native_club_xi_v5_%d+$') and i==0);return objectFor(name) end,
 AddAsset=function(self,o,lod,key,path) assert(lod==0 and not o.assets[key], 'FIFA appends duplicate asset aliases');assert(not path:find('%.%.'));o.assets[key]=path end,
 CreateMaterialFromAttribulator=function(self,o,lod,part,group,shader) local index=tonumber(part:match('(%d+)$'));assert(group=='prop_material' and shader==(index<=64 and 'prop_plastic' or 'prop_alpha'));assert(not o.materials[part]);o.materials[part]=true end,
 SetSubMesh=function(self,o,lod,part,mesh) assert(o.materials[part] and part==mesh);o.submeshes[part]=mesh end,
 SetTexture=function(self,o,lod,part,group,param,key,texture) assert(group=='textures' and o.assets[key] and o.materials[part]);o.textures[part]=o.textures[part] or {};assert(not o.textures[part][param]);o.textures[part][param]={key,texture} end,
 SetDBInt=function(self,o,key,v) assert(key=='server16_club_xi_revision' and v==5) end,
 Reload=function(self,o,lod) assert(lod==1 and not o.reloaded);o.reloaded=true;reloads=reloads+1 end
}
function ContextAddRenderable(kind,o,count,opts) assert(kind=='gameplayprops' and count==1 and not o.registered);o.registered=true;contexts=contexts+1 end
gSportsRNA={GetTable=function() return {} end,GetInt=function() return 0 end}
""")
for n,file in enumerate(sys.argv[1:],1):
    lua.execute(Path(file).read_text(encoding='utf8'))
    lua.execute("""assert(S16ClubXI.ok and S16ClubXI.object.reloaded and S16ClubXI.object.registered)
for i=1,96 do local p='xi_part_'..i;local o=S16ClubXI.object;assert(o.materials[p] and o.submeshes[p] and o.textures[p].diffuseTexture[2]=='xi_cm');assert(o.textures[p].normalMap and o.textures[p].coeffMap and o.textures[p].envDiffuseTexture and o.textures[p].envSpecTexture and o.textures[p].coverageMap);assert(o.assets.charcmn:find('neutral_v2.rx3',1,true)) end""")
    assert lua.eval('contexts')==n and lua.eval('reloads')==n
print('PASS Lua 5.1: isolated objects, immutable aliases, native prop shaders, neutral lighting, one reload and scene registration per object')
