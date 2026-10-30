#include <cassert>
#include <iostream>
#include "render.cpp"
int main(){
 _set_error_mode(_OUT_TO_STDERR);
 auto fake=(unsigned char*)VirtualAlloc(nullptr,0x3900000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);assert(fake);executable=(uintptr_t)fake;
 unsigned char nodes[4][512]{};char pageName[128]="game/screens/career/server16/ClubBrowser";
 auto store=[](void*p,uintptr_t value){memcpy(p,&value,8);};
 store(fake+0x3809030,(uintptr_t)nodes[0]);store(nodes[0]+232,(uintptr_t)nodes[1]);
 store(nodes[1]+192,(uintptr_t)nodes[2]);store(nodes[2]+136,(uintptr_t)nodes[3]);store(nodes[3]+472,(uintptr_t)pageName);
 roomEntry=false;clubPage=ClubPage::Map;hubFocus=1;enterChoice();
 for(int pass=0;pass<200;++pass){
  int index=pass%4;const char*names[]={"focus_xi","focus_roster","focus_coach","focus_mascot"};
  assert(Fifa16ClubBrowserCommand(names[index]));drainClubCommands();assert(hubFocus==index);
  clubPage=index==0?ClubPage::XI:index==1?ClubPage::Roster:index==2?ClubPage::Coach:ClubPage::Mascot;
  assert(Fifa16ClubBrowserCommand("back"));assert(Fifa16ClubBrowserCommand(names[index]));
  drainClubCommands();assert(clubPage==ClubPage::Choice&&hubFocus==index);
  // Absolute APT focus recovers from any legacy/stale native index.
  hubFocus=(index+1)%4;assert(Fifa16ClubBrowserCommand(names[index]));drainClubCommands();assert(hubFocus==index);
 }
 assert(Fifa16ClubBrowserCommand("back"));drainClubCommands();assert(clubPage==ClubPage::Map);
 executable=0;VirtualFree(fake,0,MEM_RELEASE);
 std::cout<<"PASS native choice focus: XI/roster/coach returns and absolute resynchronization across 200 cycles\n";
}
