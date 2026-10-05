#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include "webview2_overlay_host.h"
#include "mod_overlay_screens.h"
#include "../../screens/club/club_player_screen.h"
#include "../../screens/operations/career_operations.h"
#include "../../../third_party/webview2/1.0.4129.50/include/WebView2.h"
#include <wrl.h>
#include <wrl/client.h>
#include <wincodec.h>
#include <wincrypt.h>
#include <algorithm>
#include <memory>
#include <mutex>
#include <new>
#include <string>
#include <vector>

using Microsoft::WRL::Callback;
using Microsoft::WRL::ComPtr;

namespace fifa_webview {
namespace {
const UINT kHostMessage = WM_APP + 0x4b0;
const UINT kPublishMessage = WM_APP + 0x4b1;
const UINT kContextMessage = WM_APP + 0x4b2;
const wchar_t kHostName[] = L"fifa-friends.local";
const wchar_t kHomeUrl[] = L"https://fifa-friends.local/home.html";
const wchar_t kCentralUrl[] = L"https://fifa-friends.local/central.html";
const wchar_t kClubsUrl[] = L"https://fifa-friends.local/index.html";
volatile LONG g_state = 0;
volatile LONG g_requested_visible = 0;
std::wstring g_player_return_tab=L"players";int g_profile_club=0;
volatile LONG g_page = 0; /* 0: Experiência Nova home, 1: clube globe */
volatile LONG g_visible = 0;
HWND g_parent = nullptr;
HMODULE g_loader = nullptr;
ICoreWebView2Environment *g_environment = nullptr;
ICoreWebView2Controller *g_controller = nullptr;
ICoreWebView2 *g_webview = nullptr;
EventRegistrationToken g_message_token = {};
EventRegistrationToken g_navigation_token = {};
void (*g_log)(const char *) = nullptr;
std::string g_scene_png_base64;
volatile LONG g_scene_club=0;
std::string g_career_context_json = "{\"type\":\"career-context\",\"clubId\":0,\"clubName\":\"Carregando carreira...\",\"playerCount\":0,\"validXI\":false}";
std::string g_web_root_a;
std::wstring g_web_root_w;
std::wstring g_user_data_w;
bool g_com_initialized = false;
std::mutex g_payload_lock;

std::wstring to_wide(const std::string &text, UINT page = CP_UTF8) {
    if (text.empty()) return {};
    int count = MultiByteToWideChar(page, 0, text.c_str(), -1, nullptr, 0);
    if (count <= 1) return {};
    std::wstring out((size_t)count, L'\0');
    MultiByteToWideChar(page, 0, text.c_str(), -1, out.data(), count);
    out.resize((size_t)count - 1);
    return out;
}

std::string json_string(const char *value) {
    std::string out = "\"";
    if (value) for (const unsigned char *p = (const unsigned char *)value; *p; ++p) {
        switch (*p) {
        case '"': out += "\\\""; break;
        case '\\': out += "\\\\"; break;
        case '\n': out += "\\n"; break;
        case '\r': out += "\\r"; break;
        case '\t': out += "\\t"; break;
        default: if (*p < 32) out += ' '; else out += (char)*p; break;
        }
    }
    out += '"';
    return out;
}

void log_message(const char *message) {
    if (g_log && message) g_log(message);
}

std::string json_base64(const std::string &data) {
    return "{\"type\":\"scene-image\",\"clubId\":"+std::to_string(InterlockedCompareExchange(&g_scene_club,0,0))+",\"mime\":\"image/png\",\"data\":\"" + data + "\"}";
}

bool post_json(const std::string &json) {
    if (!g_webview || !g_parent || !IsWindow(g_parent)) return false;
    std::wstring wide = to_wide(json);
    if (wide.empty()) return false;
    return SUCCEEDED(g_webview->PostWebMessageAsJson(wide.c_str()));
}

void page_loaded() {
    if (InterlockedCompareExchange(&g_page, 0, 0) != 1) {
        std::string context, scene;
        {
            std::lock_guard<std::mutex> guard(g_payload_lock);
            context = g_career_context_json;
            scene = g_scene_png_base64;
        }
        post_json(context);
        if (!scene.empty()) post_json(json_base64(scene));
    }
}

void apply_visible() {
    if (!g_controller) return;
    const bool show_now = InterlockedCompareExchange(&g_requested_visible, 0, 0) != 0;
    g_controller->put_IsVisible(show_now ? TRUE : FALSE);
    InterlockedExchange(&g_visible, show_now ? 1 : 0);
    if (show_now) {
        RECT bounds = {};
        GetClientRect(g_parent, &bounds);
        g_controller->put_Bounds(bounds);
        SetFocus(g_parent);
        g_controller->MoveFocus(COREWEBVIEW2_MOVE_FOCUS_REASON_PROGRAMMATIC);
    } else if (g_parent && IsWindow(g_parent)) {
        SetFocus(g_parent);
    }
}

void navigate_home() {
    if(page_is_scene()){std::lock_guard<std::mutex> guard(g_payload_lock);g_scene_png_base64.clear();}
    InterlockedExchange(&g_page, 0);
    if (g_webview) g_webview->Navigate(kHomeUrl);
}

void navigate_clubs() {
    InterlockedExchange(&g_page, 1);
    if (g_webview) g_webview->Navigate(kClubsUrl);
}

void navigate_central(){InterlockedExchange(&g_page,2);if(g_webview)g_webview->Navigate(kCentralUrl);}
void show_native_scene(int room){
    {std::lock_guard<std::mutex> guard(g_payload_lock);g_scene_png_base64.clear();}
    club_player_screen_request_web_room(room);InterlockedExchange(&g_page,3);
    const wchar_t*names[]={L"press",L"locker",L"gym",L"training"};
    if(g_webview){std::wstring url=L"https://fifa-friends.local/scene.html?room=";url+=names[room-1];g_webview->Navigate(url.c_str());}
}
void handle_web_message(const std::wstring&message){
    if(message==L"start"){navigate_central();return;}
    if(message==L"clubs"){navigate_clubs();return;}
    if(message.rfind(L"player-pose:",0)==0){club_player_screen_request_web_pose(_wtoi(message.c_str()+12));return;}
    if(message.rfind(L"coach:",0)==0){int club=_wtoi(message.c_str()+6);if(club<=0)return;g_profile_club=club;auto separator=message.find(L':',6);g_player_return_tab=separator==message.npos?L"home":message.substr(separator+1);if(g_player_return_tab!=L"competitions"&&g_player_return_tab!=L"home"&&g_player_return_tab!=L"leagues"&&g_player_return_tab!=L"teams")g_player_return_tab=L"home";club_player_screen_request_web_player(2000000);{std::lock_guard<std::mutex>guard(g_payload_lock);g_scene_png_base64.clear();}InterlockedExchange(&g_page,4);if(g_webview){auto url=std::wstring(L"https://fifa-friends.local/coach.html?club=")+std::to_wstring(club);g_webview->Navigate(url.c_str());}return;}
    if(message.rfind(L"player:",0)==0){int id=_wtoi(message.c_str()+7);if(id<=0||id>2000000)return;auto separator=message.find(L':',7);auto club_separator=separator==message.npos?message.npos:message.find(L':',separator+1);int club=club_separator==message.npos?0:_wtoi(message.c_str()+club_separator+1);g_profile_club=club;g_player_return_tab=separator==message.npos?L"players":message.substr(separator+1,club_separator==message.npos?message.npos:club_separator-separator-1);if(g_player_return_tab!=L"competitions"&&g_player_return_tab!=L"home"&&g_player_return_tab!=L"leagues"&&g_player_return_tab!=L"teams"&&g_player_return_tab!=L"players")g_player_return_tab=L"players";{std::lock_guard<std::mutex>guard(g_payload_lock);g_scene_png_base64.clear();}club_player_screen_request_web_player(id);InterlockedExchange(&g_page,4);if(g_webview){auto url=std::wstring(L"https://fifa-friends.local/player.html?id=")+std::to_wstring(id)+L"&club="+std::to_wstring(club);g_webview->Navigate(url.c_str());}return;}
    if(message==L"back"){LONG page=InterlockedCompareExchange(&g_page,0,0);if(page==4){InterlockedExchange(&g_page,2);if(g_webview){auto url=std::wstring(kCentralUrl)+L"?tab="+g_player_return_tab+((g_player_return_tab==L"leagues"||g_player_return_tab==L"teams")?L"&club="+std::to_wstring(g_profile_club):L"");g_webview->Navigate(url.c_str());}}else if(page==1||page==3)navigate_central();else if(page==2)navigate_home();else mod_screen_request_back();return;}
    if(message==L"scene:press"){show_native_scene(1);return;}
    if(message==L"scene:locker"){show_native_scene(2);return;}
    if(message==L"scene:gym"){show_native_scene(3);return;}
    if(message==L"scene:training"){show_native_scene(4);return;}
    if(message==L"screen:transfers"){mod_screen_push_action(FIFA_TRANSFER_MARKET_ACTION);return;}
    if(message==L"preview-received")return;
}

void fail(const char *message) {
    InterlockedExchange(&g_state, -1);
    InterlockedExchange(&g_visible, 0);
    if (g_controller) g_controller->put_IsVisible(FALSE);
    log_message(message);
}

HRESULT create_controller(HRESULT result, ICoreWebView2Environment *environment) {
    if (FAILED(result) || !environment || !g_parent) {
        fail("WebView2: runtime/environment initialization failed");
        return result;
    }
    if (g_environment) g_environment->Release();
    g_environment = environment;
    g_environment->AddRef();
    HRESULT hr = g_environment->CreateCoreWebView2Controller(g_parent,
        Callback<ICoreWebView2CreateCoreWebView2ControllerCompletedHandler>(
            [](HRESULT controller_result, ICoreWebView2Controller *controller) -> HRESULT {
                if (FAILED(controller_result) || !controller) {
                    fail("WebView2: child controller creation failed");
                    return controller_result;
                }
                if (g_controller) g_controller->Release();
                g_controller = controller;
                g_controller->AddRef();
                RECT bounds = {};
                GetClientRect(g_parent, &bounds);
                g_controller->put_Bounds(bounds);
                g_controller->get_CoreWebView2(&g_webview);

                ComPtr<ICoreWebView2Settings> settings;
                if (SUCCEEDED(g_webview->get_Settings(&settings))) {
                    settings->put_AreDefaultContextMenusEnabled(FALSE);
                    settings->put_IsZoomControlEnabled(FALSE);
                    settings->put_IsStatusBarEnabled(FALSE);
                    settings->put_AreDevToolsEnabled(FALSE);
                }
                ComPtr<ICoreWebView2_3> webview3;
                if (SUCCEEDED(g_webview->QueryInterface(IID_PPV_ARGS(&webview3)))) {
                    HRESULT map_hr = webview3->SetVirtualHostNameToFolderMapping(
                        kHostName, g_web_root_w.c_str(),
                        COREWEBVIEW2_HOST_RESOURCE_ACCESS_KIND_ALLOW);
                    if (FAILED(map_hr)) {
                        fail("WebView2: local experience folder mapping failed");
                        return map_hr;
                    }
                } else {
                    fail("WebView2: local virtual-host API unavailable in this runtime");
                    return E_NOINTERFACE;
                }

                HRESULT event_hr = g_webview->add_WebMessageReceived(
                    Callback<ICoreWebView2WebMessageReceivedEventHandler>(
                        [](ICoreWebView2 *, ICoreWebView2WebMessageReceivedEventArgs *args) -> HRESULT {
                            LPWSTR value = nullptr;
                            if (SUCCEEDED(args->TryGetWebMessageAsString(&value)) && value) {
                                handle_web_message(value);
                                CoTaskMemFree(value);
                            }
                            return S_OK;
                        }).Get(), &g_message_token);
                if (FAILED(event_hr)) {
                    fail("WebView2: cannot subscribe to the HTML-to-game bridge");
                    return event_hr;
                }
                event_hr = g_webview->add_NavigationCompleted(
                    Callback<ICoreWebView2NavigationCompletedEventHandler>(
                        [](ICoreWebView2 *, ICoreWebView2NavigationCompletedEventArgs *args) -> HRESULT {
                            BOOL ok = FALSE;
                            args->get_IsSuccess(&ok);
                            if (!ok) {
                                fail("WebView2: local HTML navigation failed");
                                return S_OK;
                            }
                            InterlockedExchange(&g_state, 1);
                            page_loaded();
                            apply_visible();
                            log_message("WebView2: HTML screen is running inside the FIFA game window");
                            return S_OK;
                        }).Get(), &g_navigation_token);
                if (FAILED(event_hr)) {
                    fail("WebView2: cannot observe HTML navigation");
                    return event_hr;
                }
                InterlockedExchange(&g_state, 1);
                g_webview->Navigate(kHomeUrl);
                apply_visible();
                return S_OK;
            }).Get());
    if (FAILED(hr)) fail("WebView2: could not create the child browser window");
    return hr;
}

void begin_webview() {
    if (InterlockedCompareExchange(&g_state, 0, 0) == 1 ||
        InterlockedCompareExchange(&g_state, 0, 0) == -1) {
        apply_visible();
        return;
    }
    HRESULT com = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
    if (SUCCEEDED(com)) g_com_initialized = true;
    else if (com != RPC_E_CHANGED_MODE) {
        fail("WebView2: game window thread could not enter a COM apartment");
        return;
    }
    char loader_path[MAX_PATH] = {};
    _snprintf_s(loader_path, sizeof(loader_path), _TRUNCATE,
        "%s\\WebView2Loader.dll", g_web_root_a.c_str());
    /* The loader ships beside the injected DLL; fall back to the game's
     * current directory for an already-installed runtime helper. */
    char game_dir[MAX_PATH] = {};
    GetModuleFileNameA(nullptr, game_dir, MAX_PATH);
    char *slash = strrchr(game_dir, '\\');
    if (slash) *slash = 0;
    _snprintf_s(loader_path, sizeof(loader_path), _TRUNCATE,
        "%s\\WebView2Loader.dll", game_dir);
    g_loader = LoadLibraryA(loader_path);
    if (!g_loader) {
        fail("WebView2Loader.dll is missing beside the game executable");
        return;
    }
    typedef HRESULT (STDAPICALLTYPE *CreateEnvironmentFn)(PCWSTR, PCWSTR,
        ICoreWebView2EnvironmentOptions *,
        ICoreWebView2CreateCoreWebView2EnvironmentCompletedHandler *);
    auto create_environment = (CreateEnvironmentFn)GetProcAddress(g_loader,
        "CreateCoreWebView2EnvironmentWithOptions");
    if (!create_environment) {
        fail("WebView2: runtime loader does not export the environment API");
        return;
    }
    HRESULT hr = create_environment(nullptr, g_user_data_w.c_str(), nullptr,
        Callback<ICoreWebView2CreateCoreWebView2EnvironmentCompletedHandler>(
            create_controller).Get());
    if (FAILED(hr)) fail("WebView2: environment request failed");
}

bool encode_png(ID3D11ShaderResourceView *source, std::string &base64) {
    if (!source) return false;
    ComPtr<ID3D11Resource> resource;
    source->GetResource(&resource);
    ComPtr<ID3D11Texture2D> texture;
    if (FAILED(resource.As(&texture))) return false;
    D3D11_TEXTURE2D_DESC desc = {};
    texture->GetDesc(&desc);
    if (!desc.Width || !desc.Height || desc.Width > 2048 || desc.Height > 2048 ||
        desc.Format != DXGI_FORMAT_R8G8B8A8_UNORM || desc.SampleDesc.Count != 1)
        return false;
    ComPtr<ID3D11Device> device;
    texture->GetDevice(&device);
    ComPtr<ID3D11DeviceContext> context;
    device->GetImmediateContext(&context);
    D3D11_TEXTURE2D_DESC staging_desc = desc;
    staging_desc.Usage = D3D11_USAGE_STAGING;
    staging_desc.BindFlags = 0;
    staging_desc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    staging_desc.MiscFlags = 0;
    ComPtr<ID3D11Texture2D> staging;
    if (FAILED(device->CreateTexture2D(&staging_desc, nullptr, &staging))) return false;
    context->CopyResource(staging.Get(), texture.Get());
    D3D11_MAPPED_SUBRESOURCE mapped = {};
    if (FAILED(context->Map(staging.Get(), 0, D3D11_MAP_READ, 0, &mapped))) return false;

    std::vector<unsigned char> bgra((size_t)desc.Width * desc.Height * 4);
    for (UINT y = 0; y < desc.Height; ++y) {
        const unsigned char *row = (const unsigned char *)mapped.pData +
            (size_t)y * mapped.RowPitch;
        unsigned char *out = bgra.data() + (size_t)y * desc.Width * 4;
        for (UINT x = 0; x < desc.Width; ++x) {
            out[x * 4 + 0] = row[x * 4 + 2];
            out[x * 4 + 1] = row[x * 4 + 1];
            out[x * 4 + 2] = row[x * 4 + 0];
            out[x * 4 + 3] = row[x * 4 + 3];
        }
    }
    context->Unmap(staging.Get(), 0);

    HRESULT com = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    const bool uninitialize = SUCCEEDED(com);
    if (FAILED(com) && com != RPC_E_CHANGED_MODE) return false;
    ComPtr<IWICImagingFactory> factory;
    HRESULT hr = CoCreateInstance(CLSID_WICImagingFactory, nullptr,
        CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&factory));
    ComPtr<IStream> stream;
    if (SUCCEEDED(hr)) hr = CreateStreamOnHGlobal(nullptr, TRUE, &stream);
    ComPtr<IWICBitmapEncoder> encoder;
    if (SUCCEEDED(hr)) hr = factory->CreateEncoder(GUID_ContainerFormatPng,
        nullptr, &encoder);
    if (SUCCEEDED(hr)) hr = encoder->Initialize(stream.Get(), WICBitmapEncoderNoCache);
    ComPtr<IWICBitmapFrameEncode> frame;
    ComPtr<IPropertyBag2> properties;
    if (SUCCEEDED(hr)) hr = encoder->CreateNewFrame(&frame, &properties);
    if (SUCCEEDED(hr)) hr = frame->Initialize(properties.Get());
    if (SUCCEEDED(hr)) hr = frame->SetSize(desc.Width, desc.Height);
    WICPixelFormatGUID format = GUID_WICPixelFormat32bppBGRA;
    if (SUCCEEDED(hr)) hr = frame->SetPixelFormat(&format);
    if (SUCCEEDED(hr)) hr = frame->WritePixels(desc.Height, desc.Width * 4,
        (UINT)bgra.size(), bgra.data());
    if (SUCCEEDED(hr)) hr = frame->Commit();
    if (SUCCEEDED(hr)) hr = encoder->Commit();
    HGLOBAL handle = nullptr;
    if (SUCCEEDED(hr)) hr = GetHGlobalFromStream(stream.Get(), &handle);
    if (SUCCEEDED(hr) && handle) {
        SIZE_T size = GlobalSize(handle);
        const BYTE *bytes = (const BYTE *)GlobalLock(handle);
        if (bytes && size) {
            DWORD chars = 0;
            CryptBinaryToStringA(bytes, (DWORD)size,
                CRYPT_STRING_BASE64 | CRYPT_STRING_NOCRLF, nullptr, &chars);
            std::string encoded(chars, '\0');
            if (CryptBinaryToStringA(bytes, (DWORD)size,
                CRYPT_STRING_BASE64 | CRYPT_STRING_NOCRLF,
                encoded.data(), &chars)) {
                if (chars && encoded[chars - 1] == '\0') --chars;
                encoded.resize(chars);
                base64 = std::move(encoded);
            }
            GlobalUnlock(handle);
        }
    }
    if (uninitialize) CoUninitialize();
    return !base64.empty();
}

} // namespace

bool configure(const char *game_root, void (*log)(const char *)) {
    g_log = log;
    if (!game_root || !*game_root) return false;
    char root[MAX_PATH] = {};
    _snprintf_s(root, sizeof(root), _TRUNCATE,
        "%s\\ModCarrerMode\\tools\\club_globe", game_root);
    g_web_root_a = root;
    g_web_root_w = to_wide(g_web_root_a, CP_ACP);
    std::string user_data = std::string(game_root) +
        "\\ModCarrerMode\\runtime\\webview2";
    CreateDirectoryA((std::string(game_root) + "\\ModCarrerMode\\runtime").c_str(), nullptr);
    CreateDirectoryA(user_data.c_str(), nullptr);
    g_user_data_w = to_wide(user_data, CP_ACP);
    return !g_web_root_w.empty() && !g_user_data_w.empty();
}

void show() {
    std::wstring script=g_web_root_w+L"\\launch_preview.ps1";std::wstring cmd=L"powershell.exe -NoProfile -File \""+script+L"\" -ServerOnly";STARTUPINFOW start={};start.cb=sizeof(start);PROCESS_INFORMATION process={};if(CreateProcessW(nullptr,&cmd[0],nullptr,nullptr,FALSE,CREATE_NO_WINDOW,nullptr,g_web_root_w.c_str(),&start,&process)){CloseHandle(process.hThread);CloseHandle(process.hProcess);}
    InterlockedExchange(&g_page, 0);
    InterlockedExchange(&g_requested_visible, 1);
    if (g_parent && IsWindow(g_parent)) PostMessageW(g_parent, kHostMessage, 1, 0);
}

void hide() {
    InterlockedExchange(&g_requested_visible, 0);
    if (g_parent && IsWindow(g_parent)) PostMessageW(g_parent, kHostMessage, 0, 0);
}

int status() { return InterlockedCompareExchange(&g_state, 0, 0); }
bool page_is_player(){return InterlockedCompareExchange(&g_page,0,0)==4;}
bool page_is_scene() { return InterlockedCompareExchange(&g_page,0,0)==3; }
bool page_is_home() { return InterlockedCompareExchange(&g_page, 0, 0) == 0; }
bool visible() { return InterlockedCompareExchange(&g_visible, 0, 0) != 0; }
void clear_scene_preview() {
    std::lock_guard<std::mutex> guard(g_payload_lock);
    g_scene_png_base64.clear();
}

void set_career_context(int club_id, const char *club_name, int player_count,
    bool valid_starting_eleven, const char *detail_json) {
    std::string json = "{\"type\":\"career-context\",\"clubId\":" +
        std::to_string(club_id) + ",\"clubName\":" + json_string(club_name) +
        ",\"playerCount\":" + std::to_string(player_count) +
        ",\"validXI\":" + (valid_starting_eleven ? "true" : "false") + ",\"detail\":" + (detail_json?detail_json:"{}") + "}";
    bool changed = false;
    {
        std::lock_guard<std::mutex> guard(g_payload_lock);
        if (g_career_context_json != json) {
            if(InterlockedExchange(&g_scene_club,club_id)!=club_id)g_scene_png_base64.clear();
            g_career_context_json = json;
            changed = true;
        }
    }
    if (!changed) return;
    if (status() == 1 && !page_is_scene() && g_parent) {
        auto *pending = new (std::nothrow) std::string(std::move(json));
        if (pending && !PostMessageW(g_parent, kContextMessage, 0, (LPARAM)pending))
            delete pending;
    }
}

bool publish_scene(ID3D11ShaderResourceView *image) {
    if (!image || (!page_is_home()&&!page_is_scene()&&!page_is_player()) || status() != 1 ||
        !InterlockedCompareExchange(&g_visible, 0, 0)) return false;
    std::string encoded;
    if (!encode_png(image, encoded)) return false;
    std::string json = json_base64(encoded);
    {
        std::lock_guard<std::mutex> guard(g_payload_lock);
        g_scene_png_base64 = std::move(encoded);
    }
    std::string *pending = new (std::nothrow) std::string(std::move(json));
    if (!pending) return false;
    if (!PostMessageW(g_parent, kPublishMessage, 0, (LPARAM)pending)) {
        delete pending;
        return false;
    }
    return true;
}

bool handle_window_message(HWND window, UINT message, WPARAM wparam,
    LPARAM lparam, LRESULT *result) {
    if (!g_parent && window) g_parent = window;
    if (message == kHostMessage) {
        InterlockedExchange(&g_requested_visible, wparam ? 1 : 0);
        begin_webview();
        if (wparam && g_webview) navigate_home();
        apply_visible();
        if (result) *result = 0;
        return true;
    }
    if (message == kPublishMessage) {
        std::unique_ptr<std::string> pending((std::string *)lparam);
        if (pending) post_json(*pending);
        if (result) *result = 0;
        return true;
    }
    if (message == kContextMessage) {
        std::unique_ptr<std::string> pending((std::string *)lparam);
        if (pending) post_json(*pending);
        if (result) *result = 0;
        return true;
    }
    if (window == g_parent && message == WM_SIZE && g_controller) {
        RECT bounds = {};
        GetClientRect(window, &bounds);
        g_controller->put_Bounds(bounds);
    } else if (window == g_parent && message == WM_MOVE && g_controller) {
        g_controller->NotifyParentWindowPositionChanged();
    } else if (window == g_parent && message == WM_SETFOCUS && g_controller &&
        InterlockedCompareExchange(&g_requested_visible, 0, 0)) {
        g_controller->MoveFocus(COREWEBVIEW2_MOVE_FOCUS_REASON_PROGRAMMATIC);
    }
    (void)lparam;
    return false;
}

} // namespace fifa_webview
