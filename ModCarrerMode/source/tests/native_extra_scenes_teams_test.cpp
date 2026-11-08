// Exercise the production actor selection with private simulation/render data.
// No game process, game callbacks, saves or global club assets are modified.
#include "../native_mods/extra_scenes/extra_scenes.cpp"
#include <cassert>
#include <vector>

template<class T>static void put(uintptr_t at,const T& value){std::memcpy(reinterpret_cast<void*>(at),&value,sizeof value);}
static void readyActor(unsigned index,const Actor& actor,uint64_t now){
 readiness[index].reset();
 readiness[index].observe(index+1,1,now-200,&actor);
 readiness[index].observe(index+1,2,now-100,&actor);
 readiness[index].observe(index+1,3,now,&actor);
}
int main(){
 auto* simulated=VirtualAlloc(nullptr,0x3518000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);assert(simulated);
 image=reinterpret_cast<uintptr_t>(simulated);
 std::vector<unsigned char> manager(32),game(0xdb000),teams(16),nativeHome(64),nativeAway(64),renderer(0x120000);
 put(image+0x3517420,reinterpret_cast<uintptr_t>(manager.data()));
 put(reinterpret_cast<uintptr_t>(manager.data())+16,reinterpret_cast<uintptr_t>(game.data()));
 const uintptr_t frame=reinterpret_cast<uintptr_t>(game.data());
 put(frame+0xda840,0);put(frame+0xe30,reinterpret_cast<uintptr_t>(teams.data()));
 SceneActorSnapshot snapshot{};snapshot.renderer=reinterpret_cast<uintptr_t>(renderer.data());
 for(int side=0;side<2;++side){
  const uintptr_t native=reinterpret_cast<uintptr_t>(side?nativeAway.data():nativeHome.data());
  put(reinterpret_cast<uintptr_t>(teams.data())+side*8,native);put(native,side);
  const Vec feet{side?900.f:-900.f,0,-3700};put(native+0x10,feet*(1.f/30.48f));
  const uintptr_t palette=snapshot.renderer+static_cast<uintptr_t>(side)*0xe00+0xe7e0;
  put(snapshot.renderer+static_cast<uintptr_t>(side)*0xe00+0xf5d0,static_cast<unsigned char>(1));
  put(palette+64+48,feet);
  float head[16]{};head[6]=1;head[12]=feet.x;head[13]=170;head[14]=feet.z;
  std::memcpy(reinterpret_cast<void*>(palette+14*64),head,sizeof head);
 }
 // No selected-player/control data exists: coaches are identified by team,
 // not by possession, the camera's focus, or whether the user plays away.
 Config config;config.views[1]=0;config.weights[1]=0;
 randomizer=SceneRandom(1043);pendingPreview=false;
 unsigned selected[2]{};
 for(unsigned i=0;i<1000;++i){
  const auto now=GetTickCount64();Actor actors[2]{};
  for(int side=0;side<2;++side){assert(coach(snapshot,side,actors[side]));readyActor(side,actors[side],now);}
  Camera camera{};Actor subject{};assert(choose(config,snapshot,camera,subject));
  assert(coachTeam>=0&&coachTeam<2);++selected[coachTeam];assert(subject.root.x==actors[coachTeam].root.x);
  const int pinned=coachTeam;
  put(frame+0xb90,uintptr_t(0xffffffff)); // Native focus changes during a cut.
  Actor continued{};assert(coach(snapshot,pinned,continued));assert(continued.root.x==subject.root.x);
 }
 assert(selected[0]>400&&selected[1]>400);
 for(int side=0;side<2;++side){
  config.coachTeam=side+1;Camera camera{};Actor subject{};
  assert(choose(config,snapshot,camera,subject));assert(coachTeam==side);
 }
 config.coachTeam=0;
 // An unbuilt away model cannot be selected; the ready home coach remains.
 put(snapshot.renderer+0xe00+0xf5d0,static_cast<unsigned char>(0));
 readiness[1].reset();Actor away{};assert(!coach(snapshot,1,away));
 for(unsigned i=0;i<20;++i){
  Actor home{};assert(coach(snapshot,0,home));readyActor(0,home,GetTickCount64());
  Camera camera{};Actor subject{};assert(choose(config,snapshot,camera,subject));assert(coachTeam==0);
 }
 config.coachTeam=2;Camera camera{};Actor subject{};assert(!choose(config,snapshot,camera,subject));
 // Mascot is still the existing home snapshot, irrespective of coach scope.
 config.views[0]=0;config.views[1]=3;config.weights[0]=0;config.weights[1]=1;
 snapshot.mascotValid=1;snapshot.mascotPosition[0]=-5850;snapshot.mascotPosition[2]=2700;
 snapshot.mascotHead[4]=1;snapshot.mascotHead[13]=190;
 Actor mascotActor{};assert(mascot(snapshot,mascotActor));readyActor(2,mascotActor,GetTickCount64());
 assert(choose(config,snapshot,camera,subject));assert(currentShot>=2&&subject.root.x==-5850);
 snapshot.mascotValid=0;assert(!mascot(snapshot,subject));
 assert(VirtualFree(simulated,0,MEM_RELEASE));
 std::printf("PASS production selector: home=%u away=%u; fixed subject; absent-model fallback; home-only mascot preserved\n",selected[0],selected[1]);
}
