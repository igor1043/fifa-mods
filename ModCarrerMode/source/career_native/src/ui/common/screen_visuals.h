#pragma once
#include "../../render/assets/fifa_player_assets.h"
#include "../../../third_party/imgui/imgui.h"
#include <d3d11.h>
#include <windows.h>
#include <wincodec.h>
#include <string>
#include <vector>
#pragma comment(lib,"windowscodecs.lib")
#pragma comment(lib,"ole32.lib")
namespace screen_visuals {
/* A local scope, never replace the shared ImGui style of another screen. */
inline bool begin_fullscreen(const char*name,ImGuiWindowFlags flags){
    const ImVec2 size=ImGui::GetIO().DisplaySize;
    ImGui::SetNextWindowPos({0,0},ImGuiCond_Always);
    ImGui::SetNextWindowSize(size,ImGuiCond_Always);
    ImGui::PushStyleVar(ImGuiStyleVar_WindowRounding,0.f);
    ImGui::PushStyleVar(ImGuiStyleVar_WindowBorderSize,0.f);
    bool visible=ImGui::Begin(name,nullptr,flags|ImGuiWindowFlags_NoMove|
        ImGuiWindowFlags_NoResize|ImGuiWindowFlags_NoSavedSettings);
    ImGui::PopStyleVar(2);
    return visible;
}
struct LightTheme {
    int count=0;
    void color(ImGuiCol id,ImVec4 value){ImGui::PushStyleColor(id,value);++count;}
    LightTheme(){
        color(ImGuiCol_WindowBg,{.94f,.95f,.95f,1});color(ImGuiCol_ChildBg,{.98f,.98f,.98f,1});
        color(ImGuiCol_Text,{.20f,.27f,.29f,1});color(ImGuiCol_TextDisabled,{.43f,.48f,.50f,1});
        color(ImGuiCol_Border,{.69f,.74f,.76f,1});color(ImGuiCol_Separator,{.74f,.78f,.79f,1});
        color(ImGuiCol_Button,{.81f,.87f,.91f,1});color(ImGuiCol_ButtonHovered,{.64f,.77f,.87f,1});
        color(ImGuiCol_ButtonActive,{.48f,.68f,.82f,1});color(ImGuiCol_FrameBg,{.86f,.89f,.90f,1});
        color(ImGuiCol_FrameBgHovered,{.78f,.85f,.90f,1});color(ImGuiCol_FrameBgActive,{.69f,.79f,.86f,1});
        color(ImGuiCol_ScrollbarBg,{.88f,.90f,.90f,1});color(ImGuiCol_ScrollbarGrab,{.56f,.63f,.66f,1});
        color(ImGuiCol_Header,{.75f,.85f,.92f,1});color(ImGuiCol_HeaderHovered,{.65f,.79f,.89f,1});
        color(ImGuiCol_HeaderActive,{.52f,.70f,.84f,1});
    }
    ~LightTheme(){ImGui::PopStyleColor(count);}
};
inline ID3D11ShaderResourceView*upload(ID3D11Device*device,const fifa_player::Texture&t){
    if(!device||!t.width||!t.height||t.format>3||t.bytes.empty())return nullptr;
    D3D11_TEXTURE2D_DESC d={};d.Width=t.width;d.Height=t.height;d.MipLevels=d.ArraySize=1;d.SampleDesc.Count=1;
    d.Format=t.format==3?DXGI_FORMAT_R8G8B8A8_UNORM:t.format==0?DXGI_FORMAT_BC1_UNORM:t.format==1?DXGI_FORMAT_BC2_UNORM:DXGI_FORMAT_BC3_UNORM;
    d.BindFlags=D3D11_BIND_SHADER_RESOURCE;d.Usage=D3D11_USAGE_IMMUTABLE;
    UINT pitch=t.format==3?t.width*4:((t.width+3)/4)*(t.format?16:8);
    size_t minimum=(size_t)pitch*(t.format==3?t.height:(t.height+3)/4);if(t.bytes.size()<minimum)return nullptr;
    D3D11_SUBRESOURCE_DATA data={t.bytes.data(),pitch,(UINT)t.bytes.size()};
    ID3D11Texture2D*texture=nullptr;ID3D11ShaderResourceView*v=nullptr;
    if(SUCCEEDED(device->CreateTexture2D(&d,&data,&texture))){device->CreateShaderResourceView(texture,nullptr,&v);texture->Release();}return v;
}
/* Generic menu artwork loader. Decodes on the screen's worker thread and
 * returns owned RGBA bytes; no stadium-preview or game-resource dependency. */
inline bool load_image_file(const std::string&path,fifa_player::Texture&out){
    out={};int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,path.c_str(),-1,nullptr,0),cp=CP_UTF8;
    if(!n){cp=CP_ACP;n=MultiByteToWideChar(cp,0,path.c_str(),-1,nullptr,0);}if(!n)return false;
    std::vector<wchar_t>w(n);MultiByteToWideChar(cp,0,path.c_str(),-1,w.data(),n);
    IWICImagingFactory*f=nullptr;IWICBitmapDecoder*decoder=nullptr;IWICBitmapFrameDecode*frame=nullptr;IWICFormatConverter*converter=nullptr;
    HRESULT init=CoInitializeEx(nullptr,COINIT_MULTITHREADED);bool ok=false;
    do{if(FAILED(init)&&init!=RPC_E_CHANGED_MODE)break;
        if(FAILED(CoCreateInstance(CLSID_WICImagingFactory,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(&f))))break;
        if(FAILED(f->CreateDecoderFromFilename(w.data(),nullptr,GENERIC_READ,WICDecodeMetadataCacheOnLoad,&decoder))||
           FAILED(decoder->GetFrame(0,&frame))||FAILED(f->CreateFormatConverter(&converter)))break;
        UINT width=0,height=0;if(FAILED(frame->GetSize(&width,&height))||!width||!height||width>4096||height>4096)break;
        if(FAILED(converter->Initialize(frame,GUID_WICPixelFormat32bppRGBA,WICBitmapDitherTypeNone,nullptr,0,WICBitmapPaletteTypeCustom)))break;
        fifa_player::Texture decoded;decoded.width=width;decoded.height=height;decoded.format=3;decoded.bytes.resize(size_t(width)*height*4);
        if(FAILED(converter->CopyPixels(nullptr,width*4,(UINT)decoded.bytes.size(),decoded.bytes.data())))break;
        out=std::move(decoded);ok=true;
    }while(false);
    if(converter)converter->Release();if(frame)frame->Release();if(decoder)decoder->Release();if(f)f->Release();if(SUCCEEDED(init))CoUninitialize();return ok;
}
inline void release(ID3D11ShaderResourceView*&v){if(v){v->Release();v=nullptr;}}
}
