// Production capture/consumer against owned memory. Does not attach to FIFA.
#include <cassert>
#include <iostream>
#include "native_dressing_room_20261022.cpp"
int main(){
 image=reinterpret_cast<uintptr_t>(VirtualAlloc(nullptr,0x3900000,MEM_RESERVE,PAGE_READWRITE));assert(image);
 assert(VirtualAlloc(reinterpret_cast<void*>(image+0x3809000),4096,MEM_COMMIT,PAGE_READWRITE));
 unsigned char nodes[0x1500]{};*reinterpret_cast<void**>(image+0x3809030)=nodes;
 *reinterpret_cast<void**>(nodes+232)=nodes+0x400;*reinterpret_cast<void**>(nodes+0x400+192)=nodes+0x800;
 *reinterpret_cast<void**>(nodes+0x800+136)=nodes+0xc00;*reinterpret_cast<void**>(nodes+0xc00+472)=nodes+0x1000;
 auto name=reinterpret_cast<char*>(nodes+0x1000);strcpy_s(name,128,roomPage);
 wchar_t temp[MAX_PATH]{};GetTempPathW(MAX_PATH,temp);folder=fs::path(temp)/(L"Room direct input "+std::to_wstring(GetCurrentProcessId()));
 fs::create_directories(folder/L"runtime");logfile=folder/L"test.log";validCareerClub=componentClub=1629;
 // Only pause/resume commands need no native geometry.
 for(unsigned entry=0;entry<6;++entry){
  std::ofstream scope(folder/L"runtime/room_control_scope.txt");scope<<"S16ROOMSCOPE 1 "<<GetCurrentProcessId()<<" 1629 0123456789abcdef\n";scope.close();
  const auto command="S16ROOM2|1629|0123456789abcdef|"+std::to_string(entry+1)+"|-2|ENDROOM";
  const auto began=GetTickCount64();assert(captureRoomSceneCommand(command.c_str()));camera.controlNext=0;camera.control();
  assert(camera.controlSequence==entry+1&&camera.director.paused);assert(GetTickCount64()-began<1000);
  assert(!captureRoomSceneCommand(command.c_str()));
  strcpy_s(name,128,"game/screens/fluxHub/FluxHub");assert(!captureRoomSceneCommand(("S16ROOM2|1629|0123456789abcdef|"+std::to_string(entry+20)+"|-3|ENDROOM").c_str()));strcpy_s(name,128,roomPage);
 }
 assert(!captureRoomSceneCommand("S16ROOM2|1043|0123456789abcdef|80|-3|ENDROOM"));
 assert(!captureRoomSceneCommand("S16ROOM2|1629|fedcba9876543210|80|-3|ENDROOM"));
 std::ofstream scope(folder/L"runtime/room_control_scope.txt");scope<<"S16ROOMSCOPE 1 12345 1629 0123456789abcdef\n";scope.close();
 assert(!captureRoomSceneCommand("S16ROOM2|1629|0123456789abcdef|80|-3|ENDROOM"));
 VirtualFree(reinterpret_cast<void*>(image),0,MEM_RELEASE);image=0;
 std::cout<<"PASS production room event: six first-click/re-entry commands, duplicate/stale PID/club/nonce/page rejected; owner-frame consumer immediate\n";
}
