#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <cassert>
#include <fstream>
#include <iostream>
#include <filesystem>
#include "room_surface_shadow.h"
using namespace roomshadow;
static std::vector<unsigned char> readPixels(ID3D11Device* d,ID3D11DeviceContext* c,ID3D11Texture2D* source){
 D3D11_TEXTURE2D_DESC desc{};source->GetDesc(&desc);desc.BindFlags=desc.MiscFlags=0;desc.Usage=D3D11_USAGE_STAGING;desc.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
 ComPtr<ID3D11Texture2D> copy;assert(SUCCEEDED(d->CreateTexture2D(&desc,nullptr,&copy)));c->CopyResource(copy.Get(),source);D3D11_MAPPED_SUBRESOURCE map{};assert(SUCCEEDED(c->Map(copy.Get(),0,D3D11_MAP_READ,0,&map)));
 std::vector<unsigned char> bytes(desc.Width*desc.Height*4);for(unsigned y=0;y<desc.Height;++y)memcpy(bytes.data()+y*desc.Width*4,(char*)map.pData+y*map.RowPitch,desc.Width*4);c->Unmap(copy.Get(),0);return bytes;
}
int wmain(int argc,wchar_t**argv){
 _set_error_mode(_OUT_TO_STDERR);_set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);assert(argc>=2&&loadShaders(argv[1]));
 ComPtr<ID3D11Device> device;ComPtr<ID3D11DeviceContext> context;assert(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&device,nullptr,&context)));
 D3D11_TEXTURE2D_DESC desc{};desc.Width=192;desc.Height=256;desc.MipLevels=desc.ArraySize=desc.SampleDesc.Count=1;desc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;desc.BindFlags=D3D11_BIND_RENDER_TARGET;
 ComPtr<ID3D11Texture2D> color,ids,depth;ComPtr<ID3D11RenderTargetView> output,idOutput;ComPtr<ID3D11DepthStencilView> dsv;
 assert(SUCCEEDED(device->CreateTexture2D(&desc,nullptr,&color))&&SUCCEEDED(device->CreateRenderTargetView(color.Get(),nullptr,&output)));auto idDesc=desc;idDesc.Format=DXGI_FORMAT_R32_UINT;assert(SUCCEEDED(device->CreateTexture2D(&idDesc,nullptr,&ids))&&SUCCEEDED(device->CreateRenderTargetView(ids.Get(),nullptr,&idOutput)));
 auto depthDesc=desc;depthDesc.Format=DXGI_FORMAT_D32_FLOAT;depthDesc.BindFlags=D3D11_BIND_DEPTH_STENCIL;assert(SUCCEEDED(device->CreateTexture2D(&depthDesc,nullptr,&depth))&&SUCCEEDED(device->CreateDepthStencilView(depth.Get(),nullptr,&dsv)));
 struct V{float p[3],n[3];};std::vector<V> vertices;std::vector<uint16_t> indices;constexpr unsigned rings=8,sectors=12;
 for(unsigned r=0;r<=rings;++r)for(unsigned s=0;s<=sectors;++s){float a=float(r)*3.14159265f/rings,b=float(s)*6.2831853f/sectors;V v{};v.n[0]=std::sin(a)*std::cos(b);v.n[1]=std::cos(a);v.n[2]=std::sin(a)*std::sin(b);v.p[0]=45*v.n[0];v.p[1]=110+45*v.n[1];v.p[2]=45*v.n[2];vertices.push_back(v);}
 for(unsigned r=0;r<rings;++r)for(unsigned s=0;s<sectors;++s){unsigned a=r*(sectors+1)+s,b=a+sectors+1;for(unsigned i:{a,b,a+1,a+1,b,b+1})indices.push_back(uint16_t(i));}
 if(argc>4){std::ifstream input(argv[4],std::ios::binary);unsigned nv=0,ni=0;input.read((char*)&nv,4);input.read((char*)&ni,4);assert(nv>0&&nv<65536&&ni>0&&ni<3000000);vertices.resize(nv);indices.resize(ni);input.read((char*)vertices.data(),nv*sizeof(V));input.read((char*)indices.data(),ni*2);assert(input);}
 Mesh mesh;mesh.floatPosition=mesh.transformed=true;mesh.stride=sizeof(V);mesh.count=unsigned(indices.size());mesh.indexFormat=DXGI_FORMAT_R16_UINT;for(unsigned i=0;i<4;++i)mesh.model[i*5]=1;mesh.model[12]=origin[0];mesh.model[13]=origin[1];mesh.model[14]=origin[2];
 D3D11_BUFFER_DESC bd{};bd.ByteWidth=UINT(vertices.size()*sizeof(V));bd.BindFlags=D3D11_BIND_VERTEX_BUFFER;D3D11_SUBRESOURCE_DATA data{vertices.data(),0,0};assert(SUCCEEDED(device->CreateBuffer(&bd,&data,&mesh.vertices)));bd.ByteWidth=UINT(indices.size()*2);bd.BindFlags=D3D11_BIND_INDEX_BUFFER;data.pSysMem=indices.data();assert(SUCCEEDED(device->CreateBuffer(&bd,&data,&mesh.indices)));
 Frame frame;frame.context=context;frame.depth=dsv;frame.viewport={0,0,192,256,0,1};frame.depthState.DepthEnable=TRUE;frame.depthState.DepthFunc=D3D11_COMPARISON_LESS_EQUAL;frame.meshes={mesh};memcpy(frame.model,mesh.model,64);
 frame.viewProjection[0]=1/70.f;frame.viewProjection[5]=1/90.f;frame.viewProjection[10]=-1/800.f;frame.viewProjection[12]=-origin[0]/70;frame.viewProjection[13]=-(origin[1]+110)/90;frame.viewProjection[14]=900/800.f;frame.viewProjection[15]=1;
 if(argc>4){frame.viewProjection[0]=1/45.f;frame.viewProjection[5]=1/60.f;frame.viewProjection[12]=-origin[0]/45;frame.viewProjection[13]=-(origin[1]+140)/60;}
 roomsurface::Renderer renderer;assert(renderer.initialize(device.Get()));
 const char* shader="cbuffer C:register(b0){row_major float4x4 model;row_major float4x4 camera;};struct I{float3 p:POSITION;float3 n:NORMAL;};struct P{float4 p:SV_POSITION;float3 n:NORMAL;};P VS(I i){P o;o.p=mul(mul(float4(i.p,1),model),camera);o.n=i.n;return o;}struct O{float4 c:SV_TARGET0;uint id:SV_TARGET1;};O PS(P p,uint id:SV_PrimitiveID){O o;float l=.65+.2*normalize(p.n).y;o.c=float4(l,l,l,1);o.id=id+1;return o;}";
 ComPtr<ID3DBlob> vb,ps;assert(SUCCEEDED(D3DCompile(shader,strlen(shader),nullptr,nullptr,nullptr,"VS","vs_5_0",0,0,&vb,nullptr))&&SUCCEEDED(D3DCompile(shader,strlen(shader),nullptr,nullptr,nullptr,"PS","ps_5_0",0,0,&ps,nullptr)));
 ComPtr<ID3D11VertexShader> vertex;ComPtr<ID3D11PixelShader> pixel;ComPtr<ID3D11InputLayout> layout;assert(SUCCEEDED(device->CreateVertexShader(vb->GetBufferPointer(),vb->GetBufferSize(),nullptr,&vertex))&&SUCCEEDED(device->CreatePixelShader(ps->GetBufferPointer(),ps->GetBufferSize(),nullptr,&pixel)));
 D3D11_INPUT_ELEMENT_DESC elements[]={{"POSITION",0,DXGI_FORMAT_R32G32B32_FLOAT,0,0,D3D11_INPUT_PER_VERTEX_DATA,0},{"NORMAL",0,DXGI_FORMAT_R32G32B32_FLOAT,0,12,D3D11_INPUT_PER_VERTEX_DATA,0}};assert(SUCCEEDED(device->CreateInputLayout(elements,2,vb->GetBufferPointer(),vb->GetBufferSize(),&layout)));
 const float white[]={1,1,1,1},zero[]={0,0,0,0};context->ClearRenderTargetView(output.Get(),white);context->ClearRenderTargetView(idOutput.Get(),zero);context->ClearDepthStencilView(dsv.Get(),D3D11_CLEAR_DEPTH,1,0);ID3D11RenderTargetView* targets[]={output.Get(),idOutput.Get()};context->OMSetRenderTargets(2,targets,dsv.Get());context->OMSetDepthStencilState(renderer.writeDepth.Get(),0);context->RSSetState(renderer.raster.Get());context->RSSetViewports(1,&frame.viewport);
 roomsurface::CastConstants c{};memcpy(c.model,mesh.model,64);c.model[12]-=origin[0];c.model[13]-=origin[1];auto camera=roomsurface::relativeCamera(frame.viewProjection);memcpy(c.light,camera.data(),64);context->UpdateSubresource(renderer.castBuffer.Get(),0,nullptr,&c,0,0);auto* cb=renderer.castBuffer.Get();context->VSSetConstantBuffers(0,1,&cb);context->VSSetShader(vertex.Get(),nullptr,0);context->PSSetShader(pixel.Get(),nullptr,0);context->IASetInputLayout(layout.Get());auto* buffer=mesh.vertices.Get();context->IASetVertexBuffers(0,1,&buffer,&mesh.stride,&mesh.offset);context->IASetIndexBuffer(mesh.indices.Get(),mesh.indexFormat,0);context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);context->DrawIndexed(mesh.count,0,0);
 auto base=readPixels(device.Get(),context.Get(),color.Get()),faces=readPixels(device.Get(),context.Get(),ids.Get());Frame actor=frame;bool dynamic=argc>3;uint64_t revision=1;if(dynamic)frame.meshes.clear();auto draw=[&](){frame.tick=actor.tick=GetTickCount64();context->ClearRenderTargetView(output.Get(),white);assert(renderer.draw(frame,dynamic?&actor:nullptr,output.Get(),desc,revision,1,false));return readPixels(device.Get(),context.Get(),color.Get());};bool actorMode=dynamic;dynamic=false;frame.viewport.Width=frame.viewport.Height=1;for(unsigned i=0;i<roomsurface::lights;++i)draw();frame.viewport=actor.viewport;dynamic=actorMode;auto shaded=draw();
 double boundary=0,inside=0;unsigned boundaryCount=0,insideCount=0,dark=0;auto* face=reinterpret_cast<const uint32_t*>(faces.data());
 for(unsigned y=2;y<254;++y)for(unsigned x=2;x<190;++x){unsigned i=y*192+x;if(!face[i])continue;dark+=shaded[i*4]<250;for(unsigned j:{i+1,i+192})if(face[j]){double difference=std::abs(int(shaded[i*4])-int(shaded[j*4]))/255.;if(face[i]!=face[j]){boundary+=difference;++boundaryCount;}else{inside+=difference;++insideCount;}}}
 assert(boundaryCount>100&&insideCount>1000);double mean=boundary/boundaryCount;std::cout<<"curve boundary="<<mean<<" inside="<<inside/insideCount<<" samples="<<boundaryCount<<"\n";
 // The previous shader exceeds .011 here and exposes every polygon seam.
 if(actorMode&&argc<=4)assert(mean<.004&&mean-inside/insideCount<.0015);
 if(argc>2){std::filesystem::path out=argv[2];std::filesystem::create_directories(out);std::ofstream image(out/L"curve.rgba",std::ios::binary);image.write((char*)shaded.data(),shaded.size());std::ofstream report(out/L"curve.txt");report<<mean<<' '<<inside/insideCount<<' '<<boundaryCount<<'\n';}
 // Smooth self-shadowing must not disable real occlusion: an overhead object
 // still casts a broad shadow onto the same curved, animated receiver.
 if(actorMode){
  V panel[]={{{-90,180,-90},{0,1,0}},{{90,180,-90},{0,1,0}},{{90,180,90},{0,1,0}},{{-90,180,90},{0,1,0}}};
  uint16_t panelIndices[]={0,1,2,0,2,3};Mesh blocker=mesh;blocker.count=6;blocker.vertices.Reset();blocker.indices.Reset();
  bd.ByteWidth=sizeof(panel);bd.BindFlags=D3D11_BIND_VERTEX_BUFFER;data.pSysMem=panel;assert(SUCCEEDED(device->CreateBuffer(&bd,&data,&blocker.vertices)));
  bd.ByteWidth=sizeof(panelIndices);bd.BindFlags=D3D11_BIND_INDEX_BUFFER;data.pSysMem=panelIndices;assert(SUCCEEDED(device->CreateBuffer(&bd,&data,&blocker.indices)));
  frame.meshes={blocker};++revision;dynamic=false;frame.viewport.Width=frame.viewport.Height=1;
  for(unsigned i=0;i<roomsurface::lights;++i)draw();frame.viewport=actor.viewport;dynamic=true;auto blocked=draw();unsigned covered=0;
  for(unsigned i=0;i<desc.Width*desc.Height;++i)if(face[i]&&int(blocked[i*4])+12<int(shaded[i*4]))++covered;
  std::cout<<"external blocker coverage="<<covered<<"\n";assert(covered>1000);
  if(argc>2){std::ofstream image(std::filesystem::path(argv[2])/L"blocked.rgba",std::ios::binary);image.write((char*)blocked.data(),blocked.size());}
 }
 // A depth-only curved receiver with no caster must stay clear, even at
 // grazing polygon slopes. Empty light-map texels are lit, never blockers.
 dynamic=false;frame.meshes.clear();++revision;frame.viewport.Width=frame.viewport.Height=1;for(unsigned i=0;i<roomsurface::lights;++i)draw();frame.viewport=actor.viewport;auto empty=draw();unsigned falseShadow=0;
 for(unsigned i=0;i<desc.Width*desc.Height;++i)if(face[i]&&empty[i*4]<250)++falseShadow;
 std::cout<<"empty-map false shadow="<<falseShadow<<"\n";assert(falseShadow<100);
 renderer.clear();std::cout<<"PASS curved receiver: smooth native normals, bounded polygon seams, genuine external shadows and empty-map rejection\n";
}
