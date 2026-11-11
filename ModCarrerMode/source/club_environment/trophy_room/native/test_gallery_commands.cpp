// Exercise the actual command handler without a FIFA process or game memory.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <cstdint>
static HWND testWindow(){return reinterpret_cast<HWND>(uintptr_t(1));}
static DWORD testWindowThread(HWND,LPDWORD pid){if(pid)*pid=GetCurrentProcessId();return GetCurrentThreadId();}
static SHORT testHeld(int){return 0;}
#define GetForegroundWindow testWindow
#define GetWindowThreadProcessId testWindowThread
#define GetAsyncKeyState testHeld
#include "trophy_room.cpp"
#undef GetForegroundWindow
#undef GetWindowThreadProcessId
#undef GetAsyncKeyState
static XINPUT_STATE testPad;
static DWORD WINAPI readTestPad(DWORD i,XINPUT_STATE*out){if(i)return ERROR_DEVICE_NOT_CONNECTED;*out=testPad;return ERROR_SUCCESS;}
#include <cassert>
#include <iostream>
int main(){
 auto send=[](int value){command=value;input();};
 listMode=true;listReady=true;shelfTotal=37;shelfPage=1;shelfSelected=2;
 send(26);assert(coachCollection&&listMode&&shelfPage==0&&!listReady);
 listReady=true;shelfTotal=37;send(26);assert(coachCollection&&listReady&&shelfTotal==37);
 send(25);assert(!coachCollection&&!listReady);
 listReady=true;shelfTotal=37;shelfPage=1;shelfSelected=2;
 send(12000+2);assert(!listMode&&pendingDetailSlot==20&&selectedPage==0);
 send(11);assert(!listMode&&pendingDetailSlot==20); // RT is idempotent.
 send(10);assert(!listMode&&pendingDetailSlot==20); // LT cannot abandon pending inspection.
 send(6);send(10);assert(listMode);listReady=true;shelfTotal=1;shelfSelected=0;shelfPage=0;
 send(12000+8);assert(listMode&&shelfSelected==0); // No invisible cards.
 send(11);assert(!listMode&&pendingDetailSlot==-1);
 detailScroll=0;send(30);assert(detailScroll==0);send(31);assert(detailScroll==1);
 send(32);assert(camera.inspect.zoom<0);send(33);assert(camera.inspect.zoom==0);
 gallery_tour::Visit visit;visit.slot=0;visit.wide=visit.detail=gallery_tour::overview();
 tour.reset({visit},0);tour.details(true,0);send(10);assert(!listMode&&tour.detail);
 send(11);assert(!listMode&&tour.detail);send(32);assert(camera.inspect.zoom<0);
 send(6);send(10);assert(listMode&&!tour.detail);
 // Run the actual input poll with held triggers: inspection consumes no
 // view edges, and holding a trigger across Back cannot leave the 3D room.
 padRead=readTestPad;listMode=false;pendingDetailSlot=-1;tour.details(true,0);
 testPad.Gamepad.bLeftTrigger=255;input();assert(!listMode&&tour.detail);
 testPad.Gamepad.bLeftTrigger=0;testPad.Gamepad.bRightTrigger=255;input();assert(!listMode&&tour.detail);
 send(6);input();assert(!listMode&&!tour.detail);
 testPad={};input();testPad.Gamepad.bLeftTrigger=255;lastInput=0;input();assert(listMode);
 testPad={};input();testPad.Gamepad.bRightTrigger=255;lastInput=0;input();assert(!listMode);
 testPad={};input();send(10);assert(listMode);testPad.Gamepad.sThumbRY=-25000;testPad.Gamepad.bRightTrigger=255;lastInput=0;input();assert(!listMode);
 assert(Fifa16TrophyRoomUiMode()==1);freeCamera=true;assert(Fifa16TrophyRoomUiMode()==3);freeCamera=false;
 // LB/RB navigate trophies during inspection, preserving detail and zoom.
 auto second=visit;second.slot=15;tour.reset({visit,second},0);tour.details(true,0);pages=1;publicationPending=false;
 camera.inspect.zoom=-12;testPad={};input();
 testPad.Gamepad.wButtons=XINPUT_GAMEPAD_RIGHT_SHOULDER;lastInput=0;input();
 assert(tour.selected()==15&&tour.detail&&!tour.automatic&&!listMode&&camera.inspect.zoom==-12);
 input();assert(tour.selected()==15); // Holding RB cannot skip more cups.
 testPad={};input();testPad.Gamepad.wButtons=XINPUT_GAMEPAD_LEFT_SHOULDER;lastInput=0;input();
 assert(tour.selected()==0&&tour.detail&&!tour.automatic&&!listMode);
 // Simultaneous RT still belongs to zoom and cannot switch to another view.
 testPad={};input();testPad.Gamepad.wButtons=XINPUT_GAMEPAD_RIGHT_SHOULDER;testPad.Gamepad.bRightTrigger=255;lastInput=0;input();
 assert(tour.selected()==15&&tour.detail&&!listMode);
 // Reaching another page retains inspection; Back cancels that pending mode.
 testPad={};input();pages=2;selectedPage=0;send(0);assert(selectedPage==1&&publicationPending&&pageDetail&&pageVisit==1);
 send(6);assert(!pageDetail&&!tour.detail);publicationPending=false;pages=1;
 // Shoulders retain their vertical movement role in free camera.
 freeCamera=true;const auto selection=tour.selected();testPad={};input();testPad.Gamepad.wButtons=XINPUT_GAMEPAD_RIGHT_SHOULDER;lastInput=0;input();assert(tour.selected()==selection&&freeCamera);
 std::cout<<"PASS actual gallery commands: direct collections, view selection, selected cup mapping, history and zoom\n";
}
