// Exercise the production camera against owned memory; no FIFA or hook needed.
#include <cassert>
#include <iostream>
#include "native_dressing_room_20261022.cpp"
int main(){
 auto storage=VirtualAlloc(nullptr,0x3600000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);assert(storage);image=(uintptr_t)storage;
 alignas(16)unsigned char scene[0xd0]{};auto pointer=(uintptr_t)scene;memcpy((char*)storage+0x3517c10,&pointer,8);
 float x=1,y=.5625f;memcpy(scene+0x88,&x,4);memcpy(scene+0x8c,&y,4);unsigned char original[sizeof scene]{};
 for(int state:{1,13}){
  memcpy(scene+0x3c,&state,4);memcpy(original,scene,sizeof scene);camera.apply(true);assert(camera.scene==pointer);assert(get<float>(pointer+0x40+48)==100000.f);assert(get<float>(pointer+0x40+52)>1000.f);
  camera.restore();assert(!memcmp(scene,original,sizeof scene));
 }
 for(int state:{0,2,5,8,9,12,-1}){
  memcpy(scene+0x3c,&state,4);memcpy(original,scene,sizeof scene);camera.apply(true);assert(!camera.scene);assert(!memcmp(scene,original,sizeof scene));
 }
 int state=13;memcpy(scene+0x3c,&state,4);float invalid=0;memcpy(scene+0x8c,&invalid,4);memcpy(original,scene,sizeof scene);camera.apply(true);assert(!camera.scene&&!memcmp(scene,original,sizeof scene));
 image=0;VirtualFree(storage,0,MEM_RELEASE);std::cout<<"PASS actual room camera: states 1/13; other states and invalid projection rejected; exact restoration\n";
}
