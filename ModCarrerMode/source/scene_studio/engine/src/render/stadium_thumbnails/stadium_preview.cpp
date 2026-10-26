#define NOMINMAX
#include "stadium_preview.h"
#include <windows.h>
#include <wincodec.h>
#include <algorithm>
#include <fstream>
#pragma comment(lib,"windowscodecs.lib")
#pragma comment(lib,"ole32.lib")
namespace stadium_preview {
namespace {
bool decode(const std::string&path,fifa_player::Texture&out) {
    int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,path.c_str(),-1,nullptr,0);
    UINT cp=CP_UTF8;if(!n){cp=CP_ACP;n=MultiByteToWideChar(cp,0,path.c_str(),-1,nullptr,0);}if(!n)return false;
    std::vector<wchar_t>w(n);MultiByteToWideChar(cp,0,path.c_str(),-1,w.data(),n);
    IWICImagingFactory*f=nullptr;IWICBitmapDecoder*d=nullptr;IWICBitmapFrameDecode*frame=nullptr;IWICFormatConverter*c=nullptr;
    HRESULT init=CoInitializeEx(nullptr,COINIT_MULTITHREADED);bool ok=false;
    do {
        if(FAILED(init)&&init!=RPC_E_CHANGED_MODE)break;
        if(FAILED(CoCreateInstance(CLSID_WICImagingFactory,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(&f))))break;
        if(FAILED(f->CreateDecoderFromFilename(w.data(),nullptr,GENERIC_READ,WICDecodeMetadataCacheOnLoad,&d))||
            FAILED(d->GetFrame(0,&frame))||FAILED(f->CreateFormatConverter(&c)))break;
        UINT width=0,height=0;if(FAILED(frame->GetSize(&width,&height))||!width||!height||width>4096||height>4096)break;
        if(FAILED(c->Initialize(frame,GUID_WICPixelFormat32bppRGBA,WICBitmapDitherTypeNone,nullptr,0,WICBitmapPaletteTypeCustom)))break;
        fifa_player::Texture t;t.width=width;t.height=height;t.format=3;t.bytes.resize(size_t(width)*height*4);
        if(FAILED(c->CopyPixels(nullptr,width*4,(UINT)t.bytes.size(),t.bytes.data())))break;
        out=std::move(t);ok=true;
    }while(false);
    if(c)c->Release();if(frame)frame->Release();if(d)d->Release();if(f)f->Release();if(SUCCEEDED(init))CoUninitialize();return ok;
}
}
bool load_file(const std::string&path,fifa_player::Texture&out) {out={};return decode(path,out);}
bool load(const std::string&root,const std::string&key,fifa_player::Texture&out,std::string&source) {
    out={};source.clear();std::string candidate=key;
    while(!candidate.empty()&&(candidate.back()==' '||candidate.back()=='\t'))candidate.pop_back();
    size_t start=candidate.find_first_not_of(" \t");if(start==candidate.npos)return false;candidate.erase(0,start);
    if(candidate=="."||candidate==".."||candidate.find_first_of("/\\:*?\"<>|")!=candidate.npos)return false;
    auto lower=candidate;std::transform(lower.begin(),lower.end(),lower.begin(),[](unsigned char c){return (char)tolower(c);});
    for(const char*ext:{".rar",".zip",".png",".jpg",".jpeg",".dds"}) {
        size_t size=strlen(ext);if(lower.size()>size&&lower.compare(lower.size()-size,size,ext)==0){candidate.resize(candidate.size()-size);break;}
    }
    while(!candidate.empty()) {
        for(const char*ext:{".png",".jpg",".jpeg",".dds"}) {
            std::string path=root+"/StadiumGBD/render/thumbnail/stadium/"+candidate+ext;
            if(GetFileAttributesA(path.c_str())==INVALID_FILE_ATTRIBUTES)continue;
            bool ok=false;
            if(!strcmp(ext,".dds")){
                std::ifstream f(path,std::ios::binary|std::ios::ate);auto size=f.tellg();
                if(f&&size>128&&size<64*1024*1024){std::vector<uint8_t>bytes((size_t)size);f.seekg(0);if(f.read((char*)bytes.data(),size))ok=fifa_player::read_crest_dds(bytes,out);}
            }else ok=decode(path,out);
            if(ok){source=path;return true;}
        }
        if(candidate.back()<'0'||candidate.back()>'9')break;
        candidate.pop_back();while(!candidate.empty()&&(candidate.back()==' '||candidate.back()=='\t'))candidate.pop_back();
    }
    return false;
}
}
