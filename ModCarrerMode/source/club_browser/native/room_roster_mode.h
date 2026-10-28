#pragma once
#include <atomic>
#include <cstring>
namespace clubs {
inline bool isDressingRoomPage(const char* name){return name&&!std::strcmp(name,"game/screens/career/server16/DressingRoom");}
struct RoomRosterMode {
 std::atomic<int> club{0};
 bool open(const char* page,int career){if(!isDressingRoomPage(page)||career<=0||career>=500000)return false;club=career;return true;}
 void close(){club=0;}
 bool visible(const char* page,int career)const{return isDressingRoomPage(page)&&career>0&&club.load()==career;}
};
inline RoomRosterMode roomRosterMode;
struct RosterOrigin{float x,y,z;};
inline RosterOrigin rosterOrigin(bool indoor){return indoor?RosterOrigin{100000.f,1000.f,100.f}:RosterOrigin{0,0,0};}
}
