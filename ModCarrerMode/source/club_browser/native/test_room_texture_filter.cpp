#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include "room_texture_filter.h"
#include <cassert>
#include <chrono>
#include <iostream>
int main(){
 using namespace roomfilter;ComPtr<ID3D11Device>d;ComPtr<ID3D11DeviceContext>c;
 assert(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&d,nullptr,&c)));
 D3D11_SAMPLER_DESC desc{};desc.Filter=D3D11_FILTER_MIN_MAG_MIP_LINEAR;desc.AddressU=D3D11_TEXTURE_ADDRESS_WRAP;desc.AddressV=desc.AddressW=D3D11_TEXTURE_ADDRESS_CLAMP;desc.MinLOD=0;desc.MaxLOD=7;desc.MipLODBias=.5f;desc.MaxAnisotropy=1;
 ComPtr<ID3D11SamplerState>linear,point,comparison;assert(SUCCEEDED(d->CreateSamplerState(&desc,&linear)));
 desc.Filter=D3D11_FILTER_MIN_MAG_MIP_POINT;assert(SUCCEEDED(d->CreateSamplerState(&desc,&point)));
 desc.Filter=D3D11_FILTER_COMPARISON_MIN_MAG_LINEAR_MIP_POINT;desc.ComparisonFunc=D3D11_COMPARISON_LESS_EQUAL;assert(SUCCEEDED(d->CreateSamplerState(&desc,&comparison)));
 ID3D11SamplerState* native[]={linear.Get(),point.Get(),comparison.Get()};c->PSSetSamplers(0,3,native);
 {Draw untouched(c.Get());ComPtr<ID3D11SamplerState>s;c->PSGetSamplers(0,1,&s);assert(s.Get()==linear.Get());}
 enabled=true;{Draw improved(c.Get());ComPtr<ID3D11SamplerState>s;c->PSGetSamplers(0,1,&s);D3D11_SAMPLER_DESC actual{};s->GetDesc(&actual);
  assert(actual.Filter==D3D11_FILTER_ANISOTROPIC&&actual.MaxAnisotropy==16&&actual.MaxLOD==7&&actual.MipLODBias==.5f&&actual.AddressU==D3D11_TEXTURE_ADDRESS_WRAP);
  s.Reset();c->PSGetSamplers(1,1,&s);assert(s.Get()==point.Get());s.Reset();c->PSGetSamplers(2,1,&s);assert(s.Get()==comparison.Get());
 }
 for(unsigned i=0;i<3;++i){ComPtr<ID3D11SamplerState>s;c->PSGetSamplers(i,1,&s);assert(s.Get()==native[i]);}
 const auto count=cache.entries.size();const auto began=std::chrono::steady_clock::now();for(int i=0;i<10000;++i){Draw repeated(c.Get());}assert(cache.entries.size()==count);
 const auto us=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-began).count()/10000;
 enabled=false;std::cout<<"PASS room filtering: 16x on linear materials only, native LOD/address retained, point/comparison unchanged, bindings restored; cached CPU us/draw="<<us<<"\n";
}
