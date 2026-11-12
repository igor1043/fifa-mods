#pragma once
#include "../../../common/scene_startup.h"
// Read-only prerequisite checks. Never send a UI event, execute Lua, allocate
// an engine prop or move the camera while the native scene loader is busy.
struct RoomStartup {
 scene_startup::Gate gate;uint64_t next=0;unsigned routePid=0,routeClub=0,request=0,slot=0;int phase=0;bool enabled=false,careerEnabled=true;
 template<class Read>static bool loaderIdle(uintptr_t image,Read read){
  auto get=[&](uintptr_t at){uintptr_t value=0;read(at,&value,sizeof value);return value;};
  auto service=get(image+0x34ea0e8),commands=get(service+0x68),items=get(commands);
  if(!service||!commands||!items)return false;
  for(unsigned i=0;i<3;++i){auto object=get(items+i*8),vt=get(object);int state=-1;
   if(object&&get(vt+8)==image+0x3d8e370&&read(object+0x30,&state,sizeof state))return state==0||state==12;
  }return false;
 }
 template<class Path,class Read>bool allow(const Path&game,uintptr_t image,unsigned club,Read read){
  const auto now=GetTickCount64();
  if(now>=next){next=now+250;auto file=game/L"ModCarrerMode/runtime/frontend_stadium_live.ini";
   routePid=GetPrivateProfileIntW(L"frontend_stadium",L"pid",0,file.c_str());routeClub=GetPrivateProfileIntW(L"frontend_stadium",L"team",0,file.c_str());
   phase=int(GetPrivateProfileIntW(L"frontend_stadium",L"phase",0,file.c_str()));request=GetPrivateProfileIntW(L"frontend_stadium",L"request",0,file.c_str());slot=GetPrivateProfileIntW(L"frontend_stadium",L"slot",0,file.c_str());
   enabled=GetPrivateProfileIntW(L"frontend_stadium",L"enabled",0,(game/L"ModCarrerMode/config/frontend_stadium.ini").c_str())!=0;
   careerEnabled=GetPrivateProfileIntW(L"frontend_stadium",L"career",1,(game/L"ModCarrerMode/config/frontend_stadium.ini").c_str())!=0;
  }
  struct Context {unsigned schema,size,sequence,pid;uintptr_t service,vtable,registry;unsigned epoch,thread;};
  static_assert(sizeof(Context)==48,"Career context publication ABI");Context a{},b{};
  auto host=GetModuleHandleW(L"dinput8.dll");auto at=(uintptr_t)(host?GetProcAddress(host,"Fifa16CareerContextRead"):nullptr);
  auto get=[&](uintptr_t address){uintptr_t value=0;read(address,&value,sizeof value);return value;};
  scene_startup::Sample s;s.club=club;s.loaderIdle=loaderIdle(image,read);
  if(read(at,&a,sizeof a)&&a.schema==1&&a.size==sizeof a&&!(a.sequence&1)&&a.pid==GetCurrentProcessId()&&a.epoch&&a.registry&&a.service&&get(a.service)==a.vtable){
   int index=-1,current=0;if(read(a.service+0x14,&index,sizeof index)&&index>=0&&index<8){auto contexts=get(a.service+0x18);if(contexts)read(contexts+uintptr_t(index)*0x318+0x1a4,&current,sizeof current);}
   s.context=current>0&&unsigned(current)==club&&read(at,&b,sizeof b)&&!memcmp(&a,&b,sizeof a);s.epoch=a.epoch;s.service=a.service;s.registry=a.registry;
  }
  // Dedicated room/trophy cards do not require a custom career stadium when
  // that optional background route is disabled. An actual in-flight route
  // still owns the loader and must finish even after its switch is turned off.
  s.routeRequired=GetModuleHandleW(L"frontend_stadium_native_v11.dll")&&((enabled&&careerEnabled)||(routePid==GetCurrentProcessId()&&(phase==1||phase==2)));
  s.routeCurrent=routePid==GetCurrentProcessId()&&routeClub==club;s.phase=phase;
  if(s.routeRequired){s.request=request;s.slot=slot;}
  return gate.allow(s,now);
 }
};
