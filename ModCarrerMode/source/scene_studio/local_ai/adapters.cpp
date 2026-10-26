#include <windows.h>
#include <dxgi1_2.h>
#include <cstdio>
int main(){IDXGIFactory1*f=nullptr;if(FAILED(CreateDXGIFactory1(__uuidof(IDXGIFactory1),(void**)&f)))return 1;UINT chosen=0;SIZE_T best=0;for(UINT i=0;;++i){IDXGIAdapter1*a=nullptr;if(f->EnumAdapters1(i,&a)!=S_OK)break;DXGI_ADAPTER_DESC1 d{};a->GetDesc1(&d);if(!(d.Flags&DXGI_ADAPTER_FLAG_SOFTWARE)&&d.DedicatedVideoMemory>best){best=d.DedicatedVideoMemory;chosen=i;}a->Release();}printf("{\"device_id\":%u,\"dedicated_bytes\":%llu}\n",chosen,(unsigned long long)best);f->Release();}
