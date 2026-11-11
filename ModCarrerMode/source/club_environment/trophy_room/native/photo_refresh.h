#pragma once
#include <atomic>
#include <cstdint>
namespace gallery_background {
struct Refresh {
 bool visible=false,desired=false;unsigned frames=0;uint64_t retryAt=0;
 std::atomic<int> delivered{-1};
 void observed(bool clear){delivered.store(clear?1:0);}
 bool tick(bool show,bool clear,uint64_t now){
  if(!show){visible=false;frames=0;retryAt=0;return false;}
  if(!visible||desired!=clear){visible=true;desired=clear;frames=0;retryAt=0;delivered=-1;}
  if(delivered.load()==int(desired))return false;
  if(++frames<4||now<retryAt)return false;
  // Acceptance is not delivery: a context/factory change may cancel a job.
  // Retry at most once a second until the native factory acknowledges it.
  retryAt=now+1000;return true;
 }
};
}
