// Additional, isolated native GameplayProp objects. No game objects are reused
// by index and no native game asset is modified or distributed by this module.
struct NativeRoomComponent {
 std::string key,type,model,submesh,texture,textureName;
 int medicalPage=-1,medicalPages=0,medicalBank=0;
 bool alpha=false,loaded=false,attempted=false,failed=false;uintptr_t object=0;
 std::vector<std::array<float,16>> matrices;
 std::array<float,4> overlay{};
};
std::vector<std::unique_ptr<NativeRoomComponent>> components,retiredComponents;
NativeRoomComponent loadingSlate,errorSlate;
room_cinema::Tour roomTour;unsigned roomTourVersion=0;uint64_t roomTourFingerprint=0;
uintptr_t componentVtable[29]{};
void __fastcall componentDraw(void*self,int pass){
 const bool slate=self==(void*)loadingSlate.object||self==(void*)errorSlate.object;
 if(stopping||!page()||(slate?!roomLoading.load():!active.load()||!ready.load()))return;
 __try {if(indoorEnabled&&pass==1)nativeIndoorDraw(self);else ((void(__fastcall*)(void*,int))(image+0x43c8f20))(self,pass);}
 __except(EXCEPTION_EXECUTE_HANDLER){indoorEnabled=false;++indoorFailures;log("INDOOR_LIGHTING_DISABLED_FALLBACK_NATIVE");}
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
 if(c.medicalPages>0)visible=visible&&c.medicalPage==static_cast<int>(((GetTickCount64()/12000)*2+c.medicalBank)%c.medicalPages);
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
 std::ifstream f(folder/L"runtime/room_tour_r46.txt");std::string magic;unsigned ver=0,pid=0,id=0,stamp=0,n=0,boxes=0,paths=0,details=0,shirts=0,nav=0,extra=0;
 if(!(f>>magic>>ver>>pid>>id>>stamp>>n>>boxes>>paths>>details>>shirts>>nav>>extra)||magic!="S16TOUR"||ver!=5||pid!=GetCurrentProcessId()||id!=club||stamp!=generation||n>2||boxes>1024||paths!=8||details!=1||shirts>35||nav>32||extra>64)return false;
 room_cinema::Tour tour;
 auto vec=[&f](panorama::Vec&v){return bool(f>>v.x>>v.y>>v.z)&&std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z)&&std::abs(v.x)<2000&&std::abs(v.y)<500&&std::abs(v.z)<3000;};
 for(unsigned i=0;i<n;++i){room_cinema::Focus q;if(!(f>>q.number)||(q.number!=9&&q.number!=10)||!vec(q.eye)||!vec(q.target))return false;tour.focus.push_back(q);}
 for(unsigned i=0;i<boxes;++i){room_cinema::Box b;if(!vec(b.lo)||!vec(b.hi)||b.lo.x>b.hi.x||b.lo.y>b.hi.y||b.lo.z>b.hi.z)return false;tour.obstacles.push_back(b);}
 for(unsigned i=0;i<paths+details;++i){panorama::Pose p;if(!vec(p.eye)||!vec(p.target)||!(f>>p.fov)||!std::isfinite(p.fov)||p.fov<40||p.fov>80)return false;(i<paths?tour.path:tour.details).push_back(p);}
 for(unsigned i=0;i<shirts;++i){room_cinema::Focus q;if(!(f>>q.number)||q.number>99||!vec(q.eye)||!vec(q.target))return false;tour.shirts.push_back(q);}
 for(unsigned i=0;i<nav+extra;++i){panorama::Pose p;if(!vec(p.eye)||!vec(p.target)||!(f>>p.fov)||!std::isfinite(p.fov)||p.fov<40||p.fov>80)return false;(i<nav?tour.nav:tour.extra).push_back(p);}
 room_cinema::compile(tour);std::ifstream source(folder/L"runtime/room_tour_r46.txt");std::string header,body;std::getline(source,header);body.assign(std::istreambuf_iterator<char>(source),std::istreambuf_iterator<char>());uint64_t fingerprint=1469598103934665603ULL^club;for(unsigned char c:body){fingerprint^=c;fingerprint*=1099511628211ULL;}
 if(!roomTourVersion||fingerprint!=roomTourFingerprint){roomTour=std::move(tour);roomTourFingerprint=fingerprint;++roomTourVersion;}log("CAMERA_TOUR_LOADED: mesh obstacle bounds and save jersey 9/10");return true;
}
bool loadComponents(){
 std::ifstream f(folder/L"runtime/native_components_v2.txt");std::string magic;unsigned version=0,pid=0,club=0,generation=0,count=0;
 if(!(f>>magic>>version>>pid>>club>>generation>>count)||magic!="S16NATIVE"||(version!=2&&version!=3)||pid!=GetCurrentProcessId()||club!=validCareerClub||count==0)return false;
 if(count>256){log("NATIVE_COMPONENT_GROUP_LIMIT_EXCEEDED: max=256");return false;}
 if(generation==componentGeneration&&club==componentClub)return true;
 std::vector<std::unique_ptr<NativeRoomComponent>> prepared;
 for(unsigned i=0;i<count;++i){
  auto c=std::make_unique<NativeRoomComponent>();unsigned alpha=0,instances=0;
  if(!(f>>std::quoted(c->key)>>std::quoted(c->model)>>std::quoted(c->submesh)>>std::quoted(c->texture)>>std::quoted(c->textureName)>>alpha>>instances)||instances<1||instances>64)return false;
  if(c->model.rfind("data/sceneassets/",0)!=0||c->texture.rfind("data/",0)!=0||c->key.size()>64)return false;
  if(version==3&&(!(f>>c->medicalPage>>c->medicalPages>>c->medicalBank)||c->medicalPages<0||c->medicalPages>6||c->medicalPage< -1||c->medicalPage>=std::max(1,c->medicalPages)||c->medicalBank<0||c->medicalBank>1))return false;
  for(float&v:c->overlay)if(!(f>>v)||!std::isfinite(v)||v<0||v>1)return false;
  c->alpha=alpha!=0;c->matrices.resize(instances);
  for(auto&m:c->matrices)for(float&v:m)if(!(f>>v)||!std::isfinite(v)||std::abs(v)>1000000.f)return false;
  c->type="server16_native_room_r60_"+std::to_string(generation)+"_"+std::to_string(i);prepared.push_back(std::move(c));
 }
 hideComponents();
 for(auto&next:prepared)for(auto&old:components){
  if(old&&old->key==next->key&&old->model==next->model&&old->submesh==next->submesh&&old->texture==next->texture&&old->textureName==next->textureName&&old->alpha==next->alpha&&!old->failed){
   old->matrices=std::move(next->matrices);old->overlay=next->overlay;old->medicalPage=next->medicalPage;old->medicalPages=next->medicalPages;old->medicalBank=next->medicalBank;next=std::move(old);break;
  }
 }
 for(auto&c:components)if(c)retiredComponents.push_back(std::move(c));components=std::move(prepared);componentGeneration=generation;componentClub=club;
 loadTour(generation,club);
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
 script+="gr:AddAsset(o,lod,'shader','data/fifarna/shader.big');gr:AddAsset(o,lod,part,"+model+");gr:AddAsset(o,lod,'color',"+texture+");gr:AddAsset(o,lod,'aux','data/sceneassets/prop/prop_102_textures.rx3');";
 script+="local state=gSportsRNA:GetTable('wvState');local env=gSportsRNA:GetInt(state,'wvAttribEnvLighting');gr:AddAsset(o,lod,'charcmn','data/sceneassets/charactercmn/charactercmn_'..env..'.rx3');";
 script+="gr:AddAsset(o,lod,'coverage','data/sceneassets/server16_dressing_room_20261022/room_white_r49.rx3');";
 script+="gr:CreateMaterialFromAttribulator(o,lod,part,'prop_material',"+luaString(c.alpha?"prop_alpha":"prop_plastic")+");gr:SetSubMesh(o,lod,part,"+luaString(c.submesh)+");";
 script+="gr:SetTexture(o,lod,part,'textures','diffuseTexture','color',"+luaString(c.textureName)+");gr:SetTexture(o,lod,part,'textures','normalMap','aux','_nm');gr:SetTexture(o,lod,part,'textures','coeffMap','aux','_coeff');";
 script+="gr:SetTexture(o,lod,part,'textures','envDiffuseTexture','charcmn','envd_');gr:SetTexture(o,lod,part,'textures','envSpecTexture','charcmn','envs_');gr:SetTexture(o,lod,part,'textures','coverageMap','coverage','white_cm');gr:SetDBInt(o,'server16_room_revision',1);gr:Reload(o,1);ContextAddRenderable('gameplayprops',o,1,{}) end);if not ok then S16RoomComponentError=tostring(err) end end";
 if(!execute(script.c_str()))return false;
 ((void(__fastcall*)(void*,bool))(image+0x4ad7e50))((void*)c.object,true);log(("NATIVE_COMPONENT_REQUEST: "+c.key+" model="+c.model+" texture="+c.texture).c_str());return true;
}
void pollComponents(bool requested){
 if(!validCareerClub){hideComponents();return;}
 auto now=GetTickCount64();if(now>=componentNextCheck){componentNextCheck=now+1000;loadComponents();}
 if(componentClub!=validCareerClub){hideComponents();return;}
 unsigned created=0;const auto prepareBegan=GetTickCount64();
 for(auto&c:components){
  if(!c->attempted&&created<8&&(created==0||GetTickCount64()-prepareBegan<6)){++created;if(!createComponent(*c)){c->failed=true;log(("NATIVE_COMPONENT_FAILED_NO_RETRY: "+c->key).c_str());}}
  if(c->object&&!c->failed&&!c->loaded&&componentReady(c->object)){c->loaded=true;log(("NATIVE_COMPONENT_READY: "+c->key).c_str());}
  componentVisibility(*c,false);
 }
 (void)requested;
}
bool roomComponentsReady(){
 if(componentClub!=validCareerClub||components.empty())return false;
 for(auto&c:components)if(!c->loaded||c->failed)return false;
 return true;
}
bool roomComponentsFailed(){for(auto&c:components)if(c->failed)return true;return false;}
void showComponents(bool visible){for(auto&c:components)componentVisibility(*c,visible);}
void pollSlate(bool show,bool error){
 for(int i=0;i<2;++i){auto&c=i?errorSlate:loadingSlate;
  if(!c.attempted){c.key=i?"loading_error":"loading_slate";c.type=i?"server16_room_error_r60":"server16_room_loading_r60";c.model="data/sceneassets/server16_dressing_room_20261022/loading_slate_r56.rx3";c.submesh="room_part_1";c.texture=i?"data/sceneassets/server16_dressing_room_20261022/loading_error_r56.rx3":"data/sceneassets/server16_dressing_room_20261022/loading_slate_texture_r56.rx3";c.textureName="slate_cm";c.matrices.push_back({1,0,0,0,0,1,0,0,0,0,1,0,100000,0,0,1});if(!createComponent(c))c.failed=true;}
  if(c.object&&!c.failed&&!c.loaded&&componentReady(c.object))c.loaded=true;
  componentVisibility(c,show&&(i?error:!error));
 }
}
