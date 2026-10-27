#include "../native_mods/goal_news/goal_news_core.h"
#include "../native_mods/goal_news/concurrent_scores.h"
#include <cassert>
#include <cstdio>
using namespace goal_news;
static Score example(int h=1,int a=0){return {1629,1043,h,a,0,23};}
int main(){
 std::array<unsigned char,sim_size> sim{};put(sim.data(),0x18,0);put(sim.data(),0x20,1629);put(sim.data(),0x24,1043);
 put(sim.data(),0x28,1);put(sim.data(),0x2c,0);sim[0xd4]=1;Score score;
 assert(fromSimulation(sim.data(),sim.size(),23,score)&&score.sameScore(example()));
 assert(!fromSimulation(sim.data(),sim.size()-1,23,score));
 sim[0xd4]=0;assert(!fromSimulation(sim.data(),sim.size(),23,score));sim[0xd4]=1;
 for(int type:{1,2,3,4}){put(sim.data(),0x18,type);assert(!fromSimulation(sim.data(),sim.size(),23,score));}
 put(sim.data(),0x18,5);assert(fromSimulation(sim.data(),sim.size(),23,score));
 put(sim.data(),0x28,0);assert(!fromSimulation(sim.data(),sim.size(),23,score));put(sim.data(),0x28,1);
 put(sim.data(),0x24,1629);assert(!fromSimulation(sim.data(),sim.size(),23,score));put(sim.data(),0x24,1043);
 put(sim.data(),0x28,100);assert(!fromSimulation(sim.data(),sim.size(),23,score));put(sim.data(),0x28,1);
 assert(fromSimulation(sim.data(),sim.size(),999,score)&&score.minute==-1);
 auto native=message(example());assert(integer(native.data(),0)==1&&native[48]==0&&native.back()==0);
 assert(fromMessage(native.data(),native.size(),score)&&score.sameScore(example())&&score.minute==23);
 put(native.data(),0,2);assert(!fromMessage(native.data(),native.size(),score)); // Other native notices must pass unchanged.
 State state;state.session(1,2,23);assert(state.sessions==1&&state.enqueue(example(),100));
 assert(!state.enqueue(example(),101));assert(!state.next(200,250,false,score));assert(!state.next(500,250,true,score));
 assert(state.next(500,250,false,score)&&score.sameScore(example()));assert(!state.original(example()));
 assert(state.enqueue(example(2),600));assert(state.original(example(2)));assert(state.count==0);
 assert(!state.enqueue(example(1),700));assert(!state.next(1000,250,false,score));
 state.session(1,3,23);assert(state.sessions==2&&state.enqueue(example(),1000));
 state.session(1,3,0);assert(state.sessions==3&&state.count==0&&state.enqueue(example(),2000));
 assert(!state.next(63000,250,false,score)&&state.expired==1);
 for(int i=0;i<70;++i){auto item=example();item.home=10000+i;assert(state.enqueue(item,64000));}
 assert(state.count==64&&state.overflow==6);assert(state.next(64500,250,false,score)&&score.home==10006);
 assert(state.original(example(3)));assert(!state.original(example(3)));
 // Different competitions, repeated incident pointers and future goals all
 // appear in this native pool. Count only goals reached by the current clock.
 std::array<unsigned char,0x2b0> matchA{},matchB{};
 int goalA[5]{0,0,0,0,3},futureA[5]{0,0,0,1,77},cardA[5]{0,0,1,1,5},goalB[5]{0,0,0,1,7};
 std::uintptr_t eventsA[]{reinterpret_cast<std::uintptr_t>(goalA),reinterpret_cast<std::uintptr_t>(futureA),reinterpret_cast<std::uintptr_t>(cardA)};
 std::uintptr_t eventsB[]{reinterpret_cast<std::uintptr_t>(goalB)};
 put(matchA.data(),0,517);put(matchA.data(),4,130065);put(matchA.data(),0x2ac,3);
 put(matchB.data(),0,567);put(matchB.data(),4,130270);put(matchB.data(),0x2ac,1);
 auto pa=reinterpret_cast<std::uintptr_t>(eventsA),pb=reinterpret_cast<std::uintptr_t>(eventsB);
 std::memcpy(matchA.data()+0x2a0,&pa,8);std::memcpy(matchB.data()+0x2a0,&pb,8);
 std::uintptr_t pool[]{1,reinterpret_cast<std::uintptr_t>(matchA.data()),2,reinterpret_cast<std::uintptr_t>(matchA.data()),3,reinterpret_cast<std::uintptr_t>(matchB.data())};
 auto reader=[](std::uintptr_t p,void* dst,std::size_t n){if(!p)return false;std::memcpy(dst,reinterpret_cast<void*>(p),n);return true;};
 std::array<Score,128> scores{};
 auto poolAt=reinterpret_cast<std::uintptr_t>(pool);
 assert(concurrentScores(poolAt,3,33,reader,scores)==2);
 assert(scores[0].homeGoals==1&&scores[0].awayGoals==0&&scores[0].minute==3);
 assert(scores[1].homeGoals==0&&scores[1].awayGoals==1&&scores[1].minute==7);
 assert(concurrentScores(poolAt,3,2,reader,scores)==0);
 assert(concurrentScores(poolAt,3,78,reader,scores)==2&&scores[0].awayGoals==1);
 assert(!concurrentScores(poolAt,1025,33,reader,scores));assert(!concurrentScores(poolAt,3,-1,reader,scores));
 put(matchA.data(),0x2ac,1025);assert(concurrentScores(poolAt,3,33,reader,scores)==1);
 std::puts("goal_news_core: simulation mapping, native message, deduplication, sessions, expiry, queue OK");
}
