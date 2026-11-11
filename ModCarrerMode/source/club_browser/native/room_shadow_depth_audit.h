#pragma once
#include "room_surface_shadow.h"
#include <fstream>
#include <iomanip>
#include <sstream>
#include <filesystem>
// Explicit, process-scoped GPU diagnostics. Nothing is captured unless the
// matching PID/token request exists; each token overwrites two bounded reports.
namespace roomaudit {
using namespace roomshadow;
inline std::filesystem::path folder;
inline std::atomic<uint64_t> wanted{0};inline uint64_t nativeDone=0,uiDone=0;
inline uint64_t mapsDone=0;
inline void poll(const std::filesystem::path& path){
 if(folder.empty())folder=path;
 std::ifstream in(path/L"shadow_audit.request");unsigned pid=0;uint64_t token=0;
 if(in>>pid>>token&&pid==GetCurrentProcessId()&&token){unsigned mode=0;in>>mode;roomsurface::diagnosticMode=mode==1?1:0;wanted=token;}
 else roomsurface::diagnosticMode=0;
}
struct alignas(16) Constants {float inverse[16],viewport[4],mode[4];};
inline constexpr const char* shader=R"hlsl(
cbuffer Data:register(b0){row_major float4x4 inverseCamera;float4 viewport;float4 mode;};
#ifdef AUDIT_MSAA
Texture2DMS<float> sceneDepth:register(t0);
#else
Texture2D<float> sceneDepth:register(t0);
#endif
float4 VS(uint id:SV_VertexID):SV_POSITION{return float4((id&1)?1:-1,(id&2)?-1:1,0,1);}
float4 PS(float4 p:SV_POSITION):SV_TARGET{
 float2 uv=p.xy/float2(128,72),pixel=viewport.xy+uv*viewport.zw;float d;
#ifdef AUDIT_MSAA
 uint w,h,n;sceneDepth.GetDimensions(w,h,n);d=mode.x<0?0:1;
 [loop]for(uint i=0;i<n;++i){float value=sceneDepth.Load(int2(pixel),i);d=mode.x<0?max(d,value):min(d,value);}
#else
 d=sceneDepth.Load(int3(int2(pixel),0));
#endif
 float4 world=mul(float4(uv*float2(2,-2)+float2(-1,1),d,1),inverseCamera);
 return float4(abs(world.w)>.000001?world.xyz/world.w:float3(1e8,1e8,1e8),d);
}
)hlsl";
struct Auditor {
 ComPtr<ID3D11Device> device;roomshadow::Renderer depthReader;clubgfx::UiPipelineState pipeline;
 ComPtr<ID3D11VertexShader> vertex;ComPtr<ID3D11PixelShader> pixel,multisample;
 ComPtr<ID3D11Buffer> constants;ComPtr<ID3D11Texture2D> image,staging;ComPtr<ID3D11RenderTargetView> target;
 ComPtr<ID3D11DepthStencilState> noDepth;ComPtr<ID3D11RasterizerState> raster;
 bool initialize(ID3D11Device* d){
  if(device.Get()!=d){*this=Auditor{};device=d;}if(target&&staging&&raster&&noDepth)return true;
  auto compile=[&](const char*entry,const char*profile,const D3D_SHADER_MACRO* macros,ID3DBlob** out){return SUCCEEDED(D3DCompile(shader,strlen(shader),nullptr,macros,nullptr,entry,profile,D3DCOMPILE_OPTIMIZATION_LEVEL3,0,out,nullptr));};
  ComPtr<ID3DBlob> code;if(!compile("VS","vs_5_0",nullptr,&code)||FAILED(d->CreateVertexShader(code->GetBufferPointer(),code->GetBufferSize(),nullptr,&vertex)))return false;
  code.Reset();if(!compile("PS","ps_5_0",nullptr,&code)||FAILED(d->CreatePixelShader(code->GetBufferPointer(),code->GetBufferSize(),nullptr,&pixel)))return false;
  const D3D_SHADER_MACRO msaa[]={{"AUDIT_MSAA","1"},{nullptr,nullptr}};
  code.Reset();if(!compile("PS","ps_5_0",msaa,&code)||FAILED(d->CreatePixelShader(code->GetBufferPointer(),code->GetBufferSize(),nullptr,&multisample)))return false;
  D3D11_BUFFER_DESC b{};b.ByteWidth=sizeof(Constants);b.BindFlags=D3D11_BIND_CONSTANT_BUFFER;if(FAILED(d->CreateBuffer(&b,nullptr,&constants)))return false;
  D3D11_TEXTURE2D_DESC t{};t.Width=128;t.Height=72;t.MipLevels=t.ArraySize=t.SampleDesc.Count=1;t.Format=DXGI_FORMAT_R32G32B32A32_FLOAT;t.BindFlags=D3D11_BIND_RENDER_TARGET;
  if(FAILED(d->CreateTexture2D(&t,nullptr,&image))||FAILED(d->CreateRenderTargetView(image.Get(),nullptr,&target)))return false;
  t.BindFlags=0;t.Usage=D3D11_USAGE_STAGING;t.CPUAccessFlags=D3D11_CPU_ACCESS_READ;if(FAILED(d->CreateTexture2D(&t,nullptr,&staging)))return false;
  D3D11_DEPTH_STENCIL_DESC ds{};if(FAILED(d->CreateDepthStencilState(&ds,&noDepth)))return false;
  D3D11_RASTERIZER_DESC r{};r.FillMode=D3D11_FILL_SOLID;r.CullMode=D3D11_CULL_NONE;r.DepthClipEnable=TRUE;
  return SUCCEEDED(d->CreateRasterizerState(&r,&raster))&&depthReader.initialize(d);
 }
 bool capture(const Frame& f,std::ostream& out){
  auto*c=f.context.Get();if(!c||!f.depth)return false;ComPtr<ID3D11Device>d;c->GetDevice(&d);
  if(!initialize(d.Get()))return false;
  ComPtr<ID3D11Resource> resource;f.depth->GetResource(&resource);ComPtr<ID3D11Texture2D> depth;if(FAILED(resource.As(&depth)))return false;
  D3D11_TEXTURE2D_DESC desc{};depth->GetDesc(&desc);if(!depthReader.prepareDepth(f,desc))return false;
  roomsurface::Matrix inverse;if(!roomsurface::inverse(roomsurface::relativeCamera(f.viewProjection),inverse))return false;
  if(!pipeline.enter(c))return false;
  struct Restore {clubgfx::UiPipelineState& p;bool previous=clubanim::staticSceneDraw;Restore(clubgfx::UiPipelineState& s):p(s){clubanim::staticSceneDraw=true;}~Restore(){clubanim::staticSceneDraw=previous;p.leave();}} restore(pipeline);
  c->ClearState();if(depthReader.copyDepth)c->CopyResource(depthReader.depthCopy.Get(),resource.Get());
  auto*rt=target.Get();c->OMSetRenderTargets(1,&rt,nullptr);c->OMSetDepthStencilState(noDepth.Get(),0);c->RSSetState(raster.Get());
  D3D11_VIEWPORT vp={0,0,128,72,0,1};c->RSSetViewports(1,&vp);
  Constants data{};memcpy(data.inverse,inverse.data(),64);data.viewport[0]=f.viewport.TopLeftX;data.viewport[1]=f.viewport.TopLeftY;data.viewport[2]=f.viewport.Width;data.viewport[3]=f.viewport.Height;
  data.mode[0]=f.depthState.DepthFunc==D3D11_COMPARISON_GREATER||f.depthState.DepthFunc==D3D11_COMPARISON_GREATER_EQUAL?-1.f:1.f;
  c->UpdateSubresource(constants.Get(),0,nullptr,&data,0,0);auto*cb=constants.Get();c->PSSetConstantBuffers(0,1,&cb);
  c->VSSetShader(vertex.Get(),nullptr,0);c->PSSetShader(desc.SampleDesc.Count>1?multisample.Get():pixel.Get(),nullptr,0);auto*srv=depthReader.depthView.Get();c->PSSetShaderResources(0,1,&srv);
  c->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP);c->Draw(4,0);c->CopyResource(staging.Get(),image.Get());
  D3D11_MAPPED_SUBRESOURCE map{};if(FAILED(c->Map(staging.Get(),0,D3D11_MAP_READ,0,&map)))return false;
  unsigned foreground=0,room=0;float lo[3]={1e8,1e8,1e8},hi[3]={-1e8,-1e8,-1e8};
  for(unsigned y=0;y<72;++y)for(unsigned x=0;x<128;++x){const auto*p=reinterpret_cast<const float*>(static_cast<const char*>(map.pData)+y*map.RowPitch)+x*4;
   if(!std::isfinite(p[3])||(data.mode[0]>0?p[3]>=.999999f:p[3]<=.000001f))continue;++foreground;
   if(std::isfinite(p[0])&&std::isfinite(p[1])&&std::isfinite(p[2]))for(unsigned axis=0;axis<3;++axis){lo[axis]=std::min(lo[axis],p[axis]);hi[axis]=std::max(hi[axis],p[axis]);}
   if(std::abs(p[0])<=1500&&p[1]>=-10&&p[1]<=410&&p[2]>=-850&&p[2]<=3000)++room;
  }
  c->Unmap(staging.Get(),0);
  out<<",\"depth_size\":["<<desc.Width<<","<<desc.Height<<"],\"samples\":"<<desc.SampleDesc.Count<<",\"foreground\":"<<foreground<<",\"inside_room\":"<<room<<",\"world_min\":["<<lo[0]<<","<<lo[1]<<","<<lo[2]<<"],\"world_max\":["<<hi[0]<<","<<hi[1]<<","<<hi[2]<<"]";return true;
 }
};
inline Auditor auditor;
inline void maps(const Frame& frame,const D3D11_TEXTURE2D_DESC&color){
 const auto token=wanted.load();if(!token||mapsDone==token)return;mapsDone=token;
 try{
  auto&render=roomsurface::renderer;if(!render.ready||!render.statics.texture)return;
  auto*c=frame.context.Get();ComPtr<ID3D11Device>d;c->GetDevice(&d);
  D3D11_TEXTURE2D_DESC desc{};render.statics.texture->GetDesc(&desc);desc.Usage=D3D11_USAGE_STAGING;desc.BindFlags=0;desc.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
  ComPtr<ID3D11Texture2D>staging;if(FAILED(d->CreateTexture2D(&desc,nullptr,&staging)))return;c->CopyResource(staging.Get(),render.statics.texture.Get());
  std::vector<float>values(size_t(desc.Width)*desc.Height*desc.ArraySize,1.f);std::ostringstream report;
  report<<std::setprecision(8)<<"{\"pid\":"<<GetCurrentProcessId()<<",\"token\":"<<token<<",\"color\":["<<color.Width<<","<<color.Height<<","<<unsigned(color.Format)<<"],\"viewport\":["<<frame.viewport.TopLeftX<<","<<frame.viewport.TopLeftY<<","<<frame.viewport.Width<<","<<frame.viewport.Height<<"],\"slices\":[";
  for(unsigned i=0;i<desc.ArraySize;++i){D3D11_MAPPED_SUBRESOURCE map{};if(FAILED(c->Map(staging.Get(),i,D3D11_MAP_READ,0,&map)))return;
   unsigned count=0;float lo=1,hi=0;for(unsigned y=0;y<desc.Height;++y){const float*row=reinterpret_cast<const float*>(static_cast<const char*>(map.pData)+y*map.RowPitch);for(unsigned x=0;x<desc.Width;++x){const float value=row[x];values[(size_t(i)*desc.Height+y)*desc.Width+x]=value;if(value<.999999f){++count;lo=std::min(lo,value);hi=std::max(hi,value);}}}c->Unmap(staging.Get(),i);
   if(i)report<<',';report<<'['<<i<<','<<render.revisions[i]<<','<<count<<','<<lo<<','<<hi<<']';
  }
  report<<"],\"floor_shade\":[";bool comma=false;
  auto smooth=[](float a,float b,float v){const auto t=std::clamp((v-a)/(b-a),0.f,1.f);return t*t*(3-2*t);};
  for(float z:{-300.f,0.f,145.f,700.f})for(float x:{-450.f,-150.f,0.f,150.f,450.f}){float total=0,blocked=0;
   for(unsigned i=0;i<desc.ArraySize;++i){const auto&p=room_spotlight_r79::kSources[i];const float dx=p.x-x,dz=p.z-z,q=dx*dx+p.y*p.y+dz*dz,dist=sqrtf(q);if(dist>=620)continue;
    float e=smooth(.5f,.78f,p.y/dist)*(1-smooth(620*.68f,620,dist));e*=1-smooth(620*.68f,620,dist);total+=e;
    const float u=(x-p.x)*.5773502692f/p.y*.5f+.5f,v=-(z-p.z)*.5773502692f/p.y*.5f+.5f;if(!render.revisions[i]||u<=0||u>=1||v<=0||v>=1)continue;
    const auto ix=std::min(desc.Width-1,unsigned(u*desc.Width)),iy=std::min(desc.Height-1,unsigned(v*desc.Height));const float stored=values[(size_t(i)*desc.Height+iy)*desc.Width+ix],reference=620.f/612.f-(8.f*620.f/612.f)/(p.y-2.f);if(stored<reference)blocked+=e;
   }
   if(comma)report<<',';comma=true;report<<'['<<x<<','<<z<<','<<(total>0?.42f*blocked/total:0)<<']';
  }
  report<<"],\"meshes\":[";const auto&meshes=frame.staticMeshes?*frame.staticMeshes:frame.meshes;
  for(size_t i=0;i<std::min<size_t>(16,meshes.size());++i){const auto&m=meshes[i];if(i)report<<',';report<<'['<<m.stride<<','<<m.count<<','<<m.offset<<','<<m.baseVertex<<','<<m.model[12]<<','<<m.model[13]<<','<<m.model[14]<<']';}report<<"]}\n";
  std::ofstream out(folder/L"shadow_audit_maps.json");out<<report.str();
 }catch(...){/* Explicit diagnostics stay independent from the scene. */}
}
inline void capture(const Frame& frame,bool ui){
 const uint64_t token=wanted.load();auto&done=ui?uiDone:nativeDone;if(!token||token==done)return;done=token;
 try{std::ostringstream result;result<<std::setprecision(8)<<"{\"pid\":"<<GetCurrentProcessId()<<",\"token\":"<<token<<",\"frame\":"<<frame.sequence<<",\"flags\":"<<frame.flags;
  const bool ok=auditor.capture(frame,result);result<<",\"ok\":"<<(ok?"true":"false")<<"}\n";
  std::ofstream out(folder/(ui?L"shadow_audit_ui.json":L"shadow_audit_native.json"));out<<result.str();
 }catch(...){/* An optional report must never interrupt the game's draw. */}
}
}
