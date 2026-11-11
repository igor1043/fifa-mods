#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <cassert>
#include <iostream>
#include "native_animation.h"
#include "actor_surface_normals.h"
using namespace roomshadow;
static std::vector<float> readNormals(ID3D11Device* d,ID3D11DeviceContext* c,ID3D11Texture2D* source){
 D3D11_TEXTURE2D_DESC desc{};source->GetDesc(&desc);desc.BindFlags=0;desc.Usage=D3D11_USAGE_STAGING;desc.CPUAccessFlags=D3D11_CPU_ACCESS_READ;ComPtr<ID3D11Texture2D> copy;assert(SUCCEEDED(d->CreateTexture2D(&desc,nullptr,&copy)));c->CopyResource(copy.Get(),source);D3D11_MAPPED_SUBRESOURCE map{};assert(SUCCEEDED(c->Map(copy.Get(),0,D3D11_MAP_READ,0,&map)));std::vector<float> out(desc.Width*desc.Height*4);for(unsigned y=0;y<desc.Height;++y)memcpy(out.data()+y*desc.Width*4,(char*)map.pData+y*map.RowPitch,desc.Width*16);c->Unmap(copy.Get(),0);return out;
}
int main(){
 _set_error_mode(_OUT_TO_STDERR);_set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);
 ComPtr<ID3D11Device> device;ComPtr<ID3D11DeviceContext> context;assert(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&device,nullptr,&context)));
 struct V{uint16_t p[4];uint32_t n,t;uint16_t uv[2];};static_assert(sizeof(V)==20);
 const uint32_t left=717u|(409u<<20),right=307u|(409u<<20);
 V vertices[]={{{0xb800,0xb800,0x3800,0x3c00},left,0,{}},{{0x3800,0xb800,0x3800,0x3c00},right,0,{}},{{0x3800,0x3800,0x3800,0x3c00},right,0,{}},{{0xb800,0x3800,0x3800,0x3c00},left,0,{}}};uint16_t indices[]={0,1,2,0,2,3};
 Mesh mesh;mesh.stride=20;mesh.count=6;mesh.indexFormat=DXGI_FORMAT_R16_UINT;D3D11_BUFFER_DESC desc{};desc.ByteWidth=sizeof vertices;desc.BindFlags=D3D11_BIND_VERTEX_BUFFER;D3D11_SUBRESOURCE_DATA data{vertices,0,0};assert(SUCCEEDED(device->CreateBuffer(&desc,&data,&mesh.vertices)));desc.ByteWidth=sizeof indices;desc.BindFlags=D3D11_BIND_INDEX_BUFFER;data.pSysMem=indices;assert(SUCCEEDED(device->CreateBuffer(&desc,&data,&mesh.indices)));
 Frame scene,actor;scene.context=context;scene.viewport={0,0,64,64,0,1};scene.depthState.DepthFunc=D3D11_COMPARISON_LESS_EQUAL;actor.meshes={mesh};float camera[16]{};for(unsigned i=0;i<4;++i){camera[i*5]=1;actor.model[i*5]=1;}actor.model[12]=origin[0];actor.model[13]=origin[1];
 roomsurface::ActorNormals normals;assert(normals.draw(scene,actor,camera));auto image=readNormals(device.Get(),context.Get(),normals.color.Get());auto at=[&](unsigned x,unsigned y,unsigned c){return image[(y*64+x)*4+c];};
 assert(at(22,32,0)<-.3f&&at(42,32,0)>.3f&&at(32,32,2)>.99f);assert(std::abs(at(32,32,3)-.5f)<.00001f);assert(at(0,0,0)==0&&at(0,0,3)==0);
 scene.depthState.DepthFunc=D3D11_COMPARISON_GREATER_EQUAL;assert(normals.draw(scene,actor,camera));image=readNormals(device.Get(),context.Get(),normals.color.Get());assert(at(32,32,2)>.99f);
 auto staging=desc;staging.ByteWidth=sizeof vertices;staging.BindFlags=0;staging.Usage=D3D11_USAGE_STAGING;staging.CPUAccessFlags=D3D11_CPU_ACCESS_READ;ComPtr<ID3D11Buffer> original;assert(SUCCEEDED(device->CreateBuffer(&staging,nullptr,&original)));context->CopyResource(original.Get(),mesh.vertices.Get());D3D11_MAPPED_SUBRESOURCE map{};assert(SUCCEEDED(context->Map(original.Get(),0,D3D11_MAP_READ,0,&map)));assert(!memcmp(map.pData,vertices,sizeof vertices));context->Unmap(original.Get(),0);
 // Exercise exactly the engine's expanded live-animation representation,
 // not only the packed RX3 source stream. Both must yield the same normals.
 std::vector<unsigned char> expanded;clubanim::expand(reinterpret_cast<const unsigned char*>(vertices),4,expanded);assert(expanded.size()==4*28);
 desc.ByteWidth=UINT(expanded.size());desc.BindFlags=D3D11_BIND_VERTEX_BUFFER;data.pSysMem=expanded.data();mesh.vertices.Reset();assert(SUCCEEDED(device->CreateBuffer(&desc,&data,&mesh.vertices)));mesh.stride=28;actor.meshes={mesh};
 assert(normals.draw(scene,actor,camera));auto live=readNormals(device.Get(),context.Get(),normals.color.Get());
 for(unsigned y=17;y<47;++y)for(unsigned x=17;x<47;++x)for(unsigned c=0;c<4;++c)assert(std::abs(live[(y*64+x)*4+c]-image[(y*64+x)*4+c])<.001f);
 scene.viewport.Width=7680;scene.viewport.Height=4320;assert(normals.draw(scene,actor,camera));assert(normals.width==1024&&normals.height==576&&normals.width*normals.height*20<=20*1024*1024);
 normals.clear();std::cout<<"PASS actor surface: original packed and live 28-byte animated normals, smooth interpolation, reversed depth, original buffer intact, bounded targets at 8K\n";
}
