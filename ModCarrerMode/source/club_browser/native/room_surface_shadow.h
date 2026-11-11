#pragma once
#include "roster_native_shadow.h"
#include "native_animation.h"
#include "actor_surface_normals.h"
#include "indoor_scene_profile.h"

// A room-scoped depth pass from the actual captured native mesh streams.
// Cached ceiling-light depth maps receive on visible 3D surfaces, not only a
// floor quad. Native materials, animation buffers and stadium state are intact.
namespace roomsurface {
using namespace roomshadow;
inline constexpr unsigned size=512,dynamicSize=1024,lights=unsigned(ceilingSources),dynamicSlots=4;
inline std::atomic<unsigned> shadowFrames{0},shadowBuilds{0},shadowFailures{0};
inline std::atomic<unsigned> diagnosticMode{0};
using Matrix=std::array<float,16>;
inline Matrix relativeCamera(const float* source,unsigned flags=0){
 Matrix out;std::copy(source,source+16,out.begin());
 for(unsigned c=0;c<4;++c)out[12+c]=float(double(source[12+c])+double(indoor_profile::originX(flags))*source[c]+double(origin[1])*source[4+c]);
 return out;
}
inline bool inverse(const Matrix& source,Matrix& result){
 double a[4][8]{};for(unsigned r=0;r<4;++r)for(unsigned c=0;c<4;++c){a[r][c]=source[r*4+c];a[r][4+c]=r==c;}
 for(unsigned c=0;c<4;++c){unsigned pivot=c;for(unsigned r=c+1;r<4;++r)if(std::abs(a[r][c])>std::abs(a[pivot][c]))pivot=r;
  if(std::abs(a[pivot][c])<1e-12)return false;if(pivot!=c)for(unsigned i=0;i<8;++i)std::swap(a[c][i],a[pivot][i]);
  const double factor=a[c][c];for(unsigned i=0;i<8;++i)a[c][i]/=factor;
  for(unsigned r=0;r<4;++r)if(r!=c){const double f=a[r][c];for(unsigned i=0;i<8;++i)a[r][i]-=f*a[c][i];}
 }
 for(unsigned r=0;r<4;++r)for(unsigned c=0;c<4;++c){result[r*4+c]=float(a[r][4+c]);if(!std::isfinite(result[r*4+c]))return false;}return true;
}
inline Matrix lightMatrix(unsigned index,unsigned flags=0){
 const auto p=indoor_profile::source(index,flags);const float f=.5773502692f,lightNear=8,lightFar=room_spotlight_r79::kRange;
 const float a=lightFar/(lightFar-lightNear),b=-lightNear*a;
 return {f,0,0,0, 0,0,-a,-1, 0,f,0,0, -p.x*f,-p.z*f,p.y*a+b,p.y};
}
struct alignas(16) CastConstants {float model[16],light[16];};
struct alignas(16) ReceiveConstants {
 float inverseCamera[16],camera[16],viewport[4],depth[4],settings[4];
 float sources[lights][4],dynamic[4],diagnostic[4];
};
inline constexpr const char* shader=R"hlsl(
#ifdef ROOM_CAST
cbuffer Cast:register(b0){row_major float4x4 model;row_major float4x4 light;};
float4 VS(float4 p:POSITION):SV_POSITION{return mul(mul(float4(p.xyz,1),model),light);}
#else
cbuffer Receive:register(b0){row_major float4x4 inverseCamera;row_major float4x4 camera;
 float4 viewport;float4 depthData;float4 settings;float4 sources[36];float4 dynamicLights;float4 diagnostic;};
Texture2DArray<float> shadows:register(t0);
#ifdef ROOM_MSAA
Texture2DMS<float> sceneDepth:register(t1);
#else
Texture2D<float> sceneDepth:register(t1);
#endif
Texture2DArray<float> movingShadows:register(t2);SamplerComparisonState compareShadow:register(s0);
Texture2D<float4> actorNormals:register(t3);
SamplerState softShadow:register(s1);
struct Pixel{float4 p:SV_POSITION;};
Pixel VS(uint id:SV_VertexID){Pixel o;o.p=float4((id&1)?1:-1,(id&2)?-1:1,0,1);return o;}
float readDepth(int2 p){
#ifdef ROOM_MSAA
 uint w,h,n;sceneDepth.GetDimensions(w,h,n);float d=depthData.x<0?0:1;
 [loop]for(uint i=0;i<n;++i){float v=sceneDepth.Load(p,i);d=depthData.x<0?max(d,v):min(d,v);}return d;
#else
 return sceneDepth.Load(int3(p,0));
#endif
}
float3 worldAt(float2 pixel,float depth){
 float2 ndc=(pixel-viewport.xy)/viewport.zw*float2(2,-2)+float2(-1,1);
 float4 p=mul(float4(ndc,depth,1),inverseCamera);return abs(p.w)>.000001?p.xyz/p.w:float3(1e8,1e8,1e8);
}
float energy(float3 source,float3 world){float3 d=source-world;float q=dot(d,d);
 if(d.y<=0||q>=620*620)return 0;float distance=sqrt(q);
 float cone=smoothstep(.5,.78,d.y/distance),fade=1-smoothstep(620*.68,620,distance);return cone*fade*fade;
}
float visibility(float3 world,int index,float3 normal){
 float3 p=sources[index].xyz;float z=p.y-world.y;if(z<=8||z>=620)return 1;
 float2 uv=float2((world.x-p.x)*.5773502692,-(world.z-p.z)*.5773502692)/z*.5+.5;
 if(any(uv<=0)||any(uv>=1))return 1;
 // Correct the PCF reference for the receiver's plane. Comparing every tap
 // against one depth made sloping faces shadow themselves in visible bands.
 float plane=dot(normal,float3((world.x-p.x)/z,-1,(world.z-p.z)/z));
 float2 gradient=abs(plane)>.05?(-8.0*620.0/612.0)*float2(2*normal.x,-2*normal.z)/(.5773502692*z*plane):0;
 gradient=clamp(gradient,-16,16);
 float texel=2*z*1.732050808/512.0;
 float bias=min(3.0,.3+texel*(abs(plane)>.05?.25:1.25));
 float ref=(620.0/612.0)+(-8.0*620.0/612.0)/max(8,z-bias);
 float footprintMargin=(8.0*620.0/612.0)*(1/max(8,z-2)-1/z);
 ref-=min(footprintMargin,(abs(gradient.x)+abs(gradient.y))*.6/512.0);
 float softRef=(620.0/612.0)+(-8.0*620.0/612.0)/max(8,z-bias-min(3.0,1.5+texel*.5));
 softRef-=min(footprintMargin,(abs(gradient.x)+abs(gradient.y))*.6/512.0);
 float value=0;[unroll]for(int y=-1;y<=1;++y)[unroll]for(int x=-1;x<=1;++x)
 {float2 offset=float2(x,y)/512.0;float depth=shadows.SampleLevel(softShadow,float3(uv+offset,index),0);float correction=dot(gradient,offset);
  value+=depth>=.999999?1:smoothstep(softRef+correction,max(softRef+.000001,ref)+correction,depth);}
 value/=9;
 [loop]for(int slot=0;slot<4;++slot)if((int)dynamicLights[slot]==index){
  // Animated skin needs a continuous reference across triangle boundaries.
  // A different slope bias on each face exposes the low-poly mesh itself.
  float movingBias=max(1.25,texel*.5);
  float movingRef=(620.0/612.0)+(-8.0*620.0/612.0)/max(8,z-movingBias);
  float movingSoft=(620.0/612.0)+(-8.0*620.0/612.0)/max(8,z-movingBias-2.5);
  // Finite ceiling fixtures cast a penumbra rather than a razor-sharp point
  // shadow. Estimate blocker separation, then filter a stable light-space
  // disk. No per-frame randomness or camera-dependent sample pattern.
  const float2 search[5]={float2(0,0),float2(4,0),float2(-4,0),float2(0,4),float2(0,-4)};
  float blocker=0,count=0;
  [loop]for(int k=0;k<5;++k){float depth=movingShadows.SampleLevel(softShadow,float3(uv+search[k]/1024.0,slot),0);
   if(depth<movingRef&&depth<.999999){blocker+=(8.0*620.0/612.0)/max(.00001,(620.0/612.0)-depth);count+=1;}}
  if(count==0)continue;
  blocker/=count;
  float radius=clamp(24*(z-blocker)/max(8,blocker)*.5773502692/(2*z)*1024,2,12);
  const float2 disk[16]={float2(.1768,0),float2(-.2258,.2068),float2(.0346,-.3938),float2(.2846,.3712),float2(-.5222,-.0924),float2(.4947,-.3147),float2(-.1655,.6155),float2(-.3156,-.6077),float2(.6846,.2500),float2(-.7123,.2940),float2(.3434,-.7338),float2(.2537,.8083),float2(-.7647,-.4431),float2(.8971,-.1972),float2(-.5475,.7788),float2(-.1265,-.9761)};
  float moving=0;[loop]for(int k=0;k<16;++k){float depth=movingShadows.SampleLevel(softShadow,float3(uv+disk[k]*radius/1024.0,slot),0);
   moving+=depth>=.999999?1:smoothstep(movingSoft,max(movingSoft+.000001,movingRef),depth);}
  value=min(value,moving/16);
 }
 return value;
}
float contact(float3 world,float3 normal,float2 pixel){
 float occlusion=0,total=0;
 const float2 offsets[8]={float2(1,0),float2(-1,0),float2(0,1),float2(0,-1),float2(.7,.7),float2(-.7,.7),float2(.7,-.7),float2(-.7,-.7)};
 [unroll]for(int i=0;i<8;++i){float2 p=floor(pixel+offsets[i]*5)+.5;
  if(any(p<viewport.xy)||any(p>=viewport.xy+viewport.zw))continue;
  float3 other=worldAt(p,readDepth(int2(p)));float3 d=other-world;float q=dot(d,d);
  if(q<.25||q>18*18)continue;float distance=sqrt(q);
  occlusion+=saturate((dot(normal,d/distance)-.12)*2)*(1-distance/18);total+=1;
 }
 return total>0?occlusion/8:0;
}
float4 PS(Pixel input):SV_TARGET{
 float2 pixel=input.p.xy;
 if(pixel.y<viewport.y+viewport.w*settings.z||pixel.y>viewport.y+viewport.w*settings.w)return 0;
 float d=readDepth(int2(pixel));if((depthData.x>0&&d>=.999999)||(depthData.x<0&&d<=.000001))return 0;
 float3 world=worldAt(pixel,d);
 if(abs(world.x)>1500||world.y< -10||world.y>410||world.z< -850||world.z>3000)return 0;
 if(diagnostic.x==1)return float4(1,0,1,.45);
 float3 crossed=cross(ddy(world),ddx(world));float3 normal=crossed/max(length(crossed),.00001);
 float3 cameraPoint=worldAt(pixel,depthData.x<0?1:0);if(dot(normal,cameraPoint-world)<0)normal=-normal;
 float3 smoothNormal=normal;bool actorSurface=false;
 if(dynamicLights.x>=0){float4 n=actorNormals.SampleLevel(softShadow,(pixel-viewport.xy)/viewport.zw,0);float length2=dot(n.xyz,n.xyz);
  if(length2>.25&&length2<2){float3 delta=worldAt(pixel,n.w)-world;if(dot(delta,delta)<4){smoothNormal=n.xyz/sqrt(length2);actorSurface=true;}}}
 float total=0,blocked=0;
 [loop]for(int i=0;i<36;++i){float e=energy(sources[i].xyz,world);
  if(e<.0001)continue;
  // FIFA already lights the model using its authored smooth normals. Do not
  // reweight that lighting with per-triangle normals reconstructed from depth.
  float incidence=actorSurface?saturate(dot(smoothNormal,normalize(sources[i].xyz-world))):1;
  // Keep the room's ambient fill in the denominator. Dividing by vanishing
  // grazing illumination amplifies a tiny terminator error into a dark face.
  total+=e*(actorSurface?.2+.8*incidence:1);
  if(sources[i].w>0)blocked+=e*incidence*(1-visibility(world,i,normal));
 }
 float shade=total>0?blocked/total*settings.x:0;
 shade=max(shade,contact(world,smoothNormal,pixel)*settings.y);
 return float4(0,0,0,saturate(shade));
}
#endif
)hlsl";
struct DepthArray {
 ComPtr<ID3D11Texture2D> texture;ComPtr<ID3D11ShaderResourceView> view;std::vector<ComPtr<ID3D11DepthStencilView>> slices;
 bool make(ID3D11Device* device,unsigned count,unsigned dimension=size){
  D3D11_TEXTURE2D_DESC d{};d.Width=d.Height=dimension;d.MipLevels=1;d.ArraySize=count;d.Format=DXGI_FORMAT_R32_TYPELESS;d.SampleDesc.Count=1;d.BindFlags=D3D11_BIND_DEPTH_STENCIL|D3D11_BIND_SHADER_RESOURCE;
  if(FAILED(device->CreateTexture2D(&d,nullptr,&texture)))return false;
  D3D11_SHADER_RESOURCE_VIEW_DESC s{};s.Format=DXGI_FORMAT_R32_FLOAT;s.ViewDimension=D3D11_SRV_DIMENSION_TEXTURE2DARRAY;s.Texture2DArray.MipLevels=1;s.Texture2DArray.ArraySize=count;
  if(FAILED(device->CreateShaderResourceView(texture.Get(),&s,&view)))return false;
  slices.resize(count);for(unsigned i=0;i<count;++i){D3D11_DEPTH_STENCIL_VIEW_DESC v{};v.Format=DXGI_FORMAT_D32_FLOAT;v.ViewDimension=D3D11_DSV_DIMENSION_TEXTURE2DARRAY;v.Texture2DArray.FirstArraySlice=i;v.Texture2DArray.ArraySize=1;
   if(FAILED(device->CreateDepthStencilView(texture.Get(),&v,&slices[i])))return false;}return true;
 }
};
struct Renderer {
 ComPtr<ID3D11Device> device;clubgfx::UiPipelineState pipeline;roomshadow::Renderer depthReader;ActorNormals actorReceiver;
 DepthArray statics,moving;ComPtr<ID3D11VertexShader> caster,receiver;ComPtr<ID3D11PixelShader> pixel,multisampled;
 ComPtr<ID3D11InputLayout> halfPosition,floatPosition;ComPtr<ID3D11Buffer> castBuffer,receiveBuffer;
 ComPtr<ID3D11DepthStencilState> writeDepth,noDepth;ComPtr<ID3D11RasterizerState> raster;ComPtr<ID3D11BlendState> blend;ComPtr<ID3D11SamplerState> comparison,softSampler;
 uint64_t revisions[lights]{};uint64_t life=0;unsigned next=0;bool ready=false,attempted=false;
 void clear(){pipeline.clear();depthReader.clear();*this=Renderer{};}
 bool initialize(ID3D11Device* owner){
  if(device.Get()!=owner){clear();device=owner;}if(attempted)return ready;attempted=true;
  auto compile=[&](const char* entry,const char* target,const D3D_SHADER_MACRO* macros,ID3DBlob** out){return SUCCEEDED(D3DCompile(shader,strlen(shader),nullptr,macros,nullptr,entry,target,D3DCOMPILE_OPTIMIZATION_LEVEL3,0,out,nullptr));};
  ComPtr<ID3DBlob> v,p;const D3D_SHADER_MACRO castMacros[]={{"ROOM_CAST","1"},{nullptr,nullptr}};
  if(!compile("VS","vs_5_0",castMacros,&v)||FAILED(device->CreateVertexShader(v->GetBufferPointer(),v->GetBufferSize(),nullptr,&caster)))return false;
  D3D11_INPUT_ELEMENT_DESC input={"POSITION",0,DXGI_FORMAT_R16G16B16A16_FLOAT,0,0,D3D11_INPUT_PER_VERTEX_DATA,0};
  if(FAILED(device->CreateInputLayout(&input,1,v->GetBufferPointer(),v->GetBufferSize(),&halfPosition)))return false;
  input.Format=DXGI_FORMAT_R32G32B32_FLOAT;if(FAILED(device->CreateInputLayout(&input,1,v->GetBufferPointer(),v->GetBufferSize(),&floatPosition)))return false;
  v.Reset();if(!compile("VS","vs_5_0",nullptr,&v)||FAILED(device->CreateVertexShader(v->GetBufferPointer(),v->GetBufferSize(),nullptr,&receiver))||!compile("PS","ps_5_0",nullptr,&p)||FAILED(device->CreatePixelShader(p->GetBufferPointer(),p->GetBufferSize(),nullptr,&pixel)))return false;
  p.Reset();const D3D_SHADER_MACRO msaa[]={{"ROOM_MSAA","1"},{nullptr,nullptr}};
  if(!compile("PS","ps_5_0",msaa,&p)||FAILED(device->CreatePixelShader(p->GetBufferPointer(),p->GetBufferSize(),nullptr,&multisampled)))return false;
  auto buffer=[&](unsigned bytes,ID3D11Buffer** out){D3D11_BUFFER_DESC d{};d.ByteWidth=bytes;d.Usage=D3D11_USAGE_DEFAULT;d.BindFlags=D3D11_BIND_CONSTANT_BUFFER;return SUCCEEDED(device->CreateBuffer(&d,nullptr,out));};
  if(!buffer(sizeof(CastConstants),&castBuffer)||!buffer(sizeof(ReceiveConstants),&receiveBuffer)||!statics.make(device.Get(),lights)||!moving.make(device.Get(),dynamicSlots,dynamicSize))return false;
  D3D11_DEPTH_STENCIL_DESC depth{};depth.DepthEnable=TRUE;depth.DepthWriteMask=D3D11_DEPTH_WRITE_MASK_ALL;depth.DepthFunc=D3D11_COMPARISON_LESS_EQUAL;
  if(FAILED(device->CreateDepthStencilState(&depth,&writeDepth)))return false;depth.DepthEnable=FALSE;depth.DepthWriteMask=D3D11_DEPTH_WRITE_MASK_ZERO;
  if(FAILED(device->CreateDepthStencilState(&depth,&noDepth)))return false;
  D3D11_RASTERIZER_DESC r{};r.FillMode=D3D11_FILL_SOLID;r.CullMode=D3D11_CULL_NONE;r.DepthClipEnable=TRUE;if(FAILED(device->CreateRasterizerState(&r,&raster)))return false;
  D3D11_BLEND_DESC b{};auto& t=b.RenderTarget[0];t.BlendEnable=TRUE;t.SrcBlend=D3D11_BLEND_SRC_ALPHA;t.DestBlend=D3D11_BLEND_INV_SRC_ALPHA;t.BlendOp=D3D11_BLEND_OP_ADD;t.SrcBlendAlpha=D3D11_BLEND_ZERO;t.DestBlendAlpha=D3D11_BLEND_ONE;t.BlendOpAlpha=D3D11_BLEND_OP_ADD;t.RenderTargetWriteMask=D3D11_COLOR_WRITE_ENABLE_ALL;
  if(FAILED(device->CreateBlendState(&b,&blend)))return false;
  D3D11_SAMPLER_DESC sample{};sample.Filter=D3D11_FILTER_COMPARISON_MIN_MAG_LINEAR_MIP_POINT;sample.AddressU=sample.AddressV=sample.AddressW=D3D11_TEXTURE_ADDRESS_BORDER;for(float& c:sample.BorderColor)c=1;sample.ComparisonFunc=D3D11_COMPARISON_LESS_EQUAL;sample.MaxLOD=D3D11_FLOAT32_MAX;
  if(FAILED(device->CreateSamplerState(&sample,&comparison)))return false;
  sample.Filter=D3D11_FILTER_MIN_MAG_LINEAR_MIP_POINT;sample.ComparisonFunc=D3D11_COMPARISON_ALWAYS;
  ready=SUCCEEDED(device->CreateSamplerState(&sample,&softSampler))&&depthReader.initialize(device.Get());return ready;
 }
 void cast(ID3D11DeviceContext* context,DepthArray& target,unsigned slice,unsigned light,const Frame& frame){
  const auto& meshes=frame.staticMeshes?*frame.staticMeshes:frame.meshes;
  context->ClearState();context->OMSetRenderTargets(0,nullptr,target.slices[slice].Get());context->ClearDepthStencilView(target.slices[slice].Get(),D3D11_CLEAR_DEPTH,1,0);
  context->OMSetDepthStencilState(writeDepth.Get(),0);context->RSSetState(raster.Get());D3D11_TEXTURE2D_DESC dimensions{};target.texture->GetDesc(&dimensions);D3D11_VIEWPORT viewport={0,0,float(dimensions.Width),float(dimensions.Height),0,1};context->RSSetViewports(1,&viewport);
  context->VSSetShader(caster.Get(),nullptr,0);auto* cb=castBuffer.Get();context->VSSetConstantBuffers(0,1,&cb);context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
  CastConstants data{};auto lightProjection=lightMatrix(light,frame.flags);memcpy(data.light,lightProjection.data(),64);
  for(const auto& mesh:meshes){memcpy(data.model,mesh.transformed?mesh.model:frame.model,64);data.model[12]-=indoor_profile::originX(frame.flags);data.model[13]-=origin[1];
   context->UpdateSubresource(castBuffer.Get(),0,nullptr,&data,0,0);context->IASetInputLayout(mesh.floatPosition?floatPosition.Get():halfPosition.Get());auto* vertex=mesh.vertices.Get();context->IASetVertexBuffers(0,1,&vertex,&mesh.stride,&mesh.offset);context->IASetIndexBuffer(mesh.indices.Get(),mesh.indexFormat,mesh.indexOffset);context->DrawIndexed(mesh.count,mesh.first,mesh.baseVertex);
  }
 }
 bool draw(const Frame& frame,const Frame* actor,ID3D11RenderTargetView* output,const D3D11_TEXTURE2D_DESC& color,uint64_t revision,uint64_t lifecycle,bool protectUi=true){
  if(!frame.context||!frame.depth)return false;auto* context=frame.context.Get();ComPtr<ID3D11Device> owner;context->GetDevice(&owner);
  if(!initialize(owner.Get())||!depthReader.prepareDepth(frame,color))return false;
  if(life!=lifecycle){std::fill(std::begin(revisions),std::end(revisions),0);life=lifecycle;next=0;}
  auto camera=relativeCamera(frame.viewProjection,frame.flags);Matrix inverted;if(!inverse(camera,inverted))return false;
  if(!pipeline.enter(context))return false;struct Restore{clubgfx::UiPipelineState& pipeline;bool previous;Restore(clubgfx::UiPipelineState& p):pipeline(p),previous(clubanim::staticSceneDraw){clubanim::staticSceneDraw=true;}~Restore(){clubanim::staticSceneDraw=previous;pipeline.leave();}} restore{pipeline};
  const auto activeLights=indoor_profile::lightCount(frame.flags);
  if(next>=activeLights)next=0;
  if(revisions[next]!=revision){cast(context,statics,next,next,frame);revisions[next]=revision;++shadowBuilds;}next=(next+1)%activeLights;
  ReceiveConstants data{};memcpy(data.inverseCamera,inverted.data(),64);memcpy(data.camera,camera.data(),64);
  data.viewport[0]=frame.viewport.TopLeftX;data.viewport[1]=frame.viewport.TopLeftY;data.viewport[2]=frame.viewport.Width;data.viewport[3]=frame.viewport.Height;
  const auto compare=frame.depthState.DepthFunc;data.depth[0]=(compare==D3D11_COMPARISON_GREATER||compare==D3D11_COMPARISON_GREATER_EQUAL)?-1.f:1.f;
  data.settings[0]=.42f;data.settings[1]=.22f;data.settings[2]=protectUi?.13f:0;data.settings[3]=protectUi?.84f:1;
  data.diagnostic[0]=float(diagnosticMode.load());
  for(unsigned i=0;i<activeLights;++i){const auto s=indoor_profile::source(i,frame.flags);data.sources[i][0]=s.x;data.sources[i][1]=s.y;data.sources[i][2]=s.z;data.sources[i][3]=revisions[i]?1.f:0.f;}
  std::fill(std::begin(data.dynamic),std::end(data.dynamic),-1.f);
  bool actorNormalReady=false;
  if(actor&&!actor->meshes.empty()&&actor->context.Get()==context&&GetTickCount64()-actor->tick<250){
   std::array<std::pair<float,unsigned>,lights> distances;for(unsigned i=0;i<lights;++i){const auto& s=room_spotlight_r79::kSources[i];const float x=s.x,z=s.z-origin[2];distances[i]={x*x+z*z,i};}std::sort(distances.begin(),distances.end());
   for(unsigned slot=0;slot<dynamicSlots;++slot){unsigned light=distances[slot].second;cast(context,moving,slot,light,*actor);data.dynamic[slot]=float(light);}
   actorNormalReady=actorReceiver.draw(frame,*actor,camera.data());
  }
  context->ClearState();if(depthReader.copyDepth){ComPtr<ID3D11Resource> source;frame.depth->GetResource(&source);context->CopyResource(depthReader.depthCopy.Get(),source.Get());}
  context->OMSetRenderTargets(1,&output,nullptr);context->OMSetDepthStencilState(noDepth.Get(),0);context->OMSetBlendState(blend.Get(),nullptr,UINT_MAX);context->RSSetState(raster.Get());context->RSSetViewports(1,&frame.viewport);
  context->UpdateSubresource(receiveBuffer.Get(),0,nullptr,&data,0,0);auto* cb=receiveBuffer.Get();context->VSSetConstantBuffers(0,1,&cb);context->PSSetConstantBuffers(0,1,&cb);
  context->VSSetShader(receiver.Get(),nullptr,0);context->PSSetShader(depthReader.sampledDepth.SampleDesc.Count>1?multisampled.Get():pixel.Get(),nullptr,0);
  ID3D11ShaderResourceView* views[]={statics.view.Get(),depthReader.depthView.Get(),moving.view.Get(),actorNormalReady?actorReceiver.view.Get():nullptr};context->PSSetShaderResources(0,4,views);ID3D11SamplerState* samplers[]={comparison.Get(),softSampler.Get()};context->PSSetSamplers(0,2,samplers);context->IASetInputLayout(nullptr);context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP);context->Draw(4,0);
  ++shadowFrames;return true;
 }
};
inline Renderer renderer;
}
