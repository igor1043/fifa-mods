#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <d3d11_1.h>
#include <cassert>
#include <cstdio>
#include "graphics.h"
using Bind=void(STDMETHODCALLTYPE*)(ID3D11DeviceContext*,UINT,UINT,ID3D11Buffer*const*,const UINT*,const UINT*);
static Bind original=nullptr;
static ID3D11Buffer*player=nullptr;
static unsigned playerBinds=0;
static void STDMETHODCALLTYPE observe(ID3D11DeviceContext*c,UINT start,UINT count,ID3D11Buffer*const*buffers,const UINT*strides,const UINT*offsets){if(start==0&&count&&buffers&&buffers[0]==player)++playerBinds;original(c,start,count,buffers,strides,offsets);}
static void exchange(void**slot,void*pointer){DWORD old=0;assert(VirtualProtect(slot,8,PAGE_READWRITE,&old));*slot=pointer;DWORD ignored=0;assert(VirtualProtect(slot,8,old,&ignored));}
int main(){
 ID3D11Device*d=nullptr;ID3D11DeviceContext*c=nullptr;
 assert(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&d,nullptr,&c)));
 ID3D11DeviceContext1*c1=nullptr;assert(SUCCEEDED(c->QueryInterface(__uuidof(ID3D11DeviceContext1),(void**)&c1)));
 D3D11_BUFFER_DESC desc{};desc.ByteWidth=112;desc.BindFlags=D3D11_BIND_VERTEX_BUFFER;ID3D11Buffer*cards=nullptr;
 assert(SUCCEEDED(d->CreateBuffer(&desc,nullptr,&player)));assert(SUCCEEDED(d->CreateBuffer(&desc,nullptr,&cards)));
 desc.ByteWidth=65536;desc.BindFlags=D3D11_BIND_CONSTANT_BUFFER;ID3D11Buffer*packed=nullptr;assert(SUCCEEDED(d->CreateBuffer(&desc,nullptr,&packed)));
 D3D11_TEXTURE2D_DESC td{};td.Width=td.Height=4;td.MipLevels=td.ArraySize=td.SampleDesc.Count=1;td.Format=DXGI_FORMAT_R8G8B8A8_UNORM;td.BindFlags=D3D11_BIND_RENDER_TARGET|D3D11_BIND_SHADER_RESOURCE;
 ID3D11Texture2D*texture=nullptr;ID3D11RenderTargetView*rt=nullptr;ID3D11ShaderResourceView*srv=nullptr;
 assert(SUCCEEDED(d->CreateTexture2D(&td,nullptr,&texture)));assert(SUCCEEDED(d->CreateRenderTargetView(texture,nullptr,&rt)));assert(SUCCEEDED(d->CreateShaderResourceView(texture,nullptr,&srv)));
 auto table=*reinterpret_cast<void***>(c);original=reinterpret_cast<Bind>(table[18]);exchange(table+18,(void*)&observe);
 UINT stride=28,offset=0,first=64,count=16;c->IASetVertexBuffers(0,1,&player,&stride,&offset);
 unsigned before=playerBinds;{clubgfx::SavedState legacy;legacy.save(c);c->IASetVertexBuffers(0,1,&cards,&stride,&offset);legacy.restore(c);}assert(playerBinds==before+1);
 clubgfx::UiPipelineState ui;
 for(unsigned frame=0;frame<300;++frame){
  c->IASetVertexBuffers(0,1,&player,&stride,&offset);c->PSSetShaderResources(4,1,&srv);c1->PSSetConstantBuffers1(0,1,&packed,&first,&count);before=playerBinds;
  {clubgfx::UiPass pass(c,ui);assert(pass.isolated);ID3D11RenderTargetView*empty=nullptr;c->OMGetRenderTargets(1,&empty,nullptr);assert(!empty);
   c->ClearState();c->IASetVertexBuffers(0,1,&cards,&stride,&offset);c->OMSetRenderTargets(1,&rt,nullptr);const float color[]={float(frame%3)/3.f,.5f,.8f,1};c->ClearRenderTargetView(rt,color);}
  assert(!ui.active&&ui.enters==ui.restores&&ui.unsupported==0);assert(playerBinds==before);
  ID3D11Buffer*bound=nullptr;UINT boundStride=0,boundOffset=0;c->IAGetVertexBuffers(0,1,&bound,&boundStride,&boundOffset);assert(bound==player&&boundStride==28);bound->Release();
  ID3D11ShaderResourceView*view=nullptr;c->PSGetShaderResources(4,1,&view);assert(view==srv);view->Release();UINT actualFirst=0,actualCount=0;c1->PSGetConstantBuffers1(0,1,&bound,&actualFirst,&actualCount);assert(bound==packed&&actualFirst==first&&actualCount==count);bound->Release();
 }
 exchange(table+18,(void*)original);ui.clear();c->ClearState();srv->Release();rt->Release();texture->Release();packed->Release();cards->Release();player->Release();c1->Release();c->Release();d->Release();
 puts("PASS native UI isolation: 300 changing card frames retain player/material and packed lighting bindings without replaying animation bind; UI backbuffer references cleared before resize");
}
