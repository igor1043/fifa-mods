#pragma once
#include "../../../common/room_shadow_bridge.h"
namespace gallery_scene_bridge {
using Begin=void(WINAPI*)(const room_shadow_bridge::Submission*);
using End=void(WINAPI*)(BOOL);
using State=void(WINAPI*)(BOOL,unsigned,unsigned);
using Status=BOOL(WINAPI*)(room_shadow_bridge::Diagnostics*);
inline Begin beginCall=nullptr;inline End endCall=nullptr;inline State stateCall=nullptr;
inline HMODULE module=nullptr;inline unsigned selectedClub=0,selectedGeneration=0;
inline bool visible=false;inline std::atomic<uint64_t> submissions{0};
inline std::atomic<bool> available{false};inline std::atomic<Status> statusCall{nullptr};
inline void resolve(){
 auto found=GetModuleHandleW(L"club_browser.dll");if(found==module)return;module=found;
 beginCall=found?reinterpret_cast<Begin>(GetProcAddress(found,"Fifa16RoomPropShadowBegin")):nullptr;
 endCall=found?reinterpret_cast<End>(GetProcAddress(found,"Fifa16RoomPropShadowEnd")):nullptr;
 stateCall=found?reinterpret_cast<State>(GetProcAddress(found,"Fifa16TrophyPropShadowState")):nullptr;
 statusCall=found?reinterpret_cast<Status>(GetProcAddress(found,"Fifa16TrophyPropRenderStatus")):nullptr;
 available=beginCall&&endCall&&stateCall;
}
inline void state(bool show,unsigned club,unsigned generation){
 resolve();visible=show;selectedClub=club;selectedGeneration=generation;
 if(stateCall)stateCall(show,club,generation);
}
inline bool casts(const std::string& key,bool alpha,bool baked){
 if(alpha||baked)return false;
 for(const char* name:{"surface_stone","surface_ceiling","surface_wall","surface_case_back","surface_joint"})if(key==name)return false;
 return key.rfind("loading_",0)!=0;
}
inline void begin(uintptr_t object,unsigned index,uintptr_t instance,bool caster){
 if(!visible||!stateCall||!beginCall||!endCall)return;
 room_shadow_bridge::Submission packet;packet.club=selectedClub;packet.generation=selectedGeneration;
 packet.object=object;packet.instance=index;packet.frame=++submissions;
 packet.reserved=room_shadow_bridge::Gallery|room_shadow_bridge::Overlay|(caster?0:room_shadow_bridge::TextureOnly);
 const auto device=get<uintptr_t>(image+0x36140b0),native=get<uintptr_t>(device+0x758);
 packet.context=reinterpret_cast<void*>(get<uintptr_t>(native+0x3520));
 if(!read(instance,packet.model,sizeof packet.model)||!read(image+0x3614180,packet.viewProjection,sizeof packet.viewProjection))return;
 beginCall(&packet);
}
inline void end(bool publish=true){if(endCall)endCall(publish);}
inline void diagnostics(const fs::path& folder){
 room_shadow_bridge::Diagnostics d;const auto readStatus=statusCall.load();const bool ok=readStatus&&readStatus(&d);
 std::ofstream file(folder/L"render_status.json.new");
 file<<"{\"pid\":"<<GetCurrentProcessId()<<",\"available\":"<<(available?"true":"false")<<",\"valid\":"<<(ok?"true":"false")
     <<",\"owner\":"<<d.owner<<",\"meshes\":"<<d.meshes<<",\"instances\":"<<d.instances<<",\"submissions\":"<<submissions
     <<",\"shadow_frames\":"<<d.shadowFrames<<",\"shadow_builds\":"<<d.shadowBuilds<<",\"shadow_failures\":"<<d.shadowFailures
     <<",\"reflection_frames\":"<<d.reflectionFrames<<",\"reflection_failures\":"<<d.reflectionFailures<<",\"reflection_targets\":"<<d.reflectionTargets<<"}\n";
 file.close();MoveFileExW((folder/L"render_status.json.new").c_str(),(folder/L"render_status.json").c_str(),MOVEFILE_REPLACE_EXISTING);
}
}
