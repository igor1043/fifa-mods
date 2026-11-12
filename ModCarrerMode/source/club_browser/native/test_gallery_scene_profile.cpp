#include "indoor_scene_profile.h"
#include "../../club_environment/trophy_room/native/gallery_material.h"
#include <cassert>
#include <string>
#include <vector>
#include <iostream>
#include <xmmintrin.h>
#include <cstdint>
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
// Reproduce the native query's aligned packed-SSE read, rather than only
// checking specular slot names. Extra caller locals must not change this ABI.
__declspec(noinline) float nativeLightQuery(const float* point){
 alignas(16) float result[4];
 _mm_store_ps(result,_mm_sub_ps(_mm_set1_ps(200.f),_mm_load_ps(point)));
 return result[0]+result[1]+result[2]+result[3];
}
bool rejectsMisalignedQuery(const float* point){
 __try{volatile auto result=nativeLightQuery(point);(void)result;return false;}
 __except(GetExceptionCode()==EXCEPTION_ACCESS_VIOLATION?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return true;}
}
int main(){
 using namespace room_shadow_bridge;indoor_profile::Ownership owner;
 assert(owner.accept(DressingRoom,true));assert(owner.accept(TrophyGallery,true));
 assert(!owner.accept(DressingRoom,false)&&!owner.accept(DressingRoom,true));
 assert(owner.owner==TrophyGallery);assert(owner.accept(TrophyGallery,false));assert(owner.accept(DressingRoom,true));
 assert(indoor_profile::originX(Gallery)==-100000&&indoor_profile::originX(0)==100000);
 assert(indoor_profile::lightCount(Gallery)==26&&indoor_profile::lightCount(0)==39);
 for(unsigned i=0;i<26;++i){const auto s=indoor_profile::source(i,Gallery);assert(s.y>250&&s.y<310&&std::abs(s.x)<=572&&std::abs(s.z)<=630);}
 std::vector<std::string> slots;
 auto bind=[&](const char* name){slots.emplace_back(name);};
 gallery_material::bindSpecular(true,true,bind);assert((slots==std::vector<std::string>{"INDIRECT_SPECULAR_TEXTURE","envSpecTexture"}));
 slots.clear();gallery_material::bindSpecular(false,true,bind);assert((slots==std::vector<std::string>{"INDIRECT_SPECULAR_TEXTURE"}));
 slots.clear();gallery_material::bindSpecular(true,false,bind);assert(slots.empty());
 gallery_material::bindSpecular(true,true,bind,true);assert(slots.empty());
 gallery_material::bindSpecular(false,true,bind,true);assert(slots==std::vector<std::string>{"INDIRECT_SPECULAR_TEXTURE"});
 struct QueryFrame {char before[9];gallery_material::LightSample point;char after[13];} query{};
 assert(reinterpret_cast<std::uintptr_t>(query.point.value)%16==0);
 assert(nativeLightQuery(query.point.value)==649.f);
 alignas(16) float unsafe[8]{};
 assert(rejectsMisalignedQuery(unsafe+1));
 std::cout<<"PASS gallery scene isolation, exact ceiling lights, original dressing-room profile and trophy metal environment bindings\n";
 std::cout<<"PASS native illumination query ABI: 16-byte position alignment and packed SSE read\n";
}
