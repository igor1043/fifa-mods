#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <filesystem>
#include <fstream>
#include <vector>
#include <string>
#include <algorithm>
#include <atomic>
#include <array>
#include <cstring>
#include <cstdint>
#include <climits>
#include <cassert>
#include <cstdio>
namespace fs=std::filesystem;
static uintptr_t image;
static unsigned validCareerClub;
static fs::path folder;
static bool readyState=false,exportPresent=true;
static HMODULE host=reinterpret_cast<HMODULE>(0x5555);
static bool read(uintptr_t at,void*out,size_t size){SIZE_T got=0;return ReadProcessMemory(GetCurrentProcess(),reinterpret_cast<void*>(at),out,size,&got)&&got==size;}
template<class T>static T get(uintptr_t at){T v{};read(at,&v,sizeof v);return v;}
static void log(const char*){}
static BOOL WINAPI isReady(){return readyState;}
static HMODULE module(LPCWSTR){return host;}
static FARPROC symbol(HMODULE,LPCSTR name){
 if(!strcmp(name,"Fifa16CareerHooksReady"))return exportPresent?reinterpret_cast<FARPROC>(&isReady):nullptr;
 return reinterpret_cast<FARPROC>(&isReady);
}
static BOOL moduleOwner(DWORD,LPCWSTR,HMODULE*out){*out=host;return TRUE;}
#define GetModuleHandleW module
#define GetModuleHandleExW moduleOwner
#define GetProcAddress symbol
#include "room_medical_capture_r53.h"
#undef GetModuleHandleW
#undef GetModuleHandleExW
#undef GetProcAddress
int main(){
 image=reinterpret_cast<uintptr_t>(VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));assert(image);
 std::vector<std::array<unsigned char,5>> original;
 for(const auto&p:roomInjuryPatches){
  const int32_t delta=static_cast<int32_t>(p.target-p.source-5);auto site=reinterpret_cast<unsigned char*>(image+p.source);
  site[0]=0xe8;memcpy(site+1,&delta,4);std::array<unsigned char,5> saved{};memcpy(saved.data(),site,5);original.push_back(saved);
 }
 assert(!installMedicalCapture());assert(!roomMedicalRelay);
 // Even a legacy host without a readiness export must install its setters first.
 exportPresent=false;assert(!installMedicalCapture());assert(!roomMedicalRelay);exportPresent=true;
 for(size_t i=0;i<original.size();++i)assert(!memcmp(reinterpret_cast<void*>(image+roomInjuryPatches[i].source),original[i].data(),5));
 readyState=true;assert(!installMedicalCapture());assert(!roomMedicalRelay);
 for(size_t i=0;i<std::size(roomInjuryPatches);++i){
  auto&p=roomInjuryPatches[i];auto jump=reinterpret_cast<unsigned char*>(image+0x20000+i*0x100+(p.target&255));
  const uintptr_t fn=reinterpret_cast<uintptr_t>(&isReady);memcpy(jump,"\x48\xb8",2);memcpy(jump+2,&fn,8);memcpy(jump+10,"\xff\xe0",2);
  auto site=reinterpret_cast<unsigned char*>(image+p.source);const int32_t delta=static_cast<int32_t>(reinterpret_cast<uintptr_t>(jump)-(image+p.source+5));memcpy(site+1,&delta,4);
  memcpy(original[i].data(),site,5);
 }
 roomMedicalRelay=reinterpret_cast<void*>(image+0x10000);
 assert(installMedicalCapture());assert(installMedicalCapture());
 for(const auto&p:roomInjuryPatches)assert(p.installed&&p.previous!=image+p.target);
 stopMedicalCapture();
 for(size_t i=0;i<original.size();++i)assert(!memcmp(reinterpret_cast<void*>(image+roomInjuryPatches[i].source),original[i].data(),5));
 VirtualFree(reinterpret_cast<void*>(image),0,MEM_RELEASE);
 puts("PASS medical startup: no setter changes before career readiness; legacy original calls preserved; verified host callbacks chained and restored");
}
