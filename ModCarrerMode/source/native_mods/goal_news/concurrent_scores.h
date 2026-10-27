#pragma once
#include "goal_news_core.h"

namespace goal_news {
// Read only events already reached by the native clock. The pool also stores
// the rest of a simulated match; final score fields must never be displayed.
template<class Read> std::size_t concurrentScores(std::uintptr_t pool,int entries,int minute,Read read,std::array<Score,128>& out){
 if(!pool||entries<0||entries>1024||minute<0||minute>150)return 0;
 std::array<std::uintptr_t,128> seen{};std::size_t count=0,seenCount=0;
 for(int i=0;i<entries&&seenCount<seen.size();++i){
  std::uintptr_t match=0;if(!read(pool+static_cast<std::uintptr_t>(i)*16+8,&match,8)||!match)continue;
  bool duplicate=false;for(std::size_t j=0;j<seenCount;++j)if(seen[j]==match)duplicate=true;
  if(duplicate)continue;seen[seenCount++]=match;
  int clubs[2]{},events=0;std::uintptr_t rows=0;
  if(!read(match,clubs,8)||!read(match+0x2ac,&events,4)||events<0||events>1024||!read(match+0x2a0,&rows,8)||(events&&!rows))continue;
  Score score{clubs[0],clubs[1],0,0,0,-1};if(!score.valid())continue;
  bool valid=true;
  for(int j=0;j<events;++j){
   std::uintptr_t event=0;int row[3]{};
   if(!read(rows+static_cast<std::uintptr_t>(j)*8,&event,8)||!event||!read(event+8,row,12)){valid=false;break;}
   if(row[0]!=0||row[2]<0||row[2]>minute)continue;
   if(row[1]!=0&&row[1]!=1){valid=false;break;}
   (row[1]?score.awayGoals:score.homeGoals)++;
   if(row[2]>=score.minute){score.minute=row[2];score.side=row[1];}
  }
  if(valid&&score.valid()&&(score.homeGoals||score.awayGoals))out[count++]=score;
 }
 return count;
}
}
