#include <cassert>
#include <iostream>
#include "render.cpp"
int main(){
 using namespace clubscene;auto fake=(unsigned char*)VirtualAlloc(nullptr,0x4b00000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);assert(fake);base=(uintptr_t)fake;executable=base;
 unsigned char nodes[4][512]{};const char*name="game/screens/career/server16/ClubBrowser";auto store=[](void*p,uintptr_t v){memcpy(p,&v,8);};store(fake+0x3809030,(uintptr_t)nodes[0]);store(nodes[0]+232,(uintptr_t)nodes[1]);store(nodes[1]+192,(uintptr_t)nodes[2]);store(nodes[2]+136,(uintptr_t)nodes[3]);store(nodes[3]+472,(uintptr_t)name);assert(pageKind()==1);
 alignas(16)unsigned char scene[0xd0]{};store(fake+0x3517c10,(uintptr_t)scene);*(int*)(scene+0x3c)=13;*(float*)(scene+0x88)=1;*(float*)(scene+0x8c)=.5625f;
 unsigned char original[0x84];memcpy(original,scene+0x40,sizeof original);rosterCamera=singleView=mascotCamera=true;roomView=false;playerAngle=0;playerZoom=1;playerHeight=180;playerPan=0;
 camera.apply();assert(std::abs(*(float*)(scene+0x40+48))<.001f);camera.restore();assert(!memcmp(original,scene+0x40,sizeof original));
 auto temp=std::filesystem::temp_directory_path()/(L"mascot-native-"+std::to_wstring(GetCurrentProcessId()));std::filesystem::create_directories(temp);
 clublineup::View worker;worker.configure(temp);worker.child=OpenProcess(SYNCHRONIZE,FALSE,GetCurrentProcessId());assert(worker.running());clubmascot::View view;
 auto ready=[&](const std::string&extra){std::ofstream out(worker.folder/L"status.tsv",std::ios::binary);out<<"schema=1\npid="<<GetCurrentProcessId()<<"\nseq="<<worker.sequence<<"\nclub="<<worker.club<<"\nstatus=ready\nkind=mascot\ncareer="<<worker.career<<"\n"<<extra;};
 view.enter(worker,1043,1043);assert(!requested&&!view.submitted);ready("actor=0\n");view.poll(worker,nullptr);assert(view.ready&&view.error.empty()&&!view.submitted);
 view.enter(worker,111046,1043);std::string bindings="0";for(int i=1;i<96;++i)bindings+=",0";ready("actor=1\nrenderer=native\nheight=180\npages=1\nhash="+std::string(64,'a')+"\nbindings="+bindings+"\n");view.poll(worker,nullptr);assert(view.submitted==worker.sequence);assert(pending&&pending->club==111046&&pending->career==1043&&pending->single&&!pending->animation);
 view.enter(worker,1629,1043);ready("actor=0\n");view.poll(worker,nullptr);assert(!view.submitted&&!requested&&view.ready);
 view.enter(worker,1043,1043);ready("actor=1\nrenderer=native\nheight=180\npages=1\nhash="+std::string(64,'a')+"\nbindings=9\n");view.poll(worker,nullptr);assert(!view.error.empty()&&!view.submitted);
 worker.stop();std::filesystem::remove_all(temp);pending.reset();base=executable=0;VirtualFree(fake,0,MEM_RELEASE);
 std::cout<<"PASS mascot page: centre camera/restoration, own club, missing package hides prior actor, bounded materials\n";
}
