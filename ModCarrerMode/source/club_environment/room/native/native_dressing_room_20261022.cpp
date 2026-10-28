#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <tlhelp32.h>
#include <atomic>
#include <array>
#include <string>
#include <fstream>
#include <filesystem>
#include <cstring>
#include <cmath>
#include <vector>
#include <memory>
#include <iomanip>
#include <sstream>
#include "room_helper_process_r61.h"
#include "motions.h"
#include "room_cinema_r52.h"
#include "room_scene_command.h"
namespace fs=std::filesystem;
namespace {
constexpr float roomOriginX=100000.f;
constexpr char roomPage[]="game/screens/career/server16/DressingRoom";
uintptr_t image=0,previousFrame=0,object=0,originalVtable=0,originalDraw=0;
uintptr_t allocatedNative=0;
void*relay=nullptr;LONG beforeCall=0,oursCall=0;
uintptr_t ownVtable[29]{};
std::atomic<bool>started{false},stopping{false},installed{false},active{false},ready{false};
std::atomic<bool>holdDrawing{false},roomLoading{false},componentsReadyStatus{false};
uint64_t roomLoadBegan=0;
std::atomic<unsigned>phase{0},fault{0},frames{0},draws{0},submissions{0};
std::atomic<unsigned>roomSceneState{0};
fs::path game,folder,logfile;uint64_t requestedAt=0;
bool registered=false,creationAttempted=false,codeValidated=false,prepareAttempted=false;
bool nativeCodeReady(){
 const unsigned char signature[]={0x4c,0x8b,0x51,0x20,0x41,0x8b,0x00,0x4c,0x63,0xda};unsigned char actual[10]{};
 __try{memcpy(actual,(void*)(image+0x4ad80b0),sizeof actual);return !memcmp(actual,signature,sizeof actual);}__except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
bool read(uintptr_t at,void*out,size_t n){if(at<0x10000)return false;__try{memcpy(out,(void*)at,n);return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
template<class T>T get(uintptr_t at){T v{};read(at,&v,sizeof v);return v;}
bool write(uintptr_t at,const void*data,size_t n){__try{memcpy((void*)at,data,n);return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
void log(const char*message){std::ofstream f(logfile,std::ios::app);f<<GetTickCount64()<<" pid="<<GetCurrentProcessId()<<" "<<message<<"\n";}
bool page(){auto p=get<uintptr_t>(image+0x3809030);for(unsigned o:{232u,192u,136u,472u})p=get<uintptr_t>(p+o);char text[128]{};return read(p,text,127)&&!strcmp(text,roomPage);}
bool execute(const char*script){auto lua=get<uintptr_t>(image+0x3613fd0);if(!lua||get<int>(lua+0x80)!=5)return false;__try{((void(__fastcall*)(const char*,size_t,const char*))(image+0x4ac35e0))(script,strlen(script),"Server16NativeDressingRoom");return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
#include "room_background_r52.h"
struct LuaValue {uintptr_t value=0;int type=0;};
LuaValue field(uintptr_t table,const char*key){
 unsigned char h[64]{};if(!read(table,h,64)||h[8]!=5||h[11]>14)return {};
 uintptr_t nodes=0;memcpy(&nodes,h+32,8);size_t wanted=strlen(key);unsigned count=1u<<h[11];
 for(unsigned i=0;i<count;++i){unsigned char row[40]{};if(!read(nodes+i*40,row,40))return {};int type=0;memcpy(&type,row+24,4);if(type!=4)continue;uintptr_t s=0;memcpy(&s,row+16,8);if(get<size_t>(s+16)!=wanted)continue;char text[128]{};if(wanted>=sizeof text||!read(s+24,text,wanted)||memcmp(text,key,wanted))continue;LuaValue result;memcpy(&result.value,row,8);memcpy(&result.type,row+8,4);if(result.type==1)result.value&=0xffffffff;return result;}return {};
}
LuaValue roomField(const char*key){auto lua=get<uintptr_t>(image+0x3613fd0);auto room=field(get<uintptr_t>(lua+0x78),"S16NativeDressingRoom");return room.type==5?field(room.value,key):LuaValue{};}
bool loaded(){
 if(!object)return false;
 auto impl=get<uintptr_t>(object+0x20);auto list=get<uintptr_t>(impl+0x20);const auto count=get<unsigned>(impl+0x18);
 if(count!=1)return false;
 const auto composite=get<uintptr_t>(list);
 if(!get<unsigned char>(composite+0x10))((int(__fastcall*)(void*))(image+0x4add100))((void*)composite);
 return ((bool(__fastcall*)(void*))(image+0x4ad7d80))((void*)object);
}
void visibility(bool value){
 if(!object)return;
 alignas(16)float matrix[16]={1,0,0,0,0,1,0,0,0,0,1,0,roomOriginX,0,0,1};
 ((void(__fastcall*)(void*,int,const float*,bool))(image+0x4ad80b0))((void*)object,0,matrix,value);
 // overlayColor alpha must remain zero: alpha one paints over the diffuse map.
 alignas(16)float overlayOff[4]={0,0,0,0};
 ((void(__fastcall*)(void*,int,const float*))(image+0x43c9960))((void*)object,0,overlayOff);
}
#include "room_lighting_r46.h"
#include "room_components_native_r46.h"
#include "room_medical_capture_r53.h"
bool roomRosterCameraOwned(){using Query=BOOL(WINAPI*)();auto module=GetModuleHandleW(L"club_browser.dll");auto query=module?reinterpret_cast<Query>(GetProcAddress(module,"Fifa16ClubBrowserRoomRosterActive")):nullptr;return query&&query();}
bool medicalInstallAttempted=false;
struct BorrowedCamera {
 uintptr_t scene=0;unsigned char original[0x84]{},written[0x84]{};uint64_t tourTick=0,controlNext=0,controlSequence=0;std::string controlNonce;room_cinema::Director director;panorama::Pose lastSafe{{0,187,600},{0,170,-275},74};
 void resetTour(){tourTick=0;director.initialized=false;}
 void control(){auto now=GetTickCount64();if(now<controlNext)return;controlNext=now+100;std::ifstream scope(folder/L"runtime/room_control_scope.txt"),command(folder/L"runtime/room_camera_command.txt");std::string a,b,nonce,expected;unsigned v=0,w=0,pid=0,pid2=0,club=0,club2=0;uint64_t seq=0;int code=0;
 if(!(scope>>a>>v>>pid>>club>>expected)||a!="S16ROOMSCOPE"||v!=1||pid!=GetCurrentProcessId()||club!=componentClub||club!=validCareerClub)return;
 if(expected!=controlNonce){controlNonce=expected;controlSequence=0;}
 if(!(command>>b>>w>>pid2>>club2>>nonce>>seq>>code)||b!="S16ROOM"||w!=1||pid2!=pid||club2!=club||nonce!=expected||seq<=controlSequence||code< -3||code>=static_cast<int>(roomTour.sequence.size()))return;controlSequence=seq;const bool ok=director.command(code,roomTour);log(ok?"ROOM_SCENE_COMMAND_APPLIED":"ROOM_SCENE_COMMAND_REJECTED_UNSAFE_ROUTE");
 }
 void restore(){if(scene&&scene==get<uintptr_t>(image+0x3517c10)){
  for(auto r:std::array<std::array<unsigned,2>,4>{{{{0,64}},{{0x48,8}},{{0x70,1}},{{0x7c,8}}}}){unsigned char current[64]{};if(read(scene+0x40+r[0],current,r[1])&&!memcmp(current,written+r[0],r[1]))write(scene+0x40+r[0],original+r[0],r[1]);}
 }scene=0;}
 void apply(bool waiting=false){auto s=get<uintptr_t>(image+0x3517c10);const auto state=get<int>(s+0x3c);roomSceneState=state;if(state!=1&&state!=13)return;float x=get<float>(s+0x88),y=get<float>(s+0x8c);if(!std::isfinite(x)||!std::isfinite(y)||y<=0||x/y<.5f||x/y>4)return;
  auto now=GetTickCount64();const double dt=tourTick?std::min(.1,double(now-tourTick)*.001):0.;tourTick=now;
  if(!director.initialized||director.generation!=roomTourVersion)director.reset(roomTour,roomTourVersion,GetCurrentProcessId()^roomTourVersion^static_cast<unsigned>(now));control();
  auto pose=waiting?panorama::Pose{{0,187,750},{0,180,0},74}:director.tick(dt,roomTour);if(!waiting&&!room_cinema::poseSafe(pose,roomTour))pose=lastSafe;else if(!waiting)lastSafe=pose;pose.eye=pose.eye+panorama::Vec{roomOriginX,1000,0};pose.target=pose.target+panorama::Vec{roomOriginX,1000,0};float m[16];if(!panorama::matrix(pose,m)||!read(s+0x40,original,sizeof original))return;scene=s;
  float Y=std::tan(pose.fov*.00872664626f),X=Y*(x/y),zero=0;unsigned char off=0;write(s+0x40,m,sizeof m);write(s+0x88,&X,4);write(s+0x8c,&Y,4);write(s+0xb0,&off,1);write(s+0xbc,&zero,4);write(s+0xc0,&zero,4);read(s+0x40,written,sizeof written);
 }
}camera;
SRWLOCK roomCommandLock=SRWLOCK_INIT;
room_command::Receipt roomCommandReceipt;
bool captureRoomSceneCommand(const char*argument){
 char wire[192]{};if(!read(reinterpret_cast<uintptr_t>(argument),wire,sizeof(wire)-1)||!std::memchr(wire,0,sizeof(wire)-1))return false;
 room_command::Request request;if(!room_command::parse(wire,request)||!page())return false;
 // This callback performs no FIFA calls or camera writes. The existing
 // owner-frame consumer applies the validated mailbox within its 100ms poll.
 AcquireSRWLockExclusive(&roomCommandLock);bool accepted=false;
 std::ifstream scope(folder/L"runtime/room_control_scope.txt");std::string magic,nonce;unsigned version=0,pid=0,club=0;
 if(scope>>magic>>version>>pid>>club>>nonce && magic=="S16ROOMSCOPE"&&version==1&&pid==GetCurrentProcessId()
    &&club==request.club&&club==validCareerClub&&nonce==request.nonce&&roomCommandReceipt.accepts(request)){
  const auto target=folder/L"runtime/room_camera_command.txt",temporary=folder/L"runtime/room_camera_command.txt.direct-new";
  std::ofstream output(temporary,std::ios::binary|std::ios::trunc);
  if(output){output<<"S16ROOM 1 "<<pid<<" "<<club<<" "<<nonce<<" "<<request.sequence<<" "<<request.code<<"\n";output.close();
   if(output&&MoveFileExW(temporary.c_str(),target.c_str(),MOVEFILE_REPLACE_EXISTING)){
    roomCommandReceipt.commit(request);accepted=true;log("ROOM_SCENE_COMMAND_CAPTURED_DIRECT: no heap polling");
   }
  }
 }
 ReleaseSRWLockExclusive(&roomCommandLock);return accepted;
}
void __fastcall draw(void*self,int pass){
 ++draws;if(stopping||!active||!ready||!page()||self!=(void*)object)return;
 if(!submissions.load())log("FIRST_NATIVE_DRAW_BEGIN: forwarding GameplayProp native context");
 __try {if(indoorEnabled&&pass==1)nativeIndoorDraw(self);else ((void(__fastcall*)(void*,int))originalDraw)(self,pass);++submissions;}
 __except(EXCEPTION_EXECUTE_HANDLER){fault=GetExceptionCode();active=false;phase=9;log("NATIVE_DRAW_EXCEPTION_DISABLED");}
}
const char createScript[]=R"lua(
S16NativeDressingRoom=nil
if not S16NativeDressingRoom then
 S16NativeDressingRoom={stage='creating',ok=false}
 local s=S16NativeDressingRoom
 local ok,err=pcall(function()
  local gr=gRenderables
  assert(gr and type(ContextAddRenderable)=='function','native renderer unavailable')
  s.object=gr:Find('server16_native_dressing_room_r60',0)
  assert(s.object,'native GameplayProp creation failed')
  local root='data/sceneassets/server16_dressing_room_20261022/'
  gr:AddAsset(s.object,0,'shader','data/fifarna/shader.big')
  gr:AddAsset(s.object,0,'textures','data/sceneassets/prop/prop_102_textures.rx3')
 end)
 s.ok=ok;s.error=tostring(err);s.stage=ok and 'loading' or 'failed'
end
if S16NativeDressingRoom and not S16NativeDressingRoom.bound then
 local s=S16NativeDressingRoom
 local ok,err=pcall(function()
  local gr=gRenderables;local o=s.object;local lod=0
  local root='data/sceneassets/server16_dressing_room_20261022/'
  local state=gSportsRNA:GetTable('wvState')
  local env=gSportsRNA:GetInt(state,'wvAttribEnvLighting')
  gr:AddAsset(o,lod,'charcmn','data/sceneassets/charactercmn/charactercmn_'..env..'.rx3')
  s.stadiumID=gSportsRNA:GetInt(state,'wvAttribStadID');s.lightID=gSportsRNA:GetInt(state,'wvAttribStadLightID')
  s.stadiumType=gSportsRNA:GetString(state,'wvAttribStadType')=='festadium' and 0 or 1
  for i=0,1 do gr:AddAsset(o,lod,'atlas_'..i,root..'scenery_textures_'..i..'_r62.rx3') end
  gr:AddAsset(o,lod,'coverage',root..'room_white_r49.rx3')
  local meshes={{'room_part_1',0},{'room_part_2',0,true},{'room_part_3',1}}
  for i,m in ipairs(meshes) do
   local part='room_part_'..i
   gr:AddAsset(o,lod,part,root..'scenery_r62.rx3')
   gr:CreateMaterialFromAttribulator(o,lod,part,'prop_material',m[3] and 'prop_alpha' or 'prop_plastic')
   gr:SetSubMesh(o,lod,part,m[1])
   if m[2]==2 then gr:SetTexture(o,lod,part,'textures','diffuseTexture','floor','floor_cm') else gr:SetTexture(o,lod,part,'textures','diffuseTexture','atlas_'..m[2],'room_cm') end
   gr:SetTexture(o,lod,part,'textures','normalMap','textures','_nm')
   gr:SetTexture(o,lod,part,'textures','coeffMap','textures','_coeff')
   gr:SetTexture(o,lod,part,'textures','envDiffuseTexture','charcmn','envd_')
   gr:SetTexture(o,lod,part,'textures','envSpecTexture','charcmn','envs_')
   gr:SetTexture(o,lod,part,'textures','coverageMap','coverage','white_cm')
  end
  gr:SetDBInt(o,'server16_room_revision',1)
  gr:Reload(o,1);s.bound=true
 end)
 s.ok=ok;s.error=tostring(err);s.stage=ok and 'bound_loading' or 'failed'
end
)lua";
bool guardObject(){
 const auto value=roomField("object");if(value.type!=2||value.value<0x10000)return false;
 if(value.value!=allocatedNative){fault=12;phase=9;log("OBJECT_IS_NOT_ISOLATED_ALLOCATION_REJECTED");return false;}
 auto p=value.value,vt=get<uintptr_t>(p);
 if(vt!=image+0x2210dc0||get<uintptr_t>(vt+24)!=image+0x43c8f30||get<uintptr_t>(vt+32)!=image+0x43c8f20){fault=4;phase=9;log("UNEXPECTED_NATIVE_RENDERABLE_CLASS");return false;}
 auto ctx=get<uintptr_t>(p+0x30),impl=get<uintptr_t>(p+0x20);
 const unsigned count=get<unsigned>(impl+0x38);const auto colors=get<uintptr_t>(ctx);
 if(get<uintptr_t>(ctx+8)!=p||count<1||count>64||!colors||get<uint64_t>(colors-16)!=count){fault=5;phase=9;log("NATIVE_CONTEXT_OR_INSTANCE_CONTRACT_REJECTED");return false;}
 object=p;originalVtable=vt;originalDraw=get<uintptr_t>(vt+32);if(!read(vt,ownVtable,sizeof ownVtable)){object=0;return false;}ownVtable[4]=(uintptr_t)&draw;
 if(InterlockedCompareExchangePointer((void*volatile*)p,ownVtable,(void*)vt)!=(void*)vt){object=0;fault=6;return false;}
 alignas(16)float matrix[16]={1,0,0,0,0,1,0,0,0,0,1,0,roomOriginX,0,0,1};
 for(unsigned i=0;i<count;++i)((void(__fastcall*)(void*,int,const float*,bool))(image+0x4ad80b0))((void*)object,static_cast<int>(i),matrix,false);
 visibility(false);log("NATIVE_GAMEPLAYPROP_CONTEXT_VALIDATED: native capacity retained, only instance zero used");return true;
}
void poll(){
 const bool requested=page();active=false;
 if(!requested){roomLoading=false;roomLoadBegan=0;if(object)visibility(false);hideComponents();
  auto pointer=get<uintptr_t>(image+0x3809030);for(unsigned offset:{232u,192u,136u,472u})pointer=get<uintptr_t>(pointer+offset);char current[128]{};
  if(validCareerClub&&read(pointer,current,127)&&!strncmp(current,"game/screens/career/",20)){pollComponents(false);pollSlate(false,false);}return;}
 if(!roomLoadBegan)roomLoadBegan=GetTickCount64();roomLoading=true;pollSlate(true,false);
 if(!creationAttempted){creationAttempted=true;requestedAt=GetTickCount64();phase=1;log("ROOM_CARD_ENTER: isolated native allocation, stadium retained");
  void*allocator=((void*(__fastcall*)())(image+0x4abfba0))();
  const auto allocate=get<uintptr_t>(get<uintptr_t>((uintptr_t)allocator)+0x10);
  void*storage=((void*(__fastcall*)(void*,size_t,const char*,int))allocate)(allocator,0x38,"Server16DressingRoom",1);
  if(!storage){fault=11;phase=9;log("NATIVE_ALLOCATION_FAILED");return;}
  allocatedNative=(uintptr_t)((void*(__fastcall*)(void*,void*,const char*,int,int,int))(image+0x43c8be0))(storage,allocator,"server16_native_dressing_room_r60",0,1,1);
  if(!allocatedNative||get<uintptr_t>(allocatedNative)!=image+0x2210dc0){fault=11;phase=9;log("NATIVE_FACTORY_ALLOCATION_REJECTED");return;}
  ((void(__fastcall*)(void*,const char*,int))(image+0x4ac5450))((void*)allocatedNative,"server16_native_dressing_room_r60",0);
  if(!execute(createScript)){fault=1;phase=9;return;}}
 if(!object&&!fault){auto ok=roomField("ok");if(ok.type==1&&!ok.value){fault=2;phase=9;log("NATIVE_ASSET_REQUEST_REJECTED");return;}guardObject();}
 if(!object&&!fault&&GetTickCount64()-requestedAt>45000){fault=3;phase=9;log("NATIVE_OBJECT_TIMEOUT_NO_RETRY");}
 if(object&&!fault){
  if(!registered){
   const char script[]="local s=S16NativeDressingRoom;local ok,err=pcall(function() ContextAddRenderable('gameplayprops',s.object,1,{}) end);s.registered=ok;s.error=tostring(err);s.stage=ok and 'registered_loading' or 'failed'";
   if(!execute(script)||roomField("registered").type!=1||!roomField("registered").value){fault=7;phase=9;log("NATIVE_CONTEXT_REGISTRATION_REJECTED");return;}
   registered=true;log("NATIVE_CONTEXT_REGISTERED_LOADING");
  }
  if(!prepareAttempted){prepareAttempted=true;log("NATIVE_PREPARE_BEGIN");((void(__fastcall*)(void*,bool))(image+0x4ad7e50))((void*)object,true);log("NATIVE_PREPARE_RETURNED");}
  if(!ready&&loaded()){
   log("NATIVE_ASSETS_READY");phase=2;
   ready=true;phase=3;log("NATIVE_CONTEXT_READY");
  }else if(!ready&&GetTickCount64()-requestedAt>45000){fault=8;phase=9;log("NATIVE_ASSET_TIMEOUT_NO_RETRY");}
 }
 pollComponents(false);
 componentsReadyStatus=roomComponentsReady();active=requested&&ready&&componentsReadyStatus&&!fault&&!holdDrawing;roomLoading=requested&&!active;
 visibility(active);showComponents(active);
 const bool preparationError=fault||roomComponentsFailed()||GetTickCount64()-roomLoadBegan>90000;
 pollSlate(roomLoading,preparationError);
}
void*__fastcall frame(){
 camera.restore();void*result=((void*(__fastcall*)())previousFrame)();++frames;
 if(stopping)return result;
 __try{poll();if(active||roomLoading){if(roomRosterCameraOwned())camera.tourTick=0;else camera.apply(roomLoading);}else camera.resetTour();roomReturnTick(page());}
 __except(EXCEPTION_EXECUTE_HANDLER){fault=GetExceptionCode();phase=9;active=false;log("ROOM_MONITOR_EXCEPTION_DISABLED");}
 return result;
}
bool exchange(LONG from,LONG to){auto*p=(volatile LONG*)(image+0x3a19f80);DWORD old;if(!VirtualProtect((void*)p,4,PAGE_EXECUTE_READWRITE,&old))return false;LONG seen=InterlockedCompareExchange(p,to,from);DWORD ignored;VirtualProtect((void*)p,4,old,&ignored);FlushInstructionCache(GetCurrentProcess(),(void*)(image+0x3a19f7f),5);return seen==from;}
bool compatible(uintptr_t target){
 if(target==image+0x44d8ce0)return !GetModuleHandleW(L"panorama_drone_v5.dll")&&!GetModuleHandleW(L"frontend_stadium_native_v11.dll");
 unsigned char jump[14]{};if(!read(target,jump,14)||memcmp(jump,"\xff\x25\0\0\0\0",6))return false;uintptr_t address=0;memcpy(&address,jump+6,8);HMODULE owner=nullptr;
 if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,(LPCWSTR)address,&owner))return false;
 wchar_t path[1024]{};GetModuleFileNameW(owner,path,1024);const auto leaf=wcsrchr(path,L'\\');if(!leaf)return false;
 if(GetModuleHandleW(L"panorama_drone_v5.dll")&&wcsncmp(leaf+1,L"panorama_drone",14))return false;
 return !wcsncmp(leaf+1,L"panorama_drone",14)||!wcsncmp(leaf+1,L"frontend_stadium",16);
}
bool install(){
 if(get<unsigned char>(image+0x3a19f7f)!=0xe8)return false;beforeCall=get<LONG>(image+0x3a19f80);previousFrame=image+0x3a19f84+beforeCall;if(!compatible(previousFrame))return false;
 if(!relay){for(uintptr_t step=0x10000;step<0x70000000&&!relay;step+=0x10000)relay=VirtualAlloc((void*)(image+step),4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);if(!relay)return false;unsigned char jump[14]={0xff,0x25,0,0,0,0};auto target=(uintptr_t)&frame;memcpy(jump+6,&target,8);memcpy(relay,jump,14);DWORD old;if(!VirtualProtect(relay,4096,PAGE_EXECUTE_READ,&old))return false;FlushInstructionCache(GetCurrentProcess(),relay,4096);}
 oursCall=LONG(intptr_t(relay)-intptr_t(image+0x3a19f84));return exchange(beforeCall,oursCall);
}
void status(){std::ofstream f(folder/L"runtime/native_status.json.tmp");f<<"{\"pid\":"<<GetCurrentProcessId()<<",\"installed\":"<<(installed?"true":"false")<<",\"scene_state\":"<<roomSceneState<<",\"active\":"<<(active?"true":"false")<<",\"ready\":"<<(ready?"true":"false")<<",\"loading\":"<<(roomLoading?"true":"false")<<",\"components_ready\":"<<(componentsReadyStatus?"true":"false")<<",\"phase\":"<<phase<<",\"error\":"<<fault<<",\"frames\":"<<frames<<",\"native_draw_callbacks\":"<<draws<<",\"native_draw_returns\":"<<submissions<<",\"object\":"<<object<<",\"indoor_uploads\":"<<indoorUploads<<",\"indoor_failures\":"<<indoorFailures<<",\"return_background_refreshes\":"<<roomReturnRefreshes<<",\"return_background_hook\":"<<(roomPhotoInstalled?"true":"false")<<",\"roster_camera\":"<<(roomRosterCameraOwned()?"true":"false")<<",\"camera_automatic\":"<<(camera.director.automatic?"true":"false")<<",\"camera_selected\":"<<camera.director.selected<<",\"camera_paused\":"<<(camera.director.paused?"true":"false")<<",\"camera_command_sequence\":"<<camera.controlSequence<<",\"stadium_reloads\":0,\"renderer\":\"FIFA native GameplayProp\",\"webview\":false}\n";f.close();MoveFileExW((folder/L"runtime/native_status.json.tmp").c_str(),(folder/L"runtime/native_status.json").c_str(),MOVEFILE_REPLACE_EXISTING);}
DWORD WINAPI worker(void*){
 const auto began=GetTickCount64();log("WAIT_NATIVE_CODE: delayed signature validation after executable unpack");
 while(!stopping){
  holdDrawing=fs::exists(folder/L"runtime/HOLD_NATIVE_DRAW");validCareerClub=snapshotClub();
  {std::ifstream f(folder/L"runtime/indoor_ambient.txt");float value=0;if(f>>value&&std::isfinite(value)&&value>=.2f&&value<=1.2f)indoorAmbient=value;}
  launchNativeAssetHelper();
  if(!codeValidated&&!fault){if(nativeCodeReady()){codeValidated=true;phase=0;log("NATIVE_CODE_VALIDATED");}else if(GetTickCount64()-began>120000){fault=10;phase=9;log("NATIVE_CODE_NOT_READY_DISABLED");}}
  if(codeValidated&&!installed&&!fault){if(install()){installed=true;log("READY: separate native room scene");}}
  if(codeValidated&&installed&&!roomPhotoInstalled)installRoomPhoto();
  if(codeValidated&&installed&&!medicalInstallAttempted){medicalInstallAttempted=true;if(!installMedicalCapture())log("MEDICAL_NATIVE_CAPTURE_DISABLED_SIGNATURE_MISMATCH");}
  flushMedicalCapture();
  if(fs::exists(folder/L"runtime/STOP_NATIVE"))stopping=true;status();Sleep(500);
 }
 closeNativeAssetHelperMonitor();active=false;roomLoading=false;hideComponents();componentVisibility(loadingSlate,false);componentVisibility(errorSlate,false);camera.restore();if(object){visibility(false);InterlockedCompareExchangePointer((void*volatile*)object,(void*)originalVtable,ownVtable);}if(installed)exchange(oursCall,beforeCall);if(roomPhotoInstalled)roomPhotoExchange(roomPhotoAfter,roomPhotoBefore);stopMedicalCapture();installed=false;log("STOPPED: prior render callback restored");status();return 0;
}
}
extern "C" __declspec(dllexport) unsigned WINAPI Fifa16ModGetApiVersion(){return 1;}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16RoomSceneCommand(const char*wire){return captureRoomSceneCommand(wire)?TRUE:FALSE;}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char*){
 if(started.exchange(true))return TRUE;image=(uintptr_t)GetModuleHandleW(nullptr);if(get<unsigned>(image+get<int>(image+0x3c)+8)!=0x577de45c){started=false;return FALSE;}
 HMODULE self=nullptr;GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCWSTR)&Fifa16ModStart,&self);wchar_t path[1024]{};GetModuleFileNameW(nullptr,path,1024);game=fs::path(path).parent_path();folder=game/L"ModCarrerMode/runtime/club_environment/room";logfile=folder/L"runtime/native_room.log";
 try{fs::create_directories(folder/L"runtime");}catch(...){started=false;return FALSE;}
 {std::ofstream f(logfile);f<<"Native dressing room session pid="<<GetCurrentProcessId()<<"\n";}
 for(const auto*name:{L"scenery_r62.rx3",L"scenery_textures_0_r62.rx3",L"scenery_textures_1_r62.rx3",L"room_white_r49.rx3",L"floor_textures_r44.rx3"}){
  const auto target=game/L"data/sceneassets/server16_dressing_room_20261022"/name;
  if(!fs::is_regular_file(target)||fs::file_size(target)<128){log("MISSING_INSTALLED_ROOM_ASSET: native scene disabled before asset request");started=false;return FALSE;}
 }
 HANDLE thread=CreateThread(nullptr,0,worker,nullptr,0,nullptr);if(!thread){started=false;return FALSE;}CloseHandle(thread);return TRUE;
}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16ModStop(){stopping=true;return TRUE;}
BOOL WINAPI DllMain(HINSTANCE h,DWORD reason,LPVOID){if(reason==DLL_PROCESS_ATTACH)DisableThreadLibraryCalls(h);return TRUE;}
