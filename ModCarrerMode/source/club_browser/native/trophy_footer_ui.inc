// The footer is part of the same crisp HUD as the cards, with its own reserved
// area. It cannot be clipped by Calendar's global HelpDisplay parent transform.
#include "../../club_environment/trophy_room/native/controls_layout.h"
void drawTrophyFooter(ID3D11DeviceContext*c,HMODULE module,bool loading=false){
 using Mode=unsigned(WINAPI*)();const auto mode=(Mode)GetProcAddress(module,"Fifa16TrophyRoomUiMode");
 const unsigned current=loading?4u:mode?mode():0u;unsigned count=0;const auto items=trophy_controls::items(current,count);
 auto&r=renderer;r.rectangle(c,40,833,1520,64,0xb01a2227);int label=120;
 for(unsigned i=0;i<count;++i){
  const float x=trophy_controls::left+(i%4)*trophy_controls::column,y=trophy_controls::top+(i/4)*trophy_controls::row;
  shelfRounded(c,x,y,122,25,0xff29343b);
  r.label(c,label++,items[i].key,x+3,y,116,25,18,RGB(231,216,183),true);
  r.label(c,label++,items[i].label,x+134,y,216,25,20,RGB(250,250,250));
 }
}
