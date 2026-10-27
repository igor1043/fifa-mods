#include <cassert>
#include <iostream>
#include "render.cpp"
int main(){
 _set_error_mode(_OUT_TO_STDERR);using namespace clubscene;auto fake=(unsigned char*)VirtualAlloc(nullptr,0x4b00000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);assert(fake);base=(uintptr_t)fake;
 unsigned char nodes[4][512]{};const char*name="game/screens/career/server16/ClubBrowser";auto store=[](void*p,uintptr_t v){memcpy(p,&v,8);};store(fake+0x3809030,(uintptr_t)nodes[0]);store(nodes[0]+232,(uintptr_t)nodes[1]);store(nodes[1]+192,(uintptr_t)nodes[2]);store(nodes[2]+136,(uintptr_t)nodes[3]);store(nodes[3]+472,(uintptr_t)name);
 alignas(16)unsigned char scene[0xd0]{},lua[0x90]{},obj[0x38]{},impl[0x40]{},ctx[0x10]{};
 store(fake+0x3517c10,(uintptr_t)scene);store(fake+0x3613fd0,(uintptr_t)lua);*(int*)(lua+0x80)=5;*(int*)(scene+0x3c)=13;*(float*)(scene+0x88)=1;*(float*)(scene+0x8c)=.5625f;
 object=(uintptr_t)obj;store(obj,(uintptr_t)vtable);store(obj+0x20,(uintptr_t)impl);store(obj+0x30,(uintptr_t)ctx);store(ctx+8,object);*(unsigned*)(impl+0x38)=1;
 // The isolated callback stubs replace only this test allocation, never FIFA.
 for(unsigned offset:{0x4ad80b0u,0x43c9960u}){fake[offset]=0xc3;DWORD old;assert(VirtualProtect(fake+(offset&~4095u),4096,PAGE_EXECUTE_READ,&old));}FlushInstructionCache(GetCurrentProcess(),fake,0x4b00000);
 Assets a;a.sequence=12;a.club=a.career=1043;a.hash=std::string(64,'a');a.pages=1;loading=std::make_shared<const Assets>(a);readySequence=requestSequence=12;requested=active=true;drawObject=object;displayedClub=1043;phase=3;
 careerReader=[](){if(!active||drawObject.load()!=object||displayedClub!=1043){std::cerr<<"FAIL published draw was hidden during an unchanged native frame\n";std::exit(1);}return 1043;};
 for(int i=0;i<2000;++i){tick();assert(active&&drawObject==object&&displayedClub==1043);camera.restore();}
 careerReader=[](){return 1043;};rosterCamera=true;singleView=true;playerAngle=.7f;playerZoom=1.6f;playerPan=.1f;playerHeight=185;camera.apply();unsigned char fixed[64];memcpy(fixed,scene+0x40,64);camera.restore();requested=false;tick();assert(camera.scene&&memcmp(scene+0x40,fixed,64)==0);camera.restore();auto loaded=loading;loading.reset();tick();assert(camera.scene&&memcmp(scene+0x40,fixed,64)==0);camera.restore();loading=loaded;rosterCamera=false;singleView=false;
 careerReader=[](){return 1043;};requested=false;tick();assert(!active&&!drawObject&&!displayedClub);camera.restore();requested=true;tick();assert(active&&drawObject==object);camera.restore();
 // Reapplying the borrowed camera must not overwrite the restoration baseline.
 camera.restore();unsigned char baseline[0x84];memcpy(baseline,scene+0x40,sizeof baseline);rosterCamera=true;for(int i=0;i<120;++i){playerAngle=float(i)*.01f;camera.apply();}camera.restore();assert(!memcmp(baseline,scene+0x40,sizeof baseline));rosterCamera=false;
 *(int*)(scene+0x3c)=8;tick();assert(!active&&!drawObject);*(int*)(scene+0x3c)=13;tick();assert(active);camera.restore();
 careerReader=[](){return 1629;};tick();assert(!active&&!drawObject);careerReader=[](){return 1043;};tick();assert(active);camera.restore();
 store(nodes[3]+472,(uintptr_t)"game/screens/fluxHub/FluxHub");tick();assert(!active&&!drawObject&&!displayedClub);
 loading.reset();object=base=0;VirtualFree(fake,0,MEM_RELEASE);std::cout<<"PASS native scene publication: stable throughout 2000 unchanged frames; hide on exit, unavailable scene, career change and explicit back\n";return 0;
}
