#include <windows.h>
#include <d3d11.h>
#include <cassert>
#include <iostream>
#include <cstring>
#include "native_animation.h"
// Self-contained fixture for the normal regression suite; real exported clips
// can still be supplied as argv[1] for the full original-player vertex check.
struct Fixture{
 std::filesystem::path path;bool temporary=false;
 explicit Fixture(int argc,wchar_t**argv){if(argc==2){path=argv[1];return;}assert(argc==1);temporary=true;path=std::filesystem::temp_directory_path()/(L"fifa-native-player-"+std::to_wstring(GetCurrentProcessId())+L".bin");std::ofstream out(path,std::ios::binary);unsigned parts=8,count=23,player=205498;float duration=5.4333f;out.write("FFPVTX01",8);for(auto v:{parts,count,player})out.write((const char*)&v,4);out.write((const char*)&duration,4);
  for(unsigned part=0;part<parts;++part){unsigned slot=part<7?part:64,vertices=4+part;out.write((const char*)&slot,4);out.write((const char*)&vertices,4);std::vector<unsigned char>frame(size_t(vertices)*20);
   for(unsigned f=0;f<count;++f){for(unsigned v=0;v<vertices;++v){auto p=frame.data()+size_t(v)*20;for(unsigned axis=0;axis<4;++axis){float value=axis==3?1.f:float(axis*30+v+part)+(axis==0?std::sin(float(f)*.4f)*2:0);uint16_t h=DirectX::PackedVector::XMConvertFloatToHalf(value);memcpy(p+axis*2,&h,2);}uint32_t normal=511u<<10,tangent=511;memcpy(p+8,&normal,4);memcpy(p+12,&tangent,4);uint16_t uv=DirectX::PackedVector::XMConvertFloatToHalf(v*.1f);memcpy(p+16,&uv,2);memcpy(p+18,&uv,2);}out.write((const char*)frame.data(),frame.size());}
  }out.close();assert(out);}
 ~Fixture(){if(temporary){std::error_code e;std::filesystem::remove(path,e);}}
};

int wmain(int argc,wchar_t**argv){
 _set_error_mode(_OUT_TO_STDERR);Fixture fixture(argc,argv);auto path=fixture.path;auto clip=clubanim::load(path,205498);assert(clip&&clip->tracks.size()>=6&&clip->count>=2);assert(!clubanim::load(path,1));
 ID3D11Device*d=nullptr;ID3D11DeviceContext*c=nullptr;assert(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&d,nullptr,&c)));
 auto&t=clip->tracks[0];auto bytes=t.expandedInitial;assert(t.expandedFrames.size()==bytes.size()*clip->count&&memcmp(t.expandedFrames.data(),bytes.data(),bytes.size())==0);
 auto create=[&](const std::vector<unsigned char>&data){D3D11_BUFFER_DESC desc{};desc.ByteWidth=UINT(data.size());desc.BindFlags=D3D11_BIND_VERTEX_BUFFER;desc.Usage=D3D11_USAGE_IMMUTABLE;D3D11_SUBRESOURCE_DATA init{data.data(),0,0};ID3D11Buffer*b=nullptr;assert(SUCCEEDED(d->CreateBuffer(&desc,&init,&b)));return b;};
 auto read=[&](ID3D11Buffer*b){D3D11_BUFFER_DESC desc{};b->GetDesc(&desc);desc.BindFlags=desc.MiscFlags=0;desc.Usage=D3D11_USAGE_STAGING;desc.CPUAccessFlags=D3D11_CPU_ACCESS_READ;ID3D11Buffer*stage=nullptr;assert(SUCCEEDED(d->CreateBuffer(&desc,nullptr,&stage)));c->CopyResource(stage,b);D3D11_MAPPED_SUBRESOURCE m{};assert(SUCCEEDED(c->Map(stage,0,D3D11_MAP_READ,0,&m)));std::vector<unsigned char>result((unsigned char*)m.pData,(unsigned char*)m.pData+desc.ByteWidth);c->Unmap(stage,0);stage->Release();return result;};
 auto bind=[&](ID3D11Buffer*b,UINT offset=0){UINT stride=28;c->IASetVertexBuffers(0,1,&b,&stride,&offset);};auto bound=[&](){ID3D11Buffer*b=nullptr;UINT stride,off;c->IAGetVertexBuffers(0,1,&b,&stride,&off);if(b)b->Release();return b;};
 auto*source=create(bytes);clubanim::activate(clip);clubanim::setVisible(true);clubanim::prepareNativeDraw(c,1000);auto hook=clubanim::original(c);assert(hook.bind);bind(source);assert(clip->captured==1&&bound()!=source);
 std::shared_ptr<clubanim::PrivateBuffer>privateBuffer;{std::lock_guard<std::mutex>lock(clubanim::cacheMutex);privateBuffer=clubanim::cache.buffers[0];}assert(bound()==privateBuffer->animated&&read(privateBuffer->animated)==bytes);
 D3D11_BUFFER_DESC desc{};privateBuffer->animated->GetDesc(&desc);assert(desc.Usage==D3D11_USAGE_DYNAMIC&&desc.CPUAccessFlags==D3D11_CPU_ACCESS_WRITE);source->GetDesc(&desc);assert(desc.Usage==D3D11_USAGE_IMMUTABLE);
 auto updates=clip->updates.load();clubanim::prepareNativeDraw(c,1857);auto after=read(privateBuffer->animated);assert(after!=bytes&&read(source)==bytes&&bound()==privateBuffer->animated);auto afterUpdates=clip->updates.load();assert(afterUpdates==updates+1);bind(source);assert(clip->updates==afterUpdates);bind(privateBuffer->animated);assert(clip->captured==1&&clip->updates==afterUpdates&&bound()==privateBuffer->animated);
 for(unsigned i=0;i<t.vertices;++i){assert(!memcmp(bytes.data()+size_t(i)*28+24,after.data()+size_t(i)*28+24,4));for(unsigned axis=0;axis<3;++axis){uint16_t h;memcpy(&h,after.data()+size_t(i)*28+axis*2,2);assert(std::isfinite(DirectX::PackedVector::XMConvertHalfToFloat(h)));}}
 // Reproduce the hardware-sensitive path: keep the animated VB bound while
 // writing the next frame. DISCARD must rename storage instead of updating
 // DEFAULT storage in place or returning to frame-zero after a GPU draw.
 for(unsigned frame=0;frame<240;++frame){clubanim::prepareNativeDraw(c,2000+frame*7);bind(source);assert(bound()==privateBuffer->animated);if(frame%16==0)assert(read(source)==bytes);}assert(read(source)==bytes);
 // Runtime refresh of the native binding entry must not lose the association.
 assert(clubanim::replace(hook.table+18,(void*)&clubanim::bindVertices,(void*)hook.bind));auto rearms=clubanim::drawRearms.load();clubanim::prepareNativeDraw(c,4000);assert(clubanim::drawRearms==rearms+1);bind(source);assert(bound()==privateBuffer->animated);
 ID3D11DeviceContext*deferred=nullptr;assert(SUCCEEDED(d->CreateDeferredContext(0,&deferred)));assert(!clubanim::armNativeDraw(deferred));deferred->Release();
 clubanim::setVisible(false);auto stopped=clip->updates.load();clubanim::prepareNativeDraw(c,4100);bind(source);assert(bound()==source&&clip->updates==stopped);clubanim::setVisible(true);
 auto unrelated=bytes;unrelated[unrelated.size()/2]^=127;auto*other=create(unrelated);bind(other);assert(bound()==other&&clip->captured==1&&read(other)==unrelated);
 // A fresh player's complete fingerprint invalidates the previous cache.
 auto next=clubanim::load(path,205498);next->player=123456;auto&nt=next->tracks[0];for(unsigned frame=0;frame<next->count;++frame){uint16_t value=DirectX::PackedVector::XMConvertFloatToHalf(12.5f);memcpy(nt.frames.data()+size_t(frame)*nt.vertices*20,&value,2);clubanim::expand(nt.frames.data()+size_t(frame)*nt.vertices*20,nt.vertices,nt.expandedScratch);memcpy(nt.expandedFrames.data()+size_t(frame)*nt.vertices*28,nt.expandedScratch.data(),nt.expandedScratch.size());}nt.expandedInitial.assign(nt.expandedFrames.begin(),nt.expandedFrames.begin()+size_t(nt.vertices)*28);auto newBytes=nt.expandedInitial;auto*newSource=create(newBytes);
 clubanim::activate(next);clubanim::setVisible(true);clubanim::prepareNativeDraw(c,5000);bind(source);assert(bound()==source&&next->captured==0);bind(newSource);assert(bound()!=newSource&&next->captured==1&&read(newSource)==newBytes);
 clubanim::enabled=false;bind(newSource);assert(bound()==newSource);clubanim::enabled=true;clubanim::activate({});clubanim::setVisible(true);bind(newSource);assert(bound()==newSource);
 clubanim::stop();assert(hook.table[18]!=(void*)&clubanim::bindVertices&&clubanim::sameNativeCode(hook.table[18],(void*)hook.bind));assert(read(source)==bytes&&read(newSource)==newBytes);bind(nullptr);privateBuffer.reset();newSource->Release();other->Release();source->Release();next.reset();clip.reset();c->Release();d->Release();
 std::cout<<"PASS dynamic native animation: DISCARD storage, persistent binding across 240 frames, no pose reset per draw, original immutable sources unchanged, interpolation/UVs, frame dedup, native dispatch refresh, UI binding restore, hidden/disabled and player/club change\n";
}
