from pathlib import Path
import sys,json
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'test_dependencies'))
from lupa.lua51 import LuaRuntime
lua=LuaRuntime(unpack_returned_tuples=True)
block=(R/'var_cabin.lua').read_text()
source=Path(r'U:\fifa 16\data\fifarna\lua\assets\sle.lua').read_text(encoding='utf8')
installed=Path(r'U:\fifa 16\ModCarrerMode\mods\var_cabin\var_cabin.lua').read_text(encoding='utf8')
assert source.count(installed)==1
lua.execute(source.replace(installed,''))
lua.execute(block)
lua.execute('''
db={sle={}};function getTournamentGraphics(x)return x end
rawCompetitionId=29;failCompetitionRead=false
function makeRNA(t,i)
 local values={sletype=t,sleindex=i,suittype=0,skintone=0,bodytype=0,suitvariation=0,customcolor=0,
  wvAttribEnvLighting=0,wvAttribStadLightID=0,wvAttribStadID=1,wvAttribStadWeather=0,wvAttribStadClimate=0,
  homeKitTeamID=1043,awayKitTeamID=567,leagueID=29,policeType=0}
 gSportsRNA={GetTable=function(self,name) if name=="wvWipe" and failCompetitionRead then error("unavailable") end return{}end,GetInt=function(self,row,key) if key=="leagueID" then return rawCompetitionId end return values[key] or 0 end,
  GetString=function()return "stadium" end,Print=function()end,Assert=function()error("assert")end}
end
counts={};gr={Create=function(self,name,i)return i end,AddSubObject=function(self,batch,sle,t)counts[t]=(counts[t] or 0)+1 end}
CreateSleVariations(gr,{},{});assert(counts[3]==2 and counts[6]==2 and counts[1]==3 and counts[18]==3)
db.sle[1]={};makeRNA(3,1);SleUpdate(1);assert(db.sle[1].isVarCabin==0)
FIFA16_VAR_CABIN_HOOK_READY=true;SleUpdate(1);assert(db.sle[1].isVarCabin==1 and db.sle[1].attribmatname=="simple_character_static")
assert(GetTexture(1)=="data/sceneassets/var_cabin/textures_v2.rx3" and GetRMSle(1,0)=="data/sceneassets/var_cabin/model_v2.rx3;")
for _,id in ipairs({7,-1,83,350,7,351,83,101,31,29,0}) do
 rawCompetitionId=id;FIFA16_VAR_CABIN_REFRESH_COMPETITION(1);assert(db.sle[1].varCabinCompetitionId==id)
end
-- Graphics overrides and club league assignments cannot turn a friendly into a league match.
function getTournamentGraphics(x) if x==-1 then return 7 elseif x==31 then return 83 else return x end end
rawCompetitionId=-1;SleUpdate(1);assert(db.sle[1].tournamentid==7 and db.sle[1].varCabinCompetitionId==-1)
rawCompetitionId=31;SleUpdate(1);assert(db.sle[1].tournamentid==83 and db.sle[1].varCabinCompetitionId==31)
rawCompetitionId=7;FIFA16_VAR_CABIN_REFRESH_COMPETITION(1);assert(db.sle[1].varCabinCompetitionId==7)
failCompetitionRead=true;FIFA16_VAR_CABIN_REFRESH_COMPETITION(1);assert(db.sle[1].varCabinCompetitionId==-1)
failCompetitionRead=false;rawCompetitionId=83;FIFA16_VAR_CABIN_REFRESH_COMPETITION(1);assert(db.sle[1].varCabinCompetitionId==83)
rawCompetitionId=7.5;FIFA16_VAR_CABIN_REFRESH_COMPETITION(1);assert(db.sle[1].varCabinCompetitionId==-1)
rawCompetitionId=29
makeRNA(3,0);SleUpdate(1);assert(db.sle[1].isVarCabin==0 and not string.find(GetTexture(1),"var_cabin",1,true))
FIFA16_ENTRANCE_MODEL_FILE="data/sceneassets/entrance_props/test/model.rx3";FIFA16_ENTRANCE_TEXTURE_FILE="data/sceneassets/entrance_props/test/textures.rx3"
FIFA16_ENTRANCE_PROPS_HOOK_READY=true;makeRNA(6,1);SleUpdate(1);assert(db.sle[1].isEntranceProps==1 and db.sle[1].isVarCabin==0)
FIFA16_MASCOT_PACKAGE_STATUS={[1043]=true};makeRNA(1,2);SleUpdate(1);assert(db.sle[1].isMascot==1 and db.sle[1].isVarCabin==0)
gRenderables=gr;gRenderObj={sles={[0]=1,[1]=2,[2]=3},batchSle={}};FIFA16_VAR_CABIN_LIVE_CREATED=nil
counts={};FIFA16_VAR_CABIN_CREATE_LIVE();assert(counts[3]==1 and gRenderObj.sles[3]==3)
FIFA16_VAR_CABIN_CREATE_LIVE();assert(counts[3]==1)
''')
report={'lua_5_1':'passed','raw_match_competition_refresh':'passed','friendly_graphics_override_excluded':'passed','other_league_graphics_override_excluded':'passed','failed_query_clears_previous_competition':'passed','fractional_id_rejected':'passed','native_factory_append':'passed','live_creation_idempotent':'passed','normal_platform_camera':'preserved','entrance_prototype':'preserved','mascot_prototype':'preserved','static_model_texture_paths':'passed','startup_reservation_before_hook':'passed'}
(R/'lua_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
