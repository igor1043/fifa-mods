#define NOMINMAX
#include "../../src/render/renderer/fifa_player_renderer.h"
#include <wincodec.h>
#include <wrl/client.h>
#include <DirectXMath.h>
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

/* The offline club fixture predates the career-only identity fields now at
 * the start of ClubPlayerRow. Decode its own stable, explicitly-sized schema
 * and map fields by name; never reinterpret the old bytes as the live ABI. */
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

static bool read_club_fixture(const fs::path &path, ClubPlayerRow &selected) {
    std::ifstream in(path, std::ios::binary);
    if (!in) { std::fprintf(stderr, "Não foi possível abrir o elenco de referência: %ls\n", path.c_str()); return false; }
    char magic[8] = {};
    uint32_t count = 0, team = 0, row_size = 0;
    char team_name[128] = {};
    in.read(magic, sizeof(magic)); in.read(reinterpret_cast<char*>(&count), 4);
    in.read(reinterpret_cast<char*>(&team), 4); in.read(reinterpret_cast<char*>(&row_size), 4);
    in.read(team_name, sizeof(team_name));
    if (!in || std::memcmp(magic, "C3DQA003", 8) || team != 1043 ||
        row_size != sizeof(PreviewClubPlayerRow) || count > CLUB_PLAYER_CAPACITY) {
        std::fprintf(stderr, "Elenco incompatível: clube=%u, linhas=%u, stride=%u (esperado %zu), assinatura=%.8s.\n",
            team,count,row_size,sizeof(PreviewClubPlayerRow),magic); return false;
    }
    std::vector<PreviewClubPlayerRow> rows(count);
    in.read(reinterpret_cast<char*>(rows.data()), static_cast<std::streamsize>(rows.size()*sizeof(PreviewClubPlayerRow)));
    if (!in || in.peek() != std::char_traits<char>::eof()) {
        std::fprintf(stderr, "O arquivo de elenco está incompleto ou contém dados inesperados.\n"); return false;
    }
    auto it = std::find_if(rows.begin(), rows.end(), [](const PreviewClubPlayerRow &r) {
        return r.team_id == 1043 && r.player_id > 0 && r.squad_position > 0 &&
            r.squad_position < 28 && r.skin_tone >= 5;
    });
    if (it == rows.end()) { std::fprintf(stderr, "Não encontrei um jogador de linha válido no elenco.\n"); return false; }
    selected = {};
    selected.player_id=it->player_id; selected.team_id=it->team_id; selected.number=it->number;
    selected.position=it->position; selected.age=it->age; selected.overall=it->overall;
    selected.birthdate_raw=-1; selected.join_team_date_raw=-1; selected.career_date=-1;
    selected.retiring=-1; selected.weekly_wage=-1; selected.career_data_valid=0;
    selected.head_type=it->head_type; selected.head_class=it->head_class; selected.hair_type=it->hair_type;
    selected.hair_color=it->hair_color; selected.skin_tone=it->skin_tone; selected.skin_type=it->skin_type;
    selected.facial_hair_type=it->facial_hair_type; selected.facial_hair_color=it->facial_hair_color;
    selected.shoe_type=it->shoe_type; selected.shoe_design=it->shoe_design; selected.gender=it->gender;
    selected.height=it->height; selected.weight=it->weight; selected.body_type=it->body_type;
    selected.eye_color=it->eye_color; selected.eyebrow=it->eyebrow; selected.sideburns=it->sideburns;
    selected.sleeve_length=it->sleeve_length; selected.jersey_fit=it->jersey_fit;
    selected.jersey_style=it->jersey_style; selected.sock_length=it->sock_length;
    selected.short_style=it->short_style; selected.glove_type=it->glove_type;
    std::copy(std::begin(it->club_colors),std::end(it->club_colors),std::begin(selected.club_colors));
    selected.club_colors_valid=it->club_colors_valid;
    std::copy(std::begin(it->attributes),std::end(it->attributes),std::begin(selected.attributes));
    std::memcpy(selected.name,it->name,sizeof(selected.name));
    selected.captain=it->captain; selected.squad_position=it->squad_position;
    std::copy(std::begin(it->secondary_positions),std::end(it->secondary_positions),std::begin(selected.secondary_positions));
    selected.secondary_positions_valid=it->secondary_positions_valid;
    selected.name[sizeof(selected.name)-1] = '\0';
    return true;
}

static bool save_png(IWICImagingFactory *factory, ID3D11Device *device,
    ID3D11DeviceContext *context, ID3D11ShaderResourceView *srv, const fs::path &path) {
    if (!srv || !factory || !device || !context) return false;
    ComPtr<ID3D11Resource> resource;
    srv->GetResource(resource.GetAddressOf());
    if (!resource) return false;
    ComPtr<ID3D11Texture2D> texture;
    if (FAILED(resource.As(&texture))) return false;
    D3D11_TEXTURE2D_DESC desc = {}; texture->GetDesc(&desc);
    if (!desc.Width || !desc.Height || desc.Width > 8192 || desc.Height > 8192) return false;
    desc.Usage = D3D11_USAGE_STAGING; desc.BindFlags = 0;
    desc.CPUAccessFlags = D3D11_CPU_ACCESS_READ; desc.MiscFlags = 0;
    ComPtr<ID3D11Texture2D> staging;
    if (FAILED(device->CreateTexture2D(&desc, nullptr, staging.GetAddressOf()))) return false;
    context->CopyResource(staging.Get(), texture.Get());
    D3D11_MAPPED_SUBRESOURCE mapped = {};
    if (FAILED(context->Map(staging.Get(), 0, D3D11_MAP_READ, 0, &mapped))) return false;
    const size_t stride = size_t(desc.Width) * 4, bytes = stride * desc.Height;
    std::vector<uint8_t> bgra(bytes);
    for (UINT y=0; y<desc.Height; ++y) {
        const auto *src = static_cast<const uint8_t*>(mapped.pData) + size_t(y)*mapped.RowPitch;
        auto *dst = bgra.data() + size_t(y)*stride;
        for (UINT x=0; x<desc.Width; ++x) {
            const unsigned alpha = src[size_t(x)*4+3];
            dst[size_t(x)*4+0] = static_cast<uint8_t>((src[size_t(x)*4+2]*alpha + 255*(255-alpha) + 127)/255);
            dst[size_t(x)*4+1] = static_cast<uint8_t>((src[size_t(x)*4+1]*alpha + 255*(255-alpha) + 127)/255);
            dst[size_t(x)*4+2] = static_cast<uint8_t>((src[size_t(x)*4+0]*alpha + 255*(255-alpha) + 127)/255);
            dst[size_t(x)*4+3] = 255;
        }
    }
    context->Unmap(staging.Get(), 0);

    ComPtr<IWICStream> stream;
    ComPtr<IWICBitmapEncoder> encoder;
    ComPtr<IWICBitmapFrameEncode> frame;
    ComPtr<IPropertyBag2> properties;
    HRESULT hr = factory->CreateStream(stream.GetAddressOf());
    if (SUCCEEDED(hr)) hr = stream->InitializeFromFilename(path.c_str(), GENERIC_WRITE);
    if (SUCCEEDED(hr)) hr = factory->CreateEncoder(GUID_ContainerFormatPng, nullptr, encoder.GetAddressOf());
    if (SUCCEEDED(hr)) hr = encoder->Initialize(stream.Get(), WICBitmapEncoderNoCache);
    if (SUCCEEDED(hr)) hr = encoder->CreateNewFrame(frame.GetAddressOf(), properties.GetAddressOf());
    if (SUCCEEDED(hr)) hr = frame->Initialize(properties.Get());
    if (SUCCEEDED(hr)) hr = frame->SetSize(desc.Width, desc.Height);
    WICPixelFormatGUID format = GUID_WICPixelFormat32bppBGRA;
    if (SUCCEEDED(hr)) hr = frame->SetPixelFormat(&format);
    if (SUCCEEDED(hr) && !IsEqualGUID(format, GUID_WICPixelFormat32bppBGRA)) hr = E_FAIL;
    if (SUCCEEDED(hr)) hr = frame->WritePixels(desc.Height, static_cast<UINT>(stride), static_cast<UINT>(bytes), bgra.data());
    if (SUCCEEDED(hr)) hr = frame->Commit();
    if (SUCCEEDED(hr)) hr = encoder->Commit();
    return SUCCEEDED(hr);
}

static std::string slug(std::string name) {
    const std::pair<const char*, const char*> replacements[] = {
        {"á","a"},{"à","a"},{"â","a"},{"ã","a"},{"Á","a"},{"À","a"},{"Â","a"},{"Ã","a"},
        {"é","e"},{"ê","e"},{"É","e"},{"Ê","e"},{"í","i"},{"Í","i"},
        {"ó","o"},{"ô","o"},{"õ","o"},{"Ó","o"},{"Ô","o"},{"Õ","o"},
        {"ú","u"},{"Ú","u"},{"ç","c"},{"Ç","c"}
    };
    for (const auto &r : replacements) for (size_t at=0; (at=name.find(r.first,at))!=std::string::npos; at+=std::strlen(r.second)) name.replace(at,std::strlen(r.first),r.second);
    std::string out; bool dash=false;
    for (unsigned char c : name) {
        if (c >= 'A' && c <= 'Z') c = static_cast<unsigned char>(c-'A'+'a');
        if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9')) { out.push_back(static_cast<char>(c)); dash=false; }
        else if (!out.empty() && !dash) { out.push_back('-'); dash=true; }
    }
    while (!out.empty() && out.back()=='-') out.pop_back();
    return out;
}

int wmain(int argc, wchar_t **argv) {
    if (argc != 4) {
        std::fwprintf(stderr, L"Uso: generate_player_pose_gallery.exe <raiz-do-jogo> <elenco-flamengo.bin> <pasta-de-saida-nova>\n");
        return 2;
    }
    const fs::path game_root(argv[1]), fixture(argv[2]), output(argv[3]);
    if (fs::exists(output)) {
        std::fwprintf(stderr, L"A pasta de saída já existe; nada foi sobrescrito: %ls\n", output.c_str());
        return 2;
    }
    ClubPlayerRow row = {};
    if (!read_club_fixture(fixture, row)) return 1;
    const size_t pose_count = presentation_pose_count(PoseIndividual);
    if (pose_count != 14) {
        std::fprintf(stderr, "Esperava 14 poses individuais; o código atual contém %zu.\n", pose_count);
        return 1;
    }
    std::error_code ec;
    fs::create_directories(output, ec);
    if (ec) { std::fwprintf(stderr, L"Não consegui criar a pasta de saída: %ls\n", output.c_str()); return 1; }

    HRESULT com = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    if (FAILED(com)) { std::fprintf(stderr, "Falha ao inicializar o codificador de imagens do Windows.\n"); return 1; }
    ComPtr<IWICImagingFactory> wic;
    HRESULT hr = CoCreateInstance(CLSID_WICImagingFactory, nullptr, CLSCTX_INPROC_SERVER,
        IID_PPV_ARGS(wic.GetAddressOf()));
    if (FAILED(hr)) { std::fprintf(stderr, "Falha ao iniciar o codificador PNG do Windows.\n"); CoUninitialize(); return 1; }

    ID3D11Device *device = nullptr; ID3D11DeviceContext *context = nullptr;
    hr = D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_WARP, nullptr, 0, nullptr, 0,
        D3D11_SDK_VERSION, &device, nullptr, &context);
    if (FAILED(hr)) { std::fprintf(stderr, "Não foi possível iniciar a renderização 3D offline.\n"); CoUninitialize(); return 1; }
    bool ok = true;
    std::vector<std::string> index_rows;
    {
        Assets assets(game_root.string());
        Model base = assets.load(row);
        if (base.parts.empty()) {
            std::fprintf(stderr, "Não foi possível carregar o modelo 3D do jogador de referência.\n"); ok = false;
        } else {
            std::printf("Jogador de referência: %s (id %d), clube %d\n", row.name, row.player_id, row.team_id);
            Renderer renderer; renderer.device(device);
            struct View { const char *file; const char *label; float yaw; };
            const View views[] = {
                {"01-frente.png", "Frente", 0.f},
                {"02-perfil-lado-a.png", "Perfil — lado A (90°)", DirectX::XM_PIDIV2},
                {"03-perfil-lado-b.png", "Perfil — lado B (−90°)", -DirectX::XM_PIDIV2},
                {"04-costas.png", "Costas (180°)", DirectX::XM_PI},
                {"05-tres-quartos-45.png", "Três quartos (45°)", DirectX::XM_PIDIV4}
            };
            for (size_t i=0; i<pose_count && ok; ++i) {
                const PresentationPoseInfo *info = presentation_pose_at(i, PoseIndividual);
                if (!info) { ok=false; break; }
                char id[8]; std::snprintf(id,sizeof(id),"%03u",info->id);
                const fs::path pose_dir = output / (std::string(id)+"_"+slug(info->name));
                fs::create_directories(pose_dir, ec);
                if (ec) { ok=false; break; }
                auto posed = std::make_shared<Model>(base);
                if (!apply_presentation_pose(*posed, false, nullptr, info->id) || !renderer.model(posed)) {
                    std::fprintf(stderr, "Falha ao preparar a pose %s.\n", info->name); ok=false; break;
                }
                std::printf("Pose %zu/%zu: %s (id %u)\n",i+1,pose_count,info->name,info->id);
                for (size_t v=0; v<_countof(views); ++v) {
                    if (!renderer.render(600,800,views[v].yaw,1.04f,false,0,0,true)) {
                        std::fprintf(stderr,"Falha ao renderizar %s — %s.\n",info->name,views[v].label); ok=false; break;
                    }
                    if (!save_png(wic.Get(),device,context,renderer.image(),pose_dir / views[v].file)) {
                        std::fprintf(stderr,"Falha ao salvar PNG: %ls\n",(pose_dir/views[v].file).c_str()); ok=false; break;
                    }
                }
                /* Raised fist / pointing references also get true camera
                 * close-ups. These are rendered from the posed 3D rig, not
                 * enlarged crops of a full-body PNG, to show each knuckle,
                 * the thumb and the finger curl at useful resolution. */
                if(ok&&(info->id==113||info->id==114)) {
                    struct HandView {const char*file;const char*label;float yaw;};
                    const HandView hand_views[]={
                        {"06-mao-detalhe-frente.png","Mão — frente",0.f},
                        {"07-mao-detalhe-45.png","Mão — três quartos",DirectX::XM_PIDIV4},
                        {"08-mao-detalhe-perfil.png","Mão — perfil",DirectX::XM_PIDIV2}
                    };
                    for(const auto&v:hand_views) {
                        const float scale=std::max(1.f,float(posed->height_cm));
                        const float cosine=std::cos(v.yaw),sine=std::sin(v.yaw);
                        const float focus_x=(posed->right_hand.x*cosine+posed->right_hand.z*sine)/scale;
                        const float focus_y=(posed->right_hand.y+scale*.04f)/scale;
                        const CameraFocus focus={focus_y,focus_x,.18f};
                        if(!renderer.render(800,800,v.yaw,1.f,false,0,0,true,.50f,&focus,true)||
                            !save_png(wic.Get(),device,context,renderer.image(),pose_dir/v.file)) {
                            std::fprintf(stderr,"Falha ao renderizar close-up da mão: %s — %s.\n",info->name,v.label);
                            ok=false;break;
                        }
                    }
                }
                std::ofstream note(pose_dir / "pose.txt", std::ios::binary);
                note << "Pose " << info->id << " — " << info->name << "\r\n"
                << "Cinco vistas do mesmo modelo 3D, com enquadramento de corpo inteiro, fundo branco e a mesma pose estática.\r\n"
                     << "Jogador de referência: " << row.name << " (id " << row.player_id << "), Flamengo.\r\n";
                if(info->id==113||info->id==114)note << "Também inclui três close-ups de mão renderizados com câmera aproximada diretamente no modelo 3D.\r\n";
                if (!note) { ok=false; break; }
                index_rows.push_back(std::string(id)+"_"+slug(info->name)+"|"+info->name+"|"+id);
            }
            renderer.clear();
        }
    }
    context->Release(); device->Release();
    if (ok) {
        std::ofstream index(output / "LEIA-ME.md", std::ios::binary);
        index << "# Catálogo de poses individuais do jogo\r\n\r\n"
              << "**Total: " << pose_count << " poses estáticas** (IDs 101–114). Cada pose tem **5 vistas de corpo inteiro**: frente, dois perfis, costas e três quartos a 45°. As poses 113 e 114 também têm três close-ups de mão cada.\r\n\r\n"
              << "As imagens são renders do modelo 3D nativo do FIFA 16 usando as poses individuais já implementadas no jogo. O jogador aparece sozinho, em fundo branco. Os close-ups usam uma câmera aproximada no mesmo render 3D, não ampliação de recortes. São poses estáticas; este catálogo não inclui ciclos de animação, poses de elenco ou poses de treinador. O mesmo jogador do Flamengo foi usado em toda a série para facilitar a comparação entre vistas.\r\n\r\n"
              << "Jogador de referência: **" << row.name << "**, ID " << row.player_id << ".\r\n\r\n"
              << "| ID | Pose | Frente | Perfil A | Perfil B | Costas | 45° |\r\n|---:|---|---|---|---|---|---|\r\n";
        for (const auto &entry : index_rows) {
            const size_t a=entry.find('|'), b=entry.find('|',a+1);
            const std::string dir=entry.substr(0,a), name=entry.substr(a+1,b-a-1), id=entry.substr(b+1);
            index << "| " << id << " | [" << name << "](" << dir << "/pose.txt) | [ver](" << dir << "/01-frente.png) | [ver](" << dir << "/02-perfil-lado-a.png) | [ver](" << dir << "/03-perfil-lado-b.png) | [ver](" << dir << "/04-costas.png) | [ver](" << dir << "/05-tres-quartos-45.png) |\r\n";
        }
        index << "\r\n## Close-ups das mãos\r\n\r\n"
              << "| Pose | Frente | Três quartos | Perfil |\r\n|---|---|---|---|\r\n"
              << "| Punho erguido | [ver](113_punho-erguido/06-mao-detalhe-frente.png) | [ver](113_punho-erguido/07-mao-detalhe-45.png) | [ver](113_punho-erguido/08-mao-detalhe-perfil.png) |\r\n"
              << "| Indicador para cima | [ver](114_indicador-para-cima/06-mao-detalhe-frente.png) | [ver](114_indicador-para-cima/07-mao-detalhe-45.png) | [ver](114_indicador-para-cima/08-mao-detalhe-perfil.png) |\r\n";
        index << "\r\nO número no nome da pasta e na tabela é o ID estável da pose no código do jogo.\r\n";
        if (!index) ok=false;
    }
    CoUninitialize();
    if (!ok) { std::fprintf(stderr,"A geração do catálogo não foi concluída.\n"); return 1; }
    std::printf("Concluído: %zu poses × 5 vistas = %zu imagens PNG em %ls\n",pose_count,pose_count*5,output.c_str());
    return 0;
}
