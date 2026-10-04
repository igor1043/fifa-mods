#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include "../../src/render/renderer/fifa_player_renderer.h"
#include "../../src/render/renderer/fifa_player_card.h"
#include "../../third_party/imgui/backends/imgui_impl_dx11.h"
#include <wincodec.h>
#include <wrl/client.h>
#include <algorithm>
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

/* QA fixture schema only. It is the old 420-byte row written by the
 * read-only roster exporter, not the current live roster ABI. */
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
static_assert(sizeof(PreviewRow) == 420, "offline fixture row ABI");

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

struct Fixture { std::vector<ClubPlayerRow> rows; std::string name; };
static bool read_fixture(const fs::path &path, Fixture &out) {
    std::ifstream in(path, std::ios::binary);
    char magic[8] = {}; uint32_t count = 0, team = 0, stride = 0; char name[128] = {};
    in.read(magic, sizeof(magic)); in.read(reinterpret_cast<char*>(&count), 4);
    in.read(reinterpret_cast<char*>(&team), 4); in.read(reinterpret_cast<char*>(&stride), 4);
    in.read(name, sizeof(name));
    if (!in || std::memcmp(magic, "C3DQA003", 8) || !count ||
        count > CLUB_PLAYER_CAPACITY || stride != sizeof(PreviewRow)) return false;
    std::vector<PreviewRow> source(count);
    in.read(reinterpret_cast<char*>(source.data()), (std::streamsize)(source.size() * sizeof(PreviewRow)));
    if (!in || in.peek() != std::char_traits<char>::eof()) return false;
    out.name = name;
    for (const auto &old : source) {
        if (old.player_id <= 0 || old.team_id != (int)team || old.overall < 1 ||
            old.overall > 99 || old.height < 130 || old.height > 230) continue;
        out.rows.push_back(upgrade(old));
    }
    std::stable_sort(out.rows.begin(), out.rows.end(), [](const auto &a, const auto &b) {
        return a.overall > b.overall;
    });
    return !out.rows.empty();
}

static ID3D11ShaderResourceView *upload(ID3D11Device *device, const Texture &t) {
    if (!device || !t.width || !t.height || t.format > 2 || t.bytes.empty()) return nullptr;
    D3D11_TEXTURE2D_DESC desc = {};
    desc.Width = t.width; desc.Height = t.height; desc.MipLevels = desc.ArraySize = 1;
    desc.Format = t.format == 0 ? DXGI_FORMAT_BC1_UNORM :
        t.format == 1 ? DXGI_FORMAT_BC2_UNORM : DXGI_FORMAT_BC3_UNORM;
    desc.SampleDesc.Count = 1; desc.Usage = D3D11_USAGE_IMMUTABLE;
    desc.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    D3D11_SUBRESOURCE_DATA data = {};
    data.pSysMem = t.bytes.data(); data.SysMemPitch = ((t.width + 3) / 4) * (t.format ? 16 : 8);
    data.SysMemSlicePitch = (UINT)t.bytes.size();
    ComPtr<ID3D11Texture2D> texture; ComPtr<ID3D11ShaderResourceView> view;
    if (FAILED(device->CreateTexture2D(&desc, &data, texture.GetAddressOf())) ||
        FAILED(device->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf()))) return nullptr;
    return view.Detach();
}

struct CardSample {
    ClubPlayerRow row{};
    std::string team_name;
    std::unique_ptr<Renderer> renderer;
    ComPtr<ID3D11ShaderResourceView> crest;
};

static bool save_png(ID3D11Device *device, ID3D11DeviceContext *context,
    ID3D11Texture2D *source, const fs::path &path) {
    D3D11_TEXTURE2D_DESC desc = {}; source->GetDesc(&desc);
    desc.Usage = D3D11_USAGE_STAGING; desc.BindFlags = 0;
    desc.CPUAccessFlags = D3D11_CPU_ACCESS_READ; desc.MiscFlags = 0;
    ComPtr<ID3D11Texture2D> staging;
    if (FAILED(device->CreateTexture2D(&desc, nullptr, staging.GetAddressOf()))) return false;
    context->CopyResource(staging.Get(), source);
    D3D11_MAPPED_SUBRESOURCE mapped = {};
    if (FAILED(context->Map(staging.Get(), 0, D3D11_MAP_READ, 0, &mapped))) return false;
    const UINT stride = desc.Width * 4;
    std::vector<uint8_t> bgra((size_t)stride * desc.Height);
    /* The render target is R8G8B8A8, whereas WIC's chosen encoder format is
     * BGRA. Convert only the saved preview; the native 3D texture/render path
     * itself must remain byte-for-byte the same as the other screens. */
    for (UINT y = 0; y < desc.Height; ++y) {
        const auto *rgba = static_cast<const uint8_t*>(mapped.pData) + (size_t)y * mapped.RowPitch;
        auto *out = bgra.data() + (size_t)y * stride;
        std::memcpy(out, rgba, stride);
        for (UINT x = 0; x < desc.Width; ++x) std::swap(out[x * 4], out[x * 4 + 2]);
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
        hr = frame->WritePixels(desc.Height, stride, (UINT)bgra.size(), bgra.data());
    else if (SUCCEEDED(hr)) hr = E_FAIL;
    if (SUCCEEDED(hr)) hr = frame->Commit();
    if (SUCCEEDED(hr)) hr = encoder->Commit();
    return SUCCEEDED(hr);
}

struct UiTarget { ComPtr<ID3D11Texture2D> texture; ComPtr<ID3D11RenderTargetView> rtv; };
static bool make_target(ID3D11Device *device, UINT width, UINT height, UiTarget &out) {
    D3D11_TEXTURE2D_DESC td = {};
    td.Width = width; td.Height = height; td.MipLevels = td.ArraySize = 1;
    td.Format = DXGI_FORMAT_R8G8B8A8_UNORM; td.SampleDesc.Count = 1;
    td.BindFlags = D3D11_BIND_RENDER_TARGET | D3D11_BIND_SHADER_RESOURCE;
    return SUCCEEDED(device->CreateTexture2D(&td, nullptr, out.texture.GetAddressOf())) &&
        SUCCEEDED(device->CreateRenderTargetView(out.texture.Get(), nullptr, out.rtv.GetAddressOf()));
}

static bool begin_canvas(ID3D11DeviceContext *context, ID3D11RenderTargetView *target,
    const ImVec2 &canvas) {
    const float clear[4] = {.03f, .055f, .09f, 1};
    context->OMSetRenderTargets(1, &target, nullptr);
    context->ClearRenderTargetView(target, clear);
    (void)canvas;
    return true;
}

static bool draw_sheet(ID3D11Device *device, ID3D11DeviceContext *context,
    const UiTarget &target, ImFont *font, ImFont *bold, ImFont *card_bold, ImFont *ref_bold,
    const std::vector<CardSample> &samples, const fs::path &path) {
    ImGui_ImplDX11_NewFrame(); ImGui::NewFrame();
    const ImVec2 canvas = ImGui::GetIO().DisplaySize;
    ImDrawList *draw = ImGui::GetBackgroundDrawList();
    draw->AddRectFilled({0, 0}, canvas, IM_COL32(8, 15, 25, 255));
    draw->AddText(bold, 22, {34, 18}, IM_COL32(244, 248, 253, 255),
        "FIFA 16  /  PLAYER CARD");
    draw->AddText(font, 13, {35, 47}, IM_COL32(157, 179, 198, 255),
        "Modelo facial 3D nativo + paleta e escudo do clube");
    const float card_w = 244.f, card_h = 314.f, gap = 19.f;
    const float total = samples.size() * card_w + (samples.size() - 1) * gap;
    const float start_x = (canvas.x - total) * .5f;
    const float y = 73.f;
    for (size_t i = 0; i < samples.size(); ++i) {
        const CardSample &sample = samples[i];
        fifa_player_card::Data data;
        data.player_id = sample.row.player_id; data.team_id = sample.row.team_id;
        data.overall = sample.row.overall; data.name = sample.row.name;
        data.primary_color = sample.row.club_colors_valid ? sample.row.club_colors[0] : 0x07558d;
        static const char *positions[] = {"GK", "SW", "RWB", "RB", "RCB", "CB", "LCB", "LB",
            "LWB", "RDM", "CDM", "LDM", "RM", "RCM", "CM", "LCM", "LM", "RAM", "CAM",
            "LAM", "RS", "SS", "LS", "RW", "RF", "ST", "LF", "LW"};
        data.position = sample.row.position >= 0 && sample.row.position < 28
            ? positions[sample.row.position] : "-";
        const float x = start_x + i * (card_w + gap);
        ImTextureID face = (ImTextureID)(intptr_t)sample.renderer->image();
        ImTextureID crest = (ImTextureID)(intptr_t)sample.crest.Get();
        fifa_player_card::draw(draw, {x, y}, {card_w, card_h}, data, face, crest, card_bold);
    }
    /* Same component at the source-reference card size, so the typography and
     * spacing can be checked at 1:1 ratio instead of judged from memory. */
    draw->AddText(font, 13, {35, 407}, IM_COL32(157, 179, 198, 255),
        "MESMA PROPORCAO DA REFERENCIA  |  96 x 123 px  |  escala uniforme 1:2,54");
    constexpr float ref_w = 96.f, ref_h = 123.f, ref_gap = 19.f;
    const float ref_total = samples.size() * ref_w + (samples.size() - 1) * ref_gap;
    const float ref_start = (canvas.x - ref_total) * .5f;
    for (size_t i = 0; i < samples.size(); ++i) {
        const CardSample &sample = samples[i];
        fifa_player_card::Data data;
        data.player_id = sample.row.player_id; data.team_id = sample.row.team_id;
        data.overall = sample.row.overall; data.name = sample.row.name;
        data.primary_color = sample.row.club_colors_valid ? sample.row.club_colors[0] : 0x07558d;
        static const char *positions[] = {"GK", "SW", "RWB", "RB", "RCB", "CB", "LCB", "LB",
            "LWB", "RDM", "CDM", "LDM", "RM", "RCM", "CM", "LCM", "LM", "RAM", "CAM",
            "LAM", "RS", "SS", "LS", "RW", "RF", "ST", "LF", "LW"};
        data.position = sample.row.position >= 0 && sample.row.position < 28
            ? positions[sample.row.position] : "-";
        const float x = ref_start + i * (ref_w + ref_gap);
        fifa_player_card::draw(draw, {x, 430.f}, {ref_w, ref_h}, data,
            (ImTextureID)(intptr_t)sample.renderer->image(),
            (ImTextureID)(intptr_t)sample.crest.Get(), ref_bold);
    }
    ImGui::Render();
    begin_canvas(context, target.rtv.Get(), canvas);
    ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData());
    return save_png(device, context, target.texture.Get(), path);
}

static bool draw_single(ID3D11Device *device, ID3D11DeviceContext *context,
    const UiTarget &target, ImFont *bold, CardSample &sample, const fs::path &path) {
    ImGui_ImplDX11_NewFrame(); ImGui::NewFrame();
    auto *draw = ImGui::GetBackgroundDrawList();
    draw->AddRectFilled({0,0}, ImGui::GetIO().DisplaySize, IM_COL32(8,15,25,255));
    fifa_player_card::Data data; data.player_id=sample.row.player_id;
    data.team_id=sample.row.team_id; data.overall=sample.row.overall;
    data.name=sample.row.name; data.primary_color=sample.row.club_colors_valid?sample.row.club_colors[0]:0x07558d;
    static const char *pos[] = {"GK","SW","RWB","RB","RCB","CB","LCB","LB","LWB","RDM","CDM","LDM","RM","RCM","CM","LCM","LM","RAM","CAM","LAM","RS","SS","LS","RW","RF","ST","LF","LW"};
    data.position=sample.row.position>=0&&sample.row.position<28?pos[sample.row.position]:"-";
    fifa_player_card::draw(draw,{95,43},{330,424},data,
        (ImTextureID)(intptr_t)sample.renderer->image(),(ImTextureID)(intptr_t)sample.crest.Get(),bold);
    ImGui::Render();
    begin_canvas(context, target.rtv.Get(), ImGui::GetIO().DisplaySize);
    ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData());
    return save_png(device, context, target.texture.Get(), path);
}

int wmain(int argc, wchar_t **argv) {
    if (argc != 5) {
        std::fwprintf(stderr, L"Uso: generate_player_card_preview.exe <raiz-fifa> <fixture-clube-1.bin> <fixture-clube-2.bin> <pasta-saida-nova>\n");
        return 2;
    }
    fs::path root(argv[1]), fixture_a(argv[2]), fixture_b(argv[3]), output(argv[4]);
    if (fs::exists(output)) { std::fwprintf(stderr, L"A pasta de saída já existe; não sobrescrevi: %ls\n", output.c_str()); return 2; }
    Fixture fixtures[2];
    if (!read_fixture(fixture_a, fixtures[0]) || !read_fixture(fixture_b, fixtures[1])) {
        std::fprintf(stderr, "Fixtures offline inválidos ou sem jogadores.\n"); return 1;
    }
    HRESULT co = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    if (FAILED(co)) return 1;
    ID3D11Device *device = nullptr; ID3D11DeviceContext *context = nullptr;
    HRESULT hr = D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_WARP, nullptr, 0, nullptr, 0,
        D3D11_SDK_VERSION, &device, nullptr, &context);
    if (FAILED(hr)) { CoUninitialize(); return 1; }
    bool ok = false;
    {
        IMGUI_CHECKVERSION(); ImGui::CreateContext();
        ImGuiIO &io = ImGui::GetIO(); io.DisplaySize = {1110, 430};
        io.DeltaTime = 1.f / 60.f; io.IniFilename = nullptr;
        ImFont *font = io.Fonts->AddFontFromFileTTF("C:/Windows/Fonts/segoeui.ttf", 16);
        ImFont *bold = io.Fonts->AddFontFromFileTTF("C:/Windows/Fonts/segoeuib.ttf", 18);
        /* Bake the preview text near its actual sizes; otherwise the big
         * sample cards enlarge an 18px glyph atlas and look artificially soft. */
        ImFont *card_bold = io.Fonts->AddFontFromFileTTF("C:/Windows/Fonts/segoeuib.ttf", 52);
        ImFont *single_bold = io.Fonts->AddFontFromFileTTF("C:/Windows/Fonts/segoeuib.ttf", 72);
        if (!font) font = io.Fonts->AddFontDefault();
        if (!bold) bold = font;
        if (!card_bold) card_bold = bold;
        if (!single_bold) single_bold = bold;
        ImGui::StyleColorsDark();
        if (!font || !bold || !ImGui_ImplDX11_Init(device, context)) {
            ImGui::DestroyContext(); context->Release(); device->Release(); CoUninitialize(); return 1;
        }
        UiTarget sheet_target, single_target;
        if (make_target(device, 1110, 570, sheet_target) && make_target(device, 520, 550, single_target)) {
            Assets assets(root.string());
            std::vector<CardSample> samples;
            for (size_t f = 0; f < 2 && samples.size() < 4; ++f) {
                unsigned in_fixture = 0;
                for (const ClubPlayerRow &row : fixtures[f].rows) {
                    if (in_fixture >= 2 || samples.size() >= 4) break;
                    if (std::any_of(samples.begin(), samples.end(), [&](const CardSample &s) {
                        return s.row.player_id == row.player_id;
                    })) continue;
                    auto model = std::make_shared<Model>(assets.load(row));
                    if (model->parts.empty()) continue;
                    auto renderer = std::make_unique<Renderer>(); renderer->device(device);
                    const UINT face_w = 360, face_h = 380;
                    CameraFocus focus{.91f, 0.f, .18f};
                    if (!renderer->model(model) || !renderer->render(face_w, face_h, .04f, 1.25f,
                        true, 0, 0, true, .62f, &focus, true)) continue;
                    CardSample sample; sample.row = row; sample.team_name = fixtures[f].name;
                    sample.renderer = std::move(renderer);
                    Texture badge;
                    if (assets.crest(row.team_id, badge)) sample.crest.Attach(upload(device, badge));
                    std::printf("Card %zu: %s | id=%d team=%d overall=%d pos=%d 3D-parts=%zu specific-head=%d\n",
                        samples.size() + 1, row.name, row.player_id, row.team_id, row.overall,
                        row.position, model->parts.size(), model->specific_head);
                    samples.push_back(std::move(sample)); ++in_fixture;
                }
            }
            if (samples.size() == 4) {
                fs::create_directories(output);
                io.DisplaySize = {1110, 570};
                ok = draw_sheet(device, context, sheet_target, font, bold, card_bold, bold, samples,
                    output / L"player-cards-contact-sheet.png");
                for (size_t i = 0; i < samples.size() && ok; ++i) {
                    io.DisplaySize = {520, 550};
                    std::wstring file = L"player-card-" + std::to_wstring(i + 1) + L".png";
                    ok = draw_single(device, context, single_target, single_bold, samples[i], output / file);
                }
            }
        }
        ImGui_ImplDX11_Shutdown(); ImGui::DestroyContext();
    }
    context->Release(); device->Release(); CoUninitialize();
    if (!ok) { std::fprintf(stderr, "Prévia incompleta; verifique se os modelos têm os assets 3D necessários.\n"); return 1; }
    std::wprintf(L"Concluído: componente reutilizável renderizado com 4 jogadores 3D em %ls\n", output.c_str());
    return 0;
}
