#define NOMINMAX
#include "../../src/render/renderer/fifa_player_renderer.h"
#include <wincodec.h>
#include <wrl/client.h>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <memory>
#include <string>
#include <vector>

using namespace fifa_player;
using Microsoft::WRL::ComPtr;
namespace fs = std::filesystem;

struct PreviewClubPlayerRow {
    int player_id, team_id, number, position, age, overall;
    int head_type, head_class, hair_type, hair_color, skin_tone, skin_type;
    int facial_hair_type, facial_hair_color, shoe_type, shoe_design;
    int gender, height, weight, body_type;
    int eye_color, eyebrow, sideburns, sleeve_length, jersey_fit, jersey_style;
    int sock_length, short_style, glove_type;
    unsigned int club_colors[3];
    int club_colors_valid;
    int attributes[34];
    char name[128];
    int captain, squad_position, secondary_positions[3], secondary_positions_valid;
};
static_assert(sizeof(PreviewClubPlayerRow) == 420, "offline roster fixture ABI");

static bool read_club_fixture(const fs::path &path, int team_id, ClubPlayerRow &club) {
    std::ifstream in(path, std::ios::binary);
    char magic[8] = {};
    uint32_t count = 0, file_team = 0, row_size = 0;
    char team_name[128] = {};
    in.read(magic, 8); in.read(reinterpret_cast<char*>(&count), 4);
    in.read(reinterpret_cast<char*>(&file_team), 4); in.read(reinterpret_cast<char*>(&row_size), 4);
    in.read(team_name, sizeof(team_name));
    if (!in || std::memcmp(magic, "C3DQA003", 8) || file_team != static_cast<uint32_t>(team_id) ||
        row_size != sizeof(PreviewClubPlayerRow) || count > CLUB_PLAYER_CAPACITY) return false;
    std::vector<PreviewClubPlayerRow> rows(count);
    in.read(reinterpret_cast<char*>(rows.data()), static_cast<std::streamsize>(rows.size()*sizeof(rows[0])));
    if (!in) return false;
    auto it = std::find_if(rows.begin(), rows.end(), [team_id](const PreviewClubPlayerRow &r) {
        return r.team_id == team_id && r.club_colors_valid;
    });
    if (it == rows.end()) return false;
    club = {};
    club.team_id = team_id;
    club.club_colors_valid = it->club_colors_valid;
    std::copy(std::begin(it->club_colors), std::end(it->club_colors), std::begin(club.club_colors));
    return true;
}

static bool save_png(IWICImagingFactory *factory, ID3D11Device *device,
    ID3D11DeviceContext *context, ID3D11ShaderResourceView *srv, const fs::path &path) {
    if (!srv || !factory || !device || !context) return false;
    ComPtr<ID3D11Resource> resource; srv->GetResource(resource.GetAddressOf());
    ComPtr<ID3D11Texture2D> texture;
    if (!resource || FAILED(resource.As(&texture))) return false;
    D3D11_TEXTURE2D_DESC desc = {}; texture->GetDesc(&desc);
    desc.Usage = D3D11_USAGE_STAGING; desc.BindFlags = 0;
    desc.CPUAccessFlags = D3D11_CPU_ACCESS_READ; desc.MiscFlags = 0;
    ComPtr<ID3D11Texture2D> staging;
    if (FAILED(device->CreateTexture2D(&desc, nullptr, staging.GetAddressOf()))) return false;
    context->CopyResource(staging.Get(), texture.Get());
    D3D11_MAPPED_SUBRESOURCE mapped = {};
    if (FAILED(context->Map(staging.Get(), 0, D3D11_MAP_READ, 0, &mapped))) return false;
    const size_t stride = size_t(desc.Width)*4, bytes = stride*desc.Height;
    std::vector<uint8_t> bgra(bytes);
    for (UINT y=0; y<desc.Height; ++y) {
        const auto *src = static_cast<const uint8_t*>(mapped.pData)+size_t(y)*mapped.RowPitch;
        auto *dst = bgra.data()+size_t(y)*stride;
        for (UINT x=0; x<desc.Width; ++x) {
            const unsigned a=src[size_t(x)*4+3];
            dst[size_t(x)*4+0]=static_cast<uint8_t>((src[size_t(x)*4+2]*a+255*(255-a)+127)/255);
            dst[size_t(x)*4+1]=static_cast<uint8_t>((src[size_t(x)*4+1]*a+255*(255-a)+127)/255);
            dst[size_t(x)*4+2]=static_cast<uint8_t>((src[size_t(x)*4+0]*a+255*(255-a)+127)/255);
            dst[size_t(x)*4+3]=255;
        }
    }
    context->Unmap(staging.Get(), 0);
    ComPtr<IWICStream> stream; ComPtr<IWICBitmapEncoder> encoder;
    ComPtr<IWICBitmapFrameEncode> frame; ComPtr<IPropertyBag2> properties;
    HRESULT hr=factory->CreateStream(stream.GetAddressOf());
    if(SUCCEEDED(hr))hr=stream->InitializeFromFilename(path.c_str(),GENERIC_WRITE);
    if(SUCCEEDED(hr))hr=factory->CreateEncoder(GUID_ContainerFormatPng,nullptr,encoder.GetAddressOf());
    if(SUCCEEDED(hr))hr=encoder->Initialize(stream.Get(),WICBitmapEncoderNoCache);
    if(SUCCEEDED(hr))hr=encoder->CreateNewFrame(frame.GetAddressOf(),properties.GetAddressOf());
    if(SUCCEEDED(hr))hr=frame->Initialize(properties.Get());
    if(SUCCEEDED(hr))hr=frame->SetSize(desc.Width,desc.Height);
    WICPixelFormatGUID format=GUID_WICPixelFormat32bppBGRA;
    if(SUCCEEDED(hr))hr=frame->SetPixelFormat(&format);
    if(SUCCEEDED(hr)&&!IsEqualGUID(format,GUID_WICPixelFormat32bppBGRA))hr=E_FAIL;
    if(SUCCEEDED(hr))hr=frame->WritePixels(desc.Height,static_cast<UINT>(stride),static_cast<UINT>(bytes),bgra.data());
    if(SUCCEEDED(hr))hr=frame->Commit();
    if(SUCCEEDED(hr))hr=encoder->Commit();
    return SUCCEEDED(hr);
}

static std::string slug(std::string name) {
    const std::pair<const char*,const char*> replacements[]={{"á","a"},{"ã","a"},{"â","a"},{"é","e"},{"ê","e"},{"í","i"},{"ó","o"},{"ô","o"},{"ú","u"},{"ç","c"}};
    for(const auto&r:replacements)for(size_t at=0;(at=name.find(r.first,at))!=std::string::npos;at+=std::strlen(r.second))name.replace(at,std::strlen(r.first),r.second);
    std::string out;bool dash=false;
    for(unsigned char c:name){if(c>='A'&&c<='Z')c=static_cast<unsigned char>(c-'A'+'a');
        if((c>='a'&&c<='z')||(c>='0'&&c<='9')){out.push_back(static_cast<char>(c));dash=false;}
        else if(!out.empty()&&!dash){out.push_back('-');dash=true;}}
    while(!out.empty()&&out.back()=='-')out.pop_back();return out;
}

int wmain(int argc, wchar_t **argv) {
    if(argc!=5){std::fwprintf(stderr,L"Uso: generate_coach_pose_gallery.exe <jogo> <elenco.bin> <id-clube> <pasta-nova>\n");return 2;}
    const fs::path game_root(argv[1]),fixture(argv[2]),output(argv[4]);
    const int team_id=std::wcstol(argv[3],nullptr,10);
    if(fs::exists(output)){std::fwprintf(stderr,L"A pasta de saída já existe; nada foi sobrescrito: %ls\n",output.c_str());return 2;}
    ClubPlayerRow club={};if(team_id<=0||!read_club_fixture(fixture,team_id,club)){std::fprintf(stderr,"Elenco de referência incompatível ou sem cores do clube.\n");return 1;}
    const size_t count=presentation_pose_count(PoseCoachAny);
    if(count!=10){std::fprintf(stderr,"Esperava 10 poses de treinador; o catálogo atual contém %zu.\n",count);return 1;}
    HRESULT com=CoInitializeEx(nullptr,COINIT_MULTITHREADED);if(FAILED(com))return 1;
    ComPtr<IWICImagingFactory>wic;HRESULT hr=CoCreateInstance(CLSID_WICImagingFactory,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(wic.GetAddressOf()));
    if(FAILED(hr)){CoUninitialize();return 1;}
    ID3D11Device*device=nullptr;ID3D11DeviceContext*context=nullptr;
    hr=D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&device,nullptr,&context);
    if(FAILED(hr)){CoUninitialize();return 1;}
    bool ok=true;std::error_code ec;fs::create_directories(output,ec);if(ec)ok=false;
    std::vector<std::string> rows;
    if(ok){Assets assets(game_root.string());CoachAsset coach=assets.coach(club);
        if(!coach.model||coach.model->parts.empty()){std::fprintf(stderr,"Não consegui carregar o modelo 3D do técnico do clube %d.\n",team_id);ok=false;}
        else{Renderer renderer;renderer.device(device);
            for(size_t i=0;i<count&&ok;++i){const auto*info=presentation_pose_at(i,PoseCoachAny);if(!info){ok=false;break;}
                char id[8];std::snprintf(id,sizeof(id),"%03u",info->id);
                fs::path folder=output/(std::string(id)+"_"+slug(info->name));fs::create_directories(folder,ec);if(ec){ok=false;break;}
                auto posed=std::make_shared<Model>(*coach.model);
                if(!apply_coach_pose(*posed,info->id)||!renderer.model(posed)||!renderer.render(720,960,0,1.02f,false,0,0,true)){
                    std::fprintf(stderr,"Falha na renderização da pose %s.\n",info->name);ok=false;break;}
                if(!save_png(wic.Get(),device,context,renderer.image(),folder/"01-frente.png")){ok=false;break;}
                std::ofstream note(folder/"pose.txt",std::ios::binary);
                note<<"Pose de treinador "<<info->id<<" — "<<info->name<<"\r\n"
                    <<"Renderização estática do modelo 3D do clube "<<team_id<<", corpo inteiro, vista frontal e fundo branco.\r\n";
                if(!note){ok=false;break;}
                rows.push_back(std::string(id)+"_"+slug(info->name)+"|"+info->name+"|"+id);
                std::printf("Imagem gerada: %s (ID %u)\n",info->name,info->id);
            }
            renderer.clear();
        }
    }
    context->Release();device->Release();
    if(ok){std::ofstream index(output/"LEIA-ME.md",std::ios::binary);
        index<<"# Catálogo de poses do treinador\r\n\r\n"
             <<"Renderizações estáticas do modelo 3D específico do clube "<<team_id<<". Uma imagem frontal, de corpo inteiro e com fundo branco por pose.\r\n\r\n"
             <<"Estas imagens mostram poses estáticas; o catálogo não contém clipes de animação.\r\n\r\n";
        for(const auto&r:rows){auto a=r.find('|'),b=r.find('|',a+1);index<<"- **ID "<<r.substr(b+1)<<" — "<<r.substr(a+1,b-a-1)<<"**: [ver imagem]("<<r.substr(0,a)<<"/01-frente.png)\r\n";}
        if(!index)ok=false;
    }
    CoUninitialize();if(!ok)return 1;
    /* The progress lines above use narrow stdio; keep stdout byte-oriented. */
    std::printf("Catalogo de poses pronto.\n");return 0;
}
