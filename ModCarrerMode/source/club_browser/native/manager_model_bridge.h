#pragma once
#include "manager_model_scope.h"
#include "lua_numeric_bridge.h"
namespace managerBridge {
using namespace managerModels;
// Called only for resource selection, never from a render pass. The accessor
// is read-only and mirrors the already published Career ContextRead contract.
inline int scope(Scope& out){
 auto base=clubscene::base;auto get=[](uintptr_t p){return clubscene::get<uintptr_t>(p);};
 auto engine=GetModuleHandleW(L"FootballCompEngzf.dll");if(!engine)return -1;
 if(!get(uintptr_t(engine)+0xb13f0))return -1;
 auto host=GetModuleHandleW(L"dinput8.dll");auto published=uintptr_t(host?GetProcAddress(host,"Fifa16CareerContextRead"):nullptr);
 struct Record{uint32_t schema,size,sequence,pid;uintptr_t service,vtable,registry;uint32_t epoch,thread;};static_assert(sizeof(Record)==48,"Career read ABI");
 Record a{},b{};unsigned char descriptor[24]{},signature[22]{};
 const unsigned char expected[]={0x48,0x63,0x41,0x14,0x83,0xf8,0xff,0x75,0x03,0x31,0xc0,0xc3,0x48,0x69,0xc0,0x18,0x03,0,0,0x48,0x03,0x41};
 if(!clubscene::read(published,&a,sizeof a)||a.schema!=1||a.size!=sizeof a||(a.sequence&1)||a.pid!=GetCurrentProcessId()||!a.service||!a.registry||!a.vtable||!clubscene::read(base+0x5aafff0,signature,sizeof signature)||memcmp(signature,expected,sizeof expected)||!clubscene::read(base+0x44575e0,descriptor,24)||descriptor[7]!=0xc7||descriptor[8]!=1)return -1;
 uint32_t index=0;memcpy(&index,descriptor+9,4);if(index>4096||get(get(a.registry+index*32+24))!=a.service||get(a.service)!=a.vtable)return -1;
 int selected=-1;if(!clubscene::read(a.service+0x14,&selected,4)||selected<0||selected>7)return -1;
 auto context=get(a.service+0x18)+uintptr_t(selected)*0x318;
 if(!get(a.service+0x18)||clubscene::get<int>(context+0x18c)!=1)return -1;
 out.pid=a.pid;out.context=context;out.epoch=a.epoch;out.club=clubscene::get<unsigned>(context+0x1a4);
 // The calendar service stores day, month, year, exactly as fce_date_pack.
 if(!clubscene::read(base+0x44563f0,descriptor,24)||descriptor[7]!=0xc7||descriptor[8]!=1)return 0;
 memcpy(&index,descriptor+9,4);if(index>4096)return 0;auto calendar=get(get(a.registry+index*32+24));int d[3]{};
 if(!calendar||!clubscene::read(calendar+0x34,d,sizeof d)||d[0]<1||d[0]>31||d[1]<1||d[1]>12||d[2]<2000||d[2]>2200)return 0;
 out.date=uint64_t(d[2])*10000+d[1]*100+d[0];FILETIME created,exit,kernel,user;
 if(!GetProcessTimes(GetCurrentProcess(),&created,&exit,&kernel,&user))return 0;out.created=(uint64_t(created.dwHighDateTime)<<32)|created.dwLowDateTime;
 if(!out.club||out.club>200000||!clubscene::read(published,&b,sizeof b)||memcmp(&a,&b,sizeof a))return 0;return 1;
}
inline std::string contents(const std::filesystem::path& file){std::error_code ec;auto n=std::filesystem::file_size(file,ec);if(ec||!n||n>524288)return {};std::ifstream f(file,std::ios::binary);std::string text(size_t(n),'\0');if(!f.read(text.data(),std::streamsize(n)))return {};return text;}
inline int resolve(int club){
 Scope live;int active=scope(live);if(active<0)return -1;if(active==0||!club)return 0;
 auto runtime=clubscene::game/L"ModCarrerMode/runtime";
 Fields latest;uint64_t tick=0;for(auto name:{L"career_save_source.tsv",L"career_active_save.tsv"}){Fields candidate;if(fields(contents(runtime/name),candidate)&&event(candidate,live)&&value(candidate,"access_tick_ms")>tick){latest=std::move(candidate);tick=value(latest,"access_tick_ms");}}
 if(!tick)return 0;int asset=0;bool found=false;
 for(auto source:{L"user_manager/models_ready.tsv",L"manager_market/models_ready.tsv"}){
  Mapping mapping;if(!parse(contents(runtime/source),mapping)||!matches(mapping,live,latest))continue;
  auto row=mapping.clubs.find(club);if(row==mapping.clubs.end())continue;asset=row->second;found=true;break;
 }
 if(!found||asset<=0)return 0;
 auto folder=clubscene::game/L"data/sceneassets/slc";
 auto prefix=L"specificmanager_"+std::to_wstring(asset)+L"_0_";
 for(auto name:{prefix+L"0.rx3",prefix+L"0_textures.rx3",prefix+L"1.rx3",prefix+L"1_textures.rx3"}){std::error_code ec;if(!std::filesystem::is_regular_file(folder/name,ec))return 0;}
 return asset;
}
inline int __cdecl callback(uintptr_t L){
 int code=0;try{code=clubscene::stopping?-1:resolve(managerLua::argument(L,clubscene::read));}catch(...){code=0;}
 return managerLua::result(L,code,clubscene::read,clubscene::write);
}
inline uintptr_t installedVM=0,installedGlobals=0;inline uint64_t retryAt=0;
inline void tick(){
 auto L=clubscene::get<uintptr_t>(clubscene::base+0x3613fd0);if(!L||clubscene::get<int>(L+0x80)!=5)return;
 auto globals=clubscene::get<uintptr_t>(L+0x78);auto field=clubscene::field(globals,"FIFA16_Career_Manager_Asset");
 if(L==installedVM&&globals==installedGlobals&&field.type==6&&clubscene::get<uintptr_t>(field.value+32)==uintptr_t(&callback))return;
 auto now=GetTickCount64();if(now<retryAt)return;retryAt=now+1000;
 // Allocate a private C closure through Lua itself. Only this owned closure's
 // callback is changed; standard-library functions and their closures stay intact.
 if(!clubscene::execute("FIFA16_Career_Manager_Pending=string.gmatch('', '')"))return;
 field=clubscene::field(globals,"FIFA16_Career_Manager_Pending");if(field.type!=6)return;
 auto original=managerLua::ownedFunction(field.value,clubscene::read);MEMORY_BASIC_INFORMATION mbi{};
 if(!original||!VirtualQuery((void*)original,&mbi,sizeof mbi)||mbi.AllocationBase!=(void*)clubscene::base||!(mbi.Protect&(PAGE_EXECUTE|PAGE_EXECUTE_READ|PAGE_EXECUTE_READWRITE)))return;
 if(InterlockedCompareExchangePointer((void*volatile*)(field.value+32),(void*)&callback,(void*)original)!=(void*)original)return;
 if(!clubscene::execute("FIFA16_Career_Manager_Asset=FIFA16_Career_Manager_Pending;FIFA16_Career_Manager_Pending=nil"))return;
 installedVM=L;installedGlobals=globals;clubscene::log("CAREER_MANAGER_IDENTITY_BRIDGE_READY");
}
inline void guardedTick(){__try{tick();}__except(EXCEPTION_EXECUTE_HANDLER){retryAt=GetTickCount64()+10000;}}
}
