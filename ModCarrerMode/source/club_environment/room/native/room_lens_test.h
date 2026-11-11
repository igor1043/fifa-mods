#pragma once
#include <fstream>
// A temporary, process-scoped comparison. Missing/stale requests keep the
// user's clean view. This never changes persistent game or career settings.
struct RoomLensTest {
 bool native=false;uint64_t next=0;
 template<class Path>bool clean(const Path& request){
  const auto now=GetTickCount64();if(now<next)return !native;next=now+500;
  std::ifstream in(request);std::string magic;unsigned version=0,pid=0,mode=0;
  native=bool(in>>magic>>version>>pid>>mode)&&magic=="S16ROOMLENS"&&version==1&&pid==GetCurrentProcessId()&&mode==1;
  return !native;
 }
};
