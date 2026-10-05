#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include "../../src/render/renderer/fifa_player_renderer.h"
#include <wincodec.h>
#include "../../src/render/scenes/new_experience_rooms.h"
#include <wrl/client.h>
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <memory>
#include <set>
#include <vector>

using namespace fifa_player;
using Microsoft::WRL::ComPtr;
namespace fs = std::filesystem;

/* Read-only 420-byte snapshot fixture shared with the existing player-card
 * preview. Each row contains the save's player appearance and exact pitch slot. */
struct PreviewRow {
    int player_id, team_id, number, position, age, overall;
    int head_type, head_class, hair_type, hair_color, skin_tone, skin_type;
    int facial_hair_type, facial_hair_color, shoe_type, shoe_design;
    int gender, height, weight, body_type;
    int eye_color, eyebrow, sideburns, sleeve_length, jersey_fit, jersey_style;
    int sock_length, short_style, glove_type;
    unsigned club_colors[3]; int club_colors_valid;
    int attributes[CLUB_PLAYER_ATTRIBUTE_COUNT];
    char name[128];
    int captain, squad_position, secondary_positions[3], secondary_positions_valid;
};
static_assert(sizeof(PreviewRow) == 420, "offline roster fixture ABI");

static ClubPlayerRow upgrade(const PreviewRow &old) {
    ClubPlayerRow row{};
    std::memcpy(&row, &old, offsetof(ClubPlayerRow, head_type));
    row.birthdate_raw = row.join_team_date_raw = row.career_date = -1;
    row.retiring = row.weekly_wage = -1;
    row.career_data_valid = 0;
    std::memcpy(reinterpret_cast<unsigned char*>(&row) + offsetof(ClubPlayerRow, head_type),
        reinterpret_cast<const unsigned char*>(&old) + offsetof(PreviewRow, head_type),
        sizeof(old) - offsetof(PreviewRow, head_type));
    return row;
}

static bool read_fixture(const fs::path &path, std::vector<ClubPlayerRow> &rows,
    int &team_id, unsigned colors[3], bool roster=false) {
    std::ifstream in(path, std::ios::binary);
    char magic[8] = {}, name[128] = {};
    uint32_t count = 0, team = 0, stride = 0;
    in.read(magic, 8); in.read(reinterpret_cast<char*>(&count), 4);
    in.read(reinterpret_cast<char*>(&team), 4); in.read(reinterpret_cast<char*>(&stride), 4);
    in.read(name, sizeof(name));
    if (!in || std::memcmp(magic, "C3DQA003", 8) || (roster?(count<1||count>100):count!=11) || !team ||
        stride != sizeof(PreviewRow)) return false;
    std::vector<PreviewRow> old(count);
    in.read(reinterpret_cast<char*>(old.data()), static_cast<std::streamsize>(old.size()*sizeof(old[0])));
    if (!in || in.peek() != std::char_traits<char>::eof()) return false;
    std::set<int> ids;
    for (const auto &item : old) {
        if (item.team_id != static_cast<int>(team) || item.player_id <= 0 ||
            item.height < 130 || item.height > 230 || item.squad_position < 0 || item.squad_position > (roster?29:27) ||
            !ids.insert(item.player_id).second) return false;
        rows.push_back(upgrade(item));
    }
    if (!old.front().club_colors_valid) return false;
    std::copy(std::begin(old.front().club_colors), std::end(old.front().club_colors), colors);
    team_id = static_cast<int>(team);
    return true;
}

static bool save_png(ID3D11Device *device, ID3D11DeviceContext *context,
    ID3D11ShaderResourceView *source, const fs::path &path) {
    if (!device || !context || !source) return false;
    ComPtr<ID3D11Resource> resource; source->GetResource(resource.GetAddressOf());
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
    const UINT stride = desc.Width * 4;
    std::vector<uint8_t> bgra(static_cast<size_t>(stride) * desc.Height);
    for (UINT y = 0; y < desc.Height; ++y) {
        const auto *rgba = static_cast<const uint8_t*>(mapped.pData) + static_cast<size_t>(y) * mapped.RowPitch;
        auto *out = bgra.data() + static_cast<size_t>(y) * stride;
        std::memcpy(out, rgba, stride);
        for (UINT x = 0; x < desc.Width; ++x) std::swap(out[x*4], out[x*4+2]);
    }
    context->Unmap(staging.Get(), 0);
    ComPtr<IWICImagingFactory> wic; ComPtr<IWICStream> stream;
    ComPtr<IWICBitmapEncoder> encoder; ComPtr<IWICBitmapFrameEncode> frame;
    ComPtr<IPropertyBag2> properties;
    HRESULT hr = CoCreateInstance(CLSID_WICImagingFactory, nullptr, CLSCTX_INPROC_SERVER,
        IID_PPV_ARGS(wic.GetAddressOf()));
    if (SUCCEEDED(hr)) hr = wic->CreateStream(stream.GetAddressOf());
    if (SUCCEEDED(hr)) hr = stream->InitializeFromFilename(path.c_str(), GENERIC_WRITE);
    if (SUCCEEDED(hr)) hr = wic->CreateEncoder(GUID_ContainerFormatPng, nullptr, encoder.GetAddressOf());
    if (SUCCEEDED(hr)) hr = encoder->Initialize(stream.Get(), WICBitmapEncoderNoCache);
    if (SUCCEEDED(hr)) hr = encoder->CreateNewFrame(frame.GetAddressOf(), properties.GetAddressOf());
    if (SUCCEEDED(hr)) hr = frame->Initialize(properties.Get());
    if (SUCCEEDED(hr)) hr = frame->SetSize(desc.Width, desc.Height);
    WICPixelFormatGUID format = GUID_WICPixelFormat32bppBGRA;
    if (SUCCEEDED(hr)) hr = frame->SetPixelFormat(&format);
    if (SUCCEEDED(hr) && IsEqualGUID(format, GUID_WICPixelFormat32bppBGRA))
        hr = frame->WritePixels(desc.Height, stride, static_cast<UINT>(bgra.size()), bgra.data());
    else if (SUCCEEDED(hr)) hr = E_FAIL;
    if (SUCCEEDED(hr)) hr = frame->Commit();
    if (SUCCEEDED(hr)) hr = encoder->Commit();
    return SUCCEEDED(hr);
}

#include "web_model_export.h"
#include "web_model_worker.h"
int wmain(int argc, wchar_t **argv) {
    if(argc==3&&wcscmp(argv[1],L"--web-worker")==0)return web_model_worker(fs::path(argv[2]));
    if(argc==7&&wcscmp(argv[1],L"--player")==0){
        std::vector<ClubPlayerRow>rows;int club=0;unsigned colors[3]={};if(!read_fixture(fs::path(argv[3]),rows,club,colors,true)||rows.size()!=1)return 2;
        if(FAILED(CoInitializeEx(nullptr,COINIT_MULTITHREADED)))return 1;
        ID3D11Device*device=nullptr;ID3D11DeviceContext*context=nullptr;HRESULT hr=D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_HARDWARE,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&device,nullptr,&context);if(FAILED(hr))hr=D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&device,nullptr,&context);if(FAILED(hr)){CoUninitialize();return 1;}
        bool ok=false;{Assets assets(fs::path(argv[2]).string());auto model=std::make_shared<Model>(assets.load(rows.front()));int pose=_wtoi(argv[5]);if(pose>=101&&pose<=114)apply_presentation_pose(*model,false,nullptr,pose);if(_wtoi(argv[6])==2){bool exported=export_web_model(*model,fs::path(argv[4]));context->Release();device->Release();CoUninitialize();return exported?0:1;}Renderer renderer;renderer.device(device);ok=renderer.model(model)&&renderer.render(800,1000,0.f,1.f,_wtoi(argv[6])!=0,0,0,true)&&save_png(device,context,renderer.image(),fs::path(argv[4]));renderer.clear();}context->Release();device->Release();CoUninitialize();return ok?0:1;
    }

    if (argc != 6 && argc != 7 && argc != 8) {
        std::fwprintf(stderr, L"Uso: generate_club_details_preview.exe <raiz-fifa> <fixture.bin> <cena-11.png> <retrato-tecnico.png> <tecnico-3d.png>\n");
        return 2;
    }
    const fs::path game_root(argv[1]), fixture(argv[2]);
    const fs::path lineup_png(argv[3]), coach_portrait_png(argv[4]), coach_model_png(argv[5]);
    std::vector<ClubPlayerRow> rows; int team_id = 0; unsigned colors[3] = {};
    if (!read_fixture(fixture, rows, team_id, colors)) {
        std::fprintf(stderr, "Fixture inválido: são necessários 11 titulares únicos do mesmo clube, nas posições salvas.\n");
        return 1;
    }
    HRESULT co = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    if (FAILED(co)) return 1;
    ID3D11Device *device = nullptr; ID3D11DeviceContext *context = nullptr;
    HRESULT hr = D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr, 0, nullptr, 0,
        D3D11_SDK_VERSION, &device, nullptr, &context);
    if (FAILED(hr)) hr = D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_WARP, nullptr, 0, nullptr, 0, D3D11_SDK_VERSION, &device, nullptr, &context);
    if (FAILED(hr)) { CoUninitialize(); return 1; }
    bool ok = false;
    {
        Assets assets(game_root.string());
        std::vector<std::shared_ptr<const Model>> models; models.reserve(rows.size());
        for (const auto &row : rows) {
            auto model = std::make_shared<Model>(assets.load(row));
            if (model->player_id != row.player_id || model->team_id != team_id || model->parts.empty()) {
                std::fprintf(stderr, "Modelo nativo ausente para o jogador %d; a cena completa não foi substituída por uma parcial.\n", row.player_id);
                context->Release(); device->Release(); CoUninitialize(); return 1;
            }
            models.push_back(std::move(model));
        }
        Model scene = assemble_starting_eleven(models, 1);
        if (scene.player_count != 11 || scene.formation.size() != 11) {
            std::fprintf(stderr, "O montador nativo não produziu os 11 titulares do save.\n");
        } else {
            Renderer lineup; lineup.device(device);
            scene.room = RoomOfficeLineup;
            auto lineup_model = std::make_shared<Model>(std::move(scene));
            ok = lineup.model(lineup_model) && lineup.render(1500, 700, 0.f, 1.f, false) &&
                save_png(device, context, lineup.image(), lineup_png);
            lineup.clear();
            if (!ok) std::fprintf(stderr, "Falha ao renderizar a cena 3D dos titulares.\n");
        }

        ClubPlayerRow club{}; club.team_id = team_id; club.club_colors_valid = 1;
        std::copy(std::begin(colors), std::end(colors), std::begin(club.club_colors));
        CoachAsset assigned = assets.coach(club);
        if (ok && argc >= 7) {
            const fs::path rooms_dir(argv[6]);
            fs::create_directories(rooms_dir);
            for (const auto kind : {RoomPress, RoomDressing, RoomGym, RoomTraining}) {
                std::vector<ClubPlayerRow>room_rows=rows;auto room_models=models;
                if(kind==RoomDressing&&argc==8){int roster_club=0;unsigned roster_colors[3]={};std::vector<ClubPlayerRow>all;
                    if(read_fixture(fs::path(argv[7]),all,roster_club,roster_colors,true)&&roster_club==team_id){room_rows=all;room_models.clear();for(auto&r:room_rows)room_models.push_back(std::make_shared<Model>(assets.load(r)));}}
                auto room = std::make_shared<Model>(build_new_experience_room(assets, game_root.string(), room_models, room_rows, assigned, kind));
                Renderer renderer; renderer.device(device);
                if (!renderer.model(room) || !renderer.render(1280, 720, 0.f, 1.f) ||
                    !save_png(device, context, renderer.image(), rooms_dir / (kind == RoomPress ? L"press.png" : kind == RoomDressing ? L"locker.png" : kind == RoomGym ? L"gym.png" : L"training.png"))) {
                    std::fprintf(stderr, "Falha ao renderizar ambiente offline.\n"); ok = false;
                }
                renderer.clear();
            }
        }
        if (argc==8) {
            std::vector<ClubPlayerRow>roster;int roster_club=0;unsigned roster_colors[3]={};
            if(read_fixture(fs::path(argv[7]),roster,roster_club,roster_colors,true)&&roster_club==team_id){
                auto folder=fs::path(argv[6])/L"players";fs::create_directories(folder);
                for(const auto&r:roster){auto actor=std::make_shared<Model>(assets.load(r));if(actor->parts.empty())continue;
                    auto pose=presentation_pose_at(0,PoseIndividual);if(pose)apply_presentation_pose(*actor,false,nullptr,pose->id);
                    Renderer renderer;renderer.device(device);if(renderer.model(actor)&&renderer.render(700,900,0.f,1.f,false,0,0,true))save_png(device,context,renderer.image(),folder/(std::to_wstring(r.player_id)+L".png"));renderer.clear();
                }
            }
        }
        if (ok && (!assigned.model || assigned.model->parts.empty())) {
            std::fprintf(stderr, "O modelo SLC do técnico deste clube não está disponível.\n"); ok = false;
        }
        if (ok) {
            auto posed = std::make_shared<Model>(*assigned.model);
            if (posed->skeleton) apply_coach_pose(*posed, 201);
            Renderer portrait; portrait.device(device);
            const bool portrait_ok = portrait.model(posed) && portrait.render(540, 640, 0.f, 1.f, true, 0, 0, true, .32f) &&
                save_png(device, context, portrait.image(), coach_portrait_png);
            portrait.clear();
            Renderer full_body; full_body.device(device);
            const bool model_ok = full_body.model(posed) && full_body.render(560, 720, 0.f, 1.f, false) &&
                save_png(device, context, full_body.image(), coach_model_png);
            full_body.clear();
            ok = portrait_ok && model_ok;
            if (!ok) std::fprintf(stderr, "Falha ao renderizar retrato ou modelo 3D do técnico.\n");
        }
    }
    context->Release(); device->Release(); CoUninitialize();
    return ok ? 0 : 1;
}


