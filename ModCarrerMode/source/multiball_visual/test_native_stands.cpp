// Execute the production scene callback against a private simulated native scene.
// No FIFA process is opened, injected, or modified by this executable.
#include "standball.cpp"
#include <assert.h>

alignas(16) static unsigned char testOwner[0x50000],testModels[2][0x38],testStates[2][0x80];
static uintptr_t testVtable[16],modelPointers[2];
static unsigned char testLua[256],testGlobals[256],originalRecord[0x50];
static unsigned modelLoads=0,builds=0,consoleCalls=0,extraCount=0;
static float submittedY=0;
static bool previousHidden=true;
static unsigned char* state(void* self){uintptr_t p=0;memcpy(&p,(unsigned char*)self+16,8);return (unsigned char*)p;}
static unsigned char __fastcall initialized(void* self){return state(self)[0x4a];}
static unsigned char __fastcall loadedFlag(void* self){return state(self)[0x48];}
static unsigned char __fastcall lods(void* self){return state(self)[0x49];}
static void __fastcall initialize(void* self,const int*){state(self)[0x4a]=1;}
static void __fastcall load(void* self,int){
 auto s=state(self);s[0x4a]=1;s[0x48]=s[0x49]=0;
 if(self==testModels[1]){assert(previousHidden);++modelLoads;}
}
static void __fastcall notification(void* self){assert(state(self)[0x49]);state(self)[0x48]=1;}
static void __fastcall script(const char* text,size_t length,const char*){assert(text&&length);++consoleCalls;}
static void __fastcall build(void* self){
 ++builds;Vector v{};memcpy(&v,(unsigned char*)self+0x30*(17+0x2f),sizeof(v));
 extraCount=(unsigned)((v.end-v.begin)/0x50)-1;
 if(extraCount){
  assert(extraCount==13);
  for(unsigned i=0;i<extraCount;++i){
   auto record=(unsigned char*)(v.begin+(i+1)*0x50);float p[4];memcpy(p,record+0x20,16);
   assert(p[0]==ball_positions[i][0]&&p[2]==ball_positions[i][2]);assert(record[0x42]==1);
   if(i)assert(p[1]==submittedY);submittedY=p[1];
   uint16_t binding=(uint16_t)(i+20);memcpy(record+0x40,&binding,2);
  }
  previousHidden=submittedY<-1000;
 }
}
static void entry(uintptr_t offset,void* function){
 unsigned char* p=(unsigned char*)(image+offset);const unsigned char j[6]={0xff,0x25,0,0,0,0};
 memcpy(p,j,6);memcpy(p+6,&function,8);
}
static void complete(){for(auto& s:testStates){s[0x49]=1;s[0x48]=0;}}
int main(int argc,char** argv){
 assert(argc==2);strcpy_s(gameRoot,argv[1]);
 for(unsigned i=0;i<sizeof(standAssets)/sizeof(standAssets[0]);++i)assert(validate((int)i));
 assert(!checkFile(standAssets[0].slug,"model.rx3",standAssets[0].modelBytes,standAssets[0].textureHash));
 image=(uintptr_t)VirtualAlloc(nullptr,0x5000000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);assert(image);
 entry(0x43b4500,(void*)initialized);entry(0x43b4520,(void*)loadedFlag);entry(0x43b43e0,(void*)lods);
 entry(0x43b4640,(void*)initialize);entry(0x43b4530,(void*)load);entry(0x43b47c0,(void*)notification);entry(0x4ac35e0,(void*)script);
 const uintptr_t lua=(uintptr_t)testLua,globals=(uintptr_t)testGlobals;int tag=5;
 memcpy((void*)(image+0x3613fd0),&lua,8);memcpy(testLua+0x78,&globals,8);memcpy(testLua+0x80,&tag,4);
 testVtable[7]=image+0x43b4530;
 for(unsigned i=0;i<2;++i){uintptr_t vt=(uintptr_t)testVtable,s=(uintptr_t)testStates[i];uint16_t type=17,variation=(uint16_t)i;unsigned rna=42;
  memcpy(testModels[i],&vt,8);memcpy(testModels[i]+12,&type,2);memcpy(testModels[i]+14,&variation,2);memcpy(testModels[i]+16,&s,8);memcpy(testStates[i]+0x4c,&rna,4);modelPointers[i]=(uintptr_t)testModels[i];
 }
 Vector prototypes={(uintptr_t)modelPointers,(uintptr_t)(modelPointers+2),(uintptr_t)(modelPointers+2)};
 memcpy(testOwner+0x30*18,&prototypes,sizeof(prototypes));
 Vector original={(uintptr_t)originalRecord,(uintptr_t)originalRecord+0x50,(uintptr_t)originalRecord+0x50};
 const size_t list=0x30*(17+0x2f);memcpy(testOwner+list,&original,sizeof(original));
 originalRecord[0x42]=1;unsigned originalMask=0x1234;memcpy(testOwner+0x4f604,&originalMask,4);
 nextBuild=build;nextScene=UINT64_MAX;luaLifecycle.nextCheck=UINT64_MAX;luaLifecycle.ready=true;
 desired=asset("brasileirao");visible=true;resetRecords();
 buildHook(testOwner);assert(modelLoads==1&&extraCount==0&&standball_height()==11.1252f);
 assert(originalRecord[0x42]==0);assert(modelCycle.requested&&shadowCycle.requested);
 complete();buildHook(testOwner);assert(extraCount==13&&submittedY==0);assert(standball_height()==standAssets[desired].ballHeight);
 assert(!memcmp(testOwner+list,&original,sizeof(original)));unsigned mask=0;memcpy(&mask,testOwner+0x4f604,4);assert(mask==originalMask);
 const unsigned loads=modelLoads;desired=asset("cbf");buildHook(testOwner);
 assert(modelLoads==loads&&submittedY==-3000&&loaded==-1&&standball_height()==11.1252f);
 buildHook(testOwner);assert(modelLoads==loads+1&&extraCount==0&&loaded==desired);
 complete();buildHook(testOwner);assert(submittedY==0&&standball_height()==standAssets[desired].ballHeight);
 visible=false;buildHook(testOwner);assert(submittedY==-3000&&standball_height()==11.1252f);
 visible=true;buildHook(testOwner);assert(submittedY==0&&modelLoads==loads+1);
 testStates[1][0x4a]=testStates[1][0x48]=testStates[1][0x49]=0;previousHidden=true;
 buildHook(testOwner);assert(extraCount==0&&standball_height()==11.1252f&&modelLoads==loads+2);
 complete();buildHook(testOwner);assert(extraCount==13&&submittedY==0);
 stopping=1;buildHook(testOwner);assert(submittedY==-3000&&standball_height()==11.1252f);
 assert(consoleCalls==modelLoads);VirtualFree((void*)image,0,MEM_RELEASE);
 printf("PASS native callback: SHA-256 assets, 13 bindings, ground fallback, async load, hide before model switch, resource reload, pause resume, stop; builds=%u\n",builds);
}
