#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <d3d11.h>
#include <d3d11_1.h>
#include <cassert>
#include <algorithm>
#include <iostream>
#include "graphics.h"
using namespace clubgfx;
int main(){
 _set_error_mode(_OUT_TO_STDERR);ID3D11Device*d=nullptr;ID3D11DeviceContext*c=nullptr;
 assert(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&d,nullptr,&c)));unsigned failures=0;
 for(unsigned width:{640u,960u,1280u})for(unsigned frame=0;frame<3;++frame){
  c->ClearState();D3D11_TEXTURE2D_DESC desc{};desc.Width=width;desc.Height=width*9/16;desc.MipLevels=desc.ArraySize=desc.SampleDesc.Count=1;desc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;desc.BindFlags=D3D11_BIND_RENDER_TARGET|D3D11_BIND_SHADER_RESOURCE|D3D11_BIND_UNORDERED_ACCESS;
  ID3D11Texture2D*scene=nullptr,*back=nullptr;ID3D11RenderTargetView*sceneRT=nullptr,*backRT=nullptr;ID3D11ShaderResourceView*srv=nullptr;ID3D11UnorderedAccessView*uav=nullptr;
  assert(SUCCEEDED(d->CreateTexture2D(&desc,nullptr,&scene)));assert(SUCCEEDED(d->CreateTexture2D(&desc,nullptr,&back)));assert(SUCCEEDED(d->CreateRenderTargetView(scene,nullptr,&sceneRT)));assert(SUCCEEDED(d->CreateRenderTargetView(back,nullptr,&backRT)));assert(SUCCEEDED(d->CreateShaderResourceView(back,nullptr,&srv)));assert(SUCCEEDED(d->CreateUnorderedAccessView(back,nullptr,&uav)));
  c->OMSetRenderTargets(1,&sceneRT,nullptr);
  if(frame==0){c->VSSetShaderResources(5,1,&srv);c->PSSetShaderResources(7,1,&srv);c->GSSetShaderResources(11,1,&srv);c->HSSetShaderResources(13,1,&srv);c->DSSetShaderResources(17,1,&srv);c->CSSetShaderResources(19,1,&srv);}
  if(frame==1)c->CSSetUnorderedAccessViews(2,1,&uav,nullptr);
  if(frame==2)c->OMSetRenderTargetsAndUnorderedAccessViews(1,&sceneRT,nullptr,3,1,&uav,nullptr);
  {SavedState state;state.save(c);c->OMSetRenderTargets(1,&backRT,nullptr);const float dark[]={0,0,0,0};c->ClearRenderTargetView(backRT,dark);state.restore(c);}
  ID3D11RenderTargetView*rt=nullptr;c->OMGetRenderTargets(1,&rt,nullptr);assert(rt==sceneRT);release(rt);
  auto check=[&](ID3D11ShaderResourceView*actual,const char*stage){if(actual!=srv){++failures;std::cerr<<"LOST "<<stage<<" resource after overlay at "<<width<<"\n";}release(actual);};
  if(frame==0){ID3D11ShaderResourceView*actual=nullptr;c->VSGetShaderResources(5,1,&actual);check(actual,"VS t5");c->PSGetShaderResources(7,1,&actual);check(actual,"PS t7");c->GSGetShaderResources(11,1,&actual);check(actual,"GS t11");c->HSGetShaderResources(13,1,&actual);check(actual,"HS t13");c->DSGetShaderResources(17,1,&actual);check(actual,"DS t17");c->CSGetShaderResources(19,1,&actual);check(actual,"CS t19");}
  if(frame==1){ID3D11UnorderedAccessView*actual=nullptr;c->CSGetUnorderedAccessViews(2,1,&actual);if(actual!=uav){++failures;std::cerr<<"LOST CS UAV after overlay\n";}release(actual);}
  if(frame==2){ID3D11UnorderedAccessView*actual=nullptr;c->OMGetRenderTargetsAndUnorderedAccessViews(0,nullptr,nullptr,3,1,&actual);if(actual!=uav){++failures;std::cerr<<"LOST OM UAV after overlay\n";}release(actual);}
  c->ClearState();release(uav);release(srv);release(backRT);release(sceneRT);release(back);release(scene);
 }
 ID3D11DeviceContext1*context1=nullptr;assert(SUCCEEDED(c->QueryInterface(__uuidof(ID3D11DeviceContext1),(void**)&context1)));D3D11_BUFFER_DESC cbDesc{};cbDesc.ByteWidth=65536;cbDesc.Usage=D3D11_USAGE_DEFAULT;cbDesc.BindFlags=D3D11_BIND_CONSTANT_BUFFER;ID3D11Buffer*packed=nullptr,*overlay=nullptr;assert(SUCCEEDED(d->CreateBuffer(&cbDesc,nullptr,&packed)));cbDesc.ByteWidth=64;assert(SUCCEEDED(d->CreateBuffer(&cbDesc,nullptr,&overlay)));
 for(UINT start:{16u,64u,256u}){UINT count=16;context1->PSSetConstantBuffers1(0,1,&packed,&start,&count);ID3D11Buffer*prior=nullptr;UINT priorStart=0,priorCount=0;context1->PSGetConstantBuffers1(0,1,&prior,&priorStart,&priorCount);assert(prior==packed&&priorStart==start&&priorCount==count);prior->Release();{SavedState state;state.save(c);c->PSSetConstantBuffers(0,1,&overlay);state.restore(c);}ID3D11Buffer*restored=nullptr;UINT actualStart=0,actualCount=0;context1->PSGetConstantBuffers1(0,1,&restored,&actualStart,&actualCount);if(restored!=packed||actualStart!=start||actualCount!=count){++failures;std::cerr<<"LOST D3D11.1 PS b0 range: expected "<<start<<"/"<<count<<", got "<<actualStart<<"/"<<actualCount<<"\n";}if(restored)restored->Release();}
 c->ClearState();overlay->Release();packed->Release();context1->Release();
 c->Release();d->Release();if(failures){std::cerr<<"FAIL "<<failures<<" native render bindings were not restored\n";return 1;}std::cout<<"PASS D3D11: all six shader stages, CS/OM UAVs, render target, rotating buffers and three sizes preserved across overlay\n";return 0;
}
