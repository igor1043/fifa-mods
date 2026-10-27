#pragma once
// Native FIFA scene work is confined to the verified engine frame callback.
// Present only submits immutable jobs and visibility intent; it calls no FIFA API.
#include <atomic>
#include <memory>
#include <sstream>
#include <iomanip>
#include "../../club_environment/room/native/motions.h"
#include "native_animation.h"
namespace clubscene {
constexpr int slots=96,opaqueSlots=64,maxTextures=96;
struct Assets {uint64_t sequence=0;int club=0,career=0,pages=0,player=0;bool single=false;std::string hash;std::shared_ptr<clubanim::Clip> animation;};
std::atomic<bool> singleView{false},rosterCamera{false};std::atomic<float> playerAngle{0},playerZoom{1},playerPan{0},playerHeight{180};
std::mutex jobsMutex;std::shared_ptr<const Assets> pending;
std::atomic<bool> requested{false},installed{false},stopping{false},active{false};
std::atomic<unsigned> phase{0},fault{0},draws{0},returns{0};
std::atomic<unsigned> sceneState{0},waiting{0},frames{0};
std::atomic<uint64_t> requestSequence{0},readySequence{0};
std::atomic<uintptr_t> drawObject{0};std::atomic<int> displayedClub{0};std::atomic<unsigned> createdObjects{0},residentObjects{0};
uintptr_t base=0,prior=0,object=0,vtable[29]{};void* relay=nullptr;LONG before=0,after=0;
std::atomic<DWORD>frameThread{0},drawThread{0};std::array<std::atomic<unsigned>,8>passCounts{};uint64_t loadingAt=0;bool registered=false,materials=false,failed=false;
int(*careerReader)()=nullptr;
std::shared_ptr<const Assets> loading;std::filesystem::path game,folder;
inline bool read(uintptr_t at,void* out,size_t n){if(at<0x10000)return false;__try{memcpy(out,(void*)at,n);return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
template<class T>T get(uintptr_t at){T t{};read(at,&t,sizeof t);return t;}
inline bool write(uintptr_t at,const void* in,size_t n){__try{memcpy((void*)at,in,n);return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
inline void log(const char* value){std::ofstream f(folder/L"engine.log",std::ios::app);f<<GetTickCount64()<<" "<<value<<"\n";}
// Keep a ready draw published throughout an unchanged frame. Clearing it at
// frame entry can omit only one pass of a concurrently submitted native mesh.
inline void hideDraw(){clubanim::setVisible(false);active=false;drawObject=0;displayedClub=0;}
inline void publishDraw(bool show){if(!show){hideDraw();return;}clubanim::setVisible(singleView&&requested);drawObject=object;displayedClub=loading?loading->club:0;active=true;}
inline bool page(){auto p=get<uintptr_t>(base+0x3809030);for(unsigned off:{232u,192u,136u,472u})p=get<uintptr_t>(p+off);char n[128]{};return read(p,n,127)&&clubs::isPage(n);}
inline bool validAssets(const Assets& a){return a.sequence&&a.club>0&&a.club<500000&&a.career>0&&a.pages>=1&&a.pages<=maxTextures&&a.hash.size()==64&&a.hash.find_first_not_of("0123456789abcdef")==std::string::npos;}
inline void intent(bool show,uint64_t sequence){requestSequence=sequence;requested=show;}
// The loaded frontend stadium also uses state 13. It has the same valid
// camera/projection as state 1; equality with 1 silently blocked every XI job.
// Keep the check narrow and validate the camera before invoking scene APIs.
inline bool sceneAvailable(){auto s=get<uintptr_t>(base+0x3517c10);auto state=get<unsigned>(s+0x3c);sceneState=state;if(state!=1&&state!=13)return false;float x=get<float>(s+0x88),y=get<float>(s+0x8c);return std::isfinite(x)&&std::isfinite(y)&&y>0&&x/y>=.5f&&x/y<=4;}
struct LuaValue{uintptr_t value=0;int type=0;};
inline LuaValue field(uintptr_t table,const char* key){unsigned char h[64]{};if(!read(table,h,64)||h[8]!=5||h[11]>14)return {};uintptr_t nodes=0;memcpy(&nodes,h+32,8);size_t length=strlen(key);if(length>120)return {};for(unsigned i=0;i<(1u<<h[11]);++i){unsigned char row[40]{};if(!read(nodes+i*40,row,40))return {};if(get<int>(nodes+i*40+24)!=4)continue;uintptr_t str=0;memcpy(&str,row+16,8);if(get<size_t>(str+16)!=length)continue;char text[128]{};if(!read(str+24,text,length)||memcmp(text,key,length))continue;LuaValue v;memcpy(&v.value,row,8);memcpy(&v.type,row+8,4);if(v.type==1)v.value&=0xffffffff;return v;}return {};}
inline LuaValue stateField(const char* key){auto lua=get<uintptr_t>(base+0x3613fd0);auto state=field(get<uintptr_t>(lua+0x78),"S16ClubXI");return state.type==5?field(state.value,key):LuaValue{};}
inline bool execute(const char* text){auto lua=get<uintptr_t>(base+0x3613fd0);if(!lua||get<int>(lua+0x80)!=5)return false;__try{((void(__fastcall*)(const char*,size_t,const char*))(base+0x4ac35e0))(text,strlen(text),"Server16ClubXI");return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
inline bool validObject(){return object&&get<uintptr_t>(object)==(uintptr_t)vtable&&get<uintptr_t>(get<uintptr_t>(object+0x30)+8)==object&&get<unsigned>(get<uintptr_t>(object+0x20)+0x38)==1;}
inline void visibility(bool visible){if(!validObject())return;float cs=1,sn=0;alignas(16)float m[16]={cs,0,-sn,0,0,1,0,0,sn,0,cs,0,0,0,0,1};((void(__fastcall*)(void*,int,const float*,bool))(base+0x4ad80b0))((void*)object,0,m,visible);alignas(16)float off[4]{};((void(__fastcall*)(void*,int,const float*))(base+0x43c9960))((void*)object,0,off);}
inline bool loaded(){if(!validObject())return false;auto impl=get<uintptr_t>(object+0x20);if(get<unsigned>(impl+0x18)!=1)return false;auto composite=get<uintptr_t>(get<uintptr_t>(impl+0x20));if(!composite)return false;if(!get<unsigned char>(composite+0x10))((int(__fastcall*)(void*))(base+0x4add100))((void*)composite);return ((bool(__fastcall*)(void*))(base+0x4ad7d80))((void*)object);}
inline void animateBeforeNativeDraw(){if(!singleView||!clubanim::enabled)return;auto device=get<uintptr_t>(base+0x36140b0),native=get<uintptr_t>(device+0x758);auto context=(ID3D11DeviceContext*)get<uintptr_t>(native+0x3520);if(!context){++clubanim::drawUnavailable;return;}clubanim::prepareNativeDraw(context,GetTickCount64());}
inline void __fastcall draw(void* self,int pass){++draws;if(stopping||!active||!requested||requestSequence!=readySequence||!page()||self!=(void*)drawObject.load())return;drawThread=GetCurrentThreadId();if(pass>=0&&pass<8)++passCounts[pass];__try{if(pass==1)animateBeforeNativeDraw();((void(__fastcall*)(void*,int))(base+0x43c8f20))(self,pass);++returns;}__except(EXCEPTION_EXECUTE_HANDLER){active=false;fault=GetExceptionCode();phase=9;}}
inline std::string objectName(const Assets& a){return "server16_native_club_xi_v5_"+std::to_string(a.sequence);}
inline bool create(const std::string& name){
 auto* allocator=((void*(__fastcall*)())(base+0x4abfba0))();if(!allocator)return false;auto alloc=get<uintptr_t>(get<uintptr_t>((uintptr_t)allocator)+0x10);if(!alloc)return false;
 auto* storage=((void*(__fastcall*)(void*,size_t,const char*,int))alloc)(allocator,0x38,"Server16ClubXI",1);if(!storage)return false;
 object=(uintptr_t)((void*(__fastcall*)(void*,void*,const char*,int,int,int))(base+0x43c8be0))(storage,allocator,name.c_str(),0,1,1);
 auto vt=get<uintptr_t>(object),ctx=get<uintptr_t>(object+0x30),impl=get<uintptr_t>(object+0x20);
 if(vt!=base+0x2210dc0||get<uintptr_t>(vt+24)!=base+0x43c8f30||get<uintptr_t>(vt+32)!=base+0x43c8f20||get<uintptr_t>(ctx+8)!=object||get<unsigned>(impl+0x38)!=1){object=0;return false;}
 if(!read(vt,vtable,sizeof vtable)){object=0;return false;}vtable[4]=(uintptr_t)&draw;
 if(InterlockedCompareExchangePointer((void*volatile*)object,vtable,(void*)vt)!=(void*)vt){object=0;return false;}
 visibility(false);((void(__fastcall*)(void*,const char*,int))(base+0x4ac5450))((void*)object,name.c_str(),0);++createdObjects;return true;
}
// Per-slot atlas page from the validated converter manifest.
std::array<int,slots> pendingPages{},loadingPages{};
inline void submit(Assets a,const std::array<int,slots>& pages){if(!validAssets(a))return;for(int i:pages)if(i<0||i>=a.pages)return;std::lock_guard<std::mutex> guard(jobsMutex);pendingPages=pages;pending=std::make_shared<const Assets>(std::move(a));}
inline std::string bindScript(const Assets& a,bool initial,bool addContext){
 std::string path="data/sceneassets/server16_club_xi/"+std::to_string(GetCurrentProcessId())+"/"+a.hash+"/";
 std::ostringstream s;s<<"S16ClubXI={ok=false,club="<<a.club<<",sequence="<<a.sequence<<"};local s=S16ClubXI;local ok,err=pcall(function() local gr=gRenderables;local o=gr:Find('"<<objectName(a)<<"',0);assert(o,'XI object unavailable');s.object=o;local lod=0;local root='"<<path<<"';";
 s<<"gr:AddAsset(o,lod,'shader','data/fifarna/shader.big');gr:AddAsset(o,lod,'normal',root..'flat_normal.rx3');gr:AddAsset(o,lod,'coeff',root..'neutral_coeff.rx3');gr:AddAsset(o,lod,'coverage',root..'white.rx3');local env=gSportsRNA:GetInt(gSportsRNA:GetTable('wvState'),'wvAttribEnvLighting');gr:AddAsset(o,lod,'charcmn','data/sceneassets/server16_club_xi/lighting/charcmn_'..env..'_neutral_v2.rx3');";
 for(int i=0;i<a.pages;++i)s<<"gr:AddAsset(o,lod,'atlas_"<<i<<"',root..'atlas_"<<i<<".rx3');";
 for(int i=1;i<=slots;++i){s<<"do local part='xi_part_"<<i<<"';gr:AddAsset(o,lod,part,root..'geometry.rx3');";
 s<<"gr:CreateMaterialFromAttribulator(o,lod,part,'prop_material','"<<(i<=opaqueSlots?"prop_plastic":"prop_alpha")<<"');";
 s<<"gr:SetSubMesh(o,lod,part,part);gr:SetTexture(o,lod,part,'textures','diffuseTexture','atlas_"<<loadingPages[i-1]<<"','xi_cm');gr:SetTexture(o,lod,part,'textures','normalMap','normal','xi_nm');gr:SetTexture(o,lod,part,'textures','coeffMap','coeff','xi_coeff');gr:SetTexture(o,lod,part,'textures','envDiffuseTexture','charcmn','envd_');gr:SetTexture(o,lod,part,'textures','envSpecTexture','charcmn','envs_');gr:SetTexture(o,lod,part,'textures','coverageMap','coverage','white_cm');end;";}
 s<<"gr:SetDBInt(o,'server16_club_xi_revision',5);gr:Reload(o,1);";if(addContext)s<<"ContextAddRenderable('gameplayprops',o,1,{}) ";s<<"end);s.ok=ok;s.error=tostring(err)";return s.str();
}
// Release resources through FIFA's verified unload virtual, only on its frame
// callback and after streaming has completed. Do not mutate bound asset lists.
inline void retire(){hideDraw();if(!object)return;visibility(false);if(validObject())((void(__fastcall*)(void*))(base+0x4ad7eb0))((void*)object);residentObjects=0;object=0;loading.reset();readySequence=0;phase=0;}

struct Camera {
 uintptr_t scene=0;unsigned char original[0x84]{},written[0x84]{};
 void restore(){if(scene&&scene==get<uintptr_t>(base+0x3517c10))for(auto r:std::array<std::array<unsigned,2>,4>{{{{0,64}},{{0x48,8}},{{0x70,1}},{{0x7c,8}}}}){unsigned char current[64]{};if(read(scene+0x40+r[0],current,r[1])&&!memcmp(current,written+r[0],r[1]))write(scene+0x40+r[0],original+r[0],r[1]);}scene=0;}
 void apply(){if(!sceneAvailable())return;auto s=get<uintptr_t>(base+0x3517c10);float x=get<float>(s+0x88),y=get<float>(s+0x8c);
  float zoom=playerZoom.load(),angle=playerAngle.load(),height=playerHeight.load(),side=-114/zoom,range=height*1.78f/zoom;float focus=height*(.52f+playerPan.load());float sa=std::sin(angle),ca=std::cos(angle);panorama::Pose pose=(rosterCamera||singleView)?panorama::Pose{{ca*side+sa*range,focus+height*.055f,-sa*side+ca*range},{ca*side,focus,-sa*side},40}:panorama::Pose{{0,145,430},{0,96,10},44};float m[16];if(!panorama::matrix(pose,m))return;if(scene!=s){restore();if(!read(s+0x40,original,sizeof original))return;scene=s;}float Y=std::tan(pose.fov*.00872664626f),X=Y*(x/y),zero=0;unsigned char off=0;write(s+0x40,m,sizeof m);write(s+0x88,&X,4);write(s+0x8c,&Y,4);write(s+0xb0,&off,1);write(s+0xbc,&zero,4);write(s+0xc0,&zero,4);read(s+0x40,written,sizeof written);
 }
}camera;
inline void fail(unsigned code){hideDraw();readySequence=0;phase=9;fault=code;failed=true;if(object)visibility(false);log("NATIVE_XI_DISABLED");}
inline void tick(){
 ++frames;waiting=0;bool onPage=!stopping&&page(),show=requested&&onPage;if(!onPage){hideDraw();waiting=1;if(object)visibility(false);return;}
 if(!frameThread)frameThread=GetCurrentThreadId();if(frameThread!=GetCurrentThreadId()){fail(20);return;}
 if(rosterCamera&&sceneAvailable())camera.apply();
 if(failed){hideDraw();return;}
 if(object&&!validObject()){fail(5);return;}
 auto lua=get<uintptr_t>(base+0x3613fd0);if(!lua||get<int>(lua+0x80)!=5){hideDraw();waiting=2;visibility(false);return;}if(!sceneAvailable()){hideDraw();waiting=3;visibility(false);return;}
 if(loading&&phase==1){if(loaded()){readySequence=loading->sequence;phase=2;log("NATIVE_XI_ASSETS_READY");}else if(GetTickCount64()-loadingAt>45000){fail(4);return;}}
 std::shared_ptr<const Assets> next;{std::unique_lock<std::mutex> lock(jobsMutex,std::try_to_lock);if(lock.owns_lock()&&phase!=1&&pending&&pending->sequence==requestSequence&&(!loading||pending->sequence!=loading->sequence)){next=pending;loadingPages=pendingPages;}}
 if(next&&(!careerReader||careerReader()!=next->career)){hideDraw();visibility(false);waiting=4;return;}
 if(next&&loading&&next->hash==loading->hash&&readySequence==loading->sequence){singleView=next->single;clubanim::activate(next->animation);loading=next;readySequence=next->sequence;next.reset();}
 if(next){if(object)retire();readySequence=0;phase=1;loading=next;loadingAt=GetTickCount64();singleView=next->single;if(!next->single){playerAngle=0;playerZoom=1;}clubanim::activate(next->animation);
  if(!create(objectName(*loading))){fail(1);return;}residentObjects=1;
  auto code=bindScript(*loading,true,true);if(!execute(code.c_str())){fail(2);return;}auto ok=stateField("ok"),obj=stateField("object");if(ok.type!=1||!ok.value||obj.type!=2||obj.value!=object){auto err=stateField("error");if(err.type==4){char text[512]{};auto n=get<size_t>(err.value+16);if(n<sizeof text&&read(err.value+24,text,n))log(text);}fail(3);return;}materials=registered=true;
  log("NATIVE_XI_REQUESTED");
 }
 if(!loading||loading->sequence!=requestSequence){hideDraw();waiting=5;return;}
 if(!careerReader||careerReader()!=loading->career){hideDraw();visibility(false);return;}
 if(readySequence!=loading->sequence&&loaded()){readySequence=loading->sequence;phase=2;log("NATIVE_XI_ASSETS_READY");}
 if(readySequence!=loading->sequence){hideDraw();waiting=6;if(GetTickCount64()-loadingAt>45000)fail(4);return;}
 publishDraw(show);visibility(show);if(show){if(!rosterCamera)camera.apply();phase=3;}else phase=2;
}
inline void guardedTick(){__try{tick();}__except(EXCEPTION_EXECUTE_HANDLER){active=false;readySequence=0;phase=9;fault=GetExceptionCode();failed=true;}}
inline void guardedRestore(){__try{camera.restore();}__except(EXCEPTION_EXECUTE_HANDLER){active=false;fault=GetExceptionCode();}}
inline void* __fastcall frame(){if(stopping||!page()||(!rosterCamera&&!requested))guardedRestore();auto result=((void*(__fastcall*)())prior)();if(stopping)return result;try{guardedTick();}catch(...){active=false;readySequence=0;phase=9;fault=21;failed=true;}return result;}
inline bool signatures(){
 const std::pair<uintptr_t,const char*> tests[]={{0x4ad80b0,"\x4c\x8b\x51\x20\x41\x8b\x00\x4c"},{0x4ac35e0,"\x48\x89\x5c\x24\x08\x48\x89\x74"},{0x4abfba0,"\x48\x8b\x05\xe9\x44\xb5\xfe\xc3"},{0x43c8be0,"\x48\x89\x5c\x24\x08\x48\x89\x74"},{0x4ac5450,"\x53\x41\x57\x48\x83\xec\x48\x0f"},{0x4ad7eb0,"\x48\x89\x5c\x24\x08\x57\x48\x83"},{0x4ad7d80,"\x48\x8b\x49\x20\xeb\x0a\xcc\xcc"},{0x4add100,"\x55\x53\x48\x8d\xac\x24\xd8\xfd"},{0x43c9960,"\x48\x8b\x41\x30\x41\x0f\x28\x00"},{0x43c8f20,"\x48\x8b\x01\x45\x31\xc0\xff\x60"}};
 for(auto t:tests){unsigned char b[8]{};if(!read(base+t.first,b,8)||memcmp(b,t.second,8))return false;}return true;
}
inline bool exchange(LONG from,LONG to){auto p=(volatile LONG*)(base+0x3a19f80);DWORD old;if(!VirtualProtect((void*)p,4,PAGE_EXECUTE_READWRITE,&old))return false;auto seen=InterlockedCompareExchange(p,to,from);DWORD ignored;VirtualProtect((void*)p,4,old,&ignored);FlushInstructionCache(GetCurrentProcess(),(void*)(base+0x3a19f7f),5);return seen==from;}
inline bool install(){
 if(get<unsigned char>(base+0x3a19f7f)!=0xe8||!signatures())return false;before=get<LONG>(base+0x3a19f80);auto target=base+0x3a19f84+before;
 unsigned char jump[14]{};if(!read(target,jump,14)||memcmp(jump,"\xff\x25\0\0\0\0",6))return false;uintptr_t address=0;memcpy(&address,jump+6,8);HMODULE owner=nullptr;if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,(LPCWSTR)address,&owner)||owner!=GetModuleHandleW(L"native_dressing_room.dll"))return false;
 if(!relay){for(uintptr_t n=0x10000;n<0x70000000&&!relay;n+=0x10000)relay=VirtualAlloc((void*)(base+n),4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);if(!relay)return false;unsigned char j[14]={0xff,0x25,0,0,0,0};auto fn=(uintptr_t)&frame;memcpy(j+6,&fn,8);memcpy(relay,j,14);DWORD old;if(!VirtualProtect(relay,4096,PAGE_EXECUTE_READ,&old))return false;FlushInstructionCache(GetCurrentProcess(),relay,4096);}
 prior=target;after=LONG(intptr_t(relay)-intptr_t(base+0x3a19f84));return exchange(before,after);
}
inline DWORD WINAPI worker(void*){auto began=GetTickCount64();while(!stopping){if(!installed){if(install()){installed=true;log("ENGINE_FRAME_CHAIN_READY");}else if(GetTickCount64()-began>120000){fault=10;phase=9;log("ENGINE_SIGNATURE_OR_ROOM_CHAIN_UNAVAILABLE");return 0;}}
  auto animation=std::atomic_load(&clubanim::activeClip);
  std::ofstream f(folder/L"native_status.new");f<<"{\"pid\":"<<GetCurrentProcessId()<<",\"installed\":"<<(installed?"true":"false")<<",\"active\":"<<(active?"true":"false")<<",\"phase\":"<<phase<<",\"error\":"<<fault<<",\"scene_state\":"<<sceneState<<",\"waiting\":"<<waiting<<",\"frames\":"<<frames<<",\"club\":"<<displayedClub<<",\"created_objects\":"<<createdObjects<<",\"resident_objects\":"<<residentObjects<<",\"sequence\":"<<readySequence<<",\"native_draw_callbacks\":"<<draws<<",\"native_draw_returns\":"<<returns<<",\"player\":"<<(animation?animation->player:0)<<",\"animated_buffers\":"<<(animation?animation->captured.load():0)<<",\"animation_updates\":"<<(animation?animation->updates.load():0)<<",\"vb_creates\":"<<0<<",\"vb_candidates\":"<<0<<",\"vb_probes\":"<<0<<",\"frame_thread\":"<<frameThread.load()<<",\"draw_thread\":"<<drawThread.load()<<",\"pass0\":"<<passCounts[0]<<",\"pass1\":"<<passCounts[1]<<",\"pass2\":"<<passCounts[2]<<",\"pass3\":"<<passCounts[3]<<",\"packed_constant_restores\":"<<clubgfx::packedConstantRestores.load()<<",\"ps_constant_first\":"<<clubgfx::lastConstantFirst.load()<<",\"ps_constant_count\":"<<clubgfx::lastConstantCount.load()<<",\"animation_backend\":\"dynamic_discard_persistent_binding\""<<",\"animation_private_uploads\":"<<clubanim::drawUploads.load()<<",\"animation_context_unavailable\":"<<clubanim::drawUnavailable.load()<<",\"animation_draw_matches\":"<<clubanim::drawMatches.load()<<",\"animation_dispatch_rearms\":"<<clubanim::drawRearms.load()<<",\"animation_rejected_meshes\":"<<clubanim::drawRejected.load()<<",\"stadium_reloads\":0,\"renderer\":\"FIFA native GameplayProp\"}\n";f.close();MoveFileExW((folder/L"native_status.new").c_str(),(folder/L"native_status.json").c_str(),MOVEFILE_REPLACE_EXISTING);Sleep(500);
 }return 0;}
inline void start(const std::filesystem::path& root,uintptr_t image,int(*context)()){game=root;base=image;careerReader=context;folder=root/L"ModCarrerMode/runtime/club_browser"/std::to_wstring(GetCurrentProcessId());std::error_code e;std::filesystem::create_directories(folder,e);auto t=CreateThread(nullptr,0,worker,nullptr,0,nullptr);if(t)CloseHandle(t);else fault=11;}
inline void stop(){requested=false;stopping=true;}
}
