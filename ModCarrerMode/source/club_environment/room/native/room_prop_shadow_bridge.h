#pragma once
#include "../../../common/room_shadow_bridge.h"
namespace room_prop_bridge {
using Begin=void(WINAPI*)(const room_shadow_bridge::Submission*);
using End=void(WINAPI*)(BOOL);
using State=void(WINAPI*)(BOOL,unsigned,unsigned);
inline Begin beginCall=nullptr;inline End endCall=nullptr;inline State stateCall=nullptr;
inline HMODULE module=nullptr;inline unsigned club=0,generation=0,flags=0;
inline void resolve(){
 auto found=GetModuleHandleW(L"club_browser.dll");if(found==module)return;module=found;
 beginCall=found?reinterpret_cast<Begin>(GetProcAddress(found,"Fifa16RoomPropShadowBegin")):nullptr;
 endCall=found?reinterpret_cast<End>(GetProcAddress(found,"Fifa16RoomPropShadowEnd")):nullptr;
 stateCall=found?reinterpret_cast<State>(GetProcAddress(found,"Fifa16RoomPropShadowState")):nullptr;
}
inline void state(bool visible,unsigned selectedClub,unsigned selectedGeneration,unsigned modeFlags=0){
 resolve();club=selectedClub;generation=selectedGeneration;flags=modeFlags;
 if(stateCall)stateCall(visible,club,generation);
}
inline void begin(uintptr_t object,unsigned index,uintptr_t instance,unsigned casterFlags=0){
 if(!beginCall||!endCall)return;
 room_shadow_bridge::Submission packet;packet.club=club;packet.generation=generation;packet.frame=frames.load();packet.reserved=flags|casterFlags;packet.object=object;packet.instance=index;
 auto device=get<uintptr_t>(image+0x36140b0),native=get<uintptr_t>(device+0x758);
 packet.context=reinterpret_cast<void*>(get<uintptr_t>(native+0x3520));
 if(!read(instance,packet.model,64)||!read(image+0x3614180,packet.viewProjection,64))return;
 beginCall(&packet);
}
inline void end(bool publish=true){if(endCall)endCall(publish);}
}
