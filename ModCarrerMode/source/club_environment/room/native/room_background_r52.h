// Refresh the existing native background provider after a separate career view.
// The stadium mod still decides between its transparent image and fallback.
// No stadium choice, reload revision, environment light or save field is edited.
uintptr_t roomPhotoPrevious=0,roomPhotoView=0;void*roomPhotoRelay=nullptr;
LONG64 roomPhotoBefore=0,roomPhotoAfter=0;bool roomPhotoInstalled=false,roomWasVisible=false,roomReturnPending=false;
unsigned roomReturnFrames=0,roomReturnRefreshes=0;
bool roomEntryPending=false;unsigned roomEntryFrames=0;
bool roomHubPage(){
 auto p=get<uintptr_t>(image+0x3809030);for(unsigned o:{232u,192u,136u,472u})p=get<uintptr_t>(p+o);
 char name[128]{};if(!read(p,name,127))return false;for(auto&c:name)if(c>='A'&&c<='Z')c+=('a'-'A');
 const auto leaf=strrchr(name,'/');return leaf&&!strcmp(leaf,"/fluxhub");
}
void* __fastcall roomPhotoHook(void*self){
 auto result=((void*(__fastcall*)(void*))roomPhotoPrevious)(self);
 const auto p=reinterpret_cast<uintptr_t>(self),vt=get<uintptr_t>(p);
 if(get<uintptr_t>(vt+0x38)==image+0x408d1d0&&get<uintptr_t>(p+8))roomPhotoView=p;
 // The room owns its transparent cover independently of the stadium setting.
 // This factory is already running on the native UI owner thread.
 if(result&&page())((void(__fastcall*)(void*,const char*,const char*))(image+0x4c174d0))(result,"Param","server16_frontend_clear");
 return result;
}
bool roomPhotoExchange(LONG64 from,LONG64 to){
 auto*p=reinterpret_cast<volatile LONG64*>(image+0x408d208);DWORD old=0;
 if(!VirtualProtect((void*)p,8,PAGE_EXECUTE_READWRITE,&old))return false;
 auto seen=InterlockedCompareExchange64(p,to,from);DWORD ignored=0;VirtualProtect((void*)p,8,old,&ignored);FlushInstructionCache(GetCurrentProcess(),(void*)(image+0x408d206),10);return seen==from;
}
bool installRoomPhoto(){
 unsigned char call[5]{};if(!read(image+0x408d206,call,5)||call[0]!=0xe8||call[1]!=0xd5)return false;
 LONG delta=0;memcpy(&delta,call+1,4);const auto target=uintptr_t(intptr_t(image+0x408d20b)+delta);uintptr_t destination=target;
 if(destination!=image+0x40893e0){unsigned char jump[14]{};if(!read(target,jump,14)||jump[0]!=0xff||jump[1]!=0x25||get<unsigned>(target+2))return false;memcpy(&destination,jump+6,8);
  HMODULE owner=nullptr;if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,(LPCWSTR)destination,&owner))return false;
  wchar_t path[1024]{};GetModuleFileNameW(owner,path,1024);auto leaf=wcsrchr(path,L'\\');if(!leaf||wcsncmp(leaf+1,L"frontend_stadium",16))return false;
 }
 if(!roomPhotoRelay){for(uintptr_t step=0x10000;step<0x70000000&&!roomPhotoRelay;step+=0x10000)roomPhotoRelay=VirtualAlloc((void*)(image+step),4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);if(!roomPhotoRelay)return false;
  unsigned char jump[14]={0xff,0x25,0,0,0,0};auto fn=(uintptr_t)&roomPhotoHook;memcpy(jump+6,&fn,8);memcpy((char*)roomPhotoRelay+0xe0,jump,14);DWORD old=0;if(!VirtualProtect(roomPhotoRelay,4096,PAGE_EXECUTE_READ,&old))return false;FlushInstructionCache(GetCurrentProcess(),roomPhotoRelay,4096);
 }
 const auto next=intptr_t(roomPhotoRelay)+0xe0-intptr_t(image+0x408d20b);if(next<INT32_MIN||next>INT32_MAX||(next&255)!=0xd5)return false;
 roomPhotoBefore=get<LONG64>(image+0x408d208);roomPhotoAfter=(roomPhotoBefore&~0xffffffLL)|(static_cast<uint32_t>(next)>>8);roomPhotoPrevious=target;
 roomPhotoInstalled=roomPhotoExchange(roomPhotoBefore,roomPhotoAfter);return roomPhotoInstalled;
}
void roomReturnTick(bool visible){
 if(visible){
  if(!roomWasVisible){roomEntryPending=true;roomEntryFrames=0;}
  roomWasVisible=true;roomReturnPending=false;roomReturnFrames=0;
  if(!roomEntryPending||++roomEntryFrames<3)return;
  auto self=roomPhotoView,vt=get<uintptr_t>(self);
  if(!self||get<uintptr_t>(vt+0x38)!=image+0x408d1d0||!get<uintptr_t>(self+8))return;
  using Queue=BOOL(WINAPI*)(void*,void*);const auto host=GetModuleHandleW(L"dinput8.dll");
  const auto queue=reinterpret_cast<Queue>(host?GetProcAddress(host,"Fifa16CareerQueueBackgroundRefresh"):nullptr);
  if(queue&&queue(reinterpret_cast<void*>(self),reinterpret_cast<void*>(vt))){roomEntryPending=false;log("ROOM_ENTRY_BACKGROUND_REFRESH_QUEUED");}
  return;
 }
 if(roomWasVisible){roomWasVisible=false;roomReturnPending=true;roomReturnFrames=0;log("ROOM_EXIT: camera restored, indoor draw stopped, native background refresh queued");}
 if(!roomReturnPending||!roomHubPage())return;if(++roomReturnFrames<3)return;
 auto self=roomPhotoView,vt=get<uintptr_t>(self);
 if(!self||get<uintptr_t>(vt+0x38)!=image+0x408d1d0||!get<uintptr_t>(self+8))return;
 using Queue=BOOL(WINAPI*)(void*,void*);
 const auto host=GetModuleHandleW(L"dinput8.dll");
 const auto queue=reinterpret_cast<Queue>(host?GetProcAddress(host,"Fifa16CareerQueueBackgroundRefresh"):nullptr);
 if(!queue||!queue(reinterpret_cast<void*>(self),reinterpret_cast<void*>(vt)))return;
 roomReturnPending=false;
 ++roomReturnRefreshes;log("ROOM_RETURN_NATIVE_BACKGROUND_REFRESH: existing stadium/fallback policy reapplied");
}
