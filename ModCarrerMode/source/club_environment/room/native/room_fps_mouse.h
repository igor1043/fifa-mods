#pragma once
#include <windows.h>
#include <algorithm>

namespace room_fps {
struct Delta {float yaw=0,pitch=0;};
struct WindowsMouse {
 static bool position(POINT& p){return GetCursorPos(&p)!=FALSE;}
 static bool bounds(HWND window,RECT& r){
  if(!GetClientRect(window,&r))return false;
  POINT a{r.left,r.top},b{r.right,r.bottom};
  if(!ClientToScreen(window,&a)||!ClientToScreen(window,&b))return false;
  r={a.x,a.y,b.x,b.y};return true;
 }
 static bool clip(RECT& r){return GetClipCursor(&r)!=FALSE;}
 static bool constrain(const RECT& r){return ClipCursor(&r)!=FALSE;}
 static void move(POINT p){SetCursorPos(p.x,p.y);}
 static HWND foreground(){return GetForegroundWindow();}
 static void hide(){SetCursor(nullptr);}
};
// Capture is scoped to the active room camera. Relative look never stops at
// a screen edge, and returning to menus or another application releases it.
// The platform is replaceable so tests never move the user's real pointer.
template<class Platform=WindowsMouse> struct MouseLook {
 HWND window=nullptr;RECT area{},previous{};POINT entry{};bool captured=false;
 static bool same(const RECT&a,const RECT&b){return a.left==b.left&&a.top==b.top&&a.right==b.right&&a.bottom==b.bottom;}
 void reset(bool restore=true){
  if(!captured)return;RECT current{};bool ours=Platform::clip(current)&&same(current,area);
  if(ours)Platform::constrain(previous);
  if(ours&&restore&&Platform::foreground()==window)Platform::move(entry);
  captured=false;window=nullptr;
 }
 Delta sample(HWND active){
  RECT next{};POINT pointer{};
  if(!active||Platform::foreground()!=active||!Platform::bounds(active,next)||next.right-next.left<16||next.bottom-next.top<16||!Platform::position(pointer)){reset(false);return {};}
  if(captured&&(window!=active||!same(next,area)))reset(false);
  POINT center{next.left+(next.right-next.left)/2,next.top+(next.bottom-next.top)/2};
  if(!captured){
   if(!Platform::clip(previous))return {};
   entry=pointer;area=next;window=active;
   if(!Platform::constrain(area)){window=nullptr;return {};}
   captured=true;Platform::move(center);Platform::hide();return {};
  }
  Delta out{std::clamp(float(pointer.x-center.x),-150.f,150.f)*.003f,-std::clamp(float(pointer.y-center.y),-150.f,150.f)*.003f};
  if(pointer.x!=center.x||pointer.y!=center.y)Platform::move(center);
  Platform::hide();return out;
 }
};
// Click-and-drag look keeps the visible pointer free for native buttons.
// It never recentres, hides or confines the user's mouse.
template<class Platform=WindowsMouse>struct DragLook {
 HWND window=nullptr;POINT previous{};bool dragging=false;
 void reset(bool=true){window=nullptr;dragging=false;}
 Delta sample(HWND active,bool held){
  RECT area{};POINT p{};
  if(!held||!active||Platform::foreground()!=active||!Platform::bounds(active,area)||!Platform::position(p)){reset();return {};}
  if(!dragging||window!=active){
   const float height=float(area.bottom-area.top);
   if(p.x<area.left||p.x>=area.right||p.y<area.top+height*.15f||p.y>area.top+height*.84f)return {};
   window=active;previous=p;dragging=true;return {};
  }
  Delta result{std::clamp(float(p.x-previous.x),-150.f,150.f)*.003f,-std::clamp(float(p.y-previous.y),-150.f,150.f)*.003f};previous=p;return result;
 }
};
}
