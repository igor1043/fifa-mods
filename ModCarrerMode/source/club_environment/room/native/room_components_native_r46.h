// Additional, isolated native GameplayProp objects. No game objects are reused
// by index and no native game asset is modified or distributed by this module.
#include "room_medical_paging.h"
#include "room_sign_material.h"
#include "room_loading_progress.h"
#include "room_tour_loader.h"
struct NativeRoomComponent {
 std::string key,type,model,submesh,texture,textureName;
 int medicalPage=-1,medicalPages=0,medicalBank=0;
 bool alpha=false,loaded=false,attempted=false,failed=false;uintptr_t object=0;
 std::vector<std::array<float,16>> matrices;
 std::array<float,4> overlay{};room_light_probe::Probe lightProbe;
};
std::vector<std::unique_ptr<NativeRoomComponent>> components,retiredComponents;
NativeRoomComponent loadingSlate,errorSlate,loadingProgress,loadingBackdrop,loadingRing,loadingBadge,loadingDots,loadingStage,loadingSweep;
room_loading::Motion loadingMotion;
unsigned loadingBadgeClub=0,loadingBadgeRevision=0;
room_cinema::Tour roomTour;unsigned roomTourVersion=0;uint64_t roomTourFingerprint=0;
uintptr_t componentVtable[29]{};
void __fastcall componentDraw(void*self,int pass){
 const bool slate=self==(void*)loadingSlate.object||self==(void*)errorSlate.object||self==(void*)loadingProgress.object||self==(void*)loadingBackdrop.object||self==(void*)loadingRing.object||self==(void*)loadingBadge.object||self==(void*)loadingDots.object||self==(void*)loadingStage.object||self==(void*)loadingSweep.object;
 if(stopping||!roomVisiblePage()||(slate?!roomLoading.load():!active.load()||!ready.load()))return;
 bool caster=false;unsigned casterFlags=0;const room_light_probe::Probe* probe=nullptr;
 if(!slate&&pass==1)for(const auto& component:components)if(component&&component->object==uintptr_t(self)){
  caster=room_shadow_bridge::depthCaster(component->key.c_str(),component->alpha);if(!room_shadow_bridge::caster(component->key.c_str(),component->alpha))casterFlags|=room_shadow_bridge::Structure;probe=&component->lightProbe;break;
 }
 __try {if(indoorEnabled&&pass==1)nativeIndoorDraw(self,caster,probe,casterFlags);else ((void(__fastcall*)(void*,int))(image+0x43c8f20))(self,pass);}
 __except(EXCEPTION_EXECUTE_HANDLER){room_prop_bridge::end(false);indoorEnabled=false;++indoorFailures;log("INDOOR_LIGHTING_DISABLED_FALLBACK_NATIVE");}
}
unsigned componentGeneration=0,componentClub=0;uint64_t componentNextCheck=0;
std::atomic<unsigned> validCareerClub{0};
HANDLE nativeHelperProcess=nullptr;room_helper::Retry nativeHelperRetry;
void closeNativeAssetHelperMonitor(){if(nativeHelperProcess){CloseHandle(nativeHelperProcess);nativeHelperProcess=nullptr;}}
void launchNativeAssetHelper(){
 const auto now=GetTickCount64();if(!validCareerClub||!nativeHelperRetry.due(now))return;
 nativeHelperRetry.started(now);
 if(nativeHelperProcess){
  if(WaitForSingleObject(nativeHelperProcess,0)==WAIT_TIMEOUT)return;
  DWORD code=0;GetExitCodeProcess(nativeHelperProcess,&code);closeNativeAssetHelperMonitor();
  log(("NATIVE_ASSET_HELPER_EXIT code="+std::to_string(code)+"; checking worker handshake").c_str());
 }
 const fs::path python=game/L"Server16Python.exe";
 unsigned gamePid=0,helperPid=0;
 {std::ifstream marker(folder/L"runtime/native_asset_helper_r46.pid");marker>>gamePid>>helperPid;}
 nativeHelperProcess=room_helper::existingWorker(GetCurrentProcessId(),gamePid,helperPid,python.c_str());
 if(nativeHelperProcess){nativeHelperRetry.failures=0;log("NATIVE_ASSET_HELPER_ATTACHED: verified worker for this game session");return;}
 const auto helper=game/L"ModCarrerMode/source/club_environment/room/prepare_native_room_components_r46_20261022.py";
 if(!fs::exists(python)||!fs::exists(helper)){nativeHelperRetry.failed(now);log("NATIVE_ASSET_HELPER_MISSING: retry scheduled");return;}
 std::wstring command=L"\""+python.wstring()+L"\" --club-environment --game-root \""+game.wstring()+L"\" --pid "+std::to_wstring(GetCurrentProcessId());
 DWORD error=0;nativeHelperRetry.failed(now);
 if(room_helper::spawn(python.c_str(),command,game.c_str(),(folder/L"runtime/native_helper_startup.log").c_str(),nativeHelperProcess,error)){
  log("NATIVE_ASSET_HELPER_STARTED_R61: isolated frozen runtime; monitored process; startup log enabled");
 }else log(("NATIVE_ASSET_HELPER_START_FAILED error="+std::to_string(error)+"; retry scheduled").c_str());
}
std::string luaString(const std::string&text){std::string s="'";for(char c:text){if(c=='\\'||c=='\'')s+='\\';s+=c;}return s+"'";}
void componentVisibility(NativeRoomComponent&c,bool visible){
 if(!c.object||c.failed)return;
 if(c.medicalPages>0)visible=visible&&c.medicalPage==room_medical::page(GetTickCount64(),c.medicalPages,c.medicalBank,c.model.find("medical_room_r77.rx3")!=std::string::npos);
 alignas(16)auto overlay=c.overlay;
 for(size_t i=0;i<c.matrices.size();++i){
  alignas(16) auto matrix=c.matrices[i];matrix[12]+=roomOriginX-100000.f;
  ((void(__fastcall*)(void*,int,const float*,bool))(image+0x4ad80b0))((void*)c.object,static_cast<int>(i),matrix.data(),visible&&c.loaded);
  ((void(__fastcall*)(void*,int,const float*))(image+0x43c9960))((void*)c.object,static_cast<int>(i),overlay.data());
 }
}
void hideComponents(){for(auto&c:components)componentVisibility(*c,false);}
bool componentReady(uintptr_t o){
 auto impl=get<uintptr_t>(o+0x20);if(get<unsigned>(impl+0x18)!=1)return false;
 auto composite=get<uintptr_t>(get<uintptr_t>(impl+0x20));
 if(!get<unsigned char>(composite+0x10))((int(__fastcall*)(void*))(image+0x4add100))((void*)composite);
 return ((bool(__fastcall*)(void*))(image+0x4ad7d80))((void*)o);
}
unsigned snapshotClub(){
 std::ifstream f(game/L"ModCarrerMode/runtime/career_fce_snapshot.json");char buf[2048]{};f.read(buf,sizeof(buf)-1);std::string s(buf,static_cast<size_t>(f.gcount()));
 auto value=[&s](const char*key){auto p=s.find(key);if(p==std::string::npos)return 0u;p=s.find(':',p);if(p==std::string::npos)return 0u;return static_cast<unsigned>(strtoul(s.c_str()+p+1,nullptr,10));};
 return value("\"pid\"")==GetCurrentProcessId()?value("\"club\""):0;
}
bool loadTour(unsigned generation,unsigned club){
 std::ifstream f(folder/L"runtime/room_tour_r46.txt");room_cinema::Tour tour;
 if(!room_tour_loader::read(f,GetCurrentProcessId(),club,generation,tour)){
  log("CAMERA_TOUR_REJECTED: retaining previous room; navigation and collisions must load together");return false;
 }
 room_cinema::compile(tour);std::ifstream source(folder/L"runtime/room_tour_r46.txt");std::string header,body;std::getline(source,header);body.assign(std::istreambuf_iterator<char>(source),std::istreambuf_iterator<char>());uint64_t fingerprint=1469598103934665603ULL^club;for(unsigned char c:body){fingerprint^=c;fingerprint*=1099511628211ULL;}
 if(!roomTourVersion||fingerprint!=roomTourFingerprint){roomTour=std::move(tour);roomTourFingerprint=fingerprint;++roomTourVersion;}log("CAMERA_TOUR_LOADED: mesh obstacle bounds and save jersey 9/10");return true;
}
bool loadComponents(){
 std::ifstream f(folder/L"runtime/native_components_v2.txt");std::string magic;unsigned version=0,pid=0,club=0,generation=0,count=0;
 if(!(f>>magic>>version>>pid>>club>>generation>>count)||magic!="S16NATIVE"||(version!=2&&version!=3&&version!=4)||pid!=GetCurrentProcessId()||club!=validCareerClub||count==0)return false;
 if(count>256){log("NATIVE_COMPONENT_GROUP_LIMIT_EXCEEDED: max=256");return false;}
 if(generation==componentGeneration&&club==componentClub)return true;
 std::vector<std::unique_ptr<NativeRoomComponent>> prepared;
 for(unsigned i=0;i<count;++i){
  auto c=std::make_unique<NativeRoomComponent>();unsigned alpha=0,instances=0;
  if(!(f>>std::quoted(c->key)>>std::quoted(c->model)>>std::quoted(c->submesh)>>std::quoted(c->texture)>>std::quoted(c->textureName)>>alpha>>instances)||instances<1||instances>64)return false;
  if(c->model.rfind("data/sceneassets/",0)!=0||c->texture.rfind("data/",0)!=0||c->key.size()>64)return false;
  if(version>=3&&(!(f>>c->medicalPage>>c->medicalPages>>c->medicalBank)||c->medicalPages<0||c->medicalPages>6||c->medicalPage< -1||c->medicalPage>=std::max(1,c->medicalPages)||c->medicalBank<0||c->medicalBank>1))return false;
  for(float&v:c->overlay)if(!(f>>v)||!std::isfinite(v)||v<0||v>1)return false;
  if(version>=4){
   for(float& value:c->lightProbe.local)if(!(f>>value)||!std::isfinite(value)||std::abs(value)>100000)return false;
   if(c->lightProbe.local[3]<0)return false;c->lightProbe.valid=true;
  }
  c->alpha=alpha!=0;c->matrices.resize(instances);
  for(auto&m:c->matrices)for(float&v:m)if(!(f>>v)||!std::isfinite(v)||std::abs(v)>1000000.f)return false;
  c->type="server16_native_room_r60_"+std::to_string(generation)+"_"+std::to_string(i);prepared.push_back(std::move(c));
 }
 if(!loadTour(generation,club))return false;
 hideComponents();
 for(auto&next:prepared)for(auto&old:components){
  if(old&&old->key==next->key&&old->model==next->model&&old->submesh==next->submesh&&old->texture==next->texture&&old->textureName==next->textureName&&old->alpha==next->alpha&&!old->failed){
   old->matrices=std::move(next->matrices);old->overlay=next->overlay;old->medicalPage=next->medicalPage;old->medicalPages=next->medicalPages;old->medicalBank=next->medicalBank;old->lightProbe=next->lightProbe;next=std::move(old);break;
  }
 }
 for(auto&c:components)if(c)retiredComponents.push_back(std::move(c));components=std::move(prepared);componentGeneration=generation;componentClub=club;
 log("NATIVE_COMPONENT_CONFIG_LOADED: original FIFA mesh/texture references, career club validated");return true;
}
bool createComponent(NativeRoomComponent&c){
 c.attempted=true;
 auto*allocator=((void*(__fastcall*)())(image+0x4abfba0))();auto allocate=get<uintptr_t>(get<uintptr_t>((uintptr_t)allocator)+0x10);
 auto*storage=((void*(__fastcall*)(void*,size_t,const char*,int))allocate)(allocator,0x38,"Server16RoomNativeComponent",1);if(!storage)return false;
 c.object=(uintptr_t)((void*(__fastcall*)(void*,void*,const char*,int,int,int))(image+0x43c8be0))(storage,allocator,c.type.c_str(),0,1,64);
 if(!c.object||get<uintptr_t>(c.object)!=image+0x2210dc0){c.object=0;return false;}
 auto ctx=get<uintptr_t>(c.object+0x30);auto impl=get<uintptr_t>(c.object+0x20);
 if(get<uintptr_t>(ctx+8)!=c.object||get<unsigned>(impl+0x38)!=64){c.object=0;return false;}
 if(!componentVtable[0]){read(image+0x2210dc0,componentVtable,sizeof componentVtable);componentVtable[4]=(uintptr_t)&componentDraw;}
 InterlockedExchangePointer((void*volatile*)c.object,componentVtable);
 alignas(16)float hiddenMatrix[16]={1,0,0,0,0,1,0,0,0,0,1,0,roomOriginX,1000,0,1};
 for(int i=0;i<64;++i)((void(__fastcall*)(void*,int,const float*,bool))(image+0x4ad80b0))((void*)c.object,i,hiddenMatrix,false);
 componentVisibility(c,false);((void(__fastcall*)(void*,const char*,int))(image+0x4ac5450))((void*)c.object,c.type.c_str(),0);
 const auto model=luaString(c.model),texture=luaString(c.texture),type=luaString(c.type);
 std::string script="do local gr=gRenderables;local o=gr:Find("+type+",0);local ok,err=pcall(function() local lod=0;local part="+luaString(c.alpha?"prop_alpha":"prop_plastic")+";";
 script+="gr:AddAsset(o,lod,'shader','data/fifarna/shader.big');gr:AddAsset(o,lod,part,"+model+");gr:AddAsset(o,lod,'color',"+texture+");gr:AddAsset(o,lod,'aux',"+luaString(roomComponentAuxTexture(c.key))+");";
 script+="local state=gSportsRNA:GetTable('wvState');local env=gSportsRNA:GetInt(state,'wvAttribEnvLighting');gr:AddAsset(o,lod,'charcmn','data/sceneassets/charactercmn/charactercmn_'..env..'.rx3');";
 script+="gr:AddAsset(o,lod,'coverage','data/sceneassets/server16_dressing_room_v3/shared/room_white_r49.rx3');";
 script+="gr:CreateMaterialFromAttribulator(o,lod,part,'prop_material',"+luaString(c.alpha?"prop_alpha":"prop_plastic")+");gr:SetSubMesh(o,lod,part,"+luaString(c.submesh)+");";
 script+="gr:SetTexture(o,lod,part,'textures','diffuseTexture','color',"+luaString(c.textureName)+");gr:SetTexture(o,lod,part,'textures','normalMap','aux','_nm');gr:SetTexture(o,lod,part,'textures','coeffMap','aux','_coeff');";
 script+="gr:SetTexture(o,lod,part,'textures','envDiffuseTexture','charcmn','envd_');gr:SetTexture(o,lod,part,'textures','envSpecTexture','charcmn','envs_');gr:SetTexture(o,lod,part,'textures','coverageMap','coverage','white_cm');gr:SetDBInt(o,'server16_room_revision',1);gr:Reload(o,1);ContextAddRenderable('gameplayprops',o,1,{}) end);if not ok then S16RoomComponentError=tostring(err) end end";
 if(!execute(script.c_str()))return false;
 ((void(__fastcall*)(void*,bool))(image+0x4ad7e50))((void*)c.object,true);log(("NATIVE_COMPONENT_REQUEST: "+c.key+" model="+c.model+" texture="+c.texture).c_str());return true;
}
void pollComponents(bool requested){
 // Asset registration is allowed only on the room's UI owner callback.
 if(!requested)return;
 if(!validCareerClub){hideComponents();return;}
 auto now=GetTickCount64();if(now>=componentNextCheck){componentNextCheck=now+1000;loadComponents();}
 if(componentClub!=validCareerClub){hideComponents();return;}
 unsigned created=0;const auto prepareBegan=GetTickCount64();
 for(auto&c:components){
  if(!c->attempted&&created<8&&(created==0||GetTickCount64()-prepareBegan<6)){++created;if(!createComponent(*c)){c->failed=true;log(("NATIVE_COMPONENT_FAILED_NO_RETRY: "+c->key).c_str());}}
  if(c->object&&!c->failed&&!c->loaded&&componentReady(c->object)){c->loaded=true;log(("NATIVE_COMPONENT_READY: "+c->key).c_str());}
  componentVisibility(*c,false);
 }
}
bool roomComponentsReady(){
 if(componentClub!=validCareerClub||components.empty())return false;
 for(auto&c:components)if(!c->loaded||c->failed)return false;
 return true;
}
bool roomComponentsFailed(){for(auto&c:components)if(c->failed)return true;return false;}
void showComponents(bool visible){for(auto&c:components)componentVisibility(*c,visible);}
void loadingDecoration(NativeRoomComponent&c,const char*key,const char*model,const char*texture,bool alpha,bool visible){
 if(!visible){componentVisibility(c,false);return;}
 if(!c.attempted){c.key=key;c.type=std::string("server16_room_")+key+"_r83";c.model=model;c.submesh="room_part_1";c.texture=texture;c.textureName="slate_cm";c.alpha=alpha;c.matrices.push_back({1,0,0,0,0,1,0,0,0,0,1,0,100000,0,0,1});if(!createComponent(c))c.failed=true;}
 if(c.object&&!c.failed&&!c.loaded&&componentReady(c.object))c.loaded=true;
 componentVisibility(c,visible);
}
void loadingBrand(bool show,bool error){
 loadingDecoration(loadingBackdrop,"loading_backdrop","data/sceneassets/server16_dressing_room_v3/loading_backdrop_r83.rx3","data/sceneassets/server16_dressing_room_v3/loading_backdrop_texture_r83.rx3",false,show);
 loadingDecoration(loadingRing,"loading_ring","data/sceneassets/server16_dressing_room_v3/loading_ring_r83.rx3","data/sceneassets/server16_dressing_room_v3/loading_ring_texture_r83.rx3",true,show&&!error);
 if(!show){componentVisibility(loadingBadge,false);componentVisibility(loadingDots,false);return;}
 const unsigned club=backgroundClub?backgroundClub.load():validCareerClub.load();
 if(loadingBadgeClub!=club){
  componentVisibility(loadingBadge,false);
  // The engine may still retain the renderable; retain its backing strings,
  // but never display the previous save's crest during the next preparation.
  if(loadingBadge.object)retiredComponents.push_back(std::make_unique<NativeRoomComponent>(std::move(loadingBadge)));
  loadingBadge=NativeRoomComponent{};loadingBadgeClub=club;
 }
 if(club&&!loadingBadge.attempted){
  auto&c=loadingBadge;c.key="loading_badge";c.type="server16_room_loading_badge_r83_"+std::to_string(club)+"_"+std::to_string(++loadingBadgeRevision);c.model="data/sceneassets/server16_dressing_room_v3/loading_badge_r83.rx3";c.submesh="room_part_1";c.texture="data/ui/imgassets/crest/light/l"+std::to_string(club)+".dds";c.alpha=true;c.matrices.push_back({1,0,0,0,0,1,0,0,0,0,1,0,100000,0,0,1});
  if(!fs::exists(game/c.texture))c.texture="data/ui/imgassets/crest/dark/l"+std::to_string(club)+".dds";
  if(!createComponent(c))c.failed=true;
 }
 if(loadingBadge.object&&!loadingBadge.failed&&!loadingBadge.loaded&&componentReady(loadingBadge.object))loadingBadge.loaded=true;
 const auto activity=room_loading::activity(GetTickCount64()-loadingMotion.began);
 if(!loadingRing.matrices.empty()){
  auto&m=loadingRing.matrices[0];m[0]=activity.cosine;m[1]=activity.sine;m[4]=-activity.sine;m[5]=activity.cosine;m[12]=roomOriginX-283.59375f;m[13]=1270.71875f;m[14]=400.3f;
 }
 if(!loadingBadge.matrices.empty()){
  auto&m=loadingBadge.matrices[0];m[0]=m[5]=error?1:activity.badgeScale;m[12]=roomOriginX-283.59375f;m[13]=1270.71875f+(error?0:activity.badgeLift);m[14]=400.4f;
 }
 componentVisibility(loadingRing,show&&!error);componentVisibility(loadingBadge,show&&loadingBadgeClub==club);
 loadingDecoration(loadingDots,"loading_dots","data/sceneassets/server16_dressing_room_v3/loading_dot_r83.rx3","data/sceneassets/server16_dressing_room_v3/loading_dot_texture_r83.rx3",true,show&&!error);
 if(show&&!error&&loadingDots.attempted){
  if(loadingDots.matrices.size()!=3){const auto initial=loadingDots.matrices.front();loadingDots.matrices.resize(3,initial);}
  for(unsigned i=0;i<3;++i){auto a=room_loading::dot(GetTickCount64()-loadingMotion.began,i);auto&m=loadingDots.matrices[i];m[0]=m[5]=a.scale;m[12]=roomOriginX+253.125f+11.25f*i;m[13]=1270.71875f+a.lift;m[14]=400.5f;}
  componentVisibility(loadingDots,true);
 }

}
void pollSlate(bool show,bool error){
 loadingMotion.tick(show,GetTickCount64());loadingBrand(show,error);
 for(int i=0;i<2;++i){auto&c=i?errorSlate:loadingSlate;
  if(!show){if(c.object)componentVisibility(c,false);continue;}
  if(!c.attempted){c.key=i?"loading_error":"loading_slate";c.type=i?"server16_room_error_r83":"server16_room_loading_r83";c.model="data/sceneassets/server16_dressing_room_v3/loading_panel_r83.rx3";c.submesh="room_part_1";c.texture=i?"data/sceneassets/server16_dressing_room_v3/loading_error_texture_r83.rx3":"data/sceneassets/server16_dressing_room_v3/loading_panel_texture_r83.rx3";c.textureName="slate_cm";c.matrices.push_back({1,0,0,0,0,1,0,0,0,0,1,0,100000,0,0,1});if(!createComponent(c))c.failed=true;}
  if(c.object&&!c.failed&&!c.loaded&&componentReady(c.object))c.loaded=true;
  componentVisibility(c,show&&(i?error:!error));
 }
 auto&bar=loadingProgress;
 if(!show||error){componentVisibility(bar,false);componentVisibility(loadingStage,false);componentVisibility(loadingSweep,false);return;}
 if(!bar.attempted){bar.key="loading_progress";bar.type="server16_room_loading_progress_r83";bar.model="data/sceneassets/server16_dressing_room_v3/loading_progress_r83.rx3";bar.submesh="room_part_1";bar.texture="data/sceneassets/server16_dressing_room_v3/loading_progress_texture_r83.rx3";bar.textureName="slate_cm";bar.matrices.push_back({1,0,0,0,0,1,0,0,0,0,1,0,100000,0,0,1});if(!createComponent(bar))bar.failed=true;}
 if(bar.object&&!bar.failed&&!bar.loaded&&componentReady(bar.object))bar.loaded=true;
 unsigned loadedCount=0;for(auto&c:components)if(c->loaded&&!c->failed)++loadedCount;
 const unsigned total=componentClub==validCareerClub?static_cast<unsigned>(components.size()):0;
 const auto p=loadingMotion.smooth(room_loading::progress(ready.load(),loadedCount,total,GetTickCount64()-loadingMotion.began));
 bar.matrices[0][0]=p.scale;bar.matrices[0][12]=roomOriginX-318.75f+p.offset*637.5f;
 componentVisibility(bar,show&&!error&&p.scale>0);
 loadingDecoration(loadingStage,"loading_stage","data/sceneassets/server16_dressing_room_v3/loading_stage_r83.rx3","data/sceneassets/server16_dressing_room_v3/loading_progress_texture_r83.rx3",false,true);
 if(!loadingStage.matrices.empty()){auto&m=loadingStage.matrices[0];m[12]=roomOriginX-220.3125f+220.3125f*loadingMotion.focus(room_loading::stage(ready.load(),loadedCount,total));m[13]=1137.125f;m[14]=400.5f;componentVisibility(loadingStage,true);}
 const auto sweep=room_loading::sweep(p,GetTickCount64()-loadingMotion.began);
 loadingDecoration(loadingSweep,"loading_sweep","data/sceneassets/server16_dressing_room_v3/loading_progress_r83.rx3","data/sceneassets/server16_dressing_room_v3/loading_sweep_texture_r83.rx3",true,sweep.scale>0);
 if(!loadingSweep.matrices.empty()){auto&m=loadingSweep.matrices[0];m[0]=sweep.scale;m[12]=roomOriginX-318.75f+sweep.offset*637.5f;m[14]=.15f;componentVisibility(loadingSweep,sweep.scale>0);}

}
