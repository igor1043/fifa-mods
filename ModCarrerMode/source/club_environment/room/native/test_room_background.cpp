#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <filesystem>
#include <fstream>
#include <cstring>
#include <cstdint>
#include <cassert>
#include <cstdio>
static uintptr_t image;
static bool inRoom=true;
static int routed=0,queued=0;
static bool read(uintptr_t at,void*out,size_t n){SIZE_T got=0;return ReadProcessMemory(GetCurrentProcess(),(void*)at,out,n,&got)&&got==n;}
template<class T>static T get(uintptr_t at){T result{};read(at,&result,sizeof result);return result;}
static bool page(){return inRoom;}
static void log(const char*){}
static void* factory(void*){return reinterpret_cast<void*>(0x1234);}
static void setParameter(void*provider,const char*key,const char*value){
 assert(provider==reinterpret_cast<void*>(0x1234)&&!strcmp(key,"Param")&&!strcmp(value,"server16_frontend_clear"));++routed;
}
static BOOL WINAPI queue(void*owner,void*vtable){assert(owner&&vtable);++queued;return TRUE;}
static HMODULE fakeModule(LPCWSTR){return reinterpret_cast<HMODULE>(1);}
static FARPROC fakeExport(HMODULE,LPCSTR name){assert(!strcmp(name,"Fifa16CareerQueueBackgroundRefresh"));return reinterpret_cast<FARPROC>(&queue);}
#define GetModuleHandleW fakeModule
#define GetProcAddress fakeExport
#include "room_background_r52.h"
#undef GetModuleHandleW
#undef GetProcAddress
int main(){
 image=reinterpret_cast<uintptr_t>(VirtualAlloc(nullptr,0x4c18000,MEM_RESERVE,PAGE_NOACCESS));assert(image);
 auto region=[&](uintptr_t offset){assert(VirtualAlloc(reinterpret_cast<void*>(image+offset),4096,MEM_COMMIT,PAGE_EXECUTE_READWRITE));};
 region(0x3809000);region(0x4c17000);
 unsigned char jump[]={0x48,0xb8,0,0,0,0,0,0,0,0,0xff,0xe0};auto fn=reinterpret_cast<uintptr_t>(&setParameter);memcpy(jump+2,&fn,8);memcpy(reinterpret_cast<void*>(image+0x4c174d0),jump,sizeof jump);
 uintptr_t vtable[8]{};vtable[7]=image+0x408d1d0;uintptr_t owner[2]={reinterpret_cast<uintptr_t>(vtable),1};
 roomPhotoPrevious=reinterpret_cast<uintptr_t>(&factory);
 roomPhotoHook(owner);assert(routed==1);inRoom=false;roomPhotoHook(owner);assert(routed==1);
 unsigned char nodes[0x1500]{};
 *reinterpret_cast<void**>(image+0x3809030)=nodes;
 *reinterpret_cast<void**>(nodes+232)=nodes+0x400;*reinterpret_cast<void**>(nodes+0x400+192)=nodes+0x800;
 *reinterpret_cast<void**>(nodes+0x800+136)=nodes+0xc00;*reinterpret_cast<void**>(nodes+0xc00+472)=nodes+0x1000;
 strcpy_s(reinterpret_cast<char*>(nodes+0x1000),128,"game/screens/fluxHub/FluxHub");
 roomReturnTick(true);roomReturnTick(true);roomReturnTick(true);assert(queued==1);
 roomReturnTick(true);assert(queued==1);
 roomReturnTick(false);roomReturnTick(false);roomReturnTick(false);assert(queued==2);
 roomReturnTick(false);assert(queued==2);
 VirtualFree(reinterpret_cast<void*>(image),0,MEM_RELEASE);
 puts("PASS: room always requests its transparent background; exit queues UI-owner refresh once without native calls from render");
}
