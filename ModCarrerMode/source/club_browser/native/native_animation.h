#pragma once
// Native FIFA drawing, original materials and native vertex resources remain owned
// by FIFA. Animate a private vertex copy only while its verified mesh is drawn.
#include <windows.h>
#include <d3d11_3.h>
#include <DirectXPackedVector.h>
#include <filesystem>
#include <atomic>
#include <mutex>
#include <memory>
#include <fstream>
#include <string>
#include <vector>
#include <algorithm>
#include <cmath>
#include <thread>
#include <array>
#include <cstdint>
#include <cstring>
namespace clubanim {
struct PrivateBuffer;
struct Track{unsigned slot=0,vertices=0;std::vector<unsigned char>frames,scratch,expandedInitial,expandedScratch,expandedFrames;};
struct Clip{unsigned count=0,player=0;float duration=0;std::vector<Track>tracks;std::mutex mutex;uint64_t start=0;bool begun=false,constant=false;std::atomic<unsigned>captured{0},updates{0};};
inline std::shared_ptr<Clip>activeClip;
inline std::atomic<bool>enabled{true},visible{false};
inline std::atomic<uint64_t>drawTime{0};
inline std::atomic<unsigned>drawUploads{0},drawUnavailable{0},drawMatches{0},drawRejected{0},drawRearms{0};
// FIFA expands RX3's two packed 3s10n vectors to half4, truncating the half
// mantissa toward zero. Verified byte-for-byte against every mesh of a live
// actor; position, UV and vertex order remain unchanged (20 -> 28 bytes).
inline void expand(const unsigned char*source,unsigned vertices,std::vector<unsigned char>&target){target.resize(size_t(vertices)*28);for(unsigned i=0;i<vertices;++i){auto from=source+size_t(i)*20;auto to=target.data()+size_t(i)*28;memcpy(to,from,8);memcpy(to+24,from+16,4);for(unsigned vector=0;vector<2;++vector){uint32_t packed;memcpy(&packed,from+8+vector*4,4);for(unsigned axis=0;axis<3;++axis){int value=(packed>>(axis*10))&1023;if(value>=512)value-=1024;float f=(std::max)(-1.f,value/511.f);uint16_t h=DirectX::PackedVector::XMConvertFloatToHalf(f);if(std::abs(DirectX::PackedVector::XMConvertHalfToFloat(h))>std::abs(f))--h;memcpy(to+8+vector*8+axis*2,&h,2);}uint16_t one=0x3c00;memcpy(to+14+vector*8,&one,2);}}}
inline std::shared_ptr<Clip> load(const std::filesystem::path& path,unsigned player){
 auto c=std::make_shared<Clip>();std::ifstream in(path,std::ios::binary|std::ios::ate);auto size=in.tellg();if(size<24||size>256*1024*1024)return {};in.seekg(0);char magic[8]{};unsigned parts=0;in.read(magic,8);in.read((char*)&parts,4);in.read((char*)&c->count,4);in.read((char*)&c->player,4);in.read((char*)&c->duration,4);
 if(!in||memcmp(magic,"FFPVTX01",8)||!parts||parts>96||c->count<2||c->count>256||c->player!=player||!std::isfinite(c->duration)||c->duration<=0||c->duration>20)return {};
 size_t total=24;unsigned previous=0;
 for(unsigned i=0;i<parts;++i){Track t;in.read((char*)&t.slot,4);in.read((char*)&t.vertices,4);if(!in||t.slot>=96||(i&&t.slot<=previous)||t.vertices<3||t.vertices>58000)return {};previous=t.slot;size_t n=size_t(t.vertices)*20*c->count;total+=8+n;if(total>size_t(size))return {};t.frames.resize(n);in.read((char*)t.frames.data(),n);if(!in)return {};c->tracks.push_back(std::move(t));}
 if(total!=size_t(size))return {};c->constant=c->count==2;for(auto&t:c->tracks)if(c->constant&&memcmp(t.frames.data(),t.frames.data()+size_t(t.vertices)*20,size_t(t.vertices)*20))c->constant=false;for(auto&t:c->tracks){size_t frameBytes=size_t(t.vertices)*20,expandedBytes=size_t(t.vertices)*28;t.expandedFrames.resize(expandedBytes*c->count);for(unsigned frame=0;frame<c->count;++frame){expand(t.frames.data()+size_t(frame)*frameBytes,t.vertices,t.expandedScratch);memcpy(t.expandedFrames.data()+size_t(frame)*expandedBytes,t.expandedScratch.data(),expandedBytes);}t.expandedInitial.assign(t.expandedFrames.begin(),t.expandedFrames.begin()+expandedBytes);t.expandedScratch.clear();}return c;
}

inline size_t range(const Track&t,const void*data,size_t size,unsigned stride=20){const auto&expected=stride==28?t.expandedInitial:t.frames;size_t n=size_t(t.vertices)*stride;if(!data||size<n||expected.size()<n)return SIZE_MAX;auto first=(const unsigned char*)data,end=first+size;auto prefix=(std::min)(size_t(40),n);while(size_t(end-first)>=n){auto at=std::search(first,end,expected.data(),expected.data()+prefix);if(at==end||size_t(end-at)<n)return SIZE_MAX;if(!memcmp(at,expected.data(),n))return size_t(at-(const unsigned char*)data);first=at+1;}return SIZE_MAX;}

struct PrivateBuffer{
 ID3D11Buffer*source=nullptr,*animated=nullptr;size_t track=0;unsigned stride=0;uint64_t lastUpload=UINT64_MAX;
 ~PrivateBuffer(){if(animated)animated->Release();if(source)source->Release();}
};
struct Rejected{ID3D11Buffer*source=nullptr;uint64_t retry=0;unsigned attempts=0;explicit Rejected(ID3D11Buffer*b):source(b){source->AddRef();}~Rejected(){source->Release();}};
struct Cache{std::shared_ptr<Clip>clip;std::vector<std::shared_ptr<PrivateBuffer>>buffers;std::vector<std::shared_ptr<Rejected>>rejected;};
inline std::mutex cacheMutex;inline Cache cache;
inline void setVisible(bool show){visible=show;}
inline void activate(std::shared_ptr<Clip>c){visible=false;std::atomic_store(&activeClip,std::move(c));std::lock_guard<std::mutex>lock(cacheMutex);cache={};}
inline bool expectedSize(const Track&t,unsigned bytes,unsigned stride){return (stride==20||stride==28)&&bytes==size_t(t.vertices)*stride;}
inline std::shared_ptr<PrivateBuffer> verify(ID3D11DeviceContext*c,ID3D11Buffer*source,unsigned stride,const std::shared_ptr<Clip>&clip){
 D3D11_BUFFER_DESC desc{};source->GetDesc(&desc);if(!(desc.BindFlags&D3D11_BIND_VERTEX_BUFFER)||desc.ByteWidth>16*1024*1024)return {};
 bool candidate=false;for(auto&t:clip->tracks)if(expectedSize(t,desc.ByteWidth,stride)){candidate=true;break;}if(!candidate)return {};
 auto now=GetTickCount64();std::lock_guard<std::mutex>lock(cacheMutex);if(cache.clip!=clip){cache={};cache.clip=clip;}
 for(auto&b:cache.buffers){if(b->animated==source)return {};if(b->source==source&&b->stride==stride)return b;}
 for(auto&r:cache.rejected)if(r->source==source&&(r->attempts>=4||now<r->retry))return {};
 ID3D11Device*device=nullptr;c->GetDevice(&device);if(!device)return {};
 // Only the first encounter reads back this candidate. Its complete native
 // mesh must equal frame zero; size, pointer or prefix equality is insufficient.
 D3D11_BUFFER_DESC staging=desc;staging.Usage=D3D11_USAGE_STAGING;staging.BindFlags=staging.MiscFlags=staging.StructureByteStride=0;staging.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
 ID3D11Buffer*readback=nullptr;if(FAILED(device->CreateBuffer(&staging,nullptr,&readback))){device->Release();return {};}
 c->CopyResource(readback,source);D3D11_MAPPED_SUBRESOURCE mapped{};size_t found=SIZE_MAX;
 if(SUCCEEDED(c->Map(readback,0,D3D11_MAP_READ,0,&mapped))){for(size_t i=0;i<clip->tracks.size();++i){auto&t=clip->tracks[i];if(expectedSize(t,desc.ByteWidth,stride)&&range(t,mapped.pData,desc.ByteWidth,stride)==0){found=i;break;}}c->Unmap(readback,0);}readback->Release();
 if(found==SIZE_MAX){std::shared_ptr<Rejected>reject;for(auto&r:cache.rejected)if(r->source==source)reject=r;if(!reject){reject=std::make_shared<Rejected>(source);cache.rejected.push_back(reject);if(cache.rejected.size()>32)cache.rejected.erase(cache.rejected.begin());}++reject->attempts;reject->retry=now+250;++drawRejected;device->Release();return {};}
 auto result=std::make_shared<PrivateBuffer>();result->track=found;result->stride=stride;auto&t=clip->tracks[found];const auto&initial=stride==28?t.expandedInitial:t.frames;
 desc.Usage=D3D11_USAGE_DYNAMIC;desc.CPUAccessFlags=D3D11_CPU_ACCESS_WRITE;D3D11_SUBRESOURCE_DATA data{initial.data(),0,0};auto hr=device->CreateBuffer(&desc,&data,&result->animated);device->Release();if(FAILED(hr))return {};
 result->source=source;source->AddRef();cache.buffers.push_back(result);++clip->captured;return result;
}

inline void upload(ID3D11DeviceContext*c,const std::shared_ptr<Clip>&clip,const std::shared_ptr<PrivateBuffer>&buffer,uint64_t now){
 std::lock_guard<std::mutex>lock(clip->mutex);if(buffer->lastUpload==now)return;if(!clip->begun){clip->start=now;clip->begun=true;}
 double f=std::fmod(double(now-clip->start)*.001,double(clip->duration))/clip->duration*(clip->count-1);unsigned a=(unsigned)f,b=(std::min)(a+1,clip->count-1);float mix=float(f-a);auto&t=clip->tracks[buffer->track];size_t bytes=size_t(t.vertices)*buffer->stride;const auto&frames=buffer->stride==28?t.expandedFrames:t.frames;auto left=frames.data()+a*bytes,right=frames.data()+b*bytes;
 D3D11_MAPPED_SUBRESOURCE mapped{};if(FAILED(c->Map(buffer->animated,0,D3D11_MAP_WRITE_DISCARD,0,&mapped))){++drawUnavailable;return;}auto out=(unsigned char*)mapped.pData;memcpy(out,mix<.5?left:right,bytes);
 if(!clip->constant)for(unsigned v=0;v<t.vertices;++v)for(unsigned axis=0;axis<3;++axis){size_t offset=size_t(v)*buffer->stride+axis*2;uint16_t x,y;memcpy(&x,left+offset,2);memcpy(&y,right+offset,2);float X=DirectX::PackedVector::XMConvertHalfToFloat(x),Y=DirectX::PackedVector::XMConvertHalfToFloat(y);auto value=DirectX::PackedVector::XMConvertFloatToHalf(X+(Y-X)*mix);memcpy(out+offset,&value,2);}c->Unmap(buffer->animated,0);buffer->lastUpload=now;++clip->updates;++drawUploads;
}
using Bind=void(STDMETHODCALLTYPE*)(ID3D11DeviceContext*,UINT,UINT,ID3D11Buffer*const*,const UINT*,const UINT*);
struct ContextHook{void**table=nullptr;Bind bind=nullptr;};
inline std::mutex contextMutex;inline std::vector<ContextHook>contexts;
inline ContextHook original(ID3D11DeviceContext*c){auto vt=*reinterpret_cast<void***>(c);std::lock_guard<std::mutex>lock(contextMutex);for(auto&h:contexts)if(h.table==vt)return h;return {};}
inline void STDMETHODCALLTYPE bindVertices(ID3D11DeviceContext*c,UINT first,UINT count,ID3D11Buffer*const*buffers,const UINT*strides,const UINT*offsets){
 auto h=original(c);if(!h.bind)return;ID3D11Buffer*changed[D3D11_IA_VERTEX_INPUT_RESOURCE_SLOT_COUNT]{};bool changedBinding=false;std::shared_ptr<PrivateBuffer>privateBuffer;
 try{if(enabled&&visible&&first==0&&count>0&&count<=D3D11_IA_VERTEX_INPUT_RESOURCE_SLOT_COUNT&&buffers&&buffers[0]&&strides&&offsets&&!offsets[0]){auto clip=std::atomic_load(&activeClip);if(clip){privateBuffer=verify(c,buffers[0],strides[0],clip);if(privateBuffer&&enabled&&visible&&std::atomic_load(&activeClip)==clip){auto now=drawTime.load();if(!now)now=GetTickCount64();upload(c,clip,privateBuffer,now);std::copy(buffers,buffers+count,changed);changed[0]=privateBuffer->animated;changedBinding=true;++drawMatches;}}}}catch(...){++drawUnavailable;}
 // Keep the private animation stream bound. Restoring frame-zero geometry
 // after every draw caused visible pose swaps when D3D refreshed dispatch.
 // The native engine requests the next mesh normally; unrelated streams pass
 // through unchanged, and buffers returned by IAGet already refer to this copy.
 h.bind(c,first,count,changedBinding?changed:buffers,strides,offsets);
}
inline bool replace(void**slot,void*expected,void*replacement){if(*slot==replacement)return true;DWORD protection=0;if(!VirtualProtect(slot,sizeof(void*),PAGE_READWRITE,&protection))return false;auto seen=InterlockedCompareExchangePointer((void*volatile*)slot,replacement,expected);DWORD ignored=0;VirtualProtect(slot,sizeof(void*),protection,&ignored);return seen==expected||seen==replacement;}
inline bool sameNativeCode(void*a,void*b){MEMORY_BASIC_INFORMATION left{},right{};return a&&b&&VirtualQuery(a,&left,sizeof left)&&VirtualQuery(b,&right,sizeof right)&&left.Type==MEM_IMAGE&&right.Type==MEM_IMAGE&&left.AllocationBase==right.AllocationBase;}
inline bool armNativeDraw(ID3D11DeviceContext*c){
 if(!enabled||!c||!visible||!std::atomic_load(&activeClip))return false;if(c->GetType()!=D3D11_DEVICE_CONTEXT_IMMEDIATE){++drawUnavailable;return false;}auto vt=*reinterpret_cast<void***>(c);std::lock_guard<std::mutex>lock(contextMutex);ContextHook*h=nullptr;for(auto&item:contexts)if(item.table==vt)h=&item;
 if(!h){if(contexts.size()>=8||vt[18]==(void*)&bindVertices){++drawUnavailable;return false;}contexts.push_back({vt,(Bind)vt[18]});h=&contexts.back();}
 if(vt[18]!=(void*)&bindVertices&&vt[18]!=(void*)h->bind){if(!sameNativeCode(vt[18],(void*)h->bind)){++drawUnavailable;return false;}h->bind=(Bind)vt[18];}bool changed=vt[18]!=(void*)&bindVertices;if(!replace(vt+18,(void*)h->bind,(void*)&bindVertices)){++drawUnavailable;return false;}if(changed)++drawRearms;return true;
}
inline void prepareNativeDraw(ID3D11DeviceContext*c,uint64_t now){
 if(!armNativeDraw(c))return;drawTime=now;auto clip=std::atomic_load(&activeClip);std::vector<std::shared_ptr<PrivateBuffer>>buffers;{std::lock_guard<std::mutex>lock(cacheMutex);if(cache.clip==clip)buffers=cache.buffers;}for(auto&buffer:buffers)if(enabled&&visible&&std::atomic_load(&activeClip)==clip)upload(c,clip,buffer,now);
}
inline void stop(){enabled=false;visible=false;{std::lock_guard<std::mutex>lock(contextMutex);for(auto&h:contexts)replace(h.table+18,(void*)&bindVertices,(void*)h.bind);}activate({});}
}
