#pragma once
#include "room_surface_shadow.h"

// Low-resolution, camera-dependent reflections on the actual cabinet glass.
// Reads only the current 3D colour/depth targets, before FIFA draws the UI.
namespace gallery_reflection {
using namespace roomshadow;
inline std::atomic<unsigned> frames{0},failures{0},allocations{0};
struct alignas(16) Constants {
 float inverseCamera[16],camera[16],viewport[4],target[4],depth[4],glass[4];
};
inline constexpr const char* shader=R"hlsl(
cbuffer Data:register(b0){row_major float4x4 inverseCamera;row_major float4x4 camera;
 float4 viewport;float4 target;float4 depthData;float4 glass;};
Texture2D<float4> sceneColor:register(t0);
#ifdef GLASS_MSAA
Texture2DMS<float> sceneDepth:register(t1);
#else
Texture2D<float> sceneDepth:register(t1);
#endif
Texture2D<float4> reflectedColor:register(t2);SamplerState linearSample:register(s0);
struct Pixel{float4 p:SV_POSITION;};
Pixel VS(uint id:SV_VertexID){Pixel o;o.p=float4((id&1)?1:-1,(id&2)?-1:1,0,1);return o;}
float readDepth(int2 pixel){
#ifdef GLASS_MSAA
 uint w,h,n;sceneDepth.GetDimensions(w,h,n);float d=depthData.x<0?0:1;
 [loop]for(uint i=0;i<n;++i){float v=sceneDepth.Load(pixel,i);d=depthData.x<0?max(d,v):min(d,v);}return d;
#else
 return sceneDepth.Load(int3(pixel,0));
#endif
}
bool validDepth(float d){return depthData.x<0?d>.000001:d<.999999;}
float3 worldAt(float2 pixel,float depth){
 float2 ndc=(pixel-viewport.xy)/viewport.zw*float2(2,-2)+float2(-1,1);
 float4 p=mul(float4(ndc,depth,1),inverseCamera);return p.xyz/max(abs(p.w),.000001)*sign(p.w);
}
bool project(float3 p,out float2 uv,out float gap){
 float4 clip=mul(float4(p,1),camera);uv=0;gap=0;if(clip.w<=.001)return false;
 uv=clip.xy/clip.w*float2(.5,-.5)+.5;if(any(uv<.001)||any(uv>.999))return false;
 float2 pixel=viewport.xy+uv*viewport.zw;float depth=readDepth(int2(pixel));if(!validDepth(depth))return false;
 float3 surface=worldAt(pixel,depth);float4 scene=mul(float4(surface,1),camera);gap=clip.w-scene.w;return true;
}
float4 TracePS(Pixel input):SV_TARGET{
 float2 pixel=viewport.xy+input.p.xy/target.zw*viewport.zw;
 float depth=readDepth(int2(pixel));if(!validDepth(depth))return 0;
 float nearDepth=depthData.x<0?1:0,farDepth=depthData.x<0?.0001:.9999;
 float3 start=worldAt(pixel,nearDepth),direction=normalize(worldAt(pixel,farDepth)-start);
 if(abs(direction.x)<.00001||abs(start.x)>=glass.x)return 0;
 float side=direction.x>0?1:-1;float distance=(side*glass.x-start.x)/direction.x;if(distance<=0)return 0;
 float3 hitPoint=start+direction*distance;
 if(hitPoint.y<glass.y||hitPoint.y>glass.z||abs(hitPoint.z)>698.5)return 0;
 float seam=abs(hitPoint.z-round(hitPoint.z/350)*350);if(seam<1.7)return 0;
 float3 scene=worldAt(pixel,depth);if(dot(scene-start,direction)<distance-1)return 0;
 float3 normal=float3(-side,0,0),reflected=reflect(direction,normal);
 float3 previous=hitPoint+reflected*2;float previousGap=-1;
 float2 hitUV=0;bool hit=false;float travelled=0;
 [loop]for(int i=1;i<=48;++i){
  float t=2+1800*pow(i/48.0,2);float3 samplePoint=hitPoint+reflected*t;float2 uv;float gap;
  if(!project(samplePoint,uv,gap)){previous=samplePoint;previousGap=-1;continue;}
  if(gap>=0&&previousGap<0&&gap<80){
   float3 a=previous,b=samplePoint;float2 refined=uv;float finalGap=gap;
   [unroll]for(int j=0;j<5;++j){float3 middle=(a+b)*.5;float2 mUV;float mGap;
    if(project(middle,mUV,mGap)){if(mGap>=0){b=middle;refined=mUV;finalGap=mGap;}else a=middle;}else a=middle;}
   if(finalGap<8){hitUV=refined;travelled=t;hit=true;break;}
  }
  previous=samplePoint;previousGap=gap;
 }
 if(!hit)return 0;
 float edge=min(min(hitUV.x,hitUV.y),min(1-hitUV.x,1-hitUV.y));float confidence=smoothstep(0,.07,edge)*(1-smoothstep(1400,1800,travelled));
 float fresnel=.04+.96*pow(1-saturate(dot(-direction,normal)),5);
 float2 colorUV=(viewport.xy+hitUV*viewport.zw)/target.xy;
 return float4(sceneColor.SampleLevel(linearSample,colorUV,0).rgb,min(.38,fresnel*glass.w)*confidence);
}
float4 ComposePS(Pixel input):SV_TARGET{
 float2 uv=(input.p.xy-viewport.xy)/viewport.zw;
 return reflectedColor.SampleLevel(linearSample,uv,0);
}
)hlsl";
struct Renderer {
 ComPtr<ID3D11Device> device;clubgfx::UiPipelineState pipeline;roomshadow::Renderer depthReader;
 ComPtr<ID3D11VertexShader> vertex;ComPtr<ID3D11PixelShader> trace,traceMsaa,compose;
 ComPtr<ID3D11Texture2D> colour,reflection;ComPtr<ID3D11ShaderResourceView> colourView,reflectionView;
 ComPtr<ID3D11RenderTargetView> reflectionTarget;ComPtr<ID3D11Buffer> constants;
 ComPtr<ID3D11SamplerState> sampler;ComPtr<ID3D11BlendState> blend;ComPtr<ID3D11DepthStencilState> noDepth;
 ComPtr<ID3D11RasterizerState> raster;D3D11_TEXTURE2D_DESC current{};DXGI_FORMAT viewFormat=DXGI_FORMAT_UNKNOWN;
 bool attempted=false,ready=false;std::string shaderError;
 void clear(){pipeline.clear();depthReader.clear();*this=Renderer{};}
 bool initialize(ID3D11Device* owner){
  if(device.Get()!=owner){clear();device=owner;}if(attempted)return ready;attempted=true;
  auto compile=[&](const char* entry,const char* target,const D3D_SHADER_MACRO* macros,ID3DBlob** out){
   ComPtr<ID3DBlob> error;auto hr=D3DCompile(shader,strlen(shader),nullptr,macros,nullptr,entry,target,D3DCOMPILE_OPTIMIZATION_LEVEL3,0,out,&error);
   if(FAILED(hr)&&error)shaderError.assign(static_cast<const char*>(error->GetBufferPointer()),error->GetBufferSize());
   return SUCCEEDED(hr);
  };
  ComPtr<ID3DBlob> v,p;if(!compile("VS","vs_5_0",nullptr,&v)||FAILED(device->CreateVertexShader(v->GetBufferPointer(),v->GetBufferSize(),nullptr,&vertex)))return false;
  if(!compile("TracePS","ps_5_0",nullptr,&p)||FAILED(device->CreatePixelShader(p->GetBufferPointer(),p->GetBufferSize(),nullptr,&trace)))return false;
  p.Reset();const D3D_SHADER_MACRO macros[]={{"GLASS_MSAA","1"},{nullptr,nullptr}};
  if(!compile("TracePS","ps_5_0",macros,&p)||FAILED(device->CreatePixelShader(p->GetBufferPointer(),p->GetBufferSize(),nullptr,&traceMsaa)))return false;
  p.Reset();if(!compile("ComposePS","ps_5_0",nullptr,&p)||FAILED(device->CreatePixelShader(p->GetBufferPointer(),p->GetBufferSize(),nullptr,&compose)))return false;
  D3D11_BUFFER_DESC b{};b.ByteWidth=sizeof(Constants);b.BindFlags=D3D11_BIND_CONSTANT_BUFFER;if(FAILED(device->CreateBuffer(&b,nullptr,&constants)))return false;
  D3D11_SAMPLER_DESC s{};s.Filter=D3D11_FILTER_MIN_MAG_LINEAR_MIP_POINT;s.AddressU=s.AddressV=s.AddressW=D3D11_TEXTURE_ADDRESS_CLAMP;s.MaxLOD=D3D11_FLOAT32_MAX;
  if(FAILED(device->CreateSamplerState(&s,&sampler)))return false;
  D3D11_DEPTH_STENCIL_DESC d{};d.DepthEnable=FALSE;d.DepthWriteMask=D3D11_DEPTH_WRITE_MASK_ZERO;d.DepthFunc=D3D11_COMPARISON_ALWAYS;
  if(FAILED(device->CreateDepthStencilState(&d,&noDepth)))return false;
  D3D11_RASTERIZER_DESC r{};r.FillMode=D3D11_FILL_SOLID;r.CullMode=D3D11_CULL_NONE;r.DepthClipEnable=TRUE;
  if(FAILED(device->CreateRasterizerState(&r,&raster)))return false;
  D3D11_BLEND_DESC alpha{};auto& t=alpha.RenderTarget[0];t.BlendEnable=TRUE;t.SrcBlend=D3D11_BLEND_SRC_ALPHA;t.DestBlend=D3D11_BLEND_INV_SRC_ALPHA;t.BlendOp=D3D11_BLEND_OP_ADD;
  t.SrcBlendAlpha=D3D11_BLEND_ZERO;t.DestBlendAlpha=D3D11_BLEND_ONE;t.BlendOpAlpha=D3D11_BLEND_OP_ADD;t.RenderTargetWriteMask=D3D11_COLOR_WRITE_ENABLE_ALL;
  ready=SUCCEEDED(device->CreateBlendState(&alpha,&blend))&&depthReader.initialize(device.Get());return ready;
 }
 bool targets(const D3D11_TEXTURE2D_DESC& source,DXGI_FORMAT format,const Frame& frame){
  const float scale=std::min(.5f,960.f/frame.viewport.Width);
  const UINT width=std::max(1u,UINT(std::ceil(frame.viewport.Width*scale))),height=std::max(1u,UINT(std::ceil(frame.viewport.Height*scale)));
  if(colour&&current.Width==source.Width&&current.Height==source.Height&&current.Format==source.Format&&viewFormat==format){
   D3D11_TEXTURE2D_DESC half{};reflection->GetDesc(&half);if(half.Width==width&&half.Height==height)return true;
  }
  colour.Reset();colourView.Reset();reflection.Reset();reflectionView.Reset();reflectionTarget.Reset();
  auto copy=source;copy.Usage=D3D11_USAGE_DEFAULT;copy.CPUAccessFlags=copy.MiscFlags=0;copy.BindFlags=D3D11_BIND_SHADER_RESOURCE;copy.MipLevels=copy.ArraySize=1;
  if(FAILED(device->CreateTexture2D(&copy,nullptr,&colour)))return false;
  D3D11_SHADER_RESOURCE_VIEW_DESC srv{};srv.Format=format;srv.ViewDimension=D3D11_SRV_DIMENSION_TEXTURE2D;srv.Texture2D.MipLevels=1;
  if(FAILED(device->CreateShaderResourceView(colour.Get(),&srv,&colourView)))return false;
  copy.Width=width;copy.Height=height;copy.Format=DXGI_FORMAT_R16G16B16A16_FLOAT;copy.BindFlags=D3D11_BIND_RENDER_TARGET|D3D11_BIND_SHADER_RESOURCE;
  if(FAILED(device->CreateTexture2D(&copy,nullptr,&reflection))||FAILED(device->CreateShaderResourceView(reflection.Get(),nullptr,&reflectionView))||FAILED(device->CreateRenderTargetView(reflection.Get(),nullptr,&reflectionTarget)))return false;
  current=source;viewFormat=format;++allocations;return true;
 }
 bool draw(const Frame& frame,ID3D11RenderTargetView* output,const D3D11_TEXTURE2D_DESC& colourDesc){
  if(!indoor_profile::gallery(frame.flags)||!frame.context||!frame.depth||!output||colourDesc.SampleDesc.Count!=1)return false;
  auto* context=frame.context.Get();ComPtr<ID3D11Device> owner;context->GetDevice(&owner);
  D3D11_RENDER_TARGET_VIEW_DESC view{};output->GetDesc(&view);
  if(!initialize(owner.Get())||!depthReader.prepareDepth(frame,colourDesc)||!targets(colourDesc,view.Format,frame))return false;
  auto camera=roomsurface::relativeCamera(frame.viewProjection,frame.flags);roomsurface::Matrix inverse;if(!roomsurface::inverse(camera,inverse))return false;
  if(!pipeline.enter(context))return false;
  struct Restore{clubgfx::UiPipelineState& state;bool before=clubanim::staticSceneDraw;Restore(clubgfx::UiPipelineState& s):state(s){clubanim::staticSceneDraw=true;}~Restore(){clubanim::staticSceneDraw=before;state.leave();}} restore(pipeline);
  Constants data{};memcpy(data.camera,camera.data(),64);memcpy(data.inverseCamera,inverse.data(),64);
  data.viewport[0]=frame.viewport.TopLeftX;data.viewport[1]=frame.viewport.TopLeftY;data.viewport[2]=frame.viewport.Width;data.viewport[3]=frame.viewport.Height;
  D3D11_TEXTURE2D_DESC half{};reflection->GetDesc(&half);data.target[0]=float(colourDesc.Width);data.target[1]=float(colourDesc.Height);data.target[2]=float(half.Width);data.target[3]=float(half.Height);
  data.depth[0]=(frame.depthState.DepthFunc==D3D11_COMPARISON_GREATER||frame.depthState.DepthFunc==D3D11_COMPARISON_GREATER_EQUAL)?-1.f:1.f;
  data.glass[0]=494.7f;data.glass[1]=84.5f;data.glass[2]=267.5f;data.glass[3]=.85f;
  context->ClearState();ComPtr<ID3D11Resource> source;output->GetResource(&source);context->CopyResource(colour.Get(),source.Get());
  if(depthReader.copyDepth){ComPtr<ID3D11Resource> depth;frame.depth->GetResource(&depth);context->CopyResource(depthReader.depthCopy.Get(),depth.Get());}
  context->OMSetRenderTargets(1,reflectionTarget.GetAddressOf(),nullptr);const float clear[4]{};context->ClearRenderTargetView(reflectionTarget.Get(),clear);
  context->OMSetDepthStencilState(noDepth.Get(),0);context->RSSetState(raster.Get());const D3D11_VIEWPORT halfViewport={0,0,float(half.Width),float(half.Height),0,1};context->RSSetViewports(1,&halfViewport);
  context->UpdateSubresource(constants.Get(),0,nullptr,&data,0,0);auto* cb=constants.Get();context->VSSetConstantBuffers(0,1,&cb);context->PSSetConstantBuffers(0,1,&cb);
  context->VSSetShader(vertex.Get(),nullptr,0);context->PSSetShader(depthReader.sampledDepth.SampleDesc.Count>1?traceMsaa.Get():trace.Get(),nullptr,0);
  ID3D11ShaderResourceView* views[]={colourView.Get(),depthReader.depthView.Get()};context->PSSetShaderResources(0,2,views);context->PSSetSamplers(0,1,sampler.GetAddressOf());
  context->IASetInputLayout(nullptr);context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP);context->Draw(4,0);
  context->OMSetRenderTargets(1,&output,nullptr);context->OMSetBlendState(blend.Get(),nullptr,UINT_MAX);context->RSSetViewports(1,&frame.viewport);
  context->PSSetShader(compose.Get(),nullptr,0);context->PSSetShaderResources(2,1,reflectionView.GetAddressOf());context->Draw(4,0);
  ++frames;return true;
 }
};
inline Renderer renderer;
}
