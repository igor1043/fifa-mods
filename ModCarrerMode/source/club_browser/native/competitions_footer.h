#pragma once
#include <filesystem>
#include <string>
#include <windows.h>

namespace clubcomp {
inline int helpMode(bool ready,bool fullList,bool bracket,bool rounds){
 return !ready?0:fullList?2:bracket?3:rounds?4:1;
}
// Copy only bounded presentation metadata when the native modal changes.
// The actual button graphics/rendering/input bindings belong to FIFA's APT
// HelpManager. No FIFA calls are made on the Present/render thread.
struct FooterPublication {
 int last=-1;ULONGLONG retry=0;
 void reset(){last=-1;retry=0;}
 bool publish(const std::filesystem::path& game,int mode,ULONGLONG now){
  if(mode<0||mode>4||mode==last||now<retry)return false;
  retry=now+1000;
  auto source=game/L"ModCarrerMode/data/club_browser/competition_help"/(L"mode_"+std::to_wstring(mode)+L".big");
  auto target=game/L"data/ui/game/screens/career/server16";
  bool complete=true;
  for(int slot=0;slot<2;++slot){
   auto file=target/(L"competitionhelp"+std::to_wstring(slot)+L".big");
   auto temp=file;temp+=L".footer.new";
   if(!CopyFileW(source.c_str(),temp.c_str(),FALSE)||!MoveFileExW(temp.c_str(),file.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)){
    DeleteFileW(temp.c_str());complete=false;
   }
  }
  if(complete){last=mode;retry=0;}
  return complete;
 }
};
}
