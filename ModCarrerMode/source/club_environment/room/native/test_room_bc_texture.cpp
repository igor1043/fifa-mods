#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <d3d11.h>
#include <cassert>
#include <vector>
#include <iostream>
#pragma comment(lib,"d3d11.lib")
int main(){
 ID3D11Device* device=nullptr;ID3D11DeviceContext* context=nullptr;
 assert(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&device,nullptr,&context)));
 auto texture=[&](unsigned w,unsigned h){
  D3D11_TEXTURE2D_DESC d{};d.Width=w;d.Height=h;d.MipLevels=1;d.ArraySize=1;d.Format=DXGI_FORMAT_BC3_UNORM;d.SampleDesc.Count=1;d.Usage=D3D11_USAGE_IMMUTABLE;d.BindFlags=D3D11_BIND_SHADER_RESOURCE;
  unsigned pitch=((w+3)/4)*16;std::vector<unsigned char> pixels(pitch*((h+3)/4));D3D11_SUBRESOURCE_DATA initial{pixels.data(),pitch,0};ID3D11Texture2D* t=nullptr;HRESULT hr=device->CreateTexture2D(&d,&initial,&t);if(t)t->Release();return hr;
 };
 assert(FAILED(texture(887,1774)));assert(SUCCEEDED(texture(888,1776)));assert(SUCCEEDED(texture(768,1536)));
 context->Release();device->Release();std::cout<<"PASS D3D11 rejects the old Remo BC3 dimensions; aligned converted texture accepted\n";
}
