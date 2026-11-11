#pragma once
#include <d3d11.h>
#include <wrl/client.h>
#include <array>
#include <unordered_map>
#include <atomic>
// Room-only sampler substitution: preserve LOD/address/border settings and
// restore native bindings immediately after each actual textured draw.
namespace roomfilter {
using Microsoft::WRL::ComPtr;
inline thread_local bool enabled=false;
inline std::atomic<unsigned> draws{0};
struct Entry {ComPtr<ID3D11SamplerState> original,filtered;};
struct Cache {
 ComPtr<ID3D11Device> device;std::unordered_map<ID3D11SamplerState*,Entry> entries;
 ID3D11SamplerState* lookup(ID3D11Device* owner,ID3D11SamplerState* native){
  if(!native)return nullptr;if(device.Get()!=owner){entries.clear();device=owner;}
  auto found=entries.find(native);if(found!=entries.end())return found->second.filtered.Get();if(entries.size()>=128)return native;
  D3D11_SAMPLER_DESC d{};native->GetDesc(&d);Entry e;e.original=native;e.filtered=native;
  const bool linear=d.Filter==D3D11_FILTER_MIN_MAG_MIP_LINEAR||d.Filter==D3D11_FILTER_MIN_MAG_LINEAR_MIP_POINT||d.Filter==D3D11_FILTER_ANISOTROPIC;
  // Point/ID maps and comparison samplers retain exact native semantics.
  if(linear&&(d.Filter!=D3D11_FILTER_ANISOTROPIC||d.MaxAnisotropy<16)){
   d.Filter=D3D11_FILTER_ANISOTROPIC;d.MaxAnisotropy=16;ComPtr<ID3D11SamplerState> better;
   if(SUCCEEDED(owner->CreateSamplerState(&d,&better)))e.filtered=better;
  }
  auto* result=e.filtered.Get();entries.emplace(native,std::move(e));return result;
 }
};
inline thread_local Cache cache;
struct Draw {
 ID3D11DeviceContext* context=nullptr;
 std::array<ComPtr<ID3D11SamplerState>,D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT> retained;
 std::array<ID3D11SamplerState*,D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT> original{};
 explicit Draw(ID3D11DeviceContext*c){
  if(!enabled||!c)return;ComPtr<ID3D11Device>d;c->GetDevice(&d);
  c->PSGetSamplers(0,UINT(original.size()),original.data());auto upgraded=original;bool changed=false;
  for(unsigned i=0;i<original.size();++i){retained[i].Attach(original[i]);upgraded[i]=cache.lookup(d.Get(),original[i]);changed|=upgraded[i]!=original[i];}
  if(changed){context=c;c->PSSetSamplers(0,UINT(upgraded.size()),upgraded.data());++draws;}
 }
 ~Draw(){if(context)context->PSSetSamplers(0,UINT(original.size()),original.data());}
};
}
