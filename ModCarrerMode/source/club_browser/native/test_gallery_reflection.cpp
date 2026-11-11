#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <cassert>
#include <iostream>
#include "gallery_reflection.h"
using namespace roomshadow;
static std::vector<unsigned char> pixels(ID3D11Device* d,ID3D11DeviceContext* c,ID3D11Texture2D* source){
 D3D11_TEXTURE2D_DESC desc{};source->GetDesc(&desc);desc.BindFlags=desc.MiscFlags=0;desc.Usage=D3D11_USAGE_STAGING;desc.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
 ComPtr<ID3D11Texture2D> copy;assert(SUCCEEDED(d->CreateTexture2D(&desc,nullptr,&copy)));c->CopyResource(copy.Get(),source);
 D3D11_MAPPED_SUBRESOURCE map{};assert(SUCCEEDED(c->Map(copy.Get(),0,D3D11_MAP_READ,0,&map)));std::vector<unsigned char> result(desc.Width*desc.Height*4);
 for(unsigned y=0;y<desc.Height;++y)memcpy(result.data()+y*desc.Width*4,(char*)map.pData+y*map.RowPitch,desc.Width*4);c->Unmap(copy.Get(),0);return result;
}
int wmain(int argc,wchar_t**argv){
 _set_error_mode(_OUT_TO_STDERR);_set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);
 assert(argc==2&&loadShaders(argv[1]));
 ComPtr<ID3D11Device> device;ComPtr<ID3D11DeviceContext> context;
 assert(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&device,nullptr,&context)));
 gallery_reflection::Renderer renderer;
 if(!renderer.initialize(device.Get())){std::cerr<<renderer.shaderError;return 1;}
 const char* fixture=R"(
 cbuffer Data:register(b0){row_major float4x4 camera;};
 struct P{float4 position:SV_POSITION;float3 world:TEXCOORD0;};
 P VS(float3 p:POSITION){P o;o.position=mul(float4(p,1),camera);o.world=p;return o;}
 float4 PS(P p):SV_TARGET{return float4((p.world.x+650)/1300,.12,(p.world.z+750)/1500*.6+.2,1);})";
 ComPtr<ID3DBlob> v,p;assert(SUCCEEDED(D3DCompile(fixture,strlen(fixture),nullptr,nullptr,nullptr,"VS","vs_5_0",0,0,&v,nullptr)));
 assert(SUCCEEDED(D3DCompile(fixture,strlen(fixture),nullptr,nullptr,nullptr,"PS","ps_5_0",0,0,&p,nullptr)));
 ComPtr<ID3D11VertexShader> vs;ComPtr<ID3D11PixelShader> ps;ComPtr<ID3D11InputLayout> layout;
 assert(SUCCEEDED(device->CreateVertexShader(v->GetBufferPointer(),v->GetBufferSize(),nullptr,&vs))&&SUCCEEDED(device->CreatePixelShader(p->GetBufferPointer(),p->GetBufferSize(),nullptr,&ps)));
 const D3D11_INPUT_ELEMENT_DESC input={"POSITION",0,DXGI_FORMAT_R32G32B32_FLOAT,0,0,D3D11_INPUT_PER_VERTEX_DATA,0};
 assert(SUCCEEDED(device->CreateInputLayout(&input,1,v->GetBufferPointer(),v->GetBufferSize(),&layout)));
 std::vector<std::array<float,3>> vertices;
 auto quad=[&](std::array<float,3>a,std::array<float,3>b,std::array<float,3>c,std::array<float,3>d){for(auto point:{a,b,c,a,c,d})vertices.push_back(point);};
 quad({-650,0,-750},{650,0,-750},{650,330,-750},{-650,330,-750});
 quad({-650,0,-750},{-650,0,750},{650,0,750},{650,0,-750});
 quad({-650,330,-750},{650,330,-750},{650,330,750},{-650,330,750});
 quad({-650,0,750},{-650,0,-750},{-650,330,-750},{-650,330,750});
 quad({650,0,-750},{650,0,750},{650,330,750},{650,330,-750});
 ComPtr<ID3D11Buffer> geometry,constants;D3D11_BUFFER_DESC b{};b.ByteWidth=UINT(vertices.size()*sizeof(vertices[0]));b.BindFlags=D3D11_BIND_VERTEX_BUFFER;D3D11_SUBRESOURCE_DATA initial{vertices.data(),0,0};assert(SUCCEEDED(device->CreateBuffer(&b,&initial,&geometry)));
 b.ByteWidth=64;b.BindFlags=D3D11_BIND_CONSTANT_BUFFER;assert(SUCCEEDED(device->CreateBuffer(&b,nullptr,&constants)));
 ComPtr<ID3D11RasterizerState> raster;D3D11_RASTERIZER_DESC rd{};rd.FillMode=D3D11_FILL_SOLID;rd.CullMode=D3D11_CULL_NONE;rd.DepthClipEnable=TRUE;assert(SUCCEEDED(device->CreateRasterizerState(&rd,&raster)));
 for(unsigned width:{320u,420u})for(bool reversed:{false,true}){
  D3D11_TEXTURE2D_DESC desc{};desc.Width=width;desc.Height=180;desc.MipLevels=desc.ArraySize=desc.SampleDesc.Count=1;desc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;desc.BindFlags=D3D11_BIND_RENDER_TARGET;
  ComPtr<ID3D11Texture2D> color,depth;ComPtr<ID3D11RenderTargetView> output;ComPtr<ID3D11DepthStencilView> dsv;
  assert(SUCCEEDED(device->CreateTexture2D(&desc,nullptr,&color))&&SUCCEEDED(device->CreateRenderTargetView(color.Get(),nullptr,&output)));
  auto dd=desc;dd.Format=DXGI_FORMAT_D32_FLOAT;dd.BindFlags=D3D11_BIND_DEPTH_STENCIL;assert(SUCCEEDED(device->CreateTexture2D(&dd,nullptr,&depth))&&SUCCEEDED(device->CreateDepthStencilView(depth.Get(),nullptr,&dsv)));
  Frame frame;frame.flags=room_shadow_bridge::Gallery;frame.context=context;frame.depth=dsv;frame.viewport={0,0,float(width),180,0,1};frame.depthState.DepthEnable=TRUE;frame.depthState.DepthFunc=reversed?D3D11_COMPARISON_GREATER_EQUAL:D3D11_COMPARISON_LESS_EQUAL;
  D3D11_DEPTH_STENCIL_DESC ds{};ds.DepthEnable=TRUE;ds.DepthWriteMask=D3D11_DEPTH_WRITE_MASK_ALL;ds.DepthFunc=frame.depthState.DepthFunc;ComPtr<ID3D11DepthStencilState> depthState;assert(SUCCEEDED(device->CreateDepthStencilState(&ds,&depthState)));
  std::vector<unsigned char> first;
  for(float eye:{0.f,80.f}){
   auto& m=frame.viewProjection;std::fill(std::begin(m),std::end(m),0);const float sy=1/std::tan(70.f*.00872664626f),sx=sy*180/width,a=3000.f/2999,bias=-a;
   m[0]=sx;m[5]=sy;m[10]=-a;m[11]=-1;m[12]=(100000-eye)*sx;m[13]=-1170*sy;m[14]=660*a+bias;m[15]=660;
   if(reversed)for(unsigned r=0;r<4;++r)m[r*4+2]=m[r*4+3]-m[r*4+2];
   const auto relative=roomsurface::relativeCamera(m,frame.flags);context->UpdateSubresource(constants.Get(),0,nullptr,relative.data(),0,0);
   context->ClearState();auto* target=output.Get();context->OMSetRenderTargets(1,&target,dsv.Get());context->OMSetDepthStencilState(depthState.Get(),0);context->RSSetViewports(1,&frame.viewport);context->RSSetState(raster.Get());
   const float clear[]={0,0,0,1};context->ClearRenderTargetView(output.Get(),clear);context->ClearDepthStencilView(dsv.Get(),D3D11_CLEAR_DEPTH,reversed?0:1,0);
   context->VSSetShader(vs.Get(),nullptr,0);context->PSSetShader(ps.Get(),nullptr,0);context->VSSetConstantBuffers(0,1,constants.GetAddressOf());context->IASetInputLayout(layout.Get());context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
   auto* buffer=geometry.Get();UINT stride=12,offset=0;context->IASetVertexBuffers(0,1,&buffer,&stride,&offset);context->Draw(UINT(vertices.size()),0);
   const auto before=pixels(device.Get(),context.Get(),color.Get());
   assert(renderer.draw(frame,output.Get(),desc));const auto after=pixels(device.Get(),context.Get(),color.Get());
   unsigned changes=0;for(unsigned i=0;i<before.size();i+=4)if(before[i]!=after[i]||before[i+1]!=after[i+1]||before[i+2]!=after[i+2])++changes;
   std::cerr<<"reflection width="<<width<<" reversed="<<reversed<<" eye="<<eye<<" changed="<<changes<<"\n";assert(changes>100);
   for(unsigned y=0;y<desc.Height;++y)for(unsigned x=width/2-2;x<width/2+2;++x){unsigned i=(y*width+x)*4;assert(before[i]==after[i]&&before[i+1]==after[i+1]&&before[i+2]==after[i+2]);}
   ComPtr<ID3D11RenderTargetView> rt;ComPtr<ID3D11DepthStencilView> restored;context->OMGetRenderTargets(1,&rt,&restored);assert(rt.Get()==output.Get()&&restored.Get()==dsv.Get());
   ComPtr<ID3D11PixelShader> restoredPixel;context->PSGetShader(&restoredPixel,nullptr,nullptr);assert(restoredPixel.Get()==ps.Get());
   if(first.empty())first=after;else assert(first!=after);
  }
 }
 Frame ultra;ultra.viewport={0,0,3840,1080,0,1};D3D11_TEXTURE2D_DESC ultraDesc{};
 ultraDesc.Width=3840;ultraDesc.Height=1080;ultraDesc.MipLevels=ultraDesc.ArraySize=ultraDesc.SampleDesc.Count=1;ultraDesc.Format=DXGI_FORMAT_R16G16B16A16_FLOAT;
 assert(renderer.targets(ultraDesc,ultraDesc.Format,ultra));D3D11_TEXTURE2D_DESC bounded{};renderer.reflection->GetDesc(&bounded);assert(bounded.Width==960&&bounded.Height==270);
 const auto allocated=gallery_reflection::allocations.load();assert(renderer.targets(ultraDesc,ultraDesc.Format,ultra)&&gallery_reflection::allocations==allocated);
 std::cout<<"PASS actual glass reflections: current scene colour/depth, two camera positions and display aspects, reversed depth, glass-only coverage, bounded HDR ultrawide targets and full native state restoration\n";
}
