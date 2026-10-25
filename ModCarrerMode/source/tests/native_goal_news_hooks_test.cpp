// Exercise the real hooks against owned executable stubs. No FIFA is attached.
#include <cassert>
#include <filesystem>
#include "../native_mods/goal_news/goal_news.cpp"
static DWORD expectedThread=0;
static unsigned queryCalls=0,frameCalls=0,messageCalls=0;
static std::array<unsigned char,goal_news::message_size> lastMessage{};
static void __fastcall fakeQuery(void*,const void*,void* output){
 ++queryCalls;auto* p=static_cast<unsigned char*>(output);std::memset(p,0,goal_news::sim_size);
 goal_news::put(p,0x20,1629);goal_news::put(p,0x24,1043);goal_news::put(p,0x28,1);p[0xd4]=1;
}
static void __fastcall fakeFrame(void*){assert(GetCurrentThreadId()==expectedThread);++frameCalls;}
static void __fastcall fakeMessage(void*,const void* payload){
 assert(GetCurrentThreadId()==expectedThread);++messageCalls;std::memcpy(lastMessage.data(),payload,lastMessage.size());
}
static void stub(unsigned rva,std::uintptr_t callback){
 unsigned char jump[14]={0xff,0x25,0,0,0,0};std::memcpy(jump+6,&callback,8);std::memcpy(reinterpret_cast<void*>(image+rva),jump,sizeof jump);
}
int main(){
 wchar_t temp[MAX_PATH]{};GetTempPathW(MAX_PATH,temp);swprintf_s(logPath,L"%sgoal-news-hook-test.log",temp);
 expectedThread=GetCurrentThreadId();auto* memory=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));assert(memory);image=reinterpret_cast<std::uintptr_t>(memory);
 for(const auto& site:native_sites){assert((site.rva+1)%64<=60);std::memcpy(memory+site.rva,site.expected,16);}
 stub(0x5bea150,reinterpret_cast<std::uintptr_t>(&fakeQuery));stub(0x4908c70,reinterpret_cast<std::uintptr_t>(&fakeFrame));stub(0x48ec5e0,reinterpret_cast<std::uintptr_t>(&fakeMessage));
 // Refuse to overwrite an unexpected revision, without touching other sites.
 memory[native_sites[3].rva]^=1;assert(!install());for(unsigned i=0;i<3;++i)assert(!std::memcmp(memory+native_sites[i].rva,native_sites[i].expected,16));memory[native_sites[3].rva]^=1;
 assert(install());for(unsigned i=0;i<4;++i){std::int32_t distance=0;std::memcpy(&distance,memory+native_sites[i].rva+1,4);assert(image+native_sites[i].rva+5+distance==reinterpret_cast<std::uintptr_t>(relay+i*32));assert(!std::memcmp(memory+native_sites[i].rva+5,native_sites[i].expected+5,11));}
 std::array<unsigned char,0xa10> manager{};std::array<unsigned char,0x20> clock{};std::array<unsigned char,goal_news::sim_size> output{};goal_news::put(clock.data(),0x18,23);
 auto query=reinterpret_cast<QueryFn>(relay);query(manager.data(),clock.data(),output.data());assert(queryCalls==1&&state.count==1&&nativeEvents==1);
 std::array<unsigned char,0x2210> owner{};std::array<int,3> event{75,10,0};auto begin=reinterpret_cast<std::uintptr_t>(event.data()),end=begin+12;std::memcpy(owner.data()+0x21f8,&begin,8);std::memcpy(owner.data()+0x2200,&end,8);
 delayMs=0;auto frame=reinterpret_cast<FrameFn>(relay+64);frame(owner.data());assert(frameCalls==1&&messageCalls==0&&state.count==1);
 end=begin;std::memcpy(owner.data()+0x2200,&end,8);frame(owner.data());assert(frameCalls==2&&messageCalls==1&&forwarded==1&&state.count==0);
 goal_news::Score score;assert(goal_news::fromMessage(lastMessage.data(),lastMessage.size(),score)&&score.home==1629&&score.away==1043&&score.homeGoals==1&&score.minute==23&&goal_news::integer(lastMessage.data(),0)==1);
 auto message=reinterpret_cast<MessageFn>(relay+96);message(owner.data(),lastMessage.data());assert(messageCalls==1);query(manager.data(),clock.data(),output.data());frame(owner.data());assert(messageCalls==1);
 // Turning off forwarding still preserves FIFA's original query/frame calls.
 enabled=false;query(manager.data(),clock.data(),output.data());frame(owner.data());assert(queryCalls==3&&frameCalls==4&&messageCalls==1);
 enabled=true;goal_news::put(lastMessage.data(),0,2);message(owner.data(),lastMessage.data());assert(messageCalls==2);
 // Portuguese can return no incident while the parallel simulator already
 // holds goals. Exercise the actual query hook, reader, queue and frame path.
 std::array<unsigned char,0x2b0> parallelMatch{};int pastGoal[5]{0,0,0,1,12},futureGoal[5]{0,0,0,0,70};
 std::uintptr_t events[]{reinterpret_cast<std::uintptr_t>(pastGoal),reinterpret_cast<std::uintptr_t>(futureGoal)};
 auto eventRows=reinterpret_cast<std::uintptr_t>(events);
 goal_news::put(parallelMatch.data(),0,517);goal_news::put(parallelMatch.data(),4,130065);goal_news::put(parallelMatch.data(),0x2ac,2);std::memcpy(parallelMatch.data()+0x2a0,&eventRows,8);
 std::uintptr_t pool[]{1,reinterpret_cast<std::uintptr_t>(parallelMatch.data()),2,reinterpret_cast<std::uintptr_t>(parallelMatch.data())};auto poolAddress=reinterpret_cast<std::uintptr_t>(pool);
 std::memcpy(manager.data()+0x50,&poolAddress,8);goal_news::put(manager.data(),0x9c0,2);goal_news::put(clock.data(),0x18,33);
 state.session(123,456,33); // A different active simulator clears prior data.
 query(manager.data(),clock.data(),output.data());assert(poolScores==1);
 frame(owner.data());frame(owner.data());
 assert(goal_news::fromMessage(lastMessage.data(),lastMessage.size(),score)&&score.home==517&&score.away==130065&&score.homeGoals==0&&score.awayGoals==1&&score.minute==12);
 const auto sent=messageCalls;query(manager.data(),clock.data(),output.data());frame(owner.data());assert(messageCalls==sent);
 goal_news::put(clock.data(),0x18,71);query(manager.data(),clock.data(),output.data());frame(owner.data());
 assert(messageCalls==sent+1&&goal_news::fromMessage(lastMessage.data(),lastMessage.size(),score)&&score.homeGoals==1&&score.awayGoals==1);
 assert(Fifa16GoalNewsReplay(nullptr));assert(messageCalls==sent+1);
 frame(owner.data());assert(messageCalls==sent+1); // Paused clock cannot consume the preview.
 goal_news::put(clock.data(),0x18,72);query(manager.data(),clock.data(),output.data());frame(owner.data());assert(messageCalls==sent+2);
 assert(goal_news::fromMessage(lastMessage.data(),lastMessage.size(),score)&&score.homeGoals==1&&score.awayGoals==1);
 enabled=false;assert(!Fifa16GoalNewsReplay(nullptr));enabled=true;
 assert(restore());for(const auto& site:native_sites)assert(!std::memcmp(memory+site.rva,site.expected,16));
 VirtualFree(relay,0,MEM_RELEASE);relay=nullptr;VirtualFree(memory,0,MEM_RELEASE);image=0;
 std::puts("PASS native hook guards, original calls, busy overlay, localized payload, deduplication, engine-thread delivery, disable and full restore");
}
