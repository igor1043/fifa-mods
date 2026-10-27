#pragma once
// Globe-only loaders. Original FIFA icons/material loaders stay unchanged.
#include "graphics.h"
#include <fstream>
#include <iterator>

namespace clubgfx {
inline bool globeSurface(ID3D11Device* dev,Texture& out,const std::wstring& path){
 std::ifstream file(path,std::ios::binary);std::vector<unsigned char> data{std::istreambuf_iterator<char>(file),{}};
 if(data.size()<128||memcmp(data.data(),"DDS ",4)||clubassets::le(data.data()+4)!=124||clubassets::le(data.data()+84)!=0x31545844)return false;
 unsigned w=clubassets::le(data.data()+16),h=clubassets::le(data.data()+12),mips=clubassets::le(data.data()+28);
 if(w!=8192||h!=4096||mips!=14)return false;
 std::array<D3D11_SUBRESOURCE_DATA,14> levels{};size_t offset=128;
 for(unsigned i=0,x=w,y=h;i<mips;++i,x=(std::max)(1u,x/2),y=(std::max)(1u,y/2)){
  unsigned pitch=((x+3)/4)*8;size_t bytes=size_t(pitch)*((y+3)/4);if(bytes>data.size()-offset)return false;
  levels[i]={data.data()+offset,pitch,0};offset+=bytes;
 }
 if(offset!=data.size())return false;
 D3D11_TEXTURE2D_DESC d{};d.Width=w;d.Height=h;d.MipLevels=mips;d.ArraySize=d.SampleDesc.Count=1;d.Format=DXGI_FORMAT_BC1_UNORM;d.Usage=D3D11_USAGE_IMMUTABLE;d.BindFlags=D3D11_BIND_SHADER_RESOURCE;
 Texture next;if(FAILED(dev->CreateTexture2D(&d,levels.data(),&next.texture)))return false;
 if(FAILED(dev->CreateShaderResourceView(next.texture,nullptr,&next.view))){next.clear();return false;}
 next.w=w;next.h=h;next.key=path;out.clear();out=next;return true;
}
inline bool globeAtlas(ID3D11Device* dev,Texture& out,const std::wstring& path){
 Texture next;IWICImagingFactory* factory=nullptr;IWICBitmapDecoder* decoder=nullptr;IWICBitmapFrameDecode* frame=nullptr;IWICFormatConverter* converter=nullptr;bool ok=false;
 if(SUCCEEDED(CoCreateInstance(CLSID_WICImagingFactory,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(&factory)))&&SUCCEEDED(factory->CreateDecoderFromFilename(path.c_str(),nullptr,GENERIC_READ,WICDecodeMetadataCacheOnDemand,&decoder))&&SUCCEEDED(decoder->GetFrame(0,&frame))&&SUCCEEDED(factory->CreateFormatConverter(&converter))&&SUCCEEDED(converter->Initialize(frame,GUID_WICPixelFormat32bppBGRA,WICBitmapDitherTypeNone,nullptr,0,WICBitmapPaletteTypeCustom))){
  UINT w=0,h=0;converter->GetSize(&w,&h);if(w==8192&&h==4096){std::vector<unsigned char> bgra(size_t(w)*h*4),rg(size_t(w)*h*2);
   if(SUCCEEDED(converter->CopyPixels(nullptr,w*4,UINT(bgra.size()),bgra.data()))){for(size_t i=0;i<size_t(w)*h;++i){rg[i*2]=bgra[i*4+2];rg[i*2+1]=bgra[i*4+3];}
    D3D11_TEXTURE2D_DESC d{};d.Width=w;d.Height=h;d.MipLevels=d.ArraySize=d.SampleDesc.Count=1;d.Format=DXGI_FORMAT_R8G8_UNORM;d.Usage=D3D11_USAGE_IMMUTABLE;d.BindFlags=D3D11_BIND_SHADER_RESOURCE;D3D11_SUBRESOURCE_DATA initial{rg.data(),w*2,0};
    ok=SUCCEEDED(dev->CreateTexture2D(&d,&initial,&next.texture))&&SUCCEEDED(dev->CreateShaderResourceView(next.texture,nullptr,&next.view));if(ok){next.w=w;next.h=h;next.key=path;}
   }
  }
 }
 release(converter);release(frame);release(decoder);release(factory);if(!ok){next.clear();return false;}out.clear();out=next;return true;
}
}
