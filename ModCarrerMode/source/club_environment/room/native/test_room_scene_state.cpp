// Exercise the production camera against owned memory; no FIFA or hook needed.
#include <cassert>
#include <iostream>
#include "native_dressing_room_20261022.cpp"
int main(){
 auto storage=VirtualAlloc(nullptr,0x3600000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);assert(storage);image=(uintptr_t)storage;
 alignas(16)unsigned char scene[0xd0]{};auto pointer=(uintptr_t)scene;memcpy((char*)storage+0x3517c10,&pointer,8);
 float x=1,y=.5625f;memcpy(scene+0x88,&x,4);memcpy(scene+0x8c,&y,4);unsigned char original[sizeof scene]{};
 for(int state:{1,13}){
  backgroundClub=1043;memcpy(scene+0x3c,&state,4);memcpy(original,scene,sizeof scene);
  for(unsigned frame=0;frame<300;++frame){camera.apply(true);assert(!camera.scene);assert(!memcmp(scene,original,sizeof scene));}
  backgroundClub=0;
  memcpy(scene+0x3c,&state,4);memcpy(original,scene,sizeof scene);camera.apply(true);assert(camera.scene==pointer);assert(get<float>(pointer+0x40+48)==100000.f);assert(get<float>(pointer+0x40+52)>1000.f);
  camera.restore();assert(!memcmp(scene,original,sizeof scene));
 }
 // Loading/loaded camera transitions must preserve the physical aspect and
 // restore the native projection exactly, including ultrawide resolutions.
 for(float aspect:{16.f/9,21.f/9,32.f/9}){
  int state=13;memcpy(scene+0x3c,&state,4);float y=.5625f,x=aspect*y;memcpy(scene+0x88,&x,4);memcpy(scene+0x8c,&y,4);
  memcpy(original,scene,sizeof scene);
  for(unsigned frame=0;frame<300;++frame){camera.apply(true);assert(std::abs(get<float>(pointer+0x88)/get<float>(pointer+0x8c)-aspect)<.00001f);camera.restore();assert(!memcmp(scene,original,sizeof scene));}
 }
 for(int state:{0,2,5,8,9,12,-1}){
  memcpy(scene+0x3c,&state,4);memcpy(original,scene,sizeof scene);camera.apply(true);assert(!camera.scene);assert(!memcmp(scene,original,sizeof scene));
 }
 int state=13;memcpy(scene+0x3c,&state,4);float invalid=0;memcpy(scene+0x8c,&invalid,4);memcpy(original,scene,sizeof scene);camera.apply(true);assert(!camera.scene&&!memcmp(scene,original,sizeof scene));
 // A hub/card transition hides the room without discarding its loaded props.
 residentClub=1043;roomRequested=false;const auto ambient=indoorAmbient.load(),power=indoorSpotPower.load();poll();
 assert(residentClub==1043&&indoorAmbient==ambient&&indoorSpotPower==power);
 componentClub=1043;validCareerClub=1043;backgroundClub=1043;roomRequested=true;roomPresentedReady=true;active=false;fault=0;holdDrawing=false;
 scene_loading::Status status;assert(Fifa16RoomLoadingStatus(&status)&&status.ready&&status.club==1043);
 assert((status.variant&255)==(4|scene_loading::RoomPreparation)&&scene_loading::roomStage(status)==1);
 roomRequested=false;assert(Fifa16RoomLoadingStatus(&status)&&!status.ready);
 image=0;VirtualFree(storage,0,MEM_RELEASE);std::cout<<"PASS actual room camera: panorama during preparation; states 1/13; exact restoration; resident props, lights and ready status survive hub/card handoff\n";
}
