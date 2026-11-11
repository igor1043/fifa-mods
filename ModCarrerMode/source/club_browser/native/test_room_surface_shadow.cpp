#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <cassert>
#include <iostream>
#include "room_surface_shadow.h"
using namespace roomshadow;
static std::vector<unsigned char> pixels(ID3D11Device* d,ID3D11DeviceContext* c,ID3D11Texture2D* source){
 D3D11_TEXTURE2D_DESC desc{};source->GetDesc(&desc);desc.BindFlags=desc.MiscFlags=0;desc.Usage=D3D11_USAGE_STAGING;desc.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
 ComPtr<ID3D11Texture2D> copy;assert(SUCCEEDED(d->CreateTexture2D(&desc,nullptr,&copy)));c->CopyResource(copy.Get(),source);
 D3D11_MAPPED_SUBRESOURCE mapped{};assert(SUCCEEDED(c->Map(copy.Get(),0,D3D11_MAP_READ,0,&mapped)));
 std::vector<unsigned char> out(desc.Width*desc.Height*4);for(unsigned y=0;y<desc.Height;++y)memcpy(out.data()+y*desc.Width*4,(char*)mapped.pData+y*mapped.RowPitch,desc.Width*4);c->Unmap(copy.Get(),0);return out;
}
static unsigned dark(const std::vector<unsigned char>& image){unsigned n=0;for(unsigned i=0;i<image.size();i+=4)n+=image[i]<250;return n;}
int wmain(int argc,wchar_t** argv){
 _set_error_mode(_OUT_TO_STDERR);_set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);assert(argc==2&&loadShaders(argv[1]));
 ComPtr<ID3D11Device> device;ComPtr<ID3D11DeviceContext> context;
 assert(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&device,nullptr,&context)));
 D3D11_TEXTURE2D_DESC desc{};desc.Width=desc.Height=256;desc.MipLevels=desc.ArraySize=desc.SampleDesc.Count=1;desc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;desc.BindFlags=D3D11_BIND_RENDER_TARGET;
 ComPtr<ID3D11Texture2D> color,depth;ComPtr<ID3D11RenderTargetView> output;ComPtr<ID3D11DepthStencilView> dsv;
 assert(SUCCEEDED(device->CreateTexture2D(&desc,nullptr,&color)));assert(SUCCEEDED(device->CreateRenderTargetView(color.Get(),nullptr,&output)));
 auto depthDesc=desc;depthDesc.Format=DXGI_FORMAT_D32_FLOAT;depthDesc.BindFlags=D3D11_BIND_DEPTH_STENCIL;
 assert(SUCCEEDED(device->CreateTexture2D(&depthDesc,nullptr,&depth)));assert(SUCCEEDED(device->CreateDepthStencilView(depth.Get(),nullptr,&dsv)));
 Frame frame;frame.tick=GetTickCount64();frame.context=context;frame.depth=dsv;frame.viewport={0,0,256,256,0,1};frame.depthState.DepthEnable=TRUE;frame.depthState.DepthFunc=D3D11_COMPARISON_LESS_EQUAL;
 auto top=[&](){std::fill(std::begin(frame.viewProjection),std::end(frame.viewProjection),0);frame.viewProjection[0]=1/radius;frame.viewProjection[6]=-1/400.f;frame.viewProjection[9]=-1/radius;frame.viewProjection[12]=-origin[0]/radius;frame.viewProjection[13]=origin[2]/radius;frame.viewProjection[14]=(origin[1]+360)/400;frame.viewProjection[15]=1;};top();
 Mesh mesh;mesh.floatPosition=mesh.transformed=true;mesh.stride=24;mesh.count=3;mesh.indexFormat=DXGI_FORMAT_R16_UINT;
 for(unsigned i=0;i<4;++i)mesh.model[i*5]=1;mesh.model[12]=origin[0];mesh.model[13]=origin[1];mesh.model[14]=origin[2];memcpy(frame.model,mesh.model,64);
 struct Vertex{float p[3],padding[3];};Vertex vertices[]={{{-65,70,0},{}},{{65,70,0},{}},{{0,245,0},{}}};uint16_t indices[]={0,1,2};
 D3D11_BUFFER_DESC b{};b.ByteWidth=sizeof vertices;b.BindFlags=D3D11_BIND_VERTEX_BUFFER;D3D11_SUBRESOURCE_DATA data{vertices,0,0};assert(SUCCEEDED(device->CreateBuffer(&b,&data,&mesh.vertices)));
 b.ByteWidth=sizeof indices;b.BindFlags=D3D11_BIND_INDEX_BUFFER;data.pSysMem=indices;assert(SUCCEEDED(device->CreateBuffer(&b,&data,&mesh.indices)));frame.meshes.push_back(mesh);
 auto* rt=output.Get();context->OMSetRenderTargets(1,&rt,dsv.Get());context->RSSetViewports(1,&frame.viewport);const float white[]={1,1,1,1};
 roomsurface::Renderer renderer;assert(renderer.initialize(device.Get()));
 auto draw=[&](uint64_t revision,const Frame* actor=nullptr,bool ui=false){frame.tick=GetTickCount64();context->ClearRenderTargetView(output.Get(),white);assert(renderer.draw(frame,actor,output.Get(),desc,revision,1,ui));return pixels(device.Get(),context.Get(),color.Get());};
 auto warm=[&](uint64_t revision){for(unsigned i=0;i<roomsurface::lights;++i)draw(revision);};
 context->ClearDepthStencilView(dsv.Get(),D3D11_CLEAR_DEPTH,.9f,0);warm(1);auto floor=draw(1);assert(dark(floor)>30);
 auto builds=roomsurface::shadowBuilds.load();auto again=draw(1);assert(floor==again&&roomsurface::shadowBuilds==builds);
 // A raised receiving surface used to be rejected by the floor-only pass.
 context->ClearDepthStencilView(dsv.Get(),D3D11_CLEAR_DEPTH,.7375f,0);auto table=draw(1);assert(dark(table)>30&&table!=floor);
 // Receive on a vertical plane, with an independent occluder before that wall.
 std::fill(std::begin(frame.viewProjection),std::end(frame.viewProjection),0);frame.viewProjection[0]=frame.viewProjection[5]=1/radius;frame.viewProjection[10]=-1/400.f;
 frame.viewProjection[12]=-origin[0]/radius;frame.viewProjection[13]=-(origin[1]+110)/radius;frame.viewProjection[14]=890/400.f;frame.viewProjection[15]=1;
 frame.meshes[0].model[14]=650;context->ClearDepthStencilView(dsv.Get(),D3D11_CLEAR_DEPTH,.9f,0);warm(2);auto wall=draw(2);assert(dark(wall)>30);
 // Real moving geometry gets its own nearest-light depth slices each frame.
 top();frame.meshes[0].model[14]=origin[2];warm(3);Frame actor=frame;actor.meshes=frame.meshes;
 ComPtr<ID3D11Buffer> animated;data.pSysMem=vertices;b.ByteWidth=sizeof vertices;b.BindFlags=D3D11_BIND_VERTEX_BUFFER;assert(SUCCEEDED(device->CreateBuffer(&b,&data,&animated)));actor.meshes[0].vertices=animated;
 actor.tick=GetTickCount64();auto before=draw(3,&actor);for(auto& vertex:vertices)vertex.p[0]+=65;context->UpdateSubresource(animated.Get(),0,nullptr,vertices,0,0);actor.tick=GetTickCount64();auto moved=draw(3,&actor);assert(before!=moved);
 for(auto format:{DXGI_FORMAT_D32_FLOAT,DXGI_FORMAT_D24_UNORM_S8_UINT})for(bool reversed:{false,true}){
  auto sampleDesc=depthDesc;sampleDesc.Format=format;sampleDesc.SampleDesc.Count=4;ComPtr<ID3D11Texture2D> sampled;ComPtr<ID3D11DepthStencilView> sampledView;
  assert(SUCCEEDED(device->CreateTexture2D(&sampleDesc,nullptr,&sampled)));assert(SUCCEEDED(device->CreateDepthStencilView(sampled.Get(),nullptr,&sampledView)));frame.depth=sampledView;
  top();if(reversed)for(unsigned i=0;i<4;++i)frame.viewProjection[i*4+2]=-frame.viewProjection[i*4+2];if(reversed)frame.viewProjection[14]+=1;
  frame.depthState.DepthFunc=reversed?D3D11_COMPARISON_GREATER_EQUAL:D3D11_COMPARISON_LESS_EQUAL;context->ClearDepthStencilView(sampledView.Get(),D3D11_CLEAR_DEPTH,reversed?.1f:.9f,0);
  auto visible=draw(3);assert(dark(visible)>30);assert(depthSamples==4);
 }
 frame.depth=dsv;top();frame.depthState.DepthFunc=D3D11_COMPARISON_LESS_EQUAL;context->ClearDepthStencilView(dsv.Get(),D3D11_CLEAR_DEPTH,.9f,0);
 auto protectedUi=draw(3,nullptr,true);for(unsigned x=0;x<256;++x){assert(protectedUi[x*4]==255);assert(protectedUi[(255*256+x)*4]==255);}
 // A large overhead caster must shade the floor across the top/bottom bands
 // too. The browser UI is drawn afterwards, not protected by cutting the 3D.
 struct CanopyVertex{float p[3],padding[3];};CanopyVertex canopy[]={{{-1000,200,-1000},{}},{{1000,200,-1000},{}},{{1000,200,1000},{}},{{-1000,200,1000},{}}};uint16_t canopyIndices[]={0,1,2,0,2,3};
 Mesh cover=frame.meshes[0];cover.count=6;b.ByteWidth=sizeof canopy;b.BindFlags=D3D11_BIND_VERTEX_BUFFER;data.pSysMem=canopy;assert(SUCCEEDED(device->CreateBuffer(&b,&data,&cover.vertices)));
 b.ByteWidth=sizeof canopyIndices;b.BindFlags=D3D11_BIND_INDEX_BUFFER;data.pSysMem=canopyIndices;assert(SUCCEEDED(device->CreateBuffer(&b,&data,&cover.indices)));frame.meshes={cover};warm(4);
 auto full=draw(4);unsigned topBand=0,bottomBand=0;for(unsigned y=0;y<256;++y)for(unsigned x=0;x<256;++x)if(full[(y*256+x)*4]<250){if(y<33)++topBand;if(y>216)++bottomBand;}
 assert(topBand>100&&bottomBand>100);
 // A sloping receiver must not cast PCF stripes on itself when zoom changes.
 // Constant depth in this sheared camera reconstructs y=150+.45*x exactly.
 CanopyVertex slope[]={{{-radius,150-.45f*radius,-radius},{}},{{radius,150+.45f*radius,-radius},{}},{{radius,150+.45f*radius,radius},{}},{{-radius,150-.45f*radius,radius},{}}};
 b.ByteWidth=sizeof slope;b.BindFlags=D3D11_BIND_VERTEX_BUFFER;data.pSysMem=slope;assert(SUCCEEDED(device->CreateBuffer(&b,&data,&frame.meshes[0].vertices)));
 top();frame.viewProjection[2]=.45f/400;frame.viewProjection[14]=float((double(origin[1])+150-.45*origin[0])/400+.5);context->ClearDepthStencilView(dsv.Get(),D3D11_CLEAR_DEPTH,.5f,0);warm(5);
 for(float zoom:{.9f,1.f,1.1f,1.5f,2.f}){
  frame.viewProjection[0]=zoom/radius;frame.viewProjection[9]=-zoom/radius;frame.viewProjection[12]=-origin[0]*frame.viewProjection[0];frame.viewProjection[13]=origin[2]*zoom/radius;
  auto clean=draw(5);unsigned striped=0;for(unsigned y=8;y<248;++y)for(unsigned x=8;x<248;++x)striped+=clean[(y*256+x)*4]<245;
  std::cerr<<"self-shadow zoom="<<zoom<<" striped="<<striped<<"\n";assert(striped<240*240/25);
 }
 D3D11_TEXTURE2D_DESC movingSize{};renderer.moving.texture->GetDesc(&movingSize);assert(movingSize.Width==1024&&movingSize.Height==1024);
 ComPtr<ID3D11RenderTargetView> restored;ComPtr<ID3D11DepthStencilView> restoredDepth;context->OMGetRenderTargets(1,&restored,&restoredDepth);assert(restored.Get()==output.Get()&&restoredDepth.Get()==dsv.Get());
 roomsurface::Matrix inverse;assert(roomsurface::inverse(roomsurface::relativeCamera(frame.viewProjection),inverse));roomsurface::Matrix zero{};assert(!roomsurface::inverse(zero,inverse));
 // Trophy gallery has its own negative scene origin and 26 ceiling sources.
 frame.flags=room_shadow_bridge::Gallery;frame.staticMeshes.reset();frame.meshes={cover};
 frame.meshes[0].model[12]=-100000;frame.meshes[0].model[14]=0;
 top();frame.viewProjection[12]=100000/radius;frame.viewProjection[13]=0;
 context->ClearDepthStencilView(dsv.Get(),D3D11_CLEAR_DEPTH,.9f,0);
 warm(6);auto gallery=draw(6);assert(dark(gallery)>100);
 const auto cachedGallery=roomsurface::shadowBuilds.load();assert(draw(6)==gallery&&roomsurface::shadowBuilds==cachedGallery);
 renderer.clear();std::cout<<"PASS room surface shadows: native geometry casts on floor, raised furniture and walls; moving actor; cached light maps; D32/D24 MSAA4, reversed depth, UI protection and native state restoration; negative-origin trophy gallery\n";
}
