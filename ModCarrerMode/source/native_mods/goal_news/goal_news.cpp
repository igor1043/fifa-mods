#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <atomic>
#include <algorithm>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <cwchar>
#include "goal_news_core.h"
#include "concurrent_scores.h"
#include "native_sites.h"

using QueryFn=void(__fastcall*)(void*,const void*,void*);
using FrameFn=void(__fastcall*)(void*);
using MessageFn=void(__fastcall*)(void*,const void*);
static std::uintptr_t image=0;
static std::atomic<bool> stopping{false},enabled{true},installed{false};
static std::atomic<unsigned> delayMs{250};
static std::atomic<unsigned long long> queries{0},nativeEvents{0},invalidEvents{0},originalMessages{0},forwarded{0},frames{0},badQueue{0};
static std::atomic<unsigned long long> poolScores{0};
static std::atomic<bool> replayRequested{false};
static std::atomic<int> replayAfterMinute{-1};
static std::atomic<unsigned long long> lastQueryTick{0};
static volatile LONG started=0;
static SRWLOCK stateGate=SRWLOCK_INIT,patchGate=SRWLOCK_INIT,logGate=SRWLOCK_INIT;
static goal_news::State state;
static wchar_t configPath[32768]{},logPath[32768]{},statusPath[32768]{};
static HANDLE workerHandle=nullptr;
static unsigned char* relay=nullptr;
struct Patch {std::int32_t before=0,after=0;bool active=false;};
static Patch patches[4];

static bool read(std::uintptr_t at,void* out,std::size_t bytes){
 SIZE_T got=0;return at>=0x10000&&ReadProcessMemory(GetCurrentProcess(),reinterpret_cast<void*>(at),out,bytes,&got)&&got==bytes;
}
template<class T>static bool get(std::uintptr_t at,T& out){return read(at,&out,sizeof out);}
static void log(const char* format,...){
 char body[768]{};va_list args;va_start(args,format);vsnprintf_s(body,sizeof body,_TRUNCATE,format,args);va_end(args);
 AcquireSRWLockExclusive(&logGate);FILE* file=nullptr;
 if(!_wfopen_s(&file,logPath,L"ab")){
  SYSTEMTIME t{};GetLocalTime(&t);std::fprintf(file,"%04u-%02u-%02u %02u:%02u:%02u pid=%lu %s\r\n",t.wYear,t.wMonth,t.wDay,t.wHour,t.wMinute,t.wSecond,GetCurrentProcessId(),body);std::fclose(file);
 }
 ReleaseSRWLockExclusive(&logGate);
}
static void afterQuery(void* manager,const void* clock,const void* output){
 ++queries;if(stopping.load())return;
 lastQueryTick.store(GetTickCount64());
 std::array<unsigned char,goal_news::sim_size> data{};int minute=-1;std::uintptr_t pool=0;
 if(!get(reinterpret_cast<std::uintptr_t>(clock)+0x18,minute)||
    !get(reinterpret_cast<std::uintptr_t>(manager)+0x50,pool)||!read(reinterpret_cast<std::uintptr_t>(output),data.data(),data.size())){++invalidEvents;return;}
 goal_news::Score score;const bool event=goal_news::fromSimulation(data.data(),data.size(),minute,score);
 std::array<goal_news::Score,128> parallel{};int entries=0;std::size_t parallelCount=0;
 if(enabled.load()&&get(reinterpret_cast<std::uintptr_t>(manager)+0x9c0,entries))
  parallelCount=goal_news::concurrentScores(pool,entries,minute,read,parallel);
 if(data[0xd4]==1)++nativeEvents;
 AcquireSRWLockExclusive(&stateGate);
 const auto generation=state.sessions;state.session(reinterpret_cast<std::uintptr_t>(manager),pool,minute);
 const bool changed=generation!=state.sessions;
 const bool accepted=enabled.load()&&event&&state.enqueue(score,GetTickCount64());
 for(std::size_t i=0;i<parallelCount;++i)if(state.enqueue(parallel[i],GetTickCount64())){
  ++poolScores;log("queued source=concurrent_pool home=%d away=%d score=%d:%d minute=%d",parallel[i].home,parallel[i].away,parallel[i].homeGoals,parallel[i].awayGoals,parallel[i].minute);
 }
 ReleaseSRWLockExclusive(&stateGate);
 if(changed)log("session manager=%p pool=%p native_minute=%d",manager,reinterpret_cast<void*>(pool),minute);
 if(accepted)log("queued source=native_simulation home=%d away=%d score=%d:%d minute=%d",score.home,score.away,score.homeGoals,score.awayGoals,score.minute);
}
static void __fastcall queryHook(void* manager,const void* clock,void* output){
 reinterpret_cast<QueryFn>(image+0x5bea150)(manager,clock,output);
 afterQuery(manager,clock,output);
}
static bool scoreOverlayBusy(void* owner){
 const auto at=reinterpret_cast<std::uintptr_t>(owner);std::uintptr_t begin=0,end=0;
 if(!get(at+0x21f8,begin)||!get(at+0x2200,end)||end<begin||end-begin>12*4096||(end-begin)%12){++badQueue;return true;}
 // Both the scheduled display (10) and its removal (0) occupy overlay 75.
 for(auto cursor=begin;cursor<end;cursor+=12){int row[3]{};if(!read(cursor,row,sizeof row)){++badQueue;return true;}if(row[0]==75&&(row[1]==0||row[1]==10))return true;}
 return false;
}
static void __fastcall messageHook(void* owner,const void* message){
 ++originalMessages;bool pass=true;
 if(!stopping.load()&&enabled.load()){
  std::array<unsigned char,goal_news::message_size> bytes{};goal_news::Score score;
  if(read(reinterpret_cast<std::uintptr_t>(message),bytes.data(),bytes.size())&&goal_news::fromMessage(bytes.data(),bytes.size(),score)){
   AcquireSRWLockExclusive(&stateGate);pass=state.original(score);ReleaseSRWLockExclusive(&stateGate);
  }
 }
 if(pass)reinterpret_cast<MessageFn>(image+0x48ec5e0)(owner,message);
}
static void __fastcall frameHook(void* owner){
 reinterpret_cast<FrameFn>(image+0x4908c70)(owner);++frames;
 if(stopping.load()||!enabled.load())return;
 if(replayRequested.load()&&GetTickCount64()-lastQueryTick.load()<30000){
  AcquireSRWLockExclusive(&stateGate);
  const int baseline=replayAfterMinute.load();
  if(baseline<0&&state.lastMinute>=0)replayAfterMinute.store(state.lastMinute);
  if(baseline>=0&&state.lastMinute>baseline&&state.observedCount&&state.count<state.pending.size()){
   const auto replay=state.observed[state.observedCount-1];
   state.pending[state.count++]={replay,GetTickCount64()};
   replayRequested.store(false);
   log("manual_replay_queued home=%d away=%d score=%d:%d minute=%d",replay.home,replay.away,replay.homeGoals,replay.awayGoals,replay.minute);
  }
  ReleaseSRWLockExclusive(&stateGate);
 }
 const bool busy=scoreOverlayBusy(owner);goal_news::Score score;
 AcquireSRWLockExclusive(&stateGate);const bool ready=state.next(GetTickCount64(),delayMs.load(),busy,score);ReleaseSRWLockExclusive(&stateGate);
 if(!ready)return;
 const auto payload=goal_news::message(score);
 // This function only schedules FIFA's original APT overlay. It runs on the
 // existing OverlayManager update callback, never on the installation worker.
 reinterpret_cast<MessageFn>(image+0x48ec5e0)(owner,payload.data());++forwarded;
 log("forwarded renderer=FIFA_overlay_75 home=%d away=%d score=%d:%d minute=%d",score.home,score.away,score.homeGoals,score.awayGoals,score.minute);
}
static bool exchange(unsigned index,std::int32_t expected,std::int32_t replacement){
 auto* operand=reinterpret_cast<volatile LONG*>(image+native_sites[index].rva+1);DWORD old=0;
 if(!VirtualProtect(const_cast<LONG*>(operand),4,PAGE_EXECUTE_READWRITE,&old))return false;
 const LONG previous=InterlockedCompareExchange(operand,replacement,expected);DWORD ignored=0;
 VirtualProtect(const_cast<LONG*>(operand),4,old,&ignored);FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(image+native_sites[index].rva),5);
 return previous==expected;
}
static bool restore(){
 bool ok=true;for(unsigned i=4;i>0;--i){auto& p=patches[i-1];if(p.active){if(exchange(i-1,p.after,p.before))p.active=false;else ok=false;}}
 return ok;
}
static bool install(){
 if(installed.load())return true;
 for(unsigned i=0;i<4;++i){unsigned char bytes[16]{};if(!read(image+native_sites[i].rva,bytes,sizeof bytes)||std::memcmp(bytes,native_sites[i].expected,sizeof bytes))return false;}
 if(!relay){
  for(std::uintptr_t delta=0x10000000;delta<0x70000000&&!relay;delta+=0x10000)
   relay=static_cast<unsigned char*>(VirtualAlloc(reinterpret_cast<void*>(image+delta),4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
  if(!relay)return false;
  const std::uintptr_t callbacks[]={reinterpret_cast<std::uintptr_t>(&queryHook),reinterpret_cast<std::uintptr_t>(&queryHook),reinterpret_cast<std::uintptr_t>(&frameHook),reinterpret_cast<std::uintptr_t>(&messageHook)};
  for(unsigned i=0;i<4;++i){unsigned char jump[14]={0xff,0x25,0,0,0,0};std::memcpy(jump+6,&callbacks[i],8);std::memcpy(relay+i*32,jump,sizeof jump);}
  DWORD old=0;if(!VirtualProtect(relay,4096,PAGE_EXECUTE_READ,&old))return false;FlushInstructionCache(GetCurrentProcess(),relay,4096);
 }
 for(unsigned i=0;i<4;++i){
  auto& patch=patches[i];std::memcpy(&patch.before,native_sites[i].expected+1,4);
  const auto distance=reinterpret_cast<std::intptr_t>(relay+i*32)-static_cast<std::intptr_t>(image+native_sites[i].rva+5);
  if(distance<INT32_MIN||distance>INT32_MAX){restore();return false;}
  patch.after=static_cast<std::int32_t>(distance);
  if(!exchange(i,patch.before,patch.after)){restore();return false;}patch.active=true;
 }
 installed.store(true);log("installed revision=2 native_query_paths=2 renderer=FIFA_overlay_75 audio_language_unchanged=1 save_writes=0");return true;
}
static void status(){
 std::size_t queued=0;unsigned long long sessions=0,duplicates=0,expired=0,overflow=0;
 AcquireSRWLockShared(&stateGate);queued=state.count;sessions=state.sessions;duplicates=state.duplicates;expired=state.expired;overflow=state.overflow;ReleaseSRWLockShared(&stateGate);
 wchar_t temporary[32768]{};swprintf_s(temporary,L"%s.tmp",statusPath);FILE* file=nullptr;
 if(!_wfopen_s(&file,temporary,L"wb")){
  std::fprintf(file,"{\"revision\":2,\"pid\":%lu,\"installed\":%s,\"enabled\":%s,\"queries\":%llu,\"native_events\":%llu,\"original_messages\":%llu,\"forwarded\":%llu,\"frames\":%llu,\"queued\":%zu,\"sessions\":%llu,\"duplicates\":%llu,\"expired\":%llu,\"overflow\":%llu,\"invalid_events\":%llu,\"bad_queue\":%llu,\"pool_scores\":%llu,\"renderer\":\"FIFA native overlay 75\",\"in_match_validation\":\"pending\"}\n",GetCurrentProcessId(),installed.load()?"true":"false",enabled.load()?"true":"false",queries.load(),nativeEvents.load(),originalMessages.load(),forwarded.load(),frames.load(),queued,sessions,duplicates,expired,overflow,invalidEvents.load(),badQueue.load(),poolScores.load());
  std::fclose(file);MoveFileExW(temporary,statusPath,MOVEFILE_REPLACE_EXISTING);
 }
}
static DWORD WINAPI worker(void*){
 unsigned attempts=0;
 while(!stopping.load()){
  enabled.store(GetPrivateProfileIntW(L"goal_news",L"enabled",1,configPath)!=0);
  delayMs.store(std::clamp(GetPrivateProfileIntW(L"goal_news",L"visual_delay_ms",250,configPath),0u,2000u));
  if(!installed.load()){
   AcquireSRWLockExclusive(&patchGate);const bool ok=!stopping.load()&&install();ReleaseSRWLockExclusive(&patchGate);
   if(!ok&&++attempts==1200){log("not_installed signature_or_allocation_mismatch no_unknown_code_overwritten=1");status();break;}
  }
  status();Sleep(installed.load()?1000:250);
 }
 return 0;
}
extern "C" __declspec(dllexport) unsigned WINAPI Fifa16ModGetApiVersion(){return 1;}
// Developer-only replay request: schedules an already observed real score.
// This export never calls FIFA; the existing frame callback handles delivery.
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16GoalNewsReplay(void*){
 if(stopping.load()||!installed.load()||!enabled.load())return FALSE;
 AcquireSRWLockShared(&stateGate);replayAfterMinute.store(state.lastMinute);ReleaseSRWLockShared(&stateGate);
 replayRequested.store(true);return TRUE;
}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char*){
 if(InterlockedCompareExchange(&started,1,0))return !stopping.load();
 image=reinterpret_cast<std::uintptr_t>(GetModuleHandleW(nullptr));IMAGE_DOS_HEADER dos{};IMAGE_NT_HEADERS64 nt{};
 if(!get(image,dos)||dos.e_magic!=IMAGE_DOS_SIGNATURE||dos.e_lfanew<0||dos.e_lfanew>4096||
    !get(image+static_cast<unsigned>(dos.e_lfanew),nt)||nt.Signature!=IMAGE_NT_SIGNATURE||nt.FileHeader.Machine!=IMAGE_FILE_MACHINE_AMD64||nt.FileHeader.TimeDateStamp!=0x577de45c){started=0;return FALSE;}
 wchar_t root[32768]{};if(!GetModuleFileNameW(nullptr,root,32768))return FALSE;auto* slash=std::wcsrchr(root,L'\\');if(!slash)return FALSE;*slash=0;
 wchar_t directory[32768]{};swprintf_s(directory,L"%s\\ModCarrerMode\\logs",root);CreateDirectoryW(directory,nullptr);
 swprintf_s(directory,L"%s\\ModCarrerMode\\runtime",root);CreateDirectoryW(directory,nullptr);
 swprintf_s(configPath,L"%s\\ModCarrerMode\\config\\goal_news.ini",root);swprintf_s(logPath,L"%s\\ModCarrerMode\\logs\\goal_news.log",root);swprintf_s(statusPath,L"%s\\ModCarrerMode\\runtime\\goal_news_status.json",root);
 HMODULE pin=nullptr;if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&image),&pin))return FALSE;
 log("start experimental_visual_bridge revision=2");workerHandle=CreateThread(nullptr,0,worker,nullptr,0,nullptr);return workerHandle!=nullptr;
}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16ModStop(){
 stopping.store(true);AcquireSRWLockExclusive(&patchGate);const bool ok=restore();installed.store(false);ReleaseSRWLockExclusive(&patchGate);
 AcquireSRWLockExclusive(&stateGate);state.clear();ReleaseSRWLockExclusive(&stateGate);
 if(workerHandle){WaitForSingleObject(workerHandle,1500);CloseHandle(workerHandle);workerHandle=nullptr;}
 log("stop restored=%u",ok?1u:0u);return ok?TRUE:FALSE;
}
BOOL WINAPI DllMain(HINSTANCE module,DWORD reason,LPVOID){if(reason==DLL_PROCESS_ATTACH)DisableThreadLibraryCalls(module);return TRUE;}
