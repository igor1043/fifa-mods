// Native prop rendering with a private neutral indoor SH buffer. All meshes,
// materials, resource mapping and submissions still use FIFA's own pipeline.
// No global stadium illumination or original game object's data is changed.
struct alignas(16) RoomDrawArgs {
 float color[4];uintptr_t object;int instance;unsigned padding;
 uintptr_t buffer,view;float sphere[4];
};
static_assert(sizeof(RoomDrawArgs)==64);
std::atomic<unsigned> indoorUploads{0},indoorFailures{0};
bool indoorEnabled=true;
std::atomic<float> indoorAmbient{.65f};
void nativeRef(uintptr_t p,bool add){if(p)((void(__fastcall*)(void*))get<uintptr_t>(get<uintptr_t>(p)+(add?0:8)))((void*)p);}
bool uploadIndoor(uintptr_t buffer){
 auto device=get<uintptr_t>(image+0x36140b0);if(!device||!buffer)return false;
 uintptr_t context=0;
 ((void(__fastcall*)(void*,uintptr_t*))get<uintptr_t>(get<uintptr_t>(device)+0x30))((void*)device,&context);
 if(!context)return false;
 struct Mapped {void*data;uint64_t row;uint32_t depth;uint32_t padding;};Mapped mapped{};
 // Native critical section also used by the original lighting upload.
 ((void(__fastcall*)())(image+0x4abd6b0))();
 bool ok=false;
 __try {
 nativeRef(buffer,true);
 ((void(__fastcall*)(void*,void*,void*,unsigned,Mapped*))get<uintptr_t>(get<uintptr_t>(context)+0x340))((void*)context,(void*)buffer,(void*)(image+0x35b0e80),4,&mapped);
 nativeRef(buffer,false);
 ok=mapped.data!=nullptr;
 if(ok){
  alignas(16)float coefficients[28]{};
  // Native CPU sampler stores R[9], G[9], B[9], then one pad float.
  // The previous seven-vector packing put directional terms into the wrong channels.
  const float l0=indoorAmbient.load()/0.2820947918f;coefficients[0]=l0;coefficients[9]=l0;coefficients[18]=l0;
  ok=write((uintptr_t)mapped.data,coefficients,sizeof coefficients);
  nativeRef(buffer,true);
  ((void(__fastcall*)(void*,void*,void*,Mapped*))get<uintptr_t>(get<uintptr_t>(context)+0x348))((void*)context,(void*)buffer,(void*)(image+0x35b0e80),&mapped);
  nativeRef(buffer,false);
 }
 } __finally {((void(__fastcall*)())(image+0x4abe9f0))();nativeRef(context,false);}
 if(ok)++indoorUploads;else ++indoorFailures;return ok;
}
void __fastcall indoorMesh(void*mesh,void*material,RoomDrawArgs*args){
 ((void(__fastcall*)(void*,int,void*))(image+0x4431720))((void*)args->object,args->instance,material);
 uintptr_t buffer=args->buffer,specular=0;nativeRef(buffer,true);
 auto manager=((void*(__fastcall*)())(image+0x4405da0))();
 ((void(__fastcall*)(void*,const float*,uintptr_t*,uintptr_t*))(image+0x4405dc0))(manager,args->sphere,&buffer,&specular);
 // The original updater consumes its temporary buffer reference.
 if(indoorEnabled)uploadIndoor(args->buffer);
 ((void(__fastcall*)(void*,const char*,const char*,void*))(image+0x4acdd30))(material,"","INDIRECT_SPECULAR_TEXTURE",(void*)specular);
 ((void(__fastcall*)(void*,const char*,const char*,void*))(image+0x4acdba0))(material,"","in_sh_data",(void*)args->view);
 ((void(__fastcall*)(void*,const char*,const char*,const float*,int))(image+0x4ace000))(material,"","overlayColor",args->color,1);
 ((void(__fastcall*)(void*,int,int,void*))(image+0x4acbd90))(material,-1,0,nullptr);
 ((void(__fastcall*)(void*,void*,int,int,void*))(image+0x4ade9a0))(mesh,material,0,0,nullptr);nativeRef(specular,false);
}
void nativeIndoorDraw(void*self){
 const auto o=(uintptr_t)self,vt=get<uintptr_t>(o),ctx=get<uintptr_t>(o+0x30);
 const int count=((int(__fastcall*)(void*))(image+0x4ad7a60))(self);
 if(count<0||count>64)return;
 for(int i=0;i<count;++i){
  auto instance=((uintptr_t(__fastcall*)(void*,int))get<uintptr_t>(vt+0xe0))(self,i);if(!instance)continue;
  ((void(__fastcall*)(void*))(image+0x4abe600))((void*)instance);
  RoomDrawArgs args{};read(get<uintptr_t>(ctx)+i*16,args.color,16);args.object=o;args.instance=i;
  args.buffer=get<uintptr_t>(ctx+0x18);args.view=get<uintptr_t>(ctx+0x20);read(instance+0x30,args.sphere,16);
  nativeRef(args.buffer,true);nativeRef(args.view,true);
  const int lods=((int(__fastcall*)(void*))(image+0x4ad7a00))(self);
  for(int lod=0;lod<lods&&lod<4;++lod){auto composite=((void*(__fastcall*)(void*,int))get<uintptr_t>(vt+0x88))(self,lod);
   ((void(__fastcall*)(void*,void*,RoomDrawArgs*))(image+0x4addc70))(composite,(void*)&indoorMesh,&args);
  }
  nativeRef(args.view,false);nativeRef(args.buffer,false);
 }
}
