#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <xinput.h>
#include <atomic>
#include <array>
#include <vector>
#include <string>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <memory>
#include <algorithm>
#include <cmath>
#include <cstring>
#include "../../room/native/motions.h"
#include "../../room/native/room_camera_projection.h"
#include "../../../native_mods/frontend_stadium/career_profile.h"
#include "frame_chain.h"
#include "../../../common/scene_lens.h"
#include "../../../common/scene_loading.h"
#include "gallery_tour.h"
#include "../../../common/trophy_shelf.h"
#include "gallery_inspect.h"
#include "../../room/native/room_fps_mouse.h"
#include "gallery_light.h"
#include "gallery_material.h"
#include "gallery_postfx.h"
#include "../../room/native/room_light_probe.h"
#include "../../room/native/room_helper_process_r61.h"
#include "../../room/native/room_startup.h"

namespace fs=std::filesystem;
namespace {
scene_lens::Lease cleanLens;
gallery_postfx::Lease cleanOptics;
std::atomic<unsigned> effectsTestMode{0};std::atomic<bool> cleanCamera{false};
RoomStartup sceneStartup;std::atomic<bool>sceneStartupPermitted{false};
constexpr char pageName[]="game/screens/career/server16/TrophyRoom";
constexpr float originX=-100000.f;
uintptr_t image=0,previousFrame=0;void*relay=nullptr;
LONG oldCall=0,newCall=0;
std::atomic<bool> started{false},stopping{false},installed{false},requested{false},active{false};
std::atomic<unsigned> club{0},epoch{0},generation{0},titleCount{0},selectedPage{0},pages{1},phase{0},error{0};
std::atomic<int> command{-1},selectedTrophy{-1};std::atomic<bool> detailStatus{false};
std::atomic<unsigned> componentCount{0},loadedCount{0};
fs::path game,folder,config;
std::atomic<bool> coachCollection{false};
std::atomic<bool> listMode{true},listReady{false};
std::atomic<unsigned> shelfPage{0},shelfSelected{0},shelfTotal{0},shelfGeneration{0};
int pendingDetailSlot=-1;std::atomic<unsigned> detailScroll{0};
std::atomic<bool> custom{true},freeCamera{false};gallery_tour::Tour tour;
bool residentScene=false,publicationPending=false,pageDetail=false;int pageVisit=0;
uint64_t nextPoll=0,enteredAt=0,lastInput=0;std::atomic<unsigned> uploads{0};
uintptr_t ownVtable[29]{};
SRWLOCK componentsLock=SRWLOCK_INIT;
struct Component {
 std::string key,type,model,submesh,texture,diffuse,aux,normal,coeffTexture,coeff;
 bool alpha=false,baked=false,attempted=false,loaded=false,failed=false,roomEnvironment=false;
 int detailSlot=-1;uintptr_t object=0;std::vector<std::array<float,16>> matrices;
 std::vector<std::array<float,16>> baseMatrices;
 room_light_probe::Probe probe;
};
bool shell(const Component&c){return c.key.rfind("cup_",0)!=0&&c.key.rfind("plaque_",0)!=0&&c.key.rfind("detail_",0)!=0;}
std::vector<std::unique_ptr<Component>> components,retired;
std::vector<std::unique_ptr<Component>> loadingParts;
std::atomic<bool> loadingVisible{false};unsigned loadingClub=0;
// Independent material-lighting gains keep the room clear without washing out
// the native metal cups. Loaded by the worker, never from the render callback.
std::atomic<float> roomLightIntensity{1.75f},trophyLightIntensity{1.15f};
void refreshLighting(){
 auto setting=[&](const wchar_t* key,const wchar_t* initial,float fallback){
  wchar_t text[48]{};GetPrivateProfileStringW(L"Lighting",key,initial,text,48,config.c_str());
  wchar_t* end=nullptr;const float value=std::wcstof(text,&end);
  return end==text||*end?fallback:gallery_light::safeIntensity(value,fallback);
 };
 roomLightIntensity=setting(L"RoomIntensity",L"1.75",1.75f);
 trophyLightIntensity=setting(L"TrophyIntensity",L"1.15",1.15f);
 cleanCamera=GetPrivateProfileIntW(L"Rendering",L"CleanCamera",0,config.c_str())!=0;
 std::ifstream test(folder/L"effects_test.txt");std::string line;std::getline(test,line);
 effectsTestMode=gallery_postfx::testMode(line,GetCurrentProcessId());
}
bool read(uintptr_t at,void*out,size_t n){if(at<0x10000)return false;__try{memcpy(out,(void*)at,n);return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
template<class T>T get(uintptr_t at){T v{};read(at,&v,sizeof v);return v;}
bool write(uintptr_t at,const void*data,size_t n){__try{memcpy((void*)at,data,n);return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
void log(const char*text){std::ofstream f(folder/L"native.log",std::ios::app);f<<GetTickCount64()<<" pid="<<GetCurrentProcessId()<<" "<<text<<"\n";}
#include "gallery_scene_bridge.h"
bool visiblePage(){
 auto p=get<uintptr_t>(image+0x3809030);for(unsigned o:{232u,192u,136u,472u})p=get<uintptr_t>(p+o);
 char value[128]{};return read(p,value,127)&&!strcmp(value,pageName);
}
struct Scope {DWORD schema,size,sequence,pid;uintptr_t service,vtable,registry;DWORD epoch,thread;};
Scope scope(){
 Scope a{},b{};auto module=GetModuleHandleW(L"dinput8.dll");auto at=(uintptr_t)(module?GetProcAddress(module,"Fifa16CareerContextRead"):nullptr);
 if(!read(at,&a,sizeof a)||a.schema!=1||a.size!=sizeof a||(a.sequence&1)||a.pid!=GetCurrentProcessId()||!read(at,&b,sizeof b)||memcmp(&a,&b,sizeof a))return {};
 return a;
}
bool execute(const std::string&text){
 auto lua=get<uintptr_t>(image+0x3613fd0);if(!lua||get<int>(lua+0x80)!=5)return false;
 __try{((void(__fastcall*)(const char*,size_t,const char*))(image+0x4ac35e0))(text.c_str(),text.size(),"Server16TrophyRoom");return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
struct LuaValue {uintptr_t value=0;int type=0;};
LuaValue luaField(uintptr_t table,const char* key){
 unsigned char h[64]{};if(!read(table,h,64)||h[8]!=5||h[11]>14)return {};
 const auto nodes=get<uintptr_t>(table+32);const auto wanted=strlen(key);
 for(unsigned i=0;i<(1u<<h[11]);++i){
  const auto row=nodes+i*40;if(get<int>(row+24)!=4)continue;const auto s=get<uintptr_t>(row+16);
  char text[128]{};if(wanted>=sizeof text||get<size_t>(s+16)!=wanted||!read(s+24,text,wanted)||memcmp(text,key,wanted))continue;
  LuaValue v{get<uintptr_t>(row),get<int>(row+8)};if(v.type==1)v.value&=0xffffffff;return v;
 }return {};
}
LuaValue luaStateField(const char* key){
 const auto lua=get<uintptr_t>(image+0x3613fd0);const auto state=luaField(get<uintptr_t>(lua+0x78),"S16TrophyState");
 return state.type==5?luaField(state.value,key):LuaValue{};
}
#include "background.h"
std::string quote(const std::string&text){std::ostringstream s;s<<std::quoted(text);return s.str();}
bool safePath(const std::string&text){
 return text.size()<768&&!text.empty()&&text.find("..")==text.npos&&text.find(':')==text.npos&&text[0]!='/'&&text[0]!='\\'
  &&(text.rfind("data/sceneassets/",0)==0||text.rfind("ModCarrerMode/runtime/trophy_room/",0)==0);
}
void visibility(Component&c,bool show){
 if(!c.object)return;for(size_t i=0;i<c.matrices.size();++i)
  ((void(__fastcall*)(void*,int,const float*,bool))(image+0x4ad80b0))((void*)c.object,int(i),c.matrices[i].data(),show);
}
void hide(){for(auto&c:components)visibility(*c,false);for(auto&c:loadingParts)visibility(*c,false);loadingVisible=false;}

// Private lighting buffers belong only to this gallery's own GameplayProps.
// Their maps and original material parameters remain FIFA resources.
struct alignas(16) DrawArgs {
 float color[4];uintptr_t object;int instance;unsigned padding;uintptr_t buffer,view;float sphere[4];
 bool baked,cup,roomEnvironment;unsigned char pad;float position[3];
};
static_assert(sizeof(DrawArgs)==80);
void ref(uintptr_t p,bool add){if(p)((void(__fastcall*)(void*))get<uintptr_t>(get<uintptr_t>(p)+(add?0:8)))((void*)p);}
bool light(uintptr_t buffer,bool baked,const float*point=nullptr,float intensity=1.f){
 auto device=get<uintptr_t>(image+0x36140b0);if(!device||!buffer)return false;uintptr_t context=0;
 ((void(__fastcall*)(void*,uintptr_t*))get<uintptr_t>(get<uintptr_t>(device)+0x30))((void*)device,&context);if(!context)return false;
 struct Mapped{void*data;uint64_t row;uint32_t depth,padding;} mapped{};
 ((void(__fastcall*)())(image+0x4abd6b0))();bool ok=false;
 __try{
  ref(buffer,true);((void(__fastcall*)(void*,void*,void*,unsigned,Mapped*))get<uintptr_t>(get<uintptr_t>(context)+0x340))((void*)context,(void*)buffer,(void*)(image+0x35b0e80),4,&mapped);ref(buffer,false);
  ok=mapped.data!=nullptr;if(ok){
   std::array<float,28> sh{};
   for(int c=0;c<3;++c){sh[c*9]=(baked?1.f:.86f)/.2820947918f;if(!baked){sh[c*9+1]=.14f/.4886025119f;sh[c*9+2]=.32f/.4886025119f;sh[c*9+3]=.12f/.4886025119f;}}
   if(point)sh=gallery_light::coefficients(point[0],point[1],point[2],intensity);
   write((uintptr_t)mapped.data,sh.data(),sizeof sh);ref(buffer,true);
   ((void(__fastcall*)(void*,void*,void*,Mapped*))get<uintptr_t>(get<uintptr_t>(context)+0x348))((void*)context,(void*)buffer,(void*)(image+0x35b0e80),&mapped);ref(buffer,false);++uploads;
  }
 }__finally{((void(__fastcall*)())(image+0x4abe9f0))();ref(context,false);}return ok;
}
void __fastcall meshDraw(void*mesh,void*material,DrawArgs*args){
 ((void(__fastcall*)(void*,int,void*))(image+0x4431720))((void*)args->object,args->instance,material);
 uintptr_t buffer=args->buffer,specular=0;ref(buffer,true);auto manager=((void*(__fastcall*)())(image+0x4405da0))();
 // Probe the existing native field lighting environment, rather than the
 // distant exhibition coordinates, for the installed specular cubemap.
 gallery_material::LightSample sample;((void(__fastcall*)(void*,const float*,uintptr_t*,uintptr_t*))(image+0x4405dc0))(manager,sample.value,&buffer,&specular);
 light(args->buffer,args->baked,args->baked?nullptr:args->position,args->cup?trophyLightIntensity.load():roomLightIntensity.load());
 gallery_material::bindSpecular(args->cup,specular!=0,[&](const char* name){
  ((void(__fastcall*)(void*,const char*,const char*,void*))(image+0x4acdd30))(material,"",name,(void*)specular);
 },args->roomEnvironment);
 ((void(__fastcall*)(void*,const char*,const char*,void*))(image+0x4acdba0))(material,"","in_sh_data",(void*)args->view);
 ((void(__fastcall*)(void*,const char*,const char*,const float*,int))(image+0x4ace000))(material,"","overlayColor",args->color,1);
 ((void(__fastcall*)(void*,int,int,void*))(image+0x4acbd90))(material,-1,0,nullptr);
 ((void(__fastcall*)(void*,void*,int,int,void*))(image+0x4ade9a0))(mesh,material,0,0,nullptr);ref(specular,false);
}
void drawObject(void*self,bool baked,bool cup,unsigned instances,bool caster=false){
 auto o=(uintptr_t)self,vt=get<uintptr_t>(o),ctx=get<uintptr_t>(o+0x30);
 const int nativeCount=((int(__fastcall*)(void*))(image+0x4ad7a60))(self);if(nativeCount<0||nativeCount>64)return;
 const int count=std::min(nativeCount,int(instances));
 for(int i=0;i<count;++i){
  auto instance=((uintptr_t(__fastcall*)(void*,int))get<uintptr_t>(vt+0xe0))(self,i);if(!instance)continue;
  ((void(__fastcall*)(void*))(image+0x4abe600))((void*)instance);
  gallery_scene_bridge::begin(o,unsigned(i),instance,caster);
  DrawArgs args{};read(get<uintptr_t>(ctx)+i*16,args.color,16);args.object=o;args.instance=i;args.baked=baked;args.cup=cup;
  for(auto&c:components)if(c->object==o&&size_t(i)<c->matrices.size()){
   args.roomEnvironment=c->roomEnvironment;
   float point[4]{};if(room_light_probe::transform(c->probe,c->matrices[i].data(),point)){
    args.position[0]=point[0]-originX;args.position[1]=point[1]-1000;args.position[2]=point[2];
   }else{args.position[0]=0;args.position[1]=150;args.position[2]=0;}break;
  }
  args.buffer=get<uintptr_t>(ctx+0x18);args.view=get<uintptr_t>(ctx+0x20);read(instance+0x30,args.sphere,16);ref(args.buffer,true);ref(args.view,true);
  const int lods=((int(__fastcall*)(void*))(image+0x4ad7a00))(self);
  for(int lod=0;lod<lods&&lod<4;++lod){auto composite=((void*(__fastcall*)(void*,int))get<uintptr_t>(vt+0x88))(self,lod);((void(__fastcall*)(void*,void*,DrawArgs*))(image+0x4addc70))(composite,(void*)&meshDraw,&args);}
  ref(args.view,false);ref(args.buffer,false);
  gallery_scene_bridge::end();
 }
}
void __fastcall draw(void*self,int pass){
 if(stopping||listMode||!requested||!visiblePage())return;
 __try{
  bool baked=false,cup=false,keep=false,caster=false;unsigned instances=0;for(auto&c:components)if(c->object==uintptr_t(self)){baked=c->baked;cup=c->key.rfind("cup_",0)==0;caster=gallery_scene_bridge::casts(c->key,c->alpha,c->baked);keep=residentScene&&shell(*c)&&c->loaded;instances=unsigned(c->matrices.size());if(c->key.rfind("detail_",0)==0&&(!tour.detail||c->detailSlot!=tour.selected()))instances=0;break;}
  if(!active&&!keep){instances=0;if(loadingVisible)for(auto&c:loadingParts)if(c->object==uintptr_t(self)){baked=true;instances=1;break;}}
  if(pass==1&&instances)drawObject(self,baked,cup,instances,caster);
 }__except(EXCEPTION_EXECUTE_HANDLER){gallery_scene_bridge::end(false);error=GetExceptionCode();active=false;phase=9;}
}
bool create(Component&c){
 c.attempted=true;auto allocator=((void*(__fastcall*)())(image+0x4abfba0))();auto alloc=get<uintptr_t>(get<uintptr_t>((uintptr_t)allocator)+0x10);
 if(!alloc)return false;auto storage=((void*(__fastcall*)(void*,size_t,const char*,int))alloc)(allocator,0x38,"Server16TrophyGallery",1);if(!storage)return false;
 c.object=(uintptr_t)((void*(__fastcall*)(void*,void*,const char*,int,int,int))(image+0x43c8be0))(storage,allocator,c.type.c_str(),0,1,64);
 if(!c.object||get<uintptr_t>(c.object)!=image+0x2210dc0)return false;
 if(!ownVtable[0]){if(!read(image+0x2210dc0,ownVtable,sizeof ownVtable))return false;ownVtable[4]=(uintptr_t)&draw;}
 auto context=get<uintptr_t>(c.object+0x30),impl=get<uintptr_t>(c.object+0x20);
 if(get<uintptr_t>(context+8)!=c.object||get<unsigned>(impl+0x38)!=64)return false;
 InterlockedExchangePointer((void*volatile*)c.object,ownVtable);
 alignas(16)float hidden[16]={1,0,0,0,0,1,0,0,0,0,1,0,originX,1000,0,1};
 for(int i=0;i<64;++i)((void(__fastcall*)(void*,int,const float*,bool))(image+0x4ad80b0))((void*)c.object,i,hidden,false);
 ((void(__fastcall*)(void*,const char*,int))(image+0x4ac5450))((void*)c.object,c.type.c_str(),0);
 const bool cup=c.key.rfind("cup_",0)==0;
 c.roomEnvironment=cup&&fs::is_regular_file(game/L"data/sceneassets/server16_trophy_room/gallery-environment.rx3");
 std::string part=cup?gallery_tour::material(c.submesh):(c.alpha?"prop_alpha":"prop_plastic");
 std::string code="S16TrophyState={ok=false};do local gr=gRenderables;local o=gr:Find("+quote(c.type)+",0);local ok,err=pcall(function() assert(o,'Gallery prop unavailable');local lod=0;local part="+quote(part)+";";
 code+="gr:AddAsset(o,lod,'shader','data/fifarna/shader.big');gr:AddAsset(o,lod,part,"+quote(c.model)+");gr:AddAsset(o,lod,'color',"+quote(c.texture)+");gr:AddAsset(o,lod,'aux',"+quote(c.aux)+");gr:AddAsset(o,lod,'coeff',"+quote(c.coeffTexture)+");";
 code+="local state=gSportsRNA:GetTable('wvState');local env=gSportsRNA:GetInt(state,'wvAttribEnvLighting');gr:AddAsset(o,lod,'charcmn','data/sceneassets/charactercmn/charactercmn_'..env..'.rx3');gr:AddAsset(o,lod,'coverage','data/sceneassets/server16_trophy_room/white.rx3');";
 code+="gr:CreateMaterialFromAttribulator(o,lod,part,"+quote(cup?"trophy_material":"prop_material")+",part);gr:SetSubMesh(o,lod,part,"+quote(c.submesh)+");gr:SetTexture(o,lod,part,'textures','diffuseTexture','color',"+quote(c.diffuse)+");";
 code+="gr:SetTexture(o,lod,part,'textures','normalMap','aux',"+quote(c.normal)+");gr:SetTexture(o,lod,part,'textures','coeffMap','coeff',"+quote(c.coeff)+");gr:SetTexture(o,lod,part,'textures','envDiffuseTexture','charcmn','envd_');gr:SetTexture(o,lod,part,'textures','envSpecTexture','charcmn','envs_');gr:SetTexture(o,lod,part,'textures','coverageMap','coverage','gallery_cm');gr:SetDBInt(o,'server16_gallery_revision',2);gr:Reload(o,1);ContextAddRenderable('gameplayprops',o,1,{}) end);S16TrophyState.ok=ok;S16TrophyState.error=tostring(err) end";
 if(cup){const auto at=code.find("gr:Reload(o,1)");
  code.insert(at,c.roomEnvironment?
   "gr:AddAsset(o,lod,'galleryenv','data/sceneassets/server16_trophy_room/gallery-environment.rx3');gr:SetTexture(o,lod,part,'textures','envDiffuseTexture','galleryenv','room_diffuse');gr:SetTexture(o,lod,part,'textures','envSpecTexture','galleryenv','room_specular');gr:SetTexture(o,lod,part,'textures','INDIRECT_SPECULAR_TEXTURE','galleryenv','room_specular');":
   "gr:SetTexture(o,lod,part,'textures','INDIRECT_SPECULAR_TEXTURE','charcmn','envs_');");}
 if(!execute(code))return false;
 const auto ok=luaStateField("ok");if(ok.type!=1||!ok.value){
  const auto err=luaStateField("error");char message[512]{};
  if(err.type==4)read(err.value+24,message,std::min<size_t>(get<size_t>(err.value+16),sizeof message-1));
  log(("GALLERY_SCRIPT_FAILED: "+c.key+" "+message).c_str());return false;
 }
 ((void(__fastcall*)(void*,bool))(image+0x4ad7e50))((void*)c.object,true);log(("GALLERY_COMPONENT_REQUEST: "+c.key).c_str());return true;
}
bool loaded(Component&c){
 if(!c.object)return false;auto impl=get<uintptr_t>(c.object+0x20),list=get<uintptr_t>(impl+0x20);
 if(get<unsigned>(impl+0x18)!=1)return false;auto composite=get<uintptr_t>(list);
 if(!get<unsigned char>(composite+0x10))((int(__fastcall*)(void*))(image+0x4add100))((void*)composite);
 return ((bool(__fastcall*)(void*))(image+0x4ad7d80))((void*)c.object);
}
bool manifest(){
 std::ifstream f(folder/L"components.txt");std::string magic;unsigned version=0,pid=0,id=0,ep=0,gen=0,style=0,count=0,total=0,page=0,pageCount=1,collection=0;
 if(!(f>>magic>>version>>pid>>id>>ep>>gen>>style>>count>>total>>page>>pageCount>>collection)||magic!="S16TROPHY"||(version!=2&&version!=3)||collection!=unsigned(coachCollection)||pid!=GetCurrentProcessId()||id!=club||ep!=epoch||style!=unsigned(custom)||page!=selectedPage||count<1||count>512||pageCount<1||page>=pageCount)return false;
 if(gen==generation&&!components.empty()){publicationPending=false;return true;}
 std::vector<std::unique_ptr<Component>> next;
 for(unsigned n=0;n<count;++n){auto c=std::make_unique<Component>();unsigned alpha=0,baked=0,instances=0;
  if(!(f>>std::quoted(c->key)>>std::quoted(c->model)>>std::quoted(c->submesh)>>std::quoted(c->texture)>>std::quoted(c->diffuse)>>std::quoted(c->aux)>>std::quoted(c->normal)>>std::quoted(c->coeffTexture)>>std::quoted(c->coeff)>>alpha>>baked>>instances)
     ||instances<1||instances>64||c->key.size()>96||c->submesh.size()>128||!safePath(c->model)||!safePath(c->texture)||!safePath(c->aux)||!safePath(c->coeffTexture))return false;
  c->alpha=alpha!=0;c->baked=baked!=0;if(c->key.rfind("detail_",0)==0)c->detailSlot=atoi(c->key.c_str()+7);c->type="s16_trophy_"+std::to_string(gen)+"_"+std::to_string(n);c->matrices.resize(instances);
  c->probe.local={0,150,0,1};c->probe.valid=true;
  if(version>=3)for(unsigned axis=0;axis<3;++axis)if(!(f>>c->probe.local[axis])||!std::isfinite(c->probe.local[axis])||fabsf(c->probe.local[axis])>10000)return false;
  for(auto&m:c->matrices)for(float&v:m)if(!(f>>v)||!std::isfinite(v)||fabsf(v)>200000)return false;
  c->baseMatrices=c->matrices;
  next.push_back(std::move(c));
 }
 std::ifstream cameraFile(folder/L"cameras.txt");std::string cm;unsigned cv=0,cg=0,cn=0;
 if(!(cameraFile>>cm>>cv>>cg>>cn)||cm!="S16TROPHYCAM"||cv!=1||cg!=gen||cn>30)return false;
 std::vector<gallery_tour::Visit> visits;for(unsigned i=0;i<cn;++i){gallery_tour::Visit v;
  auto load=[&](panorama::Pose&p){return bool(cameraFile>>p.eye.x>>p.eye.y>>p.eye.z>>p.target.x>>p.target.y>>p.target.z>>p.fov)&&gallery_tour::valid(p);};
  if(!(cameraFile>>v.slot)||v.slot>=30||!load(v.wide)||!load(v.detail))return false;
  for(const auto&prior:visits)if(prior.slot==v.slot)return false;visits.push_back(v);
 }
 if(residentScene)tour.replace(std::move(visits),GetTickCount64());else{tour.reset(std::move(visits),GetTickCount64());freeCamera=false;}
 if(pendingDetailSlot>=0){for(size_t i=0;i<tour.visits.size();++i)if(tour.visits[i].slot==unsigned(pendingDetailSlot)){tour.select(int(i),GetTickCount64());break;}pendingDetailSlot=-1;}
 if(pageVisit&&!tour.visits.empty()){tour.index=-1;tour.step(pageVisit,GetTickCount64());if(pageDetail)tour.details(true,GetTickCount64());pageVisit=0;pageDetail=false;}
 for(auto&c:next)for(auto&old:components)if(old&&old->key==c->key&&old->model==c->model&&old->texture==c->texture&&old->submesh==c->submesh&&old->aux==c->aux&&old->normal==c->normal&&old->coeffTexture==c->coeffTexture&&old->coeff==c->coeff&&old->alpha==c->alpha&&old->baked==c->baked&&!old->failed){
  old->matrices=c->matrices;old->baseMatrices=c->baseMatrices;old->probe=c->probe;c=std::move(old);break;
 }
 for(auto&c:components)if(c){visibility(*c,false);retired.push_back(std::move(c));}components=std::move(next);
 publicationPending=false;generation=gen;enteredAt=GetTickCount64();error=0;componentCount=count;loadedCount=0;titleCount=total;selectedPage=page;pages=pageCount;phase=residentScene?4:2;active=false;log("EXACT_COMPETITION_TROPHIES_PUBLISHED");return true;
}

struct Camera {
 uintptr_t scene=0;std::array<unsigned char,0x84> before{},after{};room_projection::BorrowedNear nearPlane;
 panorama::Vec eye{0,166,660};float yaw=0,pitch=0,fov=66;uint64_t last=0;POINT mouse{};bool mouseHeld=false;
 room_fps::DragLook<> freeMouse,detailMouse;gallery_inspect::Controls inspect;int inspected=-1;
 void restore(){
  const auto current=get<uintptr_t>(image+0x3517c10);nearPlane.restore(current,read,write);
  if(scene&&scene==current)for(const auto&range:room_projection::ownedRanges){
   std::array<unsigned char,64> now{};if(read(scene+0x40+range[0],now.data(),range[1])&&!memcmp(now.data(),after.data()+range[0],range[1]))write(scene+0x40+range[0],before.data()+range[0],range[1]);
  }scene=0;
 }
 void preset(){
  const auto p=gallery_tour::overview();eye=p.eye;fov=p.fov;const auto d=p.target-eye;yaw=atan2f(d.x,-d.z);pitch=atan2f(d.y,sqrtf(d.x*d.x+d.z*d.z));
 }
 void apply(bool advance=true);
}camera;
using PadRead=DWORD(WINAPI*)(DWORD,XINPUT_STATE*);
PadRead padRead=nullptr;XINPUT_STATE pad{};
bool foreground(){DWORD pid=0;GetWindowThreadProcessId(GetForegroundWindow(),&pid);return pid==GetCurrentProcessId();}
void Camera::apply(bool advance){
 const uint64_t now=GetTickCount64();float dt=last?float(std::min<uint64_t>(now-last,50))*.001f:0;last=now;
 if(!freeCamera)freeMouse.reset();if(!tour.detail)detailMouse.reset();
 auto s=get<uintptr_t>(image+0x3517c10);const int state=get<int>(s+0x3c);if(!s||(state!=1&&state!=13))return;
 if((active||residentScene)&&!freeCamera){
  if(advance)tour.tick(now);auto p=tour.pose(now);
  if(tour.detail){
   if(inspected!=tour.selected()){inspect={};detailMouse.reset();detailScroll=0;}
   if(advance&&foreground()){
    auto axis=[](SHORT x){return abs(int(x))>8500?float(x)/32767.f:0.f;};
    const auto held=[](int k){return (GetAsyncKeyState(k)&0x8000)!=0;};
    const auto window=GetForegroundWindow();POINT pointer{};RECT client{};bool panel=false;
    if(GetCursorPos(&pointer)&&ScreenToClient(window,&pointer)&&GetClientRect(window,&client)){
     const float scale=std::min(client.right/1600.f,client.bottom/900.f);
     if(scale>0)panel=trophy_shelf::historyContains((pointer.x-(client.right-1600*scale)/2)/scale,(pointer.y-(client.bottom-900*scale)/2)/scale);
    }
    const auto drag=detailMouse.sample(window,held(VK_LBUTTON)&&!panel);
    inspect.step((axis(pad.Gamepad.sThumbRX)+float(held(VK_RIGHT))-float(held(VK_LEFT)))*dt*1.7f+drag.yaw,
                 (axis(pad.Gamepad.sThumbRY)+float(held('I'))-float(held('K')))*dt+drag.pitch,
                 (float(held(VK_SUBTRACT)||held(VK_OEM_MINUS))-float(held(VK_ADD)||held(VK_OEM_PLUS))+gallery_inspect::triggerZoom(pad.Gamepad.bLeftTrigger,pad.Gamepad.bRightTrigger))*dt*28.f);
   }else if(!foreground())detailMouse.reset();
   p.eye.y+=std::sin(inspect.tilt)*120.f;p.fov=std::clamp(p.fov+inspect.zoom,22.f,75.f);
   const float x=get<float>(s+0x88),y=get<float>(s+0x8c);
   if(std::isfinite(x)&&std::isfinite(y)&&y>0)p=gallery_inspect::frame(p,x/y);
  }
  eye=p.eye;fov=p.fov;const auto d=p.target-eye;yaw=atan2f(d.x,-d.z);pitch=atan2f(d.y,sqrtf(d.x*d.x+d.z*d.z));
 }
 if(tour.detail||inspected>=0){
  const int selected=tour.detail&&!freeCamera?tour.selected():-1;
  for(auto&c:components)if(c->key.rfind("cup_",0)==0&&c->matrices.size()==c->baseMatrices.size())for(size_t i=0;i<c->matrices.size();++i){
   c->matrices[i]=c->baseMatrices[i];float center[4]{};
   if(selected>=0&&room_light_probe::transform(c->probe,c->baseMatrices[i].data(),center)&&gallery_inspect::slot(center)==selected)c->matrices[i]=gallery_inspect::rotate(c->baseMatrices[i],center,inspect.yaw);
  }
  inspected=selected;
 }
 if(advance&&freeCamera&&foreground()){
  float forward=0,side=0,up=0;const float speed=(GetAsyncKeyState(VK_SHIFT)&0x8000)?280.f:145.f;
  if(GetAsyncKeyState('W')&0x8000)forward+=1;if(GetAsyncKeyState('S')&0x8000)forward-=1;if(GetAsyncKeyState('D')&0x8000)side+=1;if(GetAsyncKeyState('A')&0x8000)side-=1;
  if(GetAsyncKeyState(VK_SPACE)&0x8000)up+=1;if(GetAsyncKeyState(VK_CONTROL)&0x8000)up-=1;
  auto axis=[](SHORT x){return abs(int(x))>8500?float(x)/32767.f:0.f;};forward+=axis(pad.Gamepad.sThumbLY);side+=axis(pad.Gamepad.sThumbLX);
  up+=(int((pad.Gamepad.wButtons&XINPUT_GAMEPAD_RIGHT_SHOULDER)!=0)-int((pad.Gamepad.wButtons&XINPUT_GAMEPAD_LEFT_SHOULDER)!=0));
  yaw+=axis(pad.Gamepad.sThumbRX)*dt*1.6f;pitch+=axis(pad.Gamepad.sThumbRY)*dt*1.2f;
  const auto drag=freeMouse.sample(GetForegroundWindow(),(GetAsyncKeyState(VK_LBUTTON)&0x8000)!=0);yaw+=drag.yaw;pitch+=drag.pitch;
  pitch=std::clamp(pitch,-1.2f,1.2f);auto next=eye+panorama::Vec{sinf(yaw)*forward+cosf(yaw)*side,up,-cosf(yaw)*forward+sinf(yaw)*side}*(dt*speed);
  next.x=std::clamp(next.x,-465.f,465.f);next.z=std::clamp(next.z,-690.f,690.f);next.y=std::clamp(next.y,75.f,285.f);
  // The central bench is solid. Vitrines and the closed exit remain boundaries.
  if(!(fabsf(next.x)<63&&next.z> -14&&next.z<374&&next.y<90))eye=next;
 }
 panorama::Vec direction{sinf(yaw)*cosf(pitch),sinf(pitch),-cosf(yaw)*cosf(pitch)};
 // The selected title card follows this gallery camera, never the FIFA UI.
 if(tour.detail&&!freeCamera){
  panorama::Vec right{cosf(yaw),0,sinf(yaw)},up=panorama::cross(right,direction),back=direction*-1.f;
  const auto center=eye+direction*80+right*(-118.f/3.f)+panorama::Vec{originX,1000,0};
  for(auto&c:components)if(c->key.rfind("detail_",0)==0&&c->detailSlot==tour.selected()){
   c->matrices[0]={right.x/3,right.y/3,right.z/3,0,up.x/3,up.y/3,up.z/3,0,back.x/3,back.y/3,back.z/3,0,center.x,center.y,center.z,1};visibility(*c,true);
  }
 }
 panorama::Pose pose{eye+panorama::Vec{originX,1000,0},eye+direction*200+panorama::Vec{originX,1000,0},freeCamera?68.f:fov};
 float m[16];if(!panorama::matrix(pose,m)||!read(s+0x40,before.data(),before.size()))return;
 const float x=get<float>(s+0x88),y=get<float>(s+0x8c);if(!std::isfinite(x)||!std::isfinite(y)||y<=0)return;
 const float fy=tanf(pose.fov*.00872664626f),fx=fy*x/y,zero=0;const unsigned char off=0;
 write(s+0x40,m,sizeof m);write(s+0x88,&fx,4);write(s+0x8c,&fy,4);write(s+0xb0,&off,1);write(s+0xbc,&zero,4);write(s+0xc0,&zero,4);
 read(s+0x40,after.data(),after.size());scene=s;nearPlane.apply(s,read,write);
}
#include "loading.h"
SRWLOCK inputLock=SRWLOCK_INIT;int lastPosted=-1;
void postCommand(int value){
 AcquireSRWLockExclusive(&inputLock);const auto now=GetTickCount64();
 if(value!=lastPosted||now-lastInput>=180){lastPosted=value;lastInput=now;command=value;}
 ReleaseSRWLockExclusive(&inputLock);
}
trophy_shelf::State shelfState(){return {shelfTotal.load(),shelfPage.load(),shelfSelected.load()};}
void shelfUpdate(trophy_shelf::State state){
 state.clamp();if(state.page!=shelfPage){listReady=false;shelfGeneration=0;nextPoll=0;phase=1;}
 shelfPage=state.page;shelfSelected=state.selected;
}
bool shelfManifest(){
 std::ifstream f(folder/L"cabinet.tsv");std::string magic;unsigned v,pid,id,ep,col,gen,total,page,pages,count;
 if(!(f>>magic>>v>>pid>>id>>ep>>col>>gen>>total>>page>>pages>>count)||magic!="S16CABINET"||v!=2||pid!=GetCurrentProcessId()||id!=club||ep!=epoch||col!=unsigned(coachCollection)||page!=shelfPage||total>100000||count>trophy_shelf::capacity||!pages||page>=pages)return false;
 const auto expected=total>page*trophy_shelf::capacity?std::min(trophy_shelf::capacity,total-page*trophy_shelf::capacity):0u;
 if(count!=expected)return false;
 shelfTotal=total;shelfGeneration=gen;auto state=shelfState();state.clamp();shelfSelected=state.selected;listReady=true;titleCount=total;phase=3;error=0;return true;
}
void input(){
 pad={};if(padRead)for(DWORD i=0;i<4;++i)if(padRead(i,&pad)==ERROR_SUCCESS)break;
 static unsigned previousKeys=0;unsigned keys=0;
 if(foreground())keys=((GetAsyncKeyState(VK_F1)&0x8000)?1u:0u)|((GetAsyncKeyState(VK_F2)&0x8000)?2u:0u)|((pad.Gamepad.wButtons&XINPUT_GAMEPAD_Y)?1u:0u)|((pad.Gamepad.wButtons&XINPUT_GAMEPAD_X)?2u:0u);
 static unsigned previousViewButtons=0;unsigned viewButtons=0;
 if(foreground())viewButtons=(pad.Gamepad.bLeftTrigger>70?1u:0u)|(pad.Gamepad.bRightTrigger>70?2u:0u)|((pad.Gamepad.wButtons&XINPUT_GAMEPAD_LEFT_SHOULDER)?4u:0u)|((pad.Gamepad.wButtons&XINPUT_GAMEPAD_RIGHT_SHOULDER)?8u:0u);
 const unsigned viewEdges=viewButtons&~previousViewButtons;previousViewButtons=viewButtons;
 int viewIntent=-1;
 if(listMode||(!tour.detail&&pendingDetailSlot<0)){if(viewEdges&1)viewIntent=10;if(viewEdges&2)viewIntent=11;}if(listMode){if(viewEdges&4)viewIntent=25;if(viewEdges&8)viewIntent=26;}
 else if(!freeCamera&&pendingDetailSlot<0){if(viewEdges&4)viewIntent=7;if(viewEdges&8)viewIntent=0;}
 const auto edges=keys&~previousKeys;previousKeys=keys;if(edges&1)postCommand(listMode?14:0);if(edges&2)postCommand(listMode?11:1);
 if(listMode&&foreground()){
  static uint64_t repeat=0;const auto now=GetTickCount64();const int axis=pad.Gamepad.sThumbRY;
  if(abs(axis)>18000&&now>=repeat){repeat=now+240;postCommand(axis>0?15:14);}else if(abs(axis)<9000)repeat=0;
 }
 // A held navigation stick must not overwrite the one-shot RT/LT request.
 if(viewIntent>=0)postCommand(viewIntent);
 int value=command.exchange(-1);if(value<0)return;
 // View-switch commands are ignored during inspection; triggers belong to zoom.
 if(!listMode&&(tour.detail||pendingDetailSlot>=0)&&(value==10||value==11))return;
 if(value>=40000&&value<=50000){if(!listMode)detailScroll=unsigned(value-40000);return;}
 if(value>=12000&&value<12000+int(trophy_shelf::capacity)){if(!listMode||!listReady)return;auto state=shelfState();const auto index=unsigned(value-12000);if(index>=state.count())return;state.choose(index);shelfUpdate(state);value=24;}
 if(value==10){if(listMode)return;if(tour.selected()>=0){unsigned absolute=selectedPage*30+unsigned(tour.selected());shelfPage=absolute/trophy_shelf::capacity;shelfSelected=absolute%trophy_shelf::capacity;}listMode=true;listReady=false;shelfGeneration=0;active=false;nextPoll=0;phase=1;hide();freeCamera=false;tour.details(false,GetTickCount64());return;}
 if(value==11||value==24){
  if(value==11&&!listMode)return;
  const unsigned absolute=shelfPage*trophy_shelf::capacity+shelfSelected;
  pendingDetailSlot=value==24&&listReady&&shelfTotal?int(absolute%30):-1;
  selectedPage=pendingDetailSlot>=0?absolute/30:0;pageVisit=0;generation=0;listMode=false;active=false;residentScene=false;publicationPending=true;nextPoll=0;phase=1;enteredAt=GetTickCount64();freeCamera=false;camera.preset();return;
 }
 if(listMode){
  auto state=shelfState();
  if(value==25||value==26){const bool coach=value==26;if(coachCollection!=coach){coachCollection=coach;state={};shelfTotal=0;titleCount=0;listReady=false;shelfGeneration=0;nextPoll=0;phase=1;}}
  else if(value>=2000&&value<12000)state.page=unsigned(value-2000);
  else if(value>=1000&&value<1000+int(trophy_shelf::capacity))state.choose(unsigned(value-1000));
  else if(value==14)state.turn(1);else if(value==15)state.turn(-1);
  else if(value==20)state.step(-int(trophy_shelf::columns));else if(value==21)state.step(int(trophy_shelf::columns));
  else if(value==22)state.step(-1);else if(value==23)state.step(1);
  else if(value==9){coachCollection=!coachCollection;state={};shelfTotal=0;titleCount=0;listReady=false;shelfGeneration=0;nextPoll=0;phase=1;}
  shelfUpdate(state);return;
 }

 if(value==30){if(detailScroll)detailScroll--;return;}if(value==31){if(detailScroll<10000)detailScroll++;return;}if(value==32||value==33){camera.inspect.step(0,0,value==32?-4.f:4.f);return;}
 if(value==0||value==7){
  tour.automatic=false;
  const int direction=value==7?-1:1;
  const bool edge=direction>0?tour.index==int(tour.visits.size())-1:tour.index==0;
  if(!publicationPending&&pages>1&&edge&&!tour.visits.empty()){
   selectedPage=direction>0?(selectedPage+1)%pages:(selectedPage+pages-1)%pages;pageVisit=direction;pageDetail=tour.detail;publicationPending=true;nextPoll=0;phase=4;
  }else if(!publicationPending)tour.step(direction,GetTickCount64());freeCamera=false;
 }
 else if(value==1){tour.automatic=false;freeCamera=!freeCamera;if(freeCamera)tour.details(false,GetTickCount64());camera.mouseHeld=false;}
 else if(value==5||value==6){if(value==6){pendingDetailSlot=-1;pageDetail=false;}tour.details(value==5&&!tour.detail,GetTickCount64());freeCamera=false;}
 else if(value==8){
  if(foreground()&&!freeCamera){POINT p{};RECT r{};auto window=GetForegroundWindow();if(GetCursorPos(&p)&&ScreenToClient(window,&p)&&GetClientRect(window,&r)&&r.right>0&&r.bottom>0){
   panorama::Vec direction{sinf(camera.yaw)*cosf(camera.pitch),sinf(camera.pitch),-cosf(camera.yaw)*cosf(camera.pitch)};
   const int hit=gallery_tour::pick(tour.visits,{camera.eye,camera.eye+direction,freeCamera?68.f:camera.fov},float(r.right)/r.bottom,float(p.x)/r.right,float(p.y)/r.bottom);tour.select(hit,GetTickCount64());freeCamera=false;
  }}
 }else if(value==9){coachCollection=!coachCollection;tour.details(false,GetTickCount64());freeCamera=false;selectedPage=0;pageVisit=1;publicationPending=true;nextPoll=0;phase=4;}
 else if(value==2){
  const auto customFile=game/L"ModCarrerMode/data/trophy_room/custom"/std::to_wstring(club.load())/L"identity-wall.png";
  if(fs::is_regular_file(customFile)){custom=!custom;const auto section=std::to_wstring(club.load());WritePrivateProfileStringW(section.c_str(),L"style",custom?L"custom":L"default",config.c_str());publicationPending=true;nextPoll=0;phase=4;}
 }else if((value==3||value==4)&&pages>1){tour.automatic=false;selectedPage=value==3?(selectedPage+1)%pages:(selectedPage+pages-1)%pages;publicationPending=true;nextPoll=0;phase=4;}
}
void poll(){
 bool resolved=false;const auto id=visiblePage()?activeCareerClub(image,read,&resolved):0;const auto context=id?scope():Scope{};
 bool want=id>0&&resolved&&context.epoch;
 if(!want){sceneStartup.gate.reset();sceneStartupPermitted=false;if(requested.exchange(false)){active=false;residentScene=false;publicationPending=false;hide();freeCamera=false;phase=0;log("GALLERY_EXIT: native camera restored and props hidden");}return;}
 if(!requested.exchange(true)||club!=unsigned(id)||epoch!=context.epoch){
  hide();residentScene=false;publicationPending=false;pageVisit=0;pageDetail=false;coachCollection=false;club=id;epoch=context.epoch;generation=0;componentCount=0;loadedCount=0;titleCount=0;selectedPage=0;pages=1;phase=1;error=0;active=false;freeCamera=false;tour.reset({},GetTickCount64());camera.preset();enteredAt=GetTickCount64();listMode=true;listReady=false;shelfPage=0;shelfSelected=0;shelfTotal=0;shelfGeneration=0;pendingDetailSlot=-1;
  const auto file=game/L"ModCarrerMode/data/trophy_room/custom"/std::to_wstring(id)/L"identity-wall.png";
  custom=fs::is_regular_file(file);wchar_t style[16]{};GetPrivateProfileStringW(std::to_wstring(id).c_str(),L"style",custom?L"custom":L"default",style,16,config.c_str());custom=custom&&!wcscmp(style,L"custom");log("GALLERY_ENTER: session and career epoch validated");
 }
 input();if(listMode){sceneStartupPermitted=false;const auto now=GetTickCount64();if(now>=nextPoll){nextPoll=now+250;shelfManifest();}active=false;return;}
 if(!sceneStartup.allow(game,image,club.load(),read)){if(sceneStartupPermitted.exchange(false))hide();active=false;phase=1;return;}
 sceneStartupPermitted=true;loading(false);const auto now=GetTickCount64();if(now>=nextPoll){nextPoll=now+500;manifest();}
 unsigned created=0,loadedTotal=0;bool ready=!components.empty()&&generation!=0;
 for(auto&c:components){
  if(!c->attempted&&created<2){++created;c->failed=!create(*c);if(c->failed){error=2;phase=9;log("GALLERY_COMPONENT_FAILED");}}
  if(c->object&&!c->failed&&!c->loaded){c->loaded=loaded(*c);if(c->loaded)log(("GALLERY_COMPONENT_READY: "+c->key).c_str());}
  if(c->loaded)++loadedTotal;
  ready=ready&&c->loaded&&!c->failed;
 }
 selectedTrophy=tour.selected();detailStatus=tour.detail;loadedCount=loadedTotal;active=ready;for(auto&c:components)visibility(*c,(ready||(residentScene&&shell(*c)&&c->loaded))&&(c->key.rfind("detail_",0)!=0||(!freeCamera&&tour.detail&&c->detailSlot==tour.selected())));
 if(ready){residentScene=true;phase=publicationPending?4:3;error=0;loading(false);camera.apply(false);}else if(now-enteredAt>90000){phase=9;error=3;}
}
void*__fastcall frame(){
 camera.restore();if(sceneStartupPermitted&&!listMode&&(active||residentScene)&&visiblePage())camera.apply();auto result=((void*(__fastcall*)())previousFrame)();if(stopping)return result;
 __try{
  poll();const bool showing=visiblePage()&&!listMode;const unsigned test=effectsTestMode;
  gallery_scene_bridge::state(sceneStartupPermitted&&showing&&(active||residentScene)&&!error&&gallery_postfx::bridge(test),club.load(),generation.load());
  if(sceneStartupPermitted||((cleanLens.state>=0||cleanOptics.state>=0)&&!showing&&RoomStartup::loaderIdle(image,read))){
   cleanLens.update("trophy_room",showing&&test!=4,[](const char*s){return execute(s);});
   cleanOptics.update(showing&&cleanCamera&&gallery_postfx::optics(test),GetTickCount64(),[](const char*s){return execute(s);});
  }
  photoTick(visiblePage());
 }__except(EXCEPTION_EXECUTE_HANDLER){gallery_scene_bridge::end(false);gallery_scene_bridge::state(false,0,0);active=false;error=GetExceptionCode();phase=9;log("GALLERY_GUARD: scene disabled safely");}return result;
}
bool exchange(LONG from,LONG to){
 auto*p=(volatile LONG*)(image+0x3a19f80);DWORD old=0;if(!VirtualProtect((void*)p,4,PAGE_EXECUTE_READWRITE,&old))return false;
 const auto seen=InterlockedCompareExchange(p,to,from);DWORD ignore=0;VirtualProtect((void*)p,4,old,&ignore);FlushInstructionCache(GetCurrentProcess(),(void*)(image+0x3a19f7f),5);return seen==from;
}
bool compatible(uintptr_t target){
 if(target==image+0x44d8ce0)return trophy_chain::ready(trophy_chain::Owner::native,GetModuleHandleW(L"native_dressing_room.dll")!=nullptr,GetModuleHandleW(L"club_browser.dll")!=nullptr);
 unsigned char code[14]{};if(!read(target,code,14)||memcmp(code,"\xff\x25\0\0\0\0",6))return false;uintptr_t destination=0;memcpy(&destination,code+6,8);HMODULE module=nullptr;
 if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,(LPCWSTR)destination,&module))return false;
 wchar_t path[1024]{};GetModuleFileNameW(module,path,1024);const auto leaf=wcsrchr(path,L'\\');if(!leaf)return false;
 return trophy_chain::ready(trophy_chain::classify(leaf+1),GetModuleHandleW(L"native_dressing_room.dll")!=nullptr,GetModuleHandleW(L"club_browser.dll")!=nullptr);
}
bool install(){
 if(get<unsigned char>(image+0x3a19f7f)!=0xe8)return false;oldCall=get<LONG>(image+0x3a19f80);previousFrame=image+0x3a19f84+oldCall;if(!compatible(previousFrame))return false;
 if(!relay){for(uintptr_t step=0x10000;step<0x70000000&&!relay;step+=0x10000)relay=VirtualAlloc((void*)(image+step),4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);if(!relay)return false;
  unsigned char jump[14]={0xff,0x25,0,0,0,0};auto fn=(uintptr_t)&frame;memcpy(jump+6,&fn,8);memcpy(relay,jump,14);DWORD old=0;if(!VirtualProtect(relay,4096,PAGE_EXECUTE_READ,&old))return false;FlushInstructionCache(GetCurrentProcess(),relay,4096);
 }
 newCall=LONG(intptr_t(relay)-intptr_t(image+0x3a19f84));return exchange(oldCall,newCall);
}
void status(){
 gallery_scene_bridge::diagnostics(folder);
 {std::ofstream f(folder/L"lighting_status.json.new");f<<"{\"pid\":"<<GetCurrentProcessId()<<",\"room_intensity\":"<<roomLightIntensity<<",\"trophy_intensity\":"<<trophyLightIntensity<<",\"clean_camera\":"<<(cleanCamera?"true":"false")<<",\"effects_test\":"<<effectsTestMode<<",\"uploads\":"<<uploads<<"}\n";f.close();MoveFileExW((folder/L"lighting_status.json.new").c_str(),(folder/L"lighting_status.json").c_str(),MOVEFILE_REPLACE_EXISTING);}
 const auto temp=folder/L"request.json.new";std::ofstream f(temp);f<<"{\"pid\":"<<GetCurrentProcessId()<<",\"requested\":"<<(requested?"true":"false")<<",\"club\":"<<club<<",\"epoch\":"<<epoch<<",\"custom\":"<<(custom?"true":"false")<<",\"page\":"<<selectedPage<<",\"phase\":"<<phase<<",\"ready\":"<<((listMode?listReady.load():active.load())?"true":"false")<<",\"generation\":"<<generation<<",\"gallery_views\":5,\"presentation\":\""<<(listMode?"list":"3d")<<"\",\"shelf_page\":"<<shelfPage<<",\"shelf_selected\":"<<shelfSelected<<",\"collection\":\""<<(coachCollection?"coach":"club")<<"\",\"selected_trophy\":"<<selectedTrophy<<",\"detail\":"<<(detailStatus?"true":"false")<<",\"titles\":"<<titleCount<<",\"pages\":"<<pages<<",\"error\":"<<error<<",\"uploads\":"<<uploads<<",\"installed\":"<<(installed?"true":"false")<<",\"photo_installed\":"<<(photoInstalled?"true":"false")<<",\"components\":"<<componentCount<<",\"loaded_components\":"<<loadedCount<<"}\n";f.close();MoveFileExW(temp.c_str(),(folder/L"request.json").c_str(),MOVEFILE_REPLACE_EXISTING);
}
HANDLE assetHelper=nullptr;uint64_t nextHelper=0;
void ensureHelper(){
 if(!requested||GetTickCount64()<nextHelper)return;nextHelper=GetTickCount64()+15000;
 if(assetHelper){if(WaitForSingleObject(assetHelper,0)==WAIT_TIMEOUT)return;CloseHandle(assetHelper);assetHelper=nullptr;}
 unsigned gamePid=0,helperPid=0;{std::ifstream marker(game/L"ModCarrerMode/runtime/club_environment/room/runtime/native_asset_helper_r46.pid");marker>>gamePid>>helperPid;}
 auto python=game/L"Server16Python.exe";assetHelper=room_helper::existingWorker(GetCurrentProcessId(),gamePid,helperPid,python.c_str());if(assetHelper)return;
 if(!fs::is_regular_file(python))return;
 std::wstring command=L"\""+python.wstring()+L"\" --club-environment --game-root \""+game.wstring()+L"\" --pid "+std::to_wstring(GetCurrentProcessId());DWORD error=0;
 if(!room_helper::spawn(python.c_str(),command,game.c_str(),(folder/L"helper-startup.log").c_str(),assetHelper,error))log("GALLERY_ASSET_HELPER_START_FAILED");
}
DWORD WINAPI worker(void*){
 while(!stopping){
  if(!installed&&get<unsigned char>(image+0x3a19f7f)==0xe8){if(install()){installed=true;log("READY: independent native trophy gallery");}}
  if(installed&&!photoInstalled)photoInstalled=installPhoto();
  refreshLighting();ensureHelper();status();Sleep(400);
 }
 active=false;requested=false;if(assetHelper){CloseHandle(assetHelper);assetHelper=nullptr;}camera.restore();if(installed)exchange(newCall,oldCall);if(photoInstalled)photoExchange(photoAfter,photoBefore);status();return 0;
}
}
extern "C" __declspec(dllexport) unsigned WINAPI Fifa16ModGetApiVersion(){return 1;}
extern "C" __declspec(dllexport) unsigned WINAPI Fifa16TrophyRoomUiMode(){
 return listMode?0u:detailStatus?2u:freeCamera?3u:1u;
}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16TrophyRoomLoadingStatus(scene_loading::Status*out){
 scene_loading::Status s;s.club=club;s.visible=visiblePage();s.ready=listMode?listReady.load():sceneStartupPermitted&&active;s.total=sceneStartupPermitted?componentCount.load():0;s.loaded=sceneStartupPermitted?loadedCount.load():0;s.variant=(coachCollection?1:0)|(listMode?2:0);s.error=error;
 s.elapsedMs=enteredAt?GetTickCount64()-enteredAt:0;return write(reinterpret_cast<uintptr_t>(out),&s,sizeof s)?TRUE:FALSE;
}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16TrophyShelfStatus(trophy_shelf::Status*out){
 trophy_shelf::Status s;s.pid=GetCurrentProcessId();s.club=club;s.epoch=epoch;s.collection=coachCollection;
 s.generation=listMode?shelfGeneration.load():generation.load();s.total=listMode?shelfTotal.load():titleCount.load();s.page=listMode?shelfPage.load():selectedPage.load();
 s.pages=listMode?std::max(1u,(s.total+trophy_shelf::capacity-1)/trophy_shelf::capacity):pages.load();
 s.selected=listMode?shelfSelected.load():unsigned(std::max(0,selectedTrophy.load()));s.ready=listMode?listReady.load():active.load();s.list=listMode;s.detail=!listMode&&detailStatus;s.detailScroll=detailScroll;
 return write(reinterpret_cast<uintptr_t>(out),&s,sizeof s)?TRUE:FALSE;
}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16TrophyRoomCommand(const char*text){
 if(!requested||!visiblePage()||!text)return FALSE;
 if(!strcmp(text,"club"))postCommand(25);else if(!strcmp(text,"coach"))postCommand(26);
 else if(!strcmp(text,"detail_up"))postCommand(30);else if(!strcmp(text,"detail_down"))postCommand(31);else if(!strcmp(text,"zoom_in"))postCommand(32);else if(!strcmp(text,"zoom_out"))postCommand(33);
 else if(!strncmp(text,"detail_scroll_",14)){char*end=nullptr;long i=strtol(text+14,&end,10);if(!end||*end||i<0||i>10000)return FALSE;postCommand(40000+int(i));}
 else if(!strcmp(text,"list"))postCommand(10);else if(!strcmp(text,"3d"))postCommand(11);else if(!strcmp(text,"shelf_detail"))postCommand(24);
 else if(!strcmp(text,"shelf_next"))postCommand(14);else if(!strcmp(text,"shelf_prev"))postCommand(15);
 else if(!strcmp(text,"shelf_up"))postCommand(20);else if(!strcmp(text,"shelf_down"))postCommand(21);else if(!strcmp(text,"shelf_left"))postCommand(22);else if(!strcmp(text,"shelf_right"))postCommand(23);
 else if(!strncmp(text,"shelf_open_",11)){char*end=nullptr;long i=strtol(text+11,&end,10);if(!end||*end||i<0||i>=int(trophy_shelf::capacity))return FALSE;postCommand(12000+int(i));}
 else if(!strncmp(text,"shelf_page_",11)){char*end=nullptr;long i=strtol(text+11,&end,10);if(!end||*end||i<0||i>=10000)return FALSE;postCommand(2000+int(i));}
 else if(!strncmp(text,"shelf_select_",13)){char*end=nullptr;long i=strtol(text+13,&end,10);if(!end||*end||i<0||i>=int(trophy_shelf::capacity))return FALSE;postCommand(1000+int(i));}
 else if(!strcmp(text,"camera"))postCommand(0);else if(!strcmp(text,"free"))postCommand(1);else if(!strcmp(text,"style"))postCommand(2);else if(!strcmp(text,"page"))postCommand(3);else if(!strcmp(text,"page_prev"))postCommand(4);else if(!strcmp(text,"detail"))postCommand(5);else if(!strcmp(text,"close_detail"))postCommand(6);else if(!strcmp(text,"previous"))postCommand(7);else if(!strcmp(text,"pick"))postCommand(8);else if(!strcmp(text,"collection"))postCommand(9);else return FALSE;return TRUE;
}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char*){
 if(started.exchange(true))return TRUE;image=(uintptr_t)GetModuleHandleW(nullptr);
 if(get<uint16_t>(image)!=0x5a4d||get<uint32_t>(image+get<int32_t>(image+0x3c)+8)!=0x577de45c){started=false;return FALSE;}
 wchar_t exe[1024]{};GetModuleFileNameW(nullptr,exe,1024);game=fs::path(exe).parent_path();folder=game/L"ModCarrerMode/runtime/trophy_room";std::error_code folderError;fs::create_directories(folder,folderError);if(folderError){started=false;return FALSE;}config=game/L"ModCarrerMode/config/trophy_room.ini";
 auto module=LoadLibraryW(L"xinput1_4.dll");if(!module)module=LoadLibraryW(L"xinput1_3.dll");if(module)padRead=(PadRead)GetProcAddress(module,"XInputGetState");
 auto thread=CreateThread(nullptr,0,worker,nullptr,0,nullptr);if(thread)CloseHandle(thread);return thread!=nullptr;
}
extern "C" __declspec(dllexport) void WINAPI Fifa16ModStop(){stopping=true;}
BOOL WINAPI DllMain(HINSTANCE module,DWORD reason,void*){if(reason==DLL_PROCESS_ATTACH)DisableThreadLibraryCalls(module);if(reason==DLL_PROCESS_DETACH)stopping=true;return TRUE;}
