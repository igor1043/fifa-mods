// Borrow FIFA's existing background provider only while this gallery is open.
#include "photo_refresh.h"
uintptr_t photoPrevious=0,photoView=0;void*photoRelay=nullptr;
LONG64 photoBefore=0,photoAfter=0;bool photoInstalled=false,photoWasVisible=false,photoReturn=false;
gallery_background::Refresh photoRefresh;
void* __fastcall photoHook(void*self){
 auto result=((void*(__fastcall*)(void*))photoPrevious)(self);const auto p=(uintptr_t)self,vt=get<uintptr_t>(p);
 if(get<uintptr_t>(vt+0x38)==image+0x408d1d0&&get<uintptr_t>(p+8))photoView=p;
 if(result&&visiblePage()){
  const bool clear=!listMode&&sceneStartupPermitted&&active;
  ((void(__fastcall*)(void*,const char*,const char*))(image+0x4c174d0))(result,"Param",clear?"server16_frontend_clear":"BOOTFLOW");
  photoRefresh.observed(clear);
 }
 return result;
}
bool photoExchange(LONG64 from,LONG64 to){
 auto*p=(volatile LONG64*)(image+0x408d208);DWORD old=0;if(!VirtualProtect((void*)p,8,PAGE_EXECUTE_READWRITE,&old))return false;
 const auto seen=InterlockedCompareExchange64(p,to,from);DWORD ignored=0;VirtualProtect((void*)p,8,old,&ignored);FlushInstructionCache(GetCurrentProcess(),(void*)(image+0x408d206),10);return seen==from;
}
bool installPhoto(){
 unsigned char call[5]{};if(!read(image+0x408d206,call,5)||call[0]!=0xe8||call[1]!=0xd5)return false;
 LONG delta=0;memcpy(&delta,call+1,4);const auto target=uintptr_t(intptr_t(image+0x408d20b)+delta);uintptr_t destination=target;unsigned char jump[14]{};HMODULE owner=nullptr;
 if(target!=image+0x40893e0){
  if(!read(target,jump,14)||memcmp(jump,"\xff\x25\0\0\0\0",6))return false;memcpy(&destination,jump+6,8);
  if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,(LPCWSTR)destination,&owner))return false;
  if(GetModuleHandleW(L"native_dressing_room.dll")&&owner!=GetModuleHandleW(L"native_dressing_room.dll"))return false;
  wchar_t path[1024]{};GetModuleFileNameW(owner,path,1024);const auto leaf=wcsrchr(path,L'\\');
  if(!leaf||(wcsncmp(leaf+1,L"native_dressing_room",20)&&wcsncmp(leaf+1,L"frontend_stadium",16)))return false;
 }else if(GetModuleHandleW(L"native_dressing_room.dll"))return false;
 if(!photoRelay){
  for(uintptr_t step=0x10000;step<0x70000000&&!photoRelay;step+=0x10000)photoRelay=VirtualAlloc((void*)(image+step),4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);if(!photoRelay)return false;
  unsigned char j[14]={0xff,0x25,0,0,0,0};auto fn=(uintptr_t)&photoHook;memcpy(j+6,&fn,8);memcpy((char*)photoRelay+0xe0,j,14);DWORD old=0;if(!VirtualProtect(photoRelay,4096,PAGE_EXECUTE_READ,&old))return false;FlushInstructionCache(GetCurrentProcess(),photoRelay,4096);
 }
 const auto next=intptr_t(photoRelay)+0xe0-intptr_t(image+0x408d20b);if(next<INT32_MIN||next>INT32_MAX||(next&255)!=0xd5)return false;
 photoBefore=get<LONG64>(image+0x408d208);photoAfter=(photoBefore&~0xffffffLL)|(static_cast<uint32_t>(next)>>8);photoPrevious=target;return photoExchange(photoBefore,photoAfter);
}
void photoTick(bool visible){
 const bool ready=!listMode&&sceneStartupPermitted&&active;
 if(visible&&!ready&&!listMode){photoWasVisible=true;photoRefresh.tick(false,false,GetTickCount64());return;}
 bool refresh=photoRefresh.tick(visible,ready,GetTickCount64());
 if(!visible&&photoWasVisible)photoReturn=true;photoWasVisible=visible;
 if(!visible&&photoReturn){
  auto p=get<uintptr_t>(image+0x3809030);for(unsigned o:{232u,192u,136u,472u})p=get<uintptr_t>(p+o);char name[128]{};
  if(read(p,name,127)){const auto leaf=strrchr(name,'/');refresh=leaf&&(!_stricmp(leaf,"/FluxHub")||!_stricmp(leaf,"/StadiumPan"));}
 }
 if(!refresh)return;const auto self=photoView,vt=get<uintptr_t>(self);
 if(!self||get<uintptr_t>(vt+0x38)!=image+0x408d1d0||!get<uintptr_t>(self+8))return;
 using Queue=BOOL(WINAPI*)(void*,void*);auto host=GetModuleHandleW(L"dinput8.dll");auto queue=(Queue)(host?GetProcAddress(host,"Fifa16CareerQueueBackgroundRefresh"):nullptr);
 if(queue&&queue((void*)self,(void*)vt))photoReturn=false;
}
