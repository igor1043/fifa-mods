#pragma once
#include <xinput.h>
// Read input only for this foreground FIFA process. Never warp the cursor,
// synthesize keys, register global hooks or consume input outside the room.
struct RoomFreeInput {
 using Pad=DWORD(WINAPI*)(DWORD,XINPUT_STATE*);Pad readPad=nullptr;bool initialized=false,dragging=false;POINT mouse{};
 void reset(){dragging=false;}
 room_free::Input sample(float dt){
  room_free::Input out;DWORD pid=0;auto window=GetForegroundWindow();GetWindowThreadProcessId(window,&pid);
  if(pid!=GetCurrentProcessId()){reset();return out;}
  auto held=[](int key){return (GetAsyncKeyState(key)&0x8000)!=0;};
  out.forward=float(held('W'))-float(held('S'));out.right=float(held('D'))-float(held('A'));out.sprint=held(VK_SHIFT);
  out.yaw=(float(held(VK_RIGHT))-float(held(VK_LEFT)))*dt*1.6f;out.pitch=(float(held(VK_UP))-float(held(VK_DOWN)))*dt*1.2f;
  POINT now{};if(GetCursorPos(&now)&&held(VK_RBUTTON)){
   if(dragging){out.yaw+=std::clamp(float(now.x-mouse.x),-150.f,150.f)*.003f;out.pitch-=std::clamp(float(now.y-mouse.y),-150.f,150.f)*.003f;}
   dragging=true;mouse=now;
  }else reset();
  if(!initialized){initialized=true;auto dll=LoadLibraryW(L"xinput1_4.dll");if(!dll)dll=LoadLibraryW(L"xinput9_1_0.dll");if(dll)readPad=(Pad)GetProcAddress(dll,"XInputGetState");}
  XINPUT_STATE state{};if(readPad)for(DWORD slot=0;slot<4;++slot)if(readPad(slot,&state)==ERROR_SUCCESS){
   auto axis=[](SHORT value){float v=value/32767.f;return std::abs(v)<.18f?0.f:std::copysign((std::abs(v)-.18f)/.82f,v);};
   out.forward+=axis(state.Gamepad.sThumbLY);out.right+=axis(state.Gamepad.sThumbLX);
   out.yaw+=axis(state.Gamepad.sThumbRX)*dt*1.8f;out.pitch+=axis(state.Gamepad.sThumbRY)*dt*1.3f;
   out.sprint=out.sprint||(state.Gamepad.wButtons&XINPUT_GAMEPAD_LEFT_THUMB)!=0;break;
  }
  return out;
 }
};
