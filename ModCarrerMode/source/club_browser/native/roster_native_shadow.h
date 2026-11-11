#pragma once
#include <wrl/client.h>
#include <memory>
#include <mutex>
#include <atomic>
#include <algorithm>
#include <cmath>
#include <d3dcompiler.h>
#include "graphics.h"
#include "room_texture_filter.h"
#include "../../club_environment/room/native/room_spotlight_r79.h"

// A room-local use of FIFA's unskinned flat-shadow shader. The native actor's
// current vertex/index streams supply the silhouette, including its animation.
// The original FIFA shader is a small installed asset. No shadow image is cached.
namespace roomshadow {
using Microsoft::WRL::ComPtr;
using Bytes=clubassets::Bytes;
inline constexpr unsigned mapSize=512;
inline constexpr float radius=220.f;
inline constexpr float floorLift=.25f;
inline constexpr float origin[3]={100000.f,1000.f,530.f};
inline std::atomic<unsigned> captures{0},renders{0},failures{0},skipped{0};
inline std::atomic<unsigned> depthSamples{0},depthRejected{0};

struct ShaderCode {Bytes vertex,pixel;};
inline std::shared_ptr<const ShaderCode> shaderCode;
inline bool loadShaders(const std::filesystem::path& game){
 const auto effect=clubassets::read({game/L"ModCarrerMode/data/club_browser/room_shadow_native.fxo",0,11024});
 auto code=std::make_shared<ShaderCode>();
 for(size_t at=0;at+32<=effect.size();++at){
  if(memcmp(effect.data()+at,"DXBC",4))continue;
  const auto size=clubassets::le(effect.data()+at+24);
  if(size<32||uint64_t(at)+size>effect.size())continue;
  ComPtr<ID3D11ShaderReflection> reflection;
  if(FAILED(D3DReflect(effect.data()+at,size,IID_PPV_ARGS(&reflection))))continue;
  D3D11_SHADER_DESC desc{};if(FAILED(reflection->GetDesc(&desc)))continue;
  auto& target=D3D11_SHVER_GET_TYPE(desc.Version)==D3D11_SHVER_VERTEX_SHADER?code->vertex:code->pixel;
  if(target.empty()&&(D3D11_SHVER_GET_TYPE(desc.Version)==D3D11_SHVER_VERTEX_SHADER||D3D11_SHVER_GET_TYPE(desc.Version)==D3D11_SHVER_PIXEL_SHADER))
   target.assign(effect.begin()+at,effect.begin()+at+size);
  if(!code->vertex.empty()&&!code->pixel.empty()){std::atomic_store(&shaderCode,std::shared_ptr<const ShaderCode>(code));return true;}
  at+=size-1;
 }
 ++failures;return false;
}

struct Mesh {
 ComPtr<ID3D11Buffer> vertices,indices;
 unsigned stride=0,offset=0,count=0,first=0,indexOffset=0;
 int baseVertex=0;DXGI_FORMAT indexFormat=DXGI_FORMAT_UNKNOWN;
 bool floatPosition=false,transformed=false,structural=false;float model[16]{};
};
struct Frame {
 uint64_t sequence=0,tick=0;unsigned flags=0;std::vector<Mesh> meshes;bool scenery=false;
 std::shared_ptr<const std::vector<Mesh>> staticMeshes;
 ComPtr<ID3D11DeviceContext> context;ComPtr<ID3D11DepthStencilView> depth;
 D3D11_DEPTH_STENCIL_DESC depthState{};D3D11_VIEWPORT viewport{};
 float model[16]{},viewProjection[16]{};
};
inline std::mutex frameMutex;
inline std::shared_ptr<Frame> pending;
inline thread_local Frame* capturing=nullptr;
// Count actual native scene paints, independently of the UI clock and Present.
inline thread_local ID3D11DeviceContext* paintContext=nullptr;
inline std::atomic<uint64_t> painted{0};
inline void (*beforeOverlayDraw)(ID3D11DeviceContext*)=nullptr;
inline void discard(){std::lock_guard<std::mutex> lock(frameMutex);pending.reset();}
using DrawIndexed=void(STDMETHODCALLTYPE*)(ID3D11DeviceContext*,UINT,UINT,INT);
using DrawIndexedInstanced=void(STDMETHODCALLTYPE*)(ID3D11DeviceContext*,UINT,UINT,UINT,INT,UINT);
using Draw=void(STDMETHODCALLTYPE*)(ID3D11DeviceContext*,UINT,UINT);
using DrawInstanced=void(STDMETHODCALLTYPE*)(ID3D11DeviceContext*,UINT,UINT,UINT,UINT);
struct Hook {void** table=nullptr;DrawIndexed indexed=nullptr;DrawIndexedInstanced instanced=nullptr;Draw plain=nullptr;DrawInstanced plainInstanced=nullptr;};
inline std::mutex hookMutex;inline std::vector<Hook> hooks;
inline std::atomic<unsigned> hookEpoch{0};
inline Hook hookFor(ID3D11DeviceContext* context){
 auto table=*reinterpret_cast<void***>(context);thread_local Hook cached;thread_local unsigned epoch=UINT_MAX;
 const auto current=hookEpoch.load();if(cached.table==table&&epoch==current)return cached;
 std::lock_guard<std::mutex> lock(hookMutex);
 for(const auto& hook:hooks)if(hook.table==table){cached=hook;epoch=hookEpoch.load();return hook;}return {};
}
inline void capture(ID3D11DeviceContext* context,UINT count,UINT first,INT baseVertex){
 auto* frame=capturing;
 if(!frame||frame->context.Get()!=context||frame->meshes.size()>=96||count<3||count>3000000)return;
 D3D11_PRIMITIVE_TOPOLOGY topology{};context->IAGetPrimitiveTopology(&topology);
 if(topology!=D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST)return;
 Mesh mesh;context->IAGetVertexBuffers(0,1,mesh.vertices.GetAddressOf(),&mesh.stride,&mesh.offset);
 context->IAGetIndexBuffer(mesh.indices.GetAddressOf(),&mesh.indexFormat,&mesh.indexOffset);
 if(!mesh.vertices||!mesh.indices||(mesh.stride!=20&&mesh.stride!=28&&(!frame->scenery||(mesh.stride!=24&&mesh.stride!=32)))||
    (mesh.indexFormat!=DXGI_FORMAT_R16_UINT&&mesh.indexFormat!=DXGI_FORMAT_R32_UINT))return;
 D3D11_BUFFER_DESC indexDesc{},vertexDesc{};mesh.indices->GetDesc(&indexDesc);mesh.vertices->GetDesc(&vertexDesc);
 const unsigned width=mesh.indexFormat==DXGI_FORMAT_R16_UINT?2:4;
 if(uint64_t(mesh.indexOffset)+(uint64_t(first)+count)*width>indexDesc.ByteWidth||mesh.offset>=vertexDesc.ByteWidth)return;
 mesh.count=count;mesh.first=first;mesh.baseVertex=baseVertex;
 mesh.structural=(frame->flags&1)!=0;mesh.floatPosition=mesh.stride==24||mesh.stride==32;mesh.transformed=frame->scenery;
 if(mesh.transformed)memcpy(mesh.model,frame->model,64);
 frame->meshes.push_back(std::move(mesh));++captures;
}
inline void beforeDraw(ID3D11DeviceContext* context){
 if(beforeOverlayDraw&&paintContext!=context&&!capturing)try{beforeOverlayDraw(context);}catch(...){++failures;}
}
inline void STDMETHODCALLTYPE indexed(ID3D11DeviceContext* context,UINT count,UINT first,INT baseVertex){
 auto hook=hookFor(context);if(!hook.indexed)return;beforeDraw(context);{roomfilter::Draw filtering(context);hook.indexed(context,count,first,baseVertex);}
 if(paintContext==context&&count)++painted;
 try{capture(context,count,first,baseVertex);}catch(...){++failures;}
}
inline void STDMETHODCALLTYPE instanced(ID3D11DeviceContext* context,UINT count,UINT instances,UINT first,INT baseVertex,UINT firstInstance){
 auto hook=hookFor(context);if(!hook.instanced)return;beforeDraw(context);{roomfilter::Draw filtering(context);hook.instanced(context,count,instances,first,baseVertex,firstInstance);}
 if(paintContext==context&&count&&instances)++painted;
 if(instances==1&&firstInstance==0)try{capture(context,count,first,baseVertex);}catch(...){++failures;}
}
inline void STDMETHODCALLTYPE plain(ID3D11DeviceContext* context,UINT count,UINT first){
 auto hook=hookFor(context);if(!hook.plain)return;beforeDraw(context);hook.plain(context,count,first);
}
inline void STDMETHODCALLTYPE plainInstanced(ID3D11DeviceContext* context,UINT count,UINT instances,UINT first,UINT firstInstance){
 auto hook=hookFor(context);if(!hook.plainInstanced)return;beforeDraw(context);hook.plainInstanced(context,count,instances,first,firstInstance);
}
inline bool replace(void** slot,void* expected,void* replacement){
 if(*slot==replacement)return true;DWORD old=0;if(!VirtualProtect(slot,sizeof(void*),PAGE_READWRITE,&old))return false;
 auto seen=InterlockedCompareExchangePointer(reinterpret_cast<void*volatile*>(slot),replacement,expected);
 DWORD ignored=0;VirtualProtect(slot,sizeof(void*),old,&ignored);return seen==expected||seen==replacement;
}
inline bool sameNativeModule(void* left,void* right){
 MEMORY_BASIC_INFORMATION a{},b{};
 return left&&right&&VirtualQuery(left,&a,sizeof a)&&VirtualQuery(right,&b,sizeof b)&&a.Type==MEM_IMAGE&&b.Type==MEM_IMAGE&&a.AllocationBase==b.AllocationBase;
}
inline bool arm(ID3D11DeviceContext* context){
 if(!context||context->GetType()!=D3D11_DEVICE_CONTEXT_IMMEDIATE)return false;
 auto table=*reinterpret_cast<void***>(context);std::lock_guard<std::mutex> lock(hookMutex);
 for(auto& hook:hooks)if(hook.table==table){
  // D3D11 can refresh these entries while binding a native material. Restore
  // only our verified original entry, preserving any other add-on's hook.
  if(table[12]!=reinterpret_cast<void*>(&indexed)&&table[12]!=reinterpret_cast<void*>(hook.indexed)){
   if(!sameNativeModule(table[12],reinterpret_cast<void*>(hook.indexed)))return false;
   hook.indexed=reinterpret_cast<DrawIndexed>(table[12]);++hookEpoch;
  }
  if(table[20]!=reinterpret_cast<void*>(&instanced)&&table[20]!=reinterpret_cast<void*>(hook.instanced)){
   if(!sameNativeModule(table[20],reinterpret_cast<void*>(hook.instanced)))return false;
   hook.instanced=reinterpret_cast<DrawIndexedInstanced>(table[20]);++hookEpoch;
  }
  if(table[13]!=reinterpret_cast<void*>(&plain)&&table[13]!=reinterpret_cast<void*>(hook.plain)){
   if(!sameNativeModule(table[13],reinterpret_cast<void*>(hook.plain)))return false;hook.plain=reinterpret_cast<Draw>(table[13]);++hookEpoch;
  }
  if(table[21]!=reinterpret_cast<void*>(&plainInstanced)&&table[21]!=reinterpret_cast<void*>(hook.plainInstanced)){
   if(!sameNativeModule(table[21],reinterpret_cast<void*>(hook.plainInstanced)))return false;hook.plainInstanced=reinterpret_cast<DrawInstanced>(table[21]);++hookEpoch;
  }
  return replace(table+12,reinterpret_cast<void*>(hook.indexed),reinterpret_cast<void*>(&indexed))&&replace(table+20,reinterpret_cast<void*>(hook.instanced),reinterpret_cast<void*>(&instanced))&&replace(table+13,reinterpret_cast<void*>(hook.plain),reinterpret_cast<void*>(&plain))&&replace(table+21,reinterpret_cast<void*>(hook.plainInstanced),reinterpret_cast<void*>(&plainInstanced));
 }
 if(hooks.size()>=8||table[12]==reinterpret_cast<void*>(&indexed)||table[20]==reinterpret_cast<void*>(&instanced)||table[13]==reinterpret_cast<void*>(&plain)||table[21]==reinterpret_cast<void*>(&plainInstanced))return false;
 Hook hook{table,reinterpret_cast<DrawIndexed>(table[12]),reinterpret_cast<DrawIndexedInstanced>(table[20]),reinterpret_cast<Draw>(table[13]),reinterpret_cast<DrawInstanced>(table[21])};hooks.push_back(hook);++hookEpoch;
 if(replace(table+12,reinterpret_cast<void*>(hook.indexed),reinterpret_cast<void*>(&indexed))&&replace(table+20,reinterpret_cast<void*>(hook.instanced),reinterpret_cast<void*>(&instanced))&&replace(table+13,reinterpret_cast<void*>(hook.plain),reinterpret_cast<void*>(&plain))&&replace(table+21,reinterpret_cast<void*>(hook.plainInstanced),reinterpret_cast<void*>(&plainInstanced)))return true;
 replace(table+12,reinterpret_cast<void*>(&indexed),reinterpret_cast<void*>(hook.indexed));replace(table+20,reinterpret_cast<void*>(&instanced),reinterpret_cast<void*>(hook.instanced));replace(table+13,reinterpret_cast<void*>(&plain),reinterpret_cast<void*>(hook.plain));replace(table+21,reinterpret_cast<void*>(&plainInstanced),reinterpret_cast<void*>(hook.plainInstanced));return false;
}
inline void afterNativeVertexBinding(ID3D11DeviceContext* context){
 if(paintContext==context||(capturing&&capturing->context.Get()==context))arm(context);
 else if(beforeOverlayDraw)try{beforeOverlayDraw(context);}catch(...){++failures;}
}
struct CaptureScope {
 std::shared_ptr<Frame> frame;
 ID3D11DeviceContext* previousPaint=nullptr;
 CaptureScope(ID3D11DeviceContext* context,uint64_t sequence,const float* model,const float* viewProjection){
  if(capturing||!sequence||!std::atomic_load(&shaderCode)||!arm(context))return;
  if(!model||!viewProjection||!std::all_of(model,model+16,[](float v){return std::isfinite(v);})||
     !std::all_of(viewProjection,viewProjection+16,[](float v){return std::isfinite(v);}))return;
  if(std::abs(model[12]-origin[0])>1||std::abs(model[13]-origin[1])>1||std::abs(model[14]-origin[2])>1)return;
  frame=std::make_shared<Frame>();frame->sequence=sequence;frame->tick=GetTickCount64();frame->context=context;
  memcpy(frame->model,model,64);memcpy(frame->viewProjection,viewProjection,64);
  context->OMGetRenderTargets(0,nullptr,frame->depth.GetAddressOf());
  ComPtr<ID3D11DepthStencilState> depthState;UINT stencil=0;context->OMGetDepthStencilState(&depthState,&stencil);
  if(!frame->depth||!depthState){frame.reset();return;}depthState->GetDesc(&frame->depthState);
  UINT count=1;context->RSGetViewports(&count,&frame->viewport);
  if(count!=1||!frame->depthState.DepthEnable){frame.reset();return;}
  capturing=frame.get();previousPaint=paintContext;paintContext=context;
 }
 ~CaptureScope(){
  if(!frame)return;capturing=nullptr;paintContext=previousPaint;std::lock_guard<std::mutex> lock(frameMutex);pending=std::move(frame);
 }
};

// Original FIFA shader constants. Tile zero occupies the first 512 pixels of
// its 4096-pixel atlas viewport; the private target stores only that tile.
struct alignas(16) NativeConstants {float rows[29][4]{};};
struct Area {
 float center[3]={origin[0],origin[1],origin[2]};float halfWidth=radius,halfLength=radius;
 float light[3]={-110.f,310.f,90.f};float opacity=.46f;int spot=-1;float lift=floorLift;
};
inline NativeConstants casterConstants(const float* model,const Area& area=Area{}){
 NativeConstants constants;
 for(unsigned row=0;row<4;++row)for(unsigned column=0;column<4;++column)constants.rows[row][column]=model[column*4+row];
 for(unsigned axis=0;axis<3;++axis)constants.rows[axis][3]-=area.center[axis];
 constants.rows[21][1]=1;constants.rows[24][1]=400;constants.rows[24][2]=1;
 return constants;
}
inline std::array<float,1024> lightProjection(const Area& area=Area{}){
 // One ceiling light near the actor. Homogeneous projection intersects its
 // rays with y=0, so the outline responds to the actor's actual geometry.
 std::array<float,1024> matrix{};const float height=area.light[1],x=area.light[0],z=area.light[2];
 matrix[0]=height/area.halfWidth;matrix[1]=-x/area.halfWidth;
 matrix[5]=z/area.halfLength;matrix[6]=-height/area.halfLength;
 matrix[9]=-.5f;matrix[11]=height*.5f;
 matrix[13]=-1.f;matrix[15]=height;return matrix;
}
inline constexpr size_t ceilingSources=room_spotlight_r79::kSources.size();
static_assert(ceilingSources==36,"Update the HLSL source array when the ceiling layout changes");
struct alignas(16) ReceiverConstants {
 float viewProjection[16];float floor[4];float depth[4];
 float light[4],spot[4],sources[ceilingSources][4];
};
inline constexpr const char* receiverShader=R"hlsl(
cbuffer Receiver:register(b0){
 row_major float4x4 worldToClip;float4 floorData;float4 depthData;
 float4 lightData;float4 spotData;float4 ceilingLights[36];
};
Texture2D<float> silhouette:register(t0);SamplerState filtered:register(s0);
#ifdef ROOM_MULTISAMPLED_DEPTH
Texture2DMS<float> sceneDepth:register(t1);
#else
Texture2D<float> sceneDepth:register(t1);
#endif
struct Pixel {float4 position:SV_POSITION;float2 uv:TEXCOORD0;float3 world:TEXCOORD1;};
Pixel VS(uint id:SV_VertexID){
 Pixel p;p.uv=float2(id&1,(id>>1)&1);
 float3 surface=float3(floorData.x+(p.uv.x*2-1)*floorData.w,floorData.y,floorData.z+(p.uv.y*2-1)*depthData.z);
 p.world=surface;p.position=mul(float4(surface,1),worldToClip);return p;
}
float spotEnergy(float3 source,float3 surface){
 float3 ray=source-surface;float squared=dot(ray,ray);
 if(ray.y<=0||squared>=spotData.y*spotData.y)return 0;
 float distance=sqrt(squared);
 float cone=smoothstep(spotData.z,spotData.w,ray.y/max(distance,0.001));
 float fade=1-smoothstep(spotData.y*.68,spotData.y,distance);
 return cone*fade*fade;
}
float4 PS(Pixel p):SV_TARGET{
 float coverage=0;
#ifdef ROOM_MULTISAMPLED_DEPTH
 uint width,height,samples;sceneDepth.GetDimensions(width,height,samples);
 [loop]for(uint sampleIndex=0;sampleIndex<samples;++sampleIndex){
  float difference=(p.position.z-sceneDepth.Load(int2(p.position.xy),sampleIndex))*depthData.x;
  coverage+=difference<=depthData.y?1.0:0.0;
 }
 coverage/=max(samples,1);
#else
 float difference=(p.position.z-sceneDepth.Load(int3(int2(p.position.xy),0)))*depthData.x;
 coverage=difference<=depthData.y?1.0:0.0;
#endif
 float shade=0;
 [unroll]for(int y=-1;y<=1;++y)[unroll]for(int x=-1;x<=1;++x)
  shade+=silhouette.Sample(filtered,p.uv+float2(x,y)/512.0);
 float weight=1;
 if(spotData.x>0){
  float energy=spotEnergy(lightData.xyz,p.world);float total=0;
  [loop]for(int light=0;light<36;++light)total+=spotEnergy(ceilingLights[light].xyz,p.world);
  weight=energy/max(total,0.25); // Partial occlusion when another ceiling focus lights the same floor.
 }
 return float4(0,0,0,saturate(shade/9.0)*depthData.w*coverage*saturate(weight));
}
)hlsl";
struct Renderer {
 ComPtr<ID3D11Device> device;
 clubgfx::UiPipelineState pipeline;
 ComPtr<ID3D11VertexShader> caster,receiver;
 ComPtr<ID3D11PixelShader> maskPixel,receiverPixel,receiverMultisampled;
 ComPtr<ID3D11InputLayout> position,floatPosition;
 ComPtr<ID3D11Buffer> nativeConstants,tileConstants,projection,receiverConstants;
 ComPtr<ID3D11Texture2D> map;ComPtr<ID3D11RenderTargetView> mapTarget;ComPtr<ID3D11ShaderResourceView> mapView;
 ComPtr<ID3D11BlendState> maxBlend,alphaBlend;
 ComPtr<ID3D11RasterizerState> raster;
 ComPtr<ID3D11SamplerState> sampler;
 ComPtr<ID3D11DepthStencilState> noDepth;
 ComPtr<ID3D11Texture2D> depthCopy;
 ComPtr<ID3D11ShaderResourceView> depthView;
 D3D11_TEXTURE2D_DESC sampledDepth{};
 bool copyDepth=false;
 bool attempted=false,initialized=false;
 void clear(){
  pipeline.clear();device.Reset();caster.Reset();receiver.Reset();maskPixel.Reset();receiverPixel.Reset();receiverMultisampled.Reset();position.Reset();floatPosition.Reset();
  nativeConstants.Reset();tileConstants.Reset();projection.Reset();receiverConstants.Reset();map.Reset();mapTarget.Reset();mapView.Reset();
  maxBlend.Reset();alphaBlend.Reset();raster.Reset();sampler.Reset();noDepth.Reset();depthCopy.Reset();depthView.Reset();sampledDepth={};copyDepth=false;attempted=initialized=false;
 }
 bool buffer(UINT bytes,ID3D11Buffer** output,const void* data=nullptr){
  D3D11_BUFFER_DESC desc{};desc.ByteWidth=bytes;desc.Usage=D3D11_USAGE_DEFAULT;desc.BindFlags=D3D11_BIND_CONSTANT_BUFFER;
  D3D11_SUBRESOURCE_DATA initial{data,0,0};return SUCCEEDED(device->CreateBuffer(&desc,data?&initial:nullptr,output));
 }
 bool createMask(){
  D3D11_TEXTURE2D_DESC texture{};texture.Width=texture.Height=mapSize;texture.MipLevels=texture.ArraySize=texture.SampleDesc.Count=1;
  texture.Format=DXGI_FORMAT_R8_UNORM;texture.BindFlags=D3D11_BIND_RENDER_TARGET|D3D11_BIND_SHADER_RESOURCE;
  return SUCCEEDED(device->CreateTexture2D(&texture,nullptr,&map))&&SUCCEEDED(device->CreateRenderTargetView(map.Get(),nullptr,&mapTarget))&&
   SUCCEEDED(device->CreateShaderResourceView(map.Get(),nullptr,&mapView));
 }
 bool initialize(ID3D11Device* owner,Renderer* shared=nullptr){
  if(device.Get()!=owner){clear();device=owner;}if(attempted)return initialized;
  attempted=true;
  if(shared&&shared->initialized&&shared->device.Get()==owner){
   caster=shared->caster;receiver=shared->receiver;maskPixel=shared->maskPixel;
   receiverPixel=shared->receiverPixel;receiverMultisampled=shared->receiverMultisampled;
   position=shared->position;floatPosition=shared->floatPosition;
   nativeConstants=shared->nativeConstants;tileConstants=shared->tileConstants;projection=shared->projection;receiverConstants=shared->receiverConstants;
   maxBlend=shared->maxBlend;alphaBlend=shared->alphaBlend;raster=shared->raster;sampler=shared->sampler;noDepth=shared->noDepth;
   return initialized=createMask();
  }
  const auto code=std::atomic_load(&shaderCode);if(!code)return false;
  if(FAILED(device->CreateVertexShader(code->vertex.data(),code->vertex.size(),nullptr,&caster))||
     FAILED(device->CreatePixelShader(code->pixel.data(),code->pixel.size(),nullptr,&maskPixel)))return false;
  const D3D11_INPUT_ELEMENT_DESC element={"POSITION",0,DXGI_FORMAT_R16G16B16A16_FLOAT,0,0,D3D11_INPUT_PER_VERTEX_DATA,0};
  if(FAILED(device->CreateInputLayout(&element,1,code->vertex.data(),code->vertex.size(),&position)))return false;
  const D3D11_INPUT_ELEMENT_DESC floatElement={"POSITION",0,DXGI_FORMAT_R32G32B32_FLOAT,0,0,D3D11_INPUT_PER_VERTEX_DATA,0};
  if(FAILED(device->CreateInputLayout(&floatElement,1,code->vertex.data(),code->vertex.size(),&floatPosition)))return false;
  ComPtr<ID3DBlob> vertex,pixel;
  if(FAILED(D3DCompile(receiverShader,strlen(receiverShader),nullptr,nullptr,nullptr,"VS","vs_5_0",D3DCOMPILE_OPTIMIZATION_LEVEL3,0,&vertex,nullptr))||
     FAILED(D3DCompile(receiverShader,strlen(receiverShader),nullptr,nullptr,nullptr,"PS","ps_5_0",D3DCOMPILE_OPTIMIZATION_LEVEL3,0,&pixel,nullptr)))return false;
  if(FAILED(device->CreateVertexShader(vertex->GetBufferPointer(),vertex->GetBufferSize(),nullptr,&receiver))||
     FAILED(device->CreatePixelShader(pixel->GetBufferPointer(),pixel->GetBufferSize(),nullptr,&receiverPixel)))return false;
  const D3D_SHADER_MACRO macros[]={{"ROOM_MULTISAMPLED_DEPTH","1"},{nullptr,nullptr}};
  pixel.Reset();if(FAILED(D3DCompile(receiverShader,strlen(receiverShader),nullptr,macros,nullptr,"PS","ps_5_0",D3DCOMPILE_OPTIMIZATION_LEVEL3,0,&pixel,nullptr))||
     FAILED(device->CreatePixelShader(pixel->GetBufferPointer(),pixel->GetBufferSize(),nullptr,&receiverMultisampled)))return false;
  const float tiles[8]{};const auto matrix=lightProjection();
  if(!buffer(sizeof(NativeConstants),&nativeConstants)||!buffer(sizeof tiles,&tileConstants,tiles)||
     !buffer(sizeof matrix,&projection,matrix.data())||!buffer(sizeof(ReceiverConstants),&receiverConstants))return false;
  if(!createMask())return false;
  D3D11_BLEND_DESC blend{};auto& target=blend.RenderTarget[0];target.BlendEnable=TRUE;
  target.SrcBlend=target.DestBlend=target.SrcBlendAlpha=target.DestBlendAlpha=D3D11_BLEND_ONE;
  target.BlendOp=target.BlendOpAlpha=D3D11_BLEND_OP_MAX;target.RenderTargetWriteMask=D3D11_COLOR_WRITE_ENABLE_ALL;
  if(FAILED(device->CreateBlendState(&blend,&maxBlend)))return false;
  target.SrcBlend=D3D11_BLEND_SRC_ALPHA;target.DestBlend=D3D11_BLEND_INV_SRC_ALPHA;target.BlendOp=D3D11_BLEND_OP_ADD;
  target.SrcBlendAlpha=D3D11_BLEND_ZERO;target.DestBlendAlpha=D3D11_BLEND_ONE;target.BlendOpAlpha=D3D11_BLEND_OP_ADD;
  if(FAILED(device->CreateBlendState(&blend,&alphaBlend)))return false;
  D3D11_RASTERIZER_DESC rasterDesc{};rasterDesc.FillMode=D3D11_FILL_SOLID;rasterDesc.CullMode=D3D11_CULL_NONE;rasterDesc.DepthClipEnable=TRUE;
  if(FAILED(device->CreateRasterizerState(&rasterDesc,&raster)))return false;
  D3D11_SAMPLER_DESC sampling{};sampling.Filter=D3D11_FILTER_MIN_MAG_LINEAR_MIP_POINT;sampling.AddressU=sampling.AddressV=sampling.AddressW=D3D11_TEXTURE_ADDRESS_BORDER;
  sampling.MaxLOD=D3D11_FLOAT32_MAX;sampling.ComparisonFunc=D3D11_COMPARISON_ALWAYS;
  if(FAILED(device->CreateSamplerState(&sampling,&sampler)))return false;
  D3D11_DEPTH_STENCIL_DESC depth{};depth.DepthFunc=D3D11_COMPARISON_ALWAYS;
  initialized=SUCCEEDED(device->CreateDepthStencilState(&depth,&noDepth));return initialized;
 }
 bool prepareDepth(const Frame& frame,const D3D11_TEXTURE2D_DESC& color){
  ComPtr<ID3D11Resource> resource;frame.depth->GetResource(&resource);ComPtr<ID3D11Texture2D> texture;
  if(FAILED(resource.As(&texture)))return false;D3D11_TEXTURE2D_DESC depth{};texture->GetDesc(&depth);
  depthSamples=depth.SampleDesc.Count;
  if(depth.Width!=color.Width||depth.Height!=color.Height||depth.ArraySize!=1)return false;
  DXGI_FORMAT storage=DXGI_FORMAT_UNKNOWN,readable=DXGI_FORMAT_UNKNOWN;
  switch(depth.Format){
   case DXGI_FORMAT_R32_TYPELESS:case DXGI_FORMAT_D32_FLOAT:storage=DXGI_FORMAT_R32_TYPELESS;readable=DXGI_FORMAT_R32_FLOAT;break;
   case DXGI_FORMAT_R24G8_TYPELESS:case DXGI_FORMAT_D24_UNORM_S8_UINT:storage=DXGI_FORMAT_R24G8_TYPELESS;readable=DXGI_FORMAT_R24_UNORM_X8_TYPELESS;break;
   case DXGI_FORMAT_R16_TYPELESS:case DXGI_FORMAT_D16_UNORM:storage=DXGI_FORMAT_R16_TYPELESS;readable=DXGI_FORMAT_R16_UNORM;break;
   case DXGI_FORMAT_R32G8X24_TYPELESS:case DXGI_FORMAT_D32_FLOAT_S8X24_UINT:storage=DXGI_FORMAT_R32G8X24_TYPELESS;readable=DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS;break;
   default:return false;
  }
  ComPtr<ID3D11Resource> current;if(depthView)depthView->GetResource(&current);
  if(copyDepth&&depthCopy&&depth.Width==sampledDepth.Width&&depth.Height==sampledDepth.Height&&depth.Format==sampledDepth.Format&&
     depth.SampleDesc.Count==sampledDepth.SampleDesc.Count&&depth.SampleDesc.Quality==sampledDepth.SampleDesc.Quality)return true;
  if(!copyDepth&&current.Get()==resource.Get())return true;
  depthCopy.Reset();depthView.Reset();copyDepth=false;sampledDepth=depth;
  D3D11_SHADER_RESOURCE_VIEW_DESC view{};view.Format=readable;
  view.ViewDimension=depth.SampleDesc.Count>1?D3D11_SRV_DIMENSION_TEXTURE2DMS:D3D11_SRV_DIMENSION_TEXTURE2D;
  if(depth.SampleDesc.Count==1)view.Texture2D.MipLevels=1;
  if((depth.BindFlags&D3D11_BIND_SHADER_RESOURCE)&&SUCCEEDED(device->CreateShaderResourceView(resource.Get(),&view,&depthView)))return true;
  // Typed or depth-only game targets need a GPU copy to a readable typeless
  // resource. Its sample count is preserved; the original depth stays intact.
  auto desc=depth;desc.Format=storage;desc.BindFlags=D3D11_BIND_SHADER_RESOURCE;desc.MiscFlags=desc.CPUAccessFlags=0;desc.Usage=D3D11_USAGE_DEFAULT;
  if(FAILED(device->CreateTexture2D(&desc,nullptr,&depthCopy))||FAILED(device->CreateShaderResourceView(depthCopy.Get(),&view,&depthView)))return false;
  copyDepth=true;return true;
 }
 bool draw(const Frame& frame,ID3D11RenderTargetView* target,const D3D11_TEXTURE2D_DESC& color,const Area& area=Area{},bool rebuildMask=true,bool refreshDepth=true){
  const auto& meshes=frame.staticMeshes?*frame.staticMeshes:frame.meshes;
  if(meshes.empty()||!frame.depth)return false;
  auto* context=frame.context.Get();ComPtr<ID3D11Device> owner;context->GetDevice(&owner);
  if(!initialize(owner.Get())){++failures;return false;}
  if(!prepareDepth(frame,color)){++depthRejected;return false;}
  if(!pipeline.enter(context)){++failures;return false;}
  struct Restore {clubgfx::UiPipelineState& state;~Restore(){state.leave();}} restore{pipeline};
  context->ClearState();context->RSSetState(raster.Get());context->OMSetDepthStencilState(noDepth.Get(),0);
  if(copyDepth&&refreshDepth){ComPtr<ID3D11Resource> source;frame.depth->GetResource(&source);context->CopyResource(depthCopy.Get(),source.Get());}
  if(rebuildMask){
  ID3D11RenderTargetView* mask=mapTarget.Get();context->OMSetRenderTargets(1,&mask,nullptr);const float empty[4]{};context->ClearRenderTargetView(mask,empty);
  context->OMSetBlendState(maxBlend.Get(),nullptr,UINT_MAX);
  const D3D11_VIEWPORT atlas={0,0,4096,4096,0,1};context->RSSetViewports(1,&atlas);
  context->VSSetShader(caster.Get(),nullptr,0);context->PSSetShader(maskPixel.Get(),nullptr,0);
  const auto constants=casterConstants(frame.model,area);context->UpdateSubresource(nativeConstants.Get(),0,nullptr,&constants,0,0);
  const auto light=lightProjection(area);context->UpdateSubresource(projection.Get(),0,nullptr,light.data(),0,0);
  ID3D11Buffer* inputs[]={nativeConstants.Get(),tileConstants.Get(),projection.Get()};context->VSSetConstantBuffers(0,3,inputs);
  context->IASetInputLayout(position.Get());context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
  for(const auto& mesh:meshes){
   if(mesh.structural)continue;
   context->IASetInputLayout(mesh.floatPosition?floatPosition.Get():position.Get());
   if(mesh.transformed){const auto instance=casterConstants(mesh.model,area);context->UpdateSubresource(nativeConstants.Get(),0,nullptr,&instance,0,0);}
   auto* vertex=mesh.vertices.Get();context->IASetVertexBuffers(0,1,&vertex,&mesh.stride,&mesh.offset);
   context->IASetIndexBuffer(mesh.indices.Get(),mesh.indexFormat,mesh.indexOffset);
   // Capture is scoped to native actor submission, so this draw cannot
   // recursively register itself or any unrelated stadium mesh.
   context->DrawIndexed(mesh.count,mesh.first,mesh.baseVertex);
  }
  }
  context->OMSetRenderTargets(1,&target,nullptr);context->RSSetViewports(1,&frame.viewport);
  context->OMSetBlendState(alphaBlend.Get(),nullptr,UINT_MAX);context->OMSetDepthStencilState(noDepth.Get(),0);
  ReceiverConstants receiverData{};memcpy(receiverData.viewProjection,frame.viewProjection,64);
  receiverData.floor[0]=area.center[0];receiverData.floor[1]=area.center[1]+area.lift;receiverData.floor[2]=area.center[2];receiverData.floor[3]=area.halfWidth;
  for(unsigned axis=0;axis<3;++axis)receiverData.light[axis]=area.center[axis]+area.light[axis];
  receiverData.spot[0]=area.spot>=0?1.f:0.f;receiverData.spot[1]=room_spotlight_r79::kRange;
  receiverData.spot[2]=room_spotlight_r79::kOuterCos;receiverData.spot[3]=room_spotlight_r79::kInnerCos;
  for(size_t i=0;i<ceilingSources;++i){const auto& source=room_spotlight_r79::kSources[i];
   receiverData.sources[i][0]=origin[0]+source.x;receiverData.sources[i][1]=origin[1]+source.y;receiverData.sources[i][2]=source.z;
  }
  const auto comparison=frame.depthState.DepthFunc;
  receiverData.depth[0]=(comparison==D3D11_COMPARISON_GREATER||comparison==D3D11_COMPARISON_GREATER_EQUAL)?-1.f:1.f;
  receiverData.depth[1]=.000001f;receiverData.depth[2]=area.halfLength;receiverData.depth[3]=area.opacity;
  context->UpdateSubresource(receiverConstants.Get(),0,nullptr,&receiverData,0,0);
  auto* cb=receiverConstants.Get();context->VSSetConstantBuffers(0,1,&cb);context->PSSetConstantBuffers(0,1,&cb);
  context->VSSetShader(receiver.Get(),nullptr,0);context->PSSetShader(sampledDepth.SampleDesc.Count>1?receiverMultisampled.Get():receiverPixel.Get(),nullptr,0);
  ID3D11ShaderResourceView* textures[]={mapView.Get(),depthView.Get()};auto* filter=sampler.Get();context->PSSetShaderResources(0,2,textures);context->PSSetSamplers(0,1,&filter);
  context->IASetInputLayout(nullptr);context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP);context->Draw(4,0);
  ++renders;return true;
 }
};
inline Area actorArea(){
 Area result;float nearest=1e20f;
 for(unsigned i=0;i<ceilingSources;++i){const auto& source=room_spotlight_r79::kSources[i];
  const float x=source.x,z=source.z-origin[2],distance=x*x+z*z;
  if(distance<nearest){nearest=distance;result.light[0]=x;result.light[1]=source.y;result.light[2]=z;result.spot=int(i);}
 }
 result.lift=.8f;return result;
}
inline Renderer renderer;
inline void present(IDXGISwapChain* swap,uint64_t sequence,bool visible){
 std::shared_ptr<Frame> frame;{std::lock_guard<std::mutex> lock(frameMutex);frame.swap(pending);}
 if(!visible||!frame||frame->sequence!=sequence||GetTickCount64()-frame->tick>250){++skipped;return;}
 ComPtr<ID3D11Texture2D> color;ComPtr<ID3D11Device> owner;ComPtr<ID3D11RenderTargetView> target;
 if(FAILED(swap->GetBuffer(0,IID_PPV_ARGS(&color)))||FAILED(swap->GetDevice(IID_PPV_ARGS(&owner)))||
    FAILED(owner->CreateRenderTargetView(color.Get(),nullptr,&target))){++failures;return;}
 D3D11_TEXTURE2D_DESC desc{};color->GetDesc(&desc);renderer.draw(*frame,target.Get(),desc,actorArea());
}
inline void stop(){
 beforeOverlayDraw=nullptr;
 discard();std::lock_guard<std::mutex> lock(hookMutex);
 for(const auto& hook:hooks){replace(hook.table+12,reinterpret_cast<void*>(&indexed),reinterpret_cast<void*>(hook.indexed));replace(hook.table+20,reinterpret_cast<void*>(&instanced),reinterpret_cast<void*>(hook.instanced));replace(hook.table+13,reinterpret_cast<void*>(&plain),reinterpret_cast<void*>(hook.plain));replace(hook.table+21,reinterpret_cast<void*>(&plainInstanced),reinterpret_cast<void*>(hook.plainInstanced));}
}
}
