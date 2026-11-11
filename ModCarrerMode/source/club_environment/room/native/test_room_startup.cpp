#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <filesystem>
#include <cstring>
#include <cassert>
#include <iostream>
static uint64_t tick=100;static unsigned routePid,routeClub=112893,routeRequest=2;static int routePhase=2,nativeState=14;static bool configured=true;
struct Identity {unsigned schema=1,size=48,sequence=2,pid;uintptr_t service,vtable,registry;unsigned epoch=2,thread=42;} identity;
static HMODULE WINAPI module(LPCWSTR name){return !wcscmp(name,L"dinput8.dll")?HMODULE(1):HMODULE(2);}
static FARPROC WINAPI symbol(HMODULE,const char*){return (FARPROC)&identity;}
static ULONGLONG WINAPI clockNow(){return tick;}
static UINT WINAPI profile(LPCWSTR,LPCWSTR key,INT,LPCWSTR){
 if(!wcscmp(key,L"pid"))return routePid;if(!wcscmp(key,L"team"))return routeClub;if(!wcscmp(key,L"phase"))return unsigned(routePhase);
 if(!wcscmp(key,L"request"))return routeRequest;if(!wcscmp(key,L"slot"))return 261;if(!wcscmp(key,L"enabled"))return configured;return 0;
}
#define GetModuleHandleW module
#define GetProcAddress symbol
#define GetTickCount64 clockNow
#define GetPrivateProfileIntW profile
#include "room_startup.h"
#undef GetModuleHandleW
#undef GetProcAddress
#undef GetTickCount64
#undef GetPrivateProfileIntW
int main(){
 unsigned char service[0x40]{},contexts[0x318]{},loader[0x80]{},command[0x40]{};uintptr_t commands,items[3]{},vt[2]{};
 identity.pid=routePid=GetCurrentProcessId();identity.service=(uintptr_t)service;identity.vtable=0x140123400;identity.registry=1;
 memcpy(service,&identity.vtable,8);auto table=(uintptr_t)contexts;memcpy(service+0x18,&table,8);int club=112893;memcpy(contexts+0x1a4,&club,4);
 auto servicePtr=(uintptr_t)loader;commands=(uintptr_t)items;auto commandsPtr=(uintptr_t)&commands;memcpy(loader+0x68,&commandsPtr,8);items[0]=(uintptr_t)command;
 auto tablePtr=(uintptr_t)vt;memcpy(command,&tablePtr,8);vt[1]=0x140000000+0x3d8e370;
 auto read=[&](uintptr_t address,void*out,size_t length){
  if(address==0x140000000+0x34ea0e8){memcpy(out,&servicePtr,length);return true;}
  if(address==(uintptr_t)command+0x30){memcpy(out,&nativeState,length);return true;}
  SIZE_T got=0;return bool(ReadProcessMemory(GetCurrentProcess(),(void*)address,out,length,&got)&&got==length);
 };
 RoomStartup startup;const std::filesystem::path game=L"fixture";
 assert(!startup.allow(game,0x140000000,112893,read)&&startup.gate.reason==2);
 nativeState=0;tick=400;assert(!startup.allow(game,0x140000000,112893,read)&&startup.gate.reason==3);
 routePhase=3;tick=700;assert(!startup.allow(game,0x140000000,112893,read)&&startup.gate.reason==4);
 tick=1449;assert(!startup.allow(game,0x140000000,112893,read));tick=1450;assert(startup.allow(game,0x140000000,112893,read));
 identity.sequence=3;tick=1500;assert(!startup.allow(game,0x140000000,112893,read)&&startup.gate.reason==1);identity.sequence=4;
 routePid--;tick=1800;assert(!startup.allow(game,0x140000000,112893,read)&&startup.gate.reason==3);routePid++;
 routeClub=1043;tick=2100;assert(!startup.allow(game,0x140000000,112893,read));routeClub=112893;
 tick=2400;assert(!startup.allow(game,0x140000000,112893,read));tick=3150;assert(startup.allow(game,0x140000000,112893,read));
 std::cout<<"PASS actual startup probe: native loader, current career/club, route phase, stale session and settling checks\n";
}
