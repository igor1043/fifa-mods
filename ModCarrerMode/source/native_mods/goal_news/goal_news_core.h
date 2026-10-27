#pragma once
#include <array>
#include <cstdint>
#include <cstring>

namespace goal_news {
constexpr std::size_t sim_size=0xd8, message_size=0xc0;
inline int integer(const unsigned char* p,std::size_t at){int value;std::memcpy(&value,p+at,4);return value;}
inline void put(unsigned char* p,std::size_t at,int value){std::memcpy(p+at,&value,4);}
struct Score {
 int home=0,away=0,homeGoals=0,awayGoals=0,side=0,minute=-1;
 bool sameFixture(const Score& other)const{return home==other.home&&away==other.away;}
 bool sameScore(const Score& other)const{return sameFixture(other)&&homeGoals==other.homeGoals&&awayGoals==other.awayGoals;}
 bool valid()const{return home>0&&away>0&&home!=away&&home<10000000&&away<10000000&&homeGoals>=0&&homeGoals<=99&&awayGoals>=0&&awayGoals<=99;}
};
inline bool fromSimulation(const unsigned char* data,std::size_t bytes,int minute,Score& score){
 if(!data||bytes<sim_size||data[0xd4]!=1)return false;
 // Native incident 0 = goal; 5/6 = native score summaries. Cards and penalty
 // anticipation are not goals and must not generate a score notification.
 const int type=integer(data,0x18);if(type!=0&&type!=5&&type!=6)return false;
 score={integer(data,0x20),integer(data,0x24),integer(data,0x28),integer(data,0x2c),integer(data,0x30),minute};
 if(score.side!=0&&score.side!=1)score.side=0;
 if(score.minute<0||score.minute>150)score.minute=-1;
 return score.valid()&&(score.homeGoals||score.awayGoals);
}
inline bool fromMessage(const unsigned char* data,std::size_t bytes,Score& score){
 if(!data||bytes<message_size)return false;
 const int type=integer(data,0);if(type!=0&&type!=1)return false;
 score={integer(data,4),integer(data,12),integer(data,8),integer(data,16),integer(data,20),integer(data,28)};
 return score.valid();
}
inline std::array<unsigned char,message_size> message(const Score& score){
 std::array<unsigned char,message_size> result{};
 // Type 1 asks FIFA for its localized "ScoreUpdate" title. Type 0 uses a
 // commentator-populated scorer name, which is unavailable in visual mode.
 put(result.data(),0,1);put(result.data(),4,score.home);put(result.data(),8,score.homeGoals);
 put(result.data(),12,score.away);put(result.data(),16,score.awayGoals);put(result.data(),20,score.side);
 put(result.data(),28,score.minute);put(result.data(),36,-1); // No aggregate qualification.
 return result;
}
struct Pending {Score score{};std::uint64_t created=0;};
struct State {
 std::array<Pending,64> pending{};std::size_t count=0;
 std::array<Score,256> observed{},delivered{};std::size_t observedCount=0,deliveredCount=0;
 std::uintptr_t manager=0,pool=0;int lastMinute=-1;
 std::uint64_t sessions=0,accepted=0,duplicates=0,expired=0,overflow=0;
 void clear(){count=observedCount=deliveredCount=0;lastMinute=-1;}
 void session(std::uintptr_t object,std::uintptr_t incidents,int minute){
  if(manager!=object||pool!=incidents||(minute>=0&&lastMinute>=0&&minute+2<lastMinute)){
   clear();manager=object;pool=incidents;++sessions;
  }
  if(minute>=0)lastMinute=minute;
 }
 static bool contains(const std::array<Score,256>& list,std::size_t size,const Score& score){
  for(std::size_t i=0;i<size;++i)if(list[i].sameScore(score))return true;return false;
 }
 static void remember(std::array<Score,256>& list,std::size_t& size,const Score& score){
  if(size==list.size()){for(std::size_t i=1;i<size;++i)list[i-1]=list[i];--size;}
  list[size++]=score;
 }
 void remove(std::size_t index){for(std::size_t i=index+1;i<count;++i)pending[i-1]=pending[i];--count;}
 bool enqueue(const Score& score,std::uint64_t now){
  if(!score.valid())return false;
  if(contains(observed,observedCount,score)||contains(delivered,deliveredCount,score)){++duplicates;return false;}
  // Never replay an earlier score after a later native score was observed.
  for(std::size_t i=0;i<observedCount;++i)if(observed[i].sameFixture(score)&&
    (observed[i].homeGoals>score.homeGoals||observed[i].awayGoals>score.awayGoals)){++duplicates;return false;}
  if(count==pending.size()){remove(0);++overflow;}
  remember(observed,observedCount,score);pending[count++]={score,now};++accepted;return true;
 }
 bool original(const Score& score){
  if(contains(delivered,deliveredCount,score)){++duplicates;return false;}
  for(std::size_t i=0;i<count;)if(pending[i].score.sameScore(score))remove(i);else ++i;
  remember(delivered,deliveredCount,score);return true;
 }
 bool next(std::uint64_t now,std::uint64_t delay,bool busy,Score& score){
  while(count&&now-pending[0].created>60000){remove(0);++expired;}
  if(busy||!count||now-pending[0].created<delay)return false;
  score=pending[0].score;remove(0);remember(delivered,deliveredCount,score);return true;
 }
};
}
