#pragma once
#include "roster_native_shadow.h"

// Private, bounded receiver data. Interpolate the actor's actual skinned
// normals without altering FIFA's materials, geometry or animation buffers.
namespace roomsurface {
struct ActorNormals {
 using Frame=roomshadow::Frame;
 template<class T>using Ptr=roomshadow::ComPtr<T>;
 Ptr<ID3D11Device> device;Ptr<ID3D11VertexShader> vertex;Ptr<ID3D11PixelShader> pixel;
 Ptr<ID3D11InputLayout> packed,halfNormal,floatNormal;Ptr<ID3D11Buffer> constants;
 Ptr<ID3D11Texture2D> color,depth;Ptr<ID3D11RenderTargetView> target;Ptr<ID3D11ShaderResourceView> view;Ptr<ID3D11DepthStencilView> dsv;
 Ptr<ID3D11DepthStencilState> less,greater;Ptr<ID3D11RasterizerState> raster;
 unsigned width=0,height=0;bool ready=false,attempted=false;
 struct alignas(16) Constants{float model[16],camera[16],format[4];};
 void clear(){*this=ActorNormals{};}
 bool initialize(ID3D11Device* owner){
  if(device.Get()!=owner){clear();device=owner;}if(attempted)return ready;attempted=true;
  const char* source=R"hlsl(
cbuffer C:register(b0){row_major float4x4 model;row_major float4x4 camera;float4 format;};
struct I{float4 p:POSITION;float4 n:NORMAL;};struct P{float4 p:SV_POSITION;float3 n:NORMAL;};
P VS(I i){P o;float3 n=i.n.xyz;
 if(format.x<.5){uint3 b=uint3(round(n*1023));n=float3(int(b.x)-(b.x>511?1024:0),int(b.y)-(b.y>511?1024:0),int(b.z)-(b.z>511?1024:0))/511.0;}
 o.p=mul(mul(float4(i.p.xyz,1),model),camera);o.n=mul(float4(n,0),model).xyz;return o;}
float4 PS(P i):SV_TARGET{return float4(i.n/max(.00001,length(i.n)),i.p.z);}
)hlsl";
  Ptr<ID3DBlob> vs,ps;
  if(FAILED(D3DCompile(source,strlen(source),nullptr,nullptr,nullptr,"VS","vs_5_0",D3DCOMPILE_OPTIMIZATION_LEVEL3,0,&vs,nullptr))||FAILED(D3DCompile(source,strlen(source),nullptr,nullptr,nullptr,"PS","ps_5_0",D3DCOMPILE_OPTIMIZATION_LEVEL3,0,&ps,nullptr)))return false;
  if(FAILED(device->CreateVertexShader(vs->GetBufferPointer(),vs->GetBufferSize(),nullptr,&vertex))||FAILED(device->CreatePixelShader(ps->GetBufferPointer(),ps->GetBufferSize(),nullptr,&pixel)))return false;
  D3D11_INPUT_ELEMENT_DESC fields[]={{"POSITION",0,DXGI_FORMAT_R16G16B16A16_FLOAT,0,0,D3D11_INPUT_PER_VERTEX_DATA,0},{"NORMAL",0,DXGI_FORMAT_R10G10B10A2_UNORM,0,8,D3D11_INPUT_PER_VERTEX_DATA,0}};
  if(FAILED(device->CreateInputLayout(fields,2,vs->GetBufferPointer(),vs->GetBufferSize(),&packed)))return false;
  // FIFA's live animation stream expands the two packed vectors to half4
  // (20 -> 28-byte vertices). Its normals are no longer signed 10-bit data.
  fields[1].Format=DXGI_FORMAT_R16G16B16A16_FLOAT;
  if(FAILED(device->CreateInputLayout(fields,2,vs->GetBufferPointer(),vs->GetBufferSize(),&halfNormal)))return false;
  fields[0].Format=DXGI_FORMAT_R32G32B32_FLOAT;fields[1].Format=DXGI_FORMAT_R32G32B32_FLOAT;fields[1].AlignedByteOffset=12;
  if(FAILED(device->CreateInputLayout(fields,2,vs->GetBufferPointer(),vs->GetBufferSize(),&floatNormal)))return false;
  D3D11_BUFFER_DESC cb{};cb.ByteWidth=sizeof(Constants);cb.BindFlags=D3D11_BIND_CONSTANT_BUFFER;if(FAILED(device->CreateBuffer(&cb,nullptr,&constants)))return false;
  D3D11_DEPTH_STENCIL_DESC ds{};ds.DepthEnable=TRUE;ds.DepthWriteMask=D3D11_DEPTH_WRITE_MASK_ALL;ds.DepthFunc=D3D11_COMPARISON_LESS_EQUAL;if(FAILED(device->CreateDepthStencilState(&ds,&less)))return false;
  ds.DepthFunc=D3D11_COMPARISON_GREATER_EQUAL;if(FAILED(device->CreateDepthStencilState(&ds,&greater)))return false;
  D3D11_RASTERIZER_DESC rs{};rs.FillMode=D3D11_FILL_SOLID;rs.CullMode=D3D11_CULL_NONE;rs.DepthClipEnable=TRUE;ready=SUCCEEDED(device->CreateRasterizerState(&rs,&raster));return ready;
 }
 bool resize(unsigned w,unsigned h){
  if(w==width&&h==height&&view)return true;
  color.Reset();depth.Reset();target.Reset();view.Reset();dsv.Reset();width=height=0;
  D3D11_TEXTURE2D_DESC desc{};desc.Width=w;desc.Height=h;desc.MipLevels=desc.ArraySize=desc.SampleDesc.Count=1;desc.Format=DXGI_FORMAT_R32G32B32A32_FLOAT;desc.BindFlags=D3D11_BIND_RENDER_TARGET|D3D11_BIND_SHADER_RESOURCE;
  if(FAILED(device->CreateTexture2D(&desc,nullptr,&color))||FAILED(device->CreateRenderTargetView(color.Get(),nullptr,&target))||FAILED(device->CreateShaderResourceView(color.Get(),nullptr,&view)))return false;
  desc.Format=DXGI_FORMAT_D32_FLOAT;desc.BindFlags=D3D11_BIND_DEPTH_STENCIL;
  if(FAILED(device->CreateTexture2D(&desc,nullptr,&depth))||FAILED(device->CreateDepthStencilView(depth.Get(),nullptr,&dsv)))return false;
  width=w;height=h;return true;
 }
 bool draw(const Frame& scene,const Frame& actor,const float* camera){
  Ptr<ID3D11Device> owner;scene.context->GetDevice(&owner);if(!initialize(owner.Get()))return false;
  float scale=(std::min)(1.f,1024.f/(std::max)(scene.viewport.Width,scene.viewport.Height));
  if(!resize((std::max)(1u,unsigned(scene.viewport.Width*scale)),(std::max)(1u,unsigned(scene.viewport.Height*scale))))return false;
  auto* c=scene.context.Get();c->ClearState();const float zero[4]{};c->ClearRenderTargetView(target.Get(),zero);
  bool reversed=scene.depthState.DepthFunc==D3D11_COMPARISON_GREATER||scene.depthState.DepthFunc==D3D11_COMPARISON_GREATER_EQUAL;
  c->ClearDepthStencilView(dsv.Get(),D3D11_CLEAR_DEPTH,reversed?0.f:1.f,0);auto* rt=target.Get();c->OMSetRenderTargets(1,&rt,dsv.Get());c->OMSetDepthStencilState(reversed?greater.Get():less.Get(),0);c->RSSetState(raster.Get());D3D11_VIEWPORT viewport={0,0,float(width),float(height),0,1};c->RSSetViewports(1,&viewport);
  c->VSSetShader(vertex.Get(),nullptr,0);c->PSSetShader(pixel.Get(),nullptr,0);auto* cb=constants.Get();c->VSSetConstantBuffers(0,1,&cb);c->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
  Constants values{};memcpy(values.camera,camera,64);
  for(const auto& mesh:actor.meshes){if(!mesh.vertices||!mesh.indices||mesh.stride<(mesh.floatPosition?24u:12u))continue;
   memcpy(values.model,mesh.transformed?mesh.model:actor.model,64);values.model[12]-=roomshadow::origin[0];values.model[13]-=roomshadow::origin[1];values.format[0]=mesh.floatPosition?1.f:mesh.stride==28?2.f:0.f;
   c->UpdateSubresource(constants.Get(),0,nullptr,&values,0,0);c->IASetInputLayout(mesh.floatPosition?floatNormal.Get():mesh.stride==28?halfNormal.Get():packed.Get());auto* buffer=mesh.vertices.Get();c->IASetVertexBuffers(0,1,&buffer,&mesh.stride,&mesh.offset);c->IASetIndexBuffer(mesh.indices.Get(),mesh.indexFormat,mesh.indexOffset);c->DrawIndexed(mesh.count,mesh.first,mesh.baseVertex);
  }
  return true;
 }
};
}
