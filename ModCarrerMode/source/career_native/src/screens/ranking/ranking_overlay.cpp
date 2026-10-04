#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "../../platform/mod_paths.h"
#include <d3d11.h>
#include <dxgi.h>
#include <dxgi1_2.h>
#include <Xinput.h>
#include <psapi.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>
#include <vector>

#include "ranking_overlay.h"
#include "../club/club_player_screen.h"
#include "../clubs/clubs_browser.h"
#include "../leagues/leagues_browser.h"
#include "../competitions/club_competitions_screen.h"
#include "../player/player_search_screen.h"
#include "../operations/career_operations.h"
#include "../trophies/trophy_room_screen.h"
#include "../sponsors/sponsor_screen.h"
#include "../coach/coach_profile_screen.h"
#include "../next_match/next_match_screen.h"
#include "../../platform/input/ranking_card_action.h"
#include "../../platform/input/ranking_input_gate.h"
#include "../../platform/overlay/mod_overlay_screens.h"
#include "../../platform/input/mod_xinput_gate.h"
#include "../../../third_party/imgui/imgui.h"
#include "../../../third_party/imgui/backends/imgui_impl_dx11.h"
#include "../../../third_party/imgui/backends/imgui_impl_win32.h"

extern IMGUI_IMPL_API LRESULT ImGui_ImplWin32_WndProcHandler(
    HWND, UINT, WPARAM, LPARAM);

#pragma comment(lib, "d3d11.lib")
#pragma comment(lib, "dxgi.lib")
#pragma comment(lib, "dwmapi.lib")

typedef DWORD(WINAPI *XInputGetStateFn)(DWORD, XINPUT_STATE *);
typedef HRESULT(WINAPI *PresentFn)(IDXGISwapChain *, UINT, UINT);
typedef HRESULT(WINAPI *Present1Fn)(IDXGISwapChain1 *, UINT, UINT,
    const DXGI_PRESENT_PARAMETERS *);
typedef HRESULT(WINAPI *ResizeBuffersFn)(IDXGISwapChain *, UINT, UINT, UINT,
    DXGI_FORMAT, UINT);
typedef HRESULT(WINAPI *CreateDeviceAndSwapChainFn)(IDXGIAdapter *,
    D3D_DRIVER_TYPE, HMODULE, UINT, const D3D_FEATURE_LEVEL *, UINT, UINT,
    const DXGI_SWAP_CHAIN_DESC *, IDXGISwapChain **, ID3D11Device **,
    D3D_FEATURE_LEVEL *, ID3D11DeviceContext **);

static SRWLOCK g_rows_lock = SRWLOCK_INIT;
static std::vector<RankingOverlayRow> g_rows;
static volatile LONG g_close_requested;
static volatile LONG g_card_action_hook_state;
static DWORD g_card_action_scan_tick;
static volatile LONG g_page_reader_state;
static volatile LONG g_start_once;
static volatile LONG g_xinput_last_scan_tick;
static volatile LONG g_chord_down;
static volatile LONG g_f10_down;
static volatile LONG g_present_hooked;
static volatile LONG g_imgui_ready;
static volatile LONG g_imgui_init_attempted;
static BOOL g_overlay_enabled = TRUE;
static XInputGetStateFn g_original_xinput_get_state = mod_xinput_read_raw;
static PresentFn g_original_present;
static Present1Fn g_original_present1;
static ResizeBuffersFn g_original_resize_buffers;
static ID3D11Device *g_game_device;
static ID3D11DeviceContext *g_game_context;
static ID3D11RenderTargetView *g_render_target;
static IDXGISwapChain *g_render_target_chain;
static HWND g_game_window;
static WNDPROC g_original_wndproc;
static char g_game_root[MAX_PATH];
static char g_overlay_log_path[MAX_PATH];
static volatile LONG g_selected_row;
static volatile LONG g_scroll_to_selected;
static volatile LONG g_row_count;
static volatile LONG g_user_team_id;
static volatile LONG g_user_row;
static WORD g_previous_gamepad_buttons;
static float g_analog_scroll_axis;
static LONG g_discrete_scroll_rows;
static ImFont *g_table_font;
static ImFont *g_profile_number_font;
static BOOL g_page_reader_supported;
static DWORD g_page_poll_tick;
static char g_last_game_page[96];
static volatile LONG g_suppressed_escape;
static bool g_modal_input_session;

extern "C" BOOL ranking_overlay_captures_input(void)
{
    return g_overlay_enabled && mod_screen_captures_input();
}

struct CachedCrestTexture {
    int team_id;
    ID3D11ShaderResourceView *texture;
};

static std::vector<CachedCrestTexture> g_crest_textures;

static void overlay_log(const char *message)
{
    HANDLE file;
    DWORD written;
    char line[384];
    SYSTEMTIME now;
    if (!g_overlay_log_path[0] || !message) return;
    GetLocalTime(&now);
    _snprintf_s(line, sizeof(line), _TRUNCATE,
        "%02u:%02u:%02u.%03u %s\r\n", now.wHour, now.wMinute,
        now.wSecond, now.wMilliseconds, message);
    file = CreateFileA(g_overlay_log_path, FILE_APPEND_DATA,
        FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_ALWAYS,
        FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) return;
    WriteFile(file, line, (DWORD)strlen(line), &written, NULL);
    CloseHandle(file);
}

static void overlay_open(const char *reason)
{
    if (!mod_screen_is_open() && mod_screen_open("ranking")) {
        overlay_log(reason);
    }
}

static void restore_game_input_focus(void)
{
    /* The overlay is drawn in the FIFA window, so it never owns a separate
     * OS window. Reassert the game's focus only if FIFA is still foreground. */
    if (g_game_window && IsWindow(g_game_window) &&
        GetForegroundWindow() == g_game_window)
    {
        SetFocus(g_game_window);
        /* Let FIFA reapply its cursor policy on its own window thread. */
        PostMessageA(g_game_window, WM_SETCURSOR, (WPARAM)g_game_window,
            MAKELPARAM(HTCLIENT, WM_MOUSEMOVE));
    }
}

static void overlay_close(const char *reason, WORD exit_buttons)
{
    (void)exit_buttons; /* all held buttons/axes are quarantined by the gate */
    if (mod_screen_close()) {
        InterlockedExchange(&g_close_requested, 0);
        /* Return OS focus at the close request, regardless of which FIFA
         * navigation page is underneath. Input cleanup stays on Present. */
        restore_game_input_focus();
        if (reason) overlay_log(reason);
    }
}

/* Every registered screen gets the same cleanup, including a close requested
 * from its own draw callback. Only Present's thread touches the ImGui context. */
static void finish_modal_input_session(void)
{
    if (!g_modal_input_session) return;
    g_modal_input_session = false;
    g_previous_gamepad_buttons = 0;
    g_analog_scroll_axis = 0.0f;
    g_discrete_scroll_rows = 0;
    if (InterlockedCompareExchange(&g_imgui_ready, 0, 0)) {
        ImGuiIO &io = ImGui::GetIO();
        io.ClearEventsQueue();
        io.ClearInputKeys();
        io.MouseDrawCursor = false;
    }
    restore_game_input_focus();
    mod_xinput_log_capture_stats();
}

static bool page_reader_is_supported(void)
{
    LONG state = InterlockedCompareExchange(&g_page_reader_state, 0, 0);
    if (state == 0 && InterlockedCompareExchange(&g_page_reader_state, 1, 0) == 0) {
        HMODULE executable = GetModuleHandleA(NULL);
        MODULEINFO module_info;
        g_page_reader_supported = executable &&
            GetModuleInformation(GetCurrentProcess(), executable,
                &module_info, sizeof(module_info)) &&
            module_info.SizeOfImage == 0x09525000;
        InterlockedExchange(&g_page_reader_state,
            g_page_reader_supported ? 2 : -1);
        overlay_log(g_page_reader_supported
            ? "career page reader enabled for supported FIFA image size"
            : "career page reader disabled: unsupported FIFA image size");
        state = g_page_reader_supported ? 2 : -1;
    }
    return state == 2;
}

/* Read the active career-view name inside FIFA's own process. This mod embeds
 * the pointer chain and build guard; it has no external-process dependency. */
static bool read_current_game_page(char *destination, size_t capacity)
{
    static const uintptr_t offsets[] = { 232, 192, 136, 472, 0 };
    uintptr_t pointer = 0;
    uintptr_t address;
    SIZE_T bytes_read = 0;
    HMODULE executable;
    if (!destination || capacity < 2 || !page_reader_is_supported())
        return false;
    ZeroMemory(destination, capacity);
    executable = GetModuleHandleA(NULL);
    if (!executable) return false;
    address = (uintptr_t)executable + (uintptr_t)0x03809030;
    if (!ReadProcessMemory(GetCurrentProcess(), (LPCVOID)address,
        &pointer, sizeof(pointer), &bytes_read) || bytes_read != sizeof(pointer) ||
        !pointer) return false;
    for (size_t i = 0; i + 1 < sizeof(offsets) / sizeof(offsets[0]); ++i) {
        if (pointer > UINTPTR_MAX - offsets[i]) return false;
        address = pointer + offsets[i];
        bytes_read = 0;
        if (!ReadProcessMemory(GetCurrentProcess(), (LPCVOID)address,
            &pointer, sizeof(pointer), &bytes_read) ||
            bytes_read != sizeof(pointer) || !pointer) return false;
    }
    if (pointer > UINTPTR_MAX - offsets[sizeof(offsets) / sizeof(offsets[0]) - 1])
        return false;
    address = pointer + offsets[sizeof(offsets) / sizeof(offsets[0]) - 1];
    bytes_read = 0;
    if (!ReadProcessMemory(GetCurrentProcess(), (LPCVOID)address,
        destination, capacity - 1, &bytes_read) || !bytes_read) return false;
    destination[bytes_read] = 0;
    return _strnicmp(destination, "game/screens/", 13) == 0;
}

static void poll_career_page_for_diagnostics(void)
{
    DWORD now = GetTickCount();
    char page[sizeof(g_last_game_page)];
    const DWORD poll_interval_ms = 75;
    if (!g_overlay_enabled) return;
    if ((DWORD)(now - g_page_poll_tick) < poll_interval_ms) return;
    g_page_poll_tick = now;
    if (!read_current_game_page(page, sizeof(page))) return;
    if (_stricmp(page, g_last_game_page) != 0) {
        char message[144];
        strncpy_s(g_last_game_page, sizeof(g_last_game_page), page, _TRUNCATE);
        _snprintf_s(message, sizeof(message), _TRUNCATE,
            "FIFA screen changed: %.96s", page);
        overlay_log(message);
    }
}

static bool native_mod_screen_action_exists(const char *action)
{
    return mod_screen_has_action(action) != FALSE;
}

static void native_mod_screen_selected(const char *action)
{
    if (mod_screen_open_action(action)) {
        char message[180];
        _snprintf_s(message, sizeof(message), _TRUNCATE,
            "opened by native mod-screen card action: %s; Hub remains active", action);
        overlay_log(message);
    }
}

static void try_install_native_ranking_card_action(void)
{
    MODULEINFO info;
    HMODULE executable;
    RankingCardActionHookResult result;
    if (!g_overlay_enabled ||
        InterlockedCompareExchange(&g_card_action_hook_state, 0, 0) != 0)
        return;
    executable = GetModuleHandleA(NULL);
    if (!executable || !GetModuleInformation(GetCurrentProcess(), executable,
        &info, sizeof(info))) return;
    result = ranking_card_action_install((unsigned char *)executable,
        info.SizeOfImage, native_mod_screen_action_exists,
        native_mod_screen_selected, overlay_log);
    if (result == RANKING_CARD_ACTION_READY)
        InterlockedExchange(&g_card_action_hook_state, 1);
    else if (result < 0) {
        InterlockedExchange(&g_card_action_hook_state, -1);
        overlay_log(result == RANKING_CARD_ACTION_UNSUPPORTED
            ? "native ranking card action unavailable: unsupported FIFA image"
            : "native ranking card action unavailable: hook installation failed");
    }
}

static void overlay_set_paths(void)
{
    char game_path[MAX_PATH];
    char *slash;
    DWORD length = GetModuleFileNameA(NULL, game_path, sizeof(game_path));
    if (!length || length >= sizeof(game_path)) return;
    slash = strrchr(game_path, '\\');
    if (!slash) return;
    *slash = 0;
    strcpy_s(g_game_root, sizeof(g_game_root), game_path);
    std::string mod_path=std::string(game_path)+"\\ModCarrerMode";
    career_path_logs(mod_path.c_str());
    _snprintf_s(g_overlay_log_path, sizeof(g_overlay_log_path), _TRUNCATE,
        "%s\\logs\\career_ranking_overlay.log", mod_path.c_str());
    {
        char config_path[MAX_PATH];
        career_path_read(config_path, sizeof(config_path), mod_path.c_str(),
            "config", "ranking_overlay.ini");
        g_overlay_enabled = GetPrivateProfileIntA(
            "overlay", "enabled", 1, config_path) != 0;
    }
}

static char *utf8_name(const char *source, char *destination, size_t capacity)
{
    wchar_t wide[256];
    int wide_count;
    int bytes;
    if (!capacity) return destination;
    destination[0] = 0;
    if (!source || !source[0]) return destination;
    wide_count = MultiByteToWideChar(CP_ACP, 0, source, -1, wide,
        (int)(sizeof(wide) / sizeof(wide[0])));
    if (!wide_count) {
        strncpy_s(destination, capacity, source, _TRUNCATE);
        return destination;
    }
    bytes = WideCharToMultiByte(CP_UTF8, 0, wide, -1, destination,
        (int)capacity, NULL, NULL);
    if (!bytes) destination[0] = 0;
    return destination;
}

extern "C" void ranking_overlay_publish_rows(
    const RankingOverlayRow *rows, size_t count, int user_team_id)
{
    AcquireSRWLockExclusive(&g_rows_lock);
    try {
        if (rows && count) {
            LONG user_row = 0;
            g_rows.assign(rows, rows + count);
            for (size_t i = 0; i < g_rows.size(); ++i) {
                char converted[sizeof(g_rows[i].name)];
                utf8_name(g_rows[i].name, converted, sizeof(converted));
                strncpy_s(g_rows[i].name, sizeof(g_rows[i].name),
                    converted, _TRUNCATE);
                if (user_team_id > 0 && g_rows[i].team_id == user_team_id)
                    user_row = (LONG)i;
            }
            LONG previous_team = InterlockedExchange(&g_user_team_id,
                user_team_id);
            LONG previous_row = InterlockedExchange(&g_user_row, user_row);
            InterlockedExchange(&g_selected_row, user_row);
            if (previous_team != user_team_id || previous_row != user_row)
                InterlockedExchange(&g_scroll_to_selected, 1);
            InterlockedExchange(&g_row_count, (LONG)g_rows.size());
        } else {
            g_rows.clear();
            InterlockedExchange(&g_selected_row, 0);
            InterlockedExchange(&g_user_row, 0);
            InterlockedExchange(&g_user_team_id, user_team_id);
            InterlockedExchange(&g_row_count, 0);
        }
    } catch (...) {
        g_rows.clear();
        InterlockedExchange(&g_selected_row, 0);
        InterlockedExchange(&g_user_row, 0);
        InterlockedExchange(&g_row_count, 0);
    }
    ReleaseSRWLockExclusive(&g_rows_lock);
}

static bool patch_pointer(void **slot, void *replacement, void **original)
{
    DWORD old_protect = 0;
    if (!slot || !replacement || !VirtualProtect(slot, sizeof(void *),
        PAGE_EXECUTE_READWRITE, &old_protect)) return false;
    if (original) *original = *slot;
    InterlockedExchangePointer((PVOID volatile *)slot, replacement);
    {
        DWORD ignored;
        VirtualProtect(slot, sizeof(void *), old_protect, &ignored);
    }
    return true;
}

static BOOL patch_xinput_import(void)
{
    BOOL ready = mod_xinput_install(overlay_log);
    HMODULE frontend = GetModuleHandleA(NULL);
    HMODULE gameplay = GetModuleHandleA("fifa16.bin");
    if (frontend) ranking_input_install_cursor_import(frontend);
    if (gameplay && gameplay != frontend) ranking_input_install_cursor_import(gameplay);
    return ready;
}

static bool hook_vtable_entry(IUnknown *object, size_t index,
    void *replacement, void **original)
{
    void **vtable;
    if (!object) return false;
    vtable = *(void ***)object;
    return patch_pointer(vtable + index, replacement, original) != FALSE;
}

static HRESULT WINAPI overlay_present(IDXGISwapChain *chain,
    UINT sync_interval, UINT flags);
static HRESULT WINAPI overlay_present1(IDXGISwapChain1 *chain,
    UINT sync_interval, UINT present_flags,
    const DXGI_PRESENT_PARAMETERS *parameters);
static HRESULT WINAPI overlay_resize_buffers(IDXGISwapChain *chain,
    UINT buffer_count, UINT width, UINT height, DXGI_FORMAT format,
    UINT swap_chain_flags);

static LRESULT CALLBACK dummy_window_proc(HWND window, UINT message,
    WPARAM wparam, LPARAM lparam)
{
    return DefWindowProcA(window, message, wparam, lparam);
}

static bool install_present_hooks(void)
{
    const char *class_name = "Fifa16RankingOverlayDummyWindow";
    WNDCLASSA window_class;
    HWND window = NULL;
    HMODULE d3d11 = NULL;
    CreateDeviceAndSwapChainFn create_device = NULL;
    DXGI_SWAP_CHAIN_DESC desc;
    IDXGISwapChain *chain = NULL;
    IDXGISwapChain1 *chain1 = NULL;
    ID3D11Device *device = NULL;
    ID3D11DeviceContext *context = NULL;
    D3D_FEATURE_LEVEL feature_level;
    const D3D_FEATURE_LEVEL levels[] = {
        D3D_FEATURE_LEVEL_11_0,
        D3D_FEATURE_LEVEL_10_1,
        D3D_FEATURE_LEVEL_10_0
    };
    HRESULT hr;
    ATOM atom;
    ZeroMemory(&window_class, sizeof(window_class));
    window_class.lpfnWndProc = dummy_window_proc;
    window_class.hInstance = GetModuleHandleA(NULL);
    window_class.lpszClassName = class_name;
    atom = RegisterClassA(&window_class);
    if (!atom && GetLastError() != ERROR_CLASS_ALREADY_EXISTS) return false;
    window = CreateWindowExA(0, class_name, "", WS_POPUP,
        0, 0, 64, 64, NULL, NULL, window_class.hInstance, NULL);
    if (!window) return false;
    d3d11 = LoadLibraryA("d3d11.dll");
    if (!d3d11) {
        DestroyWindow(window);
        return false;
    }
    create_device = (CreateDeviceAndSwapChainFn)GetProcAddress(
        d3d11, "D3D11CreateDeviceAndSwapChain");
    if (!create_device) {
        FreeLibrary(d3d11);
        DestroyWindow(window);
        return false;
    }
    ZeroMemory(&desc, sizeof(desc));
    desc.BufferDesc.Width = 64;
    desc.BufferDesc.Height = 64;
    desc.BufferDesc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    desc.SampleDesc.Count = 1;
    desc.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
    desc.BufferCount = 1;
    desc.OutputWindow = window;
    desc.Windowed = TRUE;
    desc.SwapEffect = DXGI_SWAP_EFFECT_DISCARD;
    hr = create_device(NULL, D3D_DRIVER_TYPE_HARDWARE, NULL,
        D3D11_CREATE_DEVICE_BGRA_SUPPORT, levels,
        (UINT)(sizeof(levels) / sizeof(levels[0])), D3D11_SDK_VERSION,
        &desc, &chain, &device, &feature_level, &context);
    if (FAILED(hr)) {
        hr = create_device(NULL, D3D_DRIVER_TYPE_WARP, NULL,
            D3D11_CREATE_DEVICE_BGRA_SUPPORT, levels,
            (UINT)(sizeof(levels) / sizeof(levels[0])), D3D11_SDK_VERSION,
            &desc, &chain, &device, &feature_level, &context);
    }
    if (SUCCEEDED(hr) && chain) {
        bool present_ok = hook_vtable_entry((IUnknown *)chain, 8,
            (void *)overlay_present, (void **)&g_original_present);
        bool resize_ok = hook_vtable_entry((IUnknown *)chain, 13,
            (void *)overlay_resize_buffers,
            (void **)&g_original_resize_buffers);
        if (present_ok && !resize_ok) {
            hook_vtable_entry((IUnknown *)chain, 8,
                (void *)g_original_present, NULL);
            g_original_present = NULL;
            present_ok = false;
        }
        if (SUCCEEDED(chain->QueryInterface(__uuidof(IDXGISwapChain1),
            (void **)&chain1)) && chain1) {
            hook_vtable_entry((IUnknown *)chain1, 22,
                (void *)overlay_present1, (void **)&g_original_present1);
            chain1->Release();
        }
        if (present_ok && resize_ok) {
            InterlockedExchange(&g_present_hooked, 1);
            overlay_log("Direct3D 11 Present hooks installed");
        }
        if (context) context->Release();
        if (device) device->Release();
        chain->Release();
    }
    FreeLibrary(d3d11);
    DestroyWindow(window);
    UnregisterClassA(class_name, window_class.hInstance);
    return InterlockedCompareExchange(&g_present_hooked, 0, 0) != 0;
}

static bool is_keyboard_or_mouse_message(UINT message)
{
    if (message >= WM_MOUSEFIRST && message <= WM_MOUSELAST) return true;
    switch (message) {
    case WM_INPUT:
    case WM_KEYDOWN:
    case WM_KEYUP:
    case WM_CHAR:
    case WM_SYSKEYDOWN:
    case WM_SYSKEYUP:
    case WM_SYSCHAR:
    case WM_APPCOMMAND:
        return true;
    default:
        return false;
    }
}

static void overlay_f10_pressed(void)
{
    LONG is_open;
    if (!g_overlay_enabled ||
        InterlockedExchange(&g_f10_down, 1) != 0) return;
    is_open = mod_screen_is_open();
    if (is_open) {
        InterlockedExchange(&g_close_requested, 1);
        overlay_log("close requested by F10");
    } else {
        overlay_open("opened by F10");
    }
}

static LRESULT CALLBACK overlay_window_proc(HWND window, UINT message,
    WPARAM wparam, LPARAM lparam)
{
    LONG is_open = mod_screen_is_open();
    BOOL capture = mod_screen_captures_input();
    if ((message == WM_KEYDOWN || message == WM_SYSKEYDOWN) &&
        wparam == VK_F10) {
        if (!g_overlay_enabled) {
            if (g_original_wndproc)
                return CallWindowProcA(g_original_wndproc, window,
                    message, wparam, lparam);
            return DefWindowProcA(window, message, wparam, lparam);
        }
        overlay_f10_pressed();
        return 0;
    }
    if ((message == WM_KEYUP || message == WM_SYSKEYUP) &&
        wparam == VK_F10 && g_overlay_enabled) {
        InterlockedExchange(&g_f10_down, 0);
        return 0;
    }
    if ((message == WM_KEYDOWN || message == WM_SYSKEYDOWN) &&
        wparam == VK_ESCAPE && (is_open ||
            InterlockedCompareExchange(&g_suppressed_escape, 0, 0))) {
        if (is_open && InterlockedExchange(&g_suppressed_escape, 1) == 0) {
            mod_screen_request_back();
            overlay_log("Back requested by Escape");
        }
        return 0;
    }
    if ((message == WM_KEYUP || message == WM_SYSKEYUP) &&
        wparam == VK_ESCAPE && InterlockedExchange(&g_suppressed_escape, 0)) {
        return 0;
    }
    if (is_open && message == WM_SETCURSOR && LOWORD(lparam) == HTCLIENT) {
        /* The software cursor stays visible even when FIFA hides the OS
         * cursor through ShowCursor/SetCursor during controller navigation. */
        SetCursor(NULL);
        return TRUE;
    }
    if (capture && is_keyboard_or_mouse_message(message)) {
        if (is_open && InterlockedCompareExchange(&g_imgui_ready, 0, 0))
            ImGui_ImplWin32_WndProcHandler(window, message, wparam, lparam);
        return 0;
    }
    if (g_original_wndproc)
        return CallWindowProcA(g_original_wndproc, window, message,
            wparam, lparam);
    return DefWindowProcA(window, message, wparam, lparam);
}

static bool attach_overlay_window(HWND window)
{
    LONG_PTR previous;
    DWORD error;
    if (!window) return false;
    if (g_game_window == window && g_original_wndproc) return true;
    if (g_original_wndproc && g_game_window)
        SetWindowLongPtrA(g_game_window, GWLP_WNDPROC,
            (LONG_PTR)g_original_wndproc);
    g_game_window = NULL;
    g_original_wndproc = NULL;
    SetLastError(ERROR_SUCCESS);
    previous = SetWindowLongPtrA(window, GWLP_WNDPROC,
        (LONG_PTR)overlay_window_proc);
    error = GetLastError();
    if (!previous && error != ERROR_SUCCESS) {
        overlay_log("failed to install game-window keyboard hook");
        return false;
    }
    g_game_window = window;
    g_original_wndproc = (WNDPROC)previous;
    overlay_log("game-window keyboard hook installed");
    return true;
}

static bool attach_overlay_window_from_chain(IDXGISwapChain *chain)
{
    DXGI_SWAP_CHAIN_DESC desc;
    if (!chain) return false;
    if (g_game_window && g_original_wndproc && IsWindow(g_game_window))
        return true;
    if (FAILED(chain->GetDesc(&desc)) || !desc.OutputWindow) return false;
    return attach_overlay_window(desc.OutputWindow);
}

static void release_crest_textures(void)
{
    for (size_t i = 0; i < g_crest_textures.size(); ++i) {
        if (g_crest_textures[i].texture)
            g_crest_textures[i].texture->Release();
    }
    g_crest_textures.clear();
}

static ID3D11ShaderResourceView *load_crest_texture_from_file(
    const char *path)
{
    HANDLE file = INVALID_HANDLE_VALUE;
    LARGE_INTEGER file_size;
    std::vector<unsigned char> bytes;
    D3D11_SUBRESOURCE_DATA mip_data[16];
    UINT mip_width[16];
    UINT mip_height[16];
    UINT mip_count = 0;
    size_t data_offset = 128;
    DXGI_FORMAT format = DXGI_FORMAT_UNKNOWN;
    ID3D11Texture2D *texture = NULL;
    ID3D11ShaderResourceView *view = NULL;
    D3D11_TEXTURE2D_DESC texture_desc;
    D3D11_SHADER_RESOURCE_VIEW_DESC view_desc;
    DWORD read = 0;
    DWORD format_flags;
    DWORD four_cc;
    UINT width;
    UINT height;

    file = CreateFileA(path, GENERIC_READ, FILE_SHARE_READ, NULL,
        OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) return NULL;
    if (!GetFileSizeEx(file, &file_size) || file_size.QuadPart < 128 ||
        file_size.QuadPart > 4 * 1024 * 1024) {
        CloseHandle(file);
        return NULL;
    }
    try {
        bytes.resize((size_t)file_size.QuadPart);
    } catch (...) {
        CloseHandle(file);
        return NULL;
    }
    if (!ReadFile(file, bytes.data(), (DWORD)bytes.size(), &read, NULL) ||
        read != bytes.size()) {
        CloseHandle(file);
        return NULL;
    }
    CloseHandle(file);

    if (memcmp(bytes.data(), "DDS ", 4) != 0) return NULL;
    memcpy(&height, bytes.data() + 12, sizeof(height));
    memcpy(&width, bytes.data() + 16, sizeof(width));
    memcpy(&format_flags, bytes.data() + 80, sizeof(format_flags));
    memcpy(&four_cc, bytes.data() + 84, sizeof(four_cc));
    if (!width || !height || width > 4096 || height > 4096 ||
        !(format_flags & 0x4)) return NULL;

    if (four_cc == 0x31545844) format = DXGI_FORMAT_BC1_UNORM; /* DXT1 */
    else if (four_cc == 0x33545844) format = DXGI_FORMAT_BC2_UNORM; /* DXT3 */
    else if (four_cc == 0x35545844) format = DXGI_FORMAT_BC3_UNORM; /* DXT5 */
    else return NULL;

    while (mip_count < 16) {
        UINT blocks_wide = (width + 3) / 4;
        UINT blocks_high = (height + 3) / 4;
        UINT block_size = format == DXGI_FORMAT_BC1_UNORM ? 8 : 16;
        UINT row_pitch = (blocks_wide ? blocks_wide : 1) * block_size;
        UINT rows = blocks_high ? blocks_high : 1;
        size_t slice_size = (size_t)row_pitch * rows;
        if (data_offset + slice_size > bytes.size()) break;
        mip_data[mip_count].pSysMem = bytes.data() + data_offset;
        mip_data[mip_count].SysMemPitch = row_pitch;
        mip_data[mip_count].SysMemSlicePitch = (UINT)slice_size;
        mip_width[mip_count] = width;
        mip_height[mip_count] = height;
        ++mip_count;
        data_offset += slice_size;
        if (width == 1 && height == 1) break;
        width = width > 1 ? width / 2 : 1;
        height = height > 1 ? height / 2 : 1;
    }
    if (!mip_count) return NULL;

    ZeroMemory(&texture_desc, sizeof(texture_desc));
    texture_desc.Width = mip_width[0];
    texture_desc.Height = mip_height[0];
    texture_desc.MipLevels = mip_count;
    texture_desc.ArraySize = 1;
    texture_desc.Format = format;
    texture_desc.SampleDesc.Count = 1;
    texture_desc.Usage = D3D11_USAGE_DEFAULT;
    texture_desc.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    if (FAILED(g_game_device->CreateTexture2D(&texture_desc, mip_data,
        &texture))) return NULL;

    ZeroMemory(&view_desc, sizeof(view_desc));
    view_desc.Format = format;
    view_desc.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D;
    view_desc.Texture2D.MipLevels = mip_count;
    if (FAILED(g_game_device->CreateShaderResourceView(texture, &view_desc,
        &view))) view = NULL;
    texture->Release();
    return view;
}

static ID3D11ShaderResourceView *ranking_crest_texture(int team_id)
{
    CachedCrestTexture cached;
    char path[MAX_PATH];
    const char *themes[] = { "light", "dark" };
    if (team_id <= 0 || !g_game_device || !g_game_root[0]) return NULL;
    for (size_t i = 0; i < g_crest_textures.size(); ++i)
        if (g_crest_textures[i].team_id == team_id)
            return g_crest_textures[i].texture;

    cached.team_id = team_id;
    cached.texture = NULL;
    for (size_t i = 0; i < sizeof(themes) / sizeof(themes[0]); ++i) {
        DWORD attributes;
        _snprintf_s(path, sizeof(path), _TRUNCATE,
            "%s\\data\\ui\\imgAssets\\crest\\%s\\l%d.dds",
            g_game_root, themes[i], team_id);
        attributes = GetFileAttributesA(path);
        if (attributes == INVALID_FILE_ATTRIBUTES ||
            (attributes & FILE_ATTRIBUTE_DIRECTORY)) continue;
        cached.texture = load_crest_texture_from_file(path);
        if (cached.texture) break;
    }
    try {
        g_crest_textures.push_back(cached);
    } catch (...) {
        if (cached.texture) cached.texture->Release();
        return NULL;
    }
    return cached.texture;
}

static void release_render_target(void)
{
    if (g_render_target) {
        g_render_target->Release();
        g_render_target = NULL;
    }
    g_render_target_chain = NULL;
}

static bool ensure_imgui(IDXGISwapChain *chain)
{
    DXGI_SWAP_CHAIN_DESC desc;
    ID3D11Device *device = NULL;
    ID3D11DeviceContext *context = NULL;
    HRESULT hr;
    if (!chain || FAILED(chain->GetDesc(&desc)) || !desc.OutputWindow)
        return false;
    hr = chain->GetDevice(__uuidof(ID3D11Device), (void **)&device);
    if (FAILED(hr) || !device) return false;
    if (g_game_device == device &&
        InterlockedCompareExchange(&g_imgui_ready, 0, 0)) {
        device->Release();
        attach_overlay_window(desc.OutputWindow);
        return true;
    }
    if (InterlockedExchange(&g_imgui_init_attempted, 1) && !g_game_device) {
        device->Release();
        return false;
    }
    if (InterlockedCompareExchange(&g_imgui_ready, 0, 0)) {
        club_player_screen_set_number_font(NULL);
        ImGui_ImplDX11_Shutdown();
        ImGui_ImplWin32_Shutdown();
        ImGui::DestroyContext();
        InterlockedExchange(&g_imgui_ready, 0);
        if (g_original_wndproc && g_game_window)
            SetWindowLongPtrA(g_game_window, GWLP_WNDPROC,
                (LONG_PTR)g_original_wndproc);
        g_original_wndproc = NULL;
        g_game_window = NULL;
        release_render_target();
        release_crest_textures();
        if (g_game_context) g_game_context->Release();
        club_player_screen_set_device(NULL);
        player_search_screen_set_device(NULL);
        clubs_browser_device(NULL);
        leagues_browser_device(NULL);
        club_competitions_screen_device(NULL);
        trophy_room_device(NULL);
        sponsor_screen_device(NULL);
        coach_profile_device(NULL);
        next_match_device(NULL);
        career_operations_device(NULL);
        if (g_game_device) g_game_device->Release();
        g_game_context = NULL;
        g_game_device = NULL;
    }
    device->GetImmediateContext(&context);
    if (!context) {
        device->Release();
        return false;
    }
    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO &io = ImGui::GetIO();
    io.ConfigFlags |= ImGuiConfigFlags_NavEnableGamepad;
    io.MouseDrawCursor = GetSystemMetrics(SM_MOUSEPRESENT) != 0;
    io.BackendFlags |= ImGuiBackendFlags_HasGamepad;
    {
        char windows_dir[MAX_PATH];
        char bold_font_path[MAX_PATH];
        UINT path_length = GetWindowsDirectoryA(windows_dir,
            (UINT)sizeof(windows_dir));
        if (path_length && path_length < sizeof(windows_dir)) {
            static const ImWchar number_glyph_ranges[] = {0x0020, 0x0039, 0};
            _snprintf_s(bold_font_path, sizeof(bold_font_path), _TRUNCATE,
                "%s\\Fonts\\segoeuib.ttf", windows_dir);
            if (GetFileAttributesA(bold_font_path) != INVALID_FILE_ATTRIBUTES) {
                g_table_font = io.Fonts->AddFontFromFileTTF(
                    bold_font_path, 16.0f);
                /* The shirt number is displayed at ~50 px. Rasterize its own
                 * bold glyphs at that size instead of enlarging ImGui's tiny
                 * default atlas font, which made the number visibly soft. */
                g_profile_number_font = io.Fonts->AddFontFromFileTTF(
                    bold_font_path, 56.0f, nullptr, number_glyph_ranges);
            }
        }
    }
    club_player_screen_set_number_font(g_profile_number_font);
    ImGui::StyleColorsDark();
    ImGuiStyle &style = ImGui::GetStyle();
    style.WindowRounding = 8.0f;
    style.FrameRounding = 4.0f;
    style.ScrollbarRounding = 5.0f;
    style.Colors[ImGuiCol_WindowBg] = ImVec4(0.055f, 0.105f, 0.125f, 0.99f);
    style.Colors[ImGuiCol_Header] = ImVec4(0.02f, 0.31f, 0.48f, 1.0f);
    style.Colors[ImGuiCol_HeaderHovered] = ImVec4(0.03f, 0.42f, 0.62f, 1.0f);
    style.Colors[ImGuiCol_HeaderActive] = ImVec4(0.02f, 0.36f, 0.54f, 1.0f);
    style.Colors[ImGuiCol_Button] = ImVec4(0.02f, 0.31f, 0.48f, 1.0f);
    if (!ImGui_ImplWin32_Init(desc.OutputWindow) ||
        !ImGui_ImplDX11_Init(device, context)) {
        club_player_screen_set_number_font(NULL);
        g_profile_number_font = NULL;
        ImGui_ImplDX11_Shutdown();
        ImGui_ImplWin32_Shutdown();
        ImGui::DestroyContext();
        context->Release();
        device->Release();
        InterlockedExchange(&g_imgui_init_attempted, 0);
        return false;
    }
    g_game_device = device;
    g_game_context = context;
    attach_overlay_window(desc.OutputWindow);
    InterlockedExchange(&g_imgui_ready, 1);
    overlay_log("in-process Direct3D overlay initialized");
    return true;
}

static float axis_value(SHORT value, bool positive)
{
    const SHORT deadzone = XINPUT_GAMEPAD_LEFT_THUMB_DEADZONE;
    int adjusted = value;
    if (positive ? adjusted <= deadzone : adjusted >= -deadzone) return 0.0f;
    if (positive) adjusted -= deadzone;
    else adjusted += deadzone;
    return (float)(positive ? adjusted : -adjusted) /
        (32767.0f - (float)deadzone);
}

static void update_gamepad_navigation(void)
{
    XINPUT_STATE state;
    ImGuiIO &io = ImGui::GetIO();
    ZeroMemory(&state, sizeof(state));
    if (!g_original_xinput_get_state ||
        g_original_xinput_get_state(0, &state) != ERROR_SUCCESS) {
        io.BackendFlags &= ~ImGuiBackendFlags_HasGamepad;
        return;
    }
    io.BackendFlags |= ImGuiBackendFlags_HasGamepad;
#define OVERLAY_BUTTON(key, button) \
    io.AddKeyEvent(key, (state.Gamepad.wButtons & (button)) != 0)
    OVERLAY_BUTTON(ImGuiKey_GamepadFaceDown, XINPUT_GAMEPAD_A);
    OVERLAY_BUTTON(ImGuiKey_GamepadFaceRight, XINPUT_GAMEPAD_B);
    OVERLAY_BUTTON(ImGuiKey_GamepadFaceLeft, XINPUT_GAMEPAD_X);
    OVERLAY_BUTTON(ImGuiKey_GamepadFaceUp, XINPUT_GAMEPAD_Y);
    OVERLAY_BUTTON(ImGuiKey_GamepadDpadLeft, XINPUT_GAMEPAD_DPAD_LEFT);
    OVERLAY_BUTTON(ImGuiKey_GamepadDpadRight, XINPUT_GAMEPAD_DPAD_RIGHT);
    OVERLAY_BUTTON(ImGuiKey_GamepadDpadUp, XINPUT_GAMEPAD_DPAD_UP);
    OVERLAY_BUTTON(ImGuiKey_GamepadDpadDown, XINPUT_GAMEPAD_DPAD_DOWN);
    OVERLAY_BUTTON(ImGuiKey_GamepadStart, XINPUT_GAMEPAD_START);
    OVERLAY_BUTTON(ImGuiKey_GamepadBack, XINPUT_GAMEPAD_BACK);
#undef OVERLAY_BUTTON
    io.AddKeyAnalogEvent(ImGuiKey_GamepadLStickLeft,
        axis_value(state.Gamepad.sThumbLX, false) > 0.0f,
        axis_value(state.Gamepad.sThumbLX, false));
    io.AddKeyAnalogEvent(ImGuiKey_GamepadLStickRight,
        axis_value(state.Gamepad.sThumbLX, true) > 0.0f,
        axis_value(state.Gamepad.sThumbLX, true));
    io.AddKeyAnalogEvent(ImGuiKey_GamepadLStickUp,
        axis_value(state.Gamepad.sThumbLY, true) > 0.0f,
        axis_value(state.Gamepad.sThumbLY, true));
    io.AddKeyAnalogEvent(ImGuiKey_GamepadLStickDown,
        axis_value(state.Gamepad.sThumbLY, false) > 0.0f,
        axis_value(state.Gamepad.sThumbLY, false));
}

/* The ranking is a read-only list: analog input scrolls the viewport while
 * the career club remains highlighted. D-pad moves by one row at a time. */
static void handle_ranking_gamepad(size_t row_count)
{
    XINPUT_STATE state;
    WORD buttons;
    WORD pressed;
    if (!row_count) {
        g_analog_scroll_axis = 0.0f;
        g_discrete_scroll_rows = 0;
        return;
    }
    ZeroMemory(&state, sizeof(state));
    if (!g_original_xinput_get_state ||
        g_original_xinput_get_state(0, &state) != ERROR_SUCCESS) {
        g_previous_gamepad_buttons = 0;
        g_analog_scroll_axis = 0.0f;
        return;
    }
    buttons = state.Gamepad.wButtons;
    pressed = (WORD)(buttons & ~g_previous_gamepad_buttons);
    g_analog_scroll_axis = axis_value(state.Gamepad.sThumbLY, true) -
        axis_value(state.Gamepad.sThumbLY, false);
    if (pressed & XINPUT_GAMEPAD_DPAD_UP) --g_discrete_scroll_rows;
    if (pressed & XINPUT_GAMEPAD_DPAD_DOWN) ++g_discrete_scroll_rows;
    g_previous_gamepad_buttons = buttons;
}

static void center_cell_item(float item_width, float item_height,
    float row_height)
{
    const ImGuiStyle &style = ImGui::GetStyle();
    ImVec2 cursor = ImGui::GetCursorPos();
    ImVec2 available = ImGui::GetContentRegionAvail();
    float x_offset = (available.x - item_width) * 0.5f;
    float y_offset = (row_height - 2.0f * style.CellPadding.y -
        item_height) * 0.5f;
    if (x_offset < 0.0f) x_offset = 0.0f;
    if (y_offset < 0.0f) y_offset = 0.0f;
    ImGui::SetCursorPos(ImVec2(cursor.x + x_offset,
        cursor.y + y_offset));
}

static void center_cell_text_y(float item_height, float row_height)
{
    const ImGuiStyle &style = ImGui::GetStyle();
    float y_offset = (row_height - 2.0f * style.CellPadding.y -
        item_height) * 0.5f;
    if (y_offset > 0.0f)
        ImGui::SetCursorPosY(ImGui::GetCursorPosY() + y_offset);
}

static void draw_ranking_overlay(void)
{
    ImGuiIO &io = ImGui::GetIO();
    ImVec2 panel_size = io.DisplaySize;
    std::vector<RankingOverlayRow> rows;
    LONG selected_row;

    AcquireSRWLockShared(&g_rows_lock);
    try {
        rows = g_rows;
    } catch (...) {
        rows.clear();
    }
    ReleaseSRWLockShared(&g_rows_lock);
    selected_row = InterlockedCompareExchange(&g_selected_row, 0, 0);

    ImGui::GetBackgroundDrawList()->AddRectFilled(ImVec2(0, 0),
        io.DisplaySize, IM_COL32(3, 21, 35, 190));
    ImGui::SetNextWindowPos(ImVec2(0, 0), ImGuiCond_Always);
    ImGui::SetNextWindowSize(io.DisplaySize, ImGuiCond_Always);
    ImGui::PushStyleVar(ImGuiStyleVar_WindowRounding, 0.0f);
    ImGui::PushStyleColor(ImGuiCol_WindowBg,
        ImVec4(0.0f, 0.0f, 0.0f, 0.0f));
    ImGui::Begin("##fifa16_rank_overlay_root", NULL,
        ImGuiWindowFlags_NoDecoration | ImGuiWindowFlags_NoMove |
        ImGuiWindowFlags_NoSavedSettings | ImGuiWindowFlags_NoBringToFrontOnFocus |
        ImGuiWindowFlags_NoBackground);
    ImGui::SetNextWindowPos(ImVec2(0.0f, 0.0f), ImGuiCond_Always);
    ImGui::SetNextWindowSize(panel_size, ImGuiCond_Always);
    ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding, ImVec2(0, 0));
    ImGui::PushStyleColor(ImGuiCol_WindowBg, ImVec4(0.78f, 0.80f, 0.80f, 1.0f));
    ImGui::PushStyleVar(ImGuiStyleVar_WindowBorderSize, 0.0f);
    ImGui::Begin("Ranking Mundial", NULL,
        ImGuiWindowFlags_NoTitleBar | ImGuiWindowFlags_NoResize |
        ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoCollapse |
        ImGuiWindowFlags_NoSavedSettings);

    ImDrawList *draw = ImGui::GetWindowDrawList();
    ImVec2 window_pos = ImGui::GetWindowPos();
    ImVec2 window_size = ImGui::GetWindowSize();
    ImVec2 title_end(window_pos.x + window_size.x, window_pos.y + 66.0f);
    draw->AddRectFilled(window_pos, title_end, IM_COL32(0, 82, 158, 255));
    draw->AddText(ImGui::GetFont(), ImGui::GetFont()->FontSize * 1.65f,
        ImVec2(window_pos.x + 30.0f, window_pos.y + 9.0f),
        IM_COL32(255, 255, 255, 255), "Ranking Mundial");
    draw->AddText(ImGui::GetFont(), ImGui::GetFont()->FontSize * 1.0f,
        ImVec2(window_pos.x + 33.0f, window_pos.y + 43.0f),
        IM_COL32(222, 235, 244, 255), "RANKING DE CLUBES  |  LISTA COMPLETA");

    if (rows.empty()) {
        ImGui::SetCursorPos(ImVec2(32.0f, 94.0f));
        ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(0.20f, 0.27f, 0.29f, 1.0f));
        ImGui::TextWrapped("Ainda nao recebi os dados do ranking desta carreira. "
            "Volte a Central, aguarde o card carregar e abra esta tela novamente.");
        ImGui::PopStyleColor();
    } else {
        char club_count[48];
        _snprintf_s(club_count, sizeof(club_count), _TRUNCATE,
            "%u clubes", (unsigned)rows.size());
        ImGui::SetCursorPos(ImVec2(32.0f, 78.0f));
        ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(0.22f, 0.30f, 0.32f, 1.0f));
        ImGui::TextUnformatted(club_count);
        ImGui::PopStyleColor();

        ImGui::SetCursorPos(ImVec2(26.0f, 106.0f));
        ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(0.21f, 0.29f, 0.32f, 1.0f));
        ImGui::PushStyleColor(ImGuiCol_TableHeaderBg,
            ImVec4(0.83f, 0.85f, 0.85f, 1.0f));
        ImGui::PushStyleVar(ImGuiStyleVar_CellPadding, ImVec2(10.0f, 5.0f));
        ImGui::PushStyleColor(ImGuiCol_TableBorderStrong,
            ImVec4(0.05f, 0.05f, 0.05f, 1.0f));
        ImGui::PushStyleColor(ImGuiCol_TableBorderLight,
            ImVec4(0.05f, 0.05f, 0.05f, 1.0f));
        const ImGuiTableFlags table_flags = ImGuiTableFlags_BordersOuter |
            ImGuiTableFlags_RowBg | ImGuiTableFlags_ScrollY |
            ImGuiTableFlags_SizingStretchProp | ImGuiTableFlags_NoPadOuterX;
        ImVec2 table_size(window_size.x - 52.0f, window_size.y - 174.0f);
        if (g_table_font) ImGui::PushFont(g_table_font);
        if (ImGui::BeginTable("##ranking_table", 4, table_flags, table_size)) {
            const float row_height = 40.0f;
            ImGui::TableSetupColumn("POS.", ImGuiTableColumnFlags_WidthFixed,
                72.0f);
            ImGui::TableSetupColumn("", ImGuiTableColumnFlags_WidthFixed,
                56.0f);
            ImGui::TableSetupColumn("CLUBE", ImGuiTableColumnFlags_WidthStretch);
            ImGui::TableSetupColumn("PONTUAÇÃO",
                ImGuiTableColumnFlags_WidthFixed, 118.0f);
            ImGui::TableSetupScrollFreeze(0, 1);
            ImGui::TableNextRow(ImGuiTableRowFlags_Headers, 36.0f);
            {
                const char *headers[] = { "POS.", "", "CLUBE",
                    "PONTUAÇÃO" };
                for (int column = 0; column < 4; ++column) {
                    ImGui::TableSetColumnIndex(column);
                    if (!headers[column][0]) continue;
                    ImVec2 text_size = ImGui::CalcTextSize(headers[column]);
                    if (column == 2)
                        center_cell_text_y(text_size.y, 36.0f);
                    else
                        center_cell_item(text_size.x, text_size.y, 36.0f);
                    ImGui::TextUnformatted(headers[column]);
                }
            }

            if (InterlockedExchange(&g_scroll_to_selected, 0)) {
                float body_height = table_size.y - 36.0f;
                float target = ((float)selected_row + 0.5f) * row_height -
                    body_height * 0.5f;
                ImGui::SetScrollY(target > 0.0f ? target : 0.0f);
            }
            {
                LONG discrete_rows = g_discrete_scroll_rows;
                g_discrete_scroll_rows = 0;
                float delta_time = io.DeltaTime;
                if (delta_time > 0.05f) delta_time = 0.05f;
                ImGui::SetScrollY(ImGui::GetScrollY() +
                    (float)discrete_rows * row_height -
                    g_analog_scroll_axis * 900.0f * delta_time);
            }

            ImGuiListClipper clipper;
            clipper.Begin((int)rows.size(), row_height);
            while (clipper.Step()) {
                for (int i = clipper.DisplayStart; i < clipper.DisplayEnd; ++i) {
                    const RankingOverlayRow &row = rows[(size_t)i];
                    const bool is_selected = i == selected_row;
                    const ImU32 row_color = is_selected
                        ? IM_COL32(128, 169, 166, 255)
                        : (i % 2 == 0 ? IM_COL32(202, 205, 205, 255)
                                      : IM_COL32(184, 188, 189, 255));
                    ImGui::TableNextRow(ImGuiTableRowFlags_None, row_height);
                    ImGui::TableSetBgColor(ImGuiTableBgTarget_RowBg0,
                        row_color);
                    ImGui::PushID(i);
                    ImGui::TableSetColumnIndex(0);
                    char rank_text[24];
                    _snprintf_s(rank_text, sizeof(rank_text), _TRUNCATE,
                        "%d", row.rank);
                    ImVec2 rank_size = ImGui::CalcTextSize(rank_text);
                    center_cell_item(rank_size.x, rank_size.y, row_height);
                    ImGui::TextUnformatted(rank_text);

                    ImGui::TableSetColumnIndex(1);
                    ID3D11ShaderResourceView *crest =
                        ranking_crest_texture(row.team_id);
                    const float crest_size = 27.0f;
                    center_cell_item(crest_size, crest_size, row_height);
                    if (crest) {
                        ImGui::Image((ImTextureID)(intptr_t)crest,
                            ImVec2(crest_size, crest_size));
                    } else ImGui::Dummy(ImVec2(27.0f, 27.0f));

                    ImGui::TableSetColumnIndex(2);
                    center_cell_text_y(ImGui::GetTextLineHeight(), row_height);
                    ImGui::TextUnformatted(row.name[0] ? row.name :
                        "Clube sem nome");

                    ImGui::TableSetColumnIndex(3);
                    char score[32];
                    _snprintf_s(score, sizeof(score), _TRUNCATE, "%d.%d",
                        row.score_tenths / 10, abs(row.score_tenths % 10));
                    ImVec2 score_size = ImGui::CalcTextSize(score);
                    center_cell_item(score_size.x, score_size.y, row_height);
                    ImGui::TextUnformatted(score);
                    ImGui::PopID();
                }
            }
            ImGui::EndTable();
        }
        if (g_table_font) ImGui::PopFont();
        ImGui::PopStyleColor(2);
        ImGui::PopStyleVar();
        ImGui::PopStyleColor(2);
    }

    ImDrawList *footer = ImGui::GetWindowDrawList();
    footer->AddRectFilled(ImVec2(window_pos.x,
        window_pos.y + window_size.y - 45.0f),
        ImVec2(window_pos.x + window_size.x, window_pos.y + window_size.y),
        IM_COL32(211, 214, 214, 255));
    footer->AddText(ImVec2(window_pos.x + 28.0f,
        window_pos.y + window_size.y - 31.0f), IM_COL32(55, 72, 77, 255),
        "DIRECIONAL / ANALÓGICO  NAVEGA   |   B / ESC  VOLTA");

    ImGui::End();
    ImGui::PopStyleVar();
    ImGui::PopStyleColor();
    ImGui::PopStyleVar();
    ImGui::End();
    ImGui::PopStyleColor();
    ImGui::PopStyleVar();
}

static bool ensure_render_target(IDXGISwapChain *chain)
{
    ID3D11Texture2D *back_buffer = NULL;
    HRESULT hr;
    if (g_render_target && g_render_target_chain == chain) return true;
    release_render_target();
    hr = chain->GetBuffer(0, __uuidof(ID3D11Texture2D),
        (void **)&back_buffer);
    if (FAILED(hr) || !back_buffer) return false;
    hr = g_game_device->CreateRenderTargetView(back_buffer, NULL,
        &g_render_target);
    back_buffer->Release();
    if (FAILED(hr) || !g_render_target) return false;
    g_render_target_chain = chain;
    return true;
}

static void ranking_screen_opened(void *)
{
    InterlockedExchange(&g_scroll_to_selected, 1);
    g_previous_gamepad_buttons = 0;
    g_analog_scroll_axis = 0.0f;
    g_discrete_scroll_rows = 0;
}

static void ranking_screen_draw(void *)
{
    handle_ranking_gamepad((size_t)InterlockedCompareExchange(&g_row_count, 0, 0));
    draw_ranking_overlay();
}

static bool register_builtin_screens(void)
{
    const ModOverlayScreen ranking = {"ranking", FIFA16_RANKING_CARD_ACTION_NAME,
        ranking_screen_opened, ranking_screen_draw, NULL, NULL};
    if (!mod_screen_register(&ranking)) return false;
    if (!club_player_screen_register(g_game_root, overlay_log))
        overlay_log("Club3D unavailable: existing ranking host remains enabled");
    if (!player_search_screen_register(g_game_root, overlay_log))
        overlay_log("Player search unavailable: existing screens remain enabled");
    if (!clubs_browser_register(g_game_root, overlay_log))
        overlay_log("Other clubs unavailable: existing screens remain enabled");
    if (!leagues_browser_register(g_game_root, overlay_log))
        overlay_log("Other leagues unavailable: existing screens remain enabled");
    if (!club_competitions_screen_register(g_game_root, overlay_log))
        overlay_log("Club competitions unavailable: existing screens remain enabled");
    if (!career_operations_register(g_game_root, overlay_log))
        overlay_log("CareerOps unavailable: existing screens remain enabled");
    if (!trophy_room_register(g_game_root, overlay_log))
        overlay_log("Trophy room unavailable: existing screens remain enabled");
    if (!sponsor_screen_register(g_game_root, overlay_log))
        overlay_log("Sponsors screen unavailable: existing screens remain enabled");
    if (!coach_profile_register(g_game_root, overlay_log))
        overlay_log("Coach profile unavailable: existing screens remain enabled");
    if (!next_match_register(g_game_root, overlay_log))
        overlay_log("Next match screen unavailable: existing screens remain enabled");
    return true;
}

static void poll_gamepad_shortcut(void)
{
    XINPUT_STATE state = {};
    const WORD chord = XINPUT_GAMEPAD_LEFT_SHOULDER |
        XINPUT_GAMEPAD_RIGHT_SHOULDER | XINPUT_GAMEPAD_BACK;
    bool down = g_original_xinput_get_state(0, &state) == ERROR_SUCCESS &&
        (state.Gamepad.wButtons & chord) == chord;
    if (!down) InterlockedExchange(&g_chord_down, 0);
    else if (InterlockedExchange(&g_chord_down, 1) == 0 && !mod_screen_captures_input())
        overlay_open("opened by Xbox LB+RB+View");
}

static void render_overlay(IDXGISwapChain *chain)
{
    ID3D11RenderTargetView *old_target = NULL;
    ID3D11DepthStencilView *old_depth = NULL;
    XINPUT_STATE controller;
    {
        DWORD now = GetTickCount();
        LONG previous = InterlockedCompareExchange(
            &g_xinput_last_scan_tick, 0, 0);
        if ((DWORD)(now - (DWORD)previous) >= 1000 &&
            InterlockedCompareExchange(&g_xinput_last_scan_tick,
                (LONG)now, previous) == previous)
            patch_xinput_import();
    }
    if (g_overlay_enabled) {
        poll_gamepad_shortcut();
        if (GetAsyncKeyState(VK_F10) & 0x8000)
            overlay_f10_pressed();
        else
            InterlockedExchange(&g_f10_down, 0);
    }
    if ((DWORD)(GetTickCount() - g_card_action_scan_tick) >= 1000) {
        g_card_action_scan_tick = GetTickCount();
        try_install_native_ranking_card_action();
    }
    poll_career_page_for_diagnostics();
    if (InterlockedExchange(&g_close_requested, 0))
        overlay_close("closed; game input focus restored", 0);
    mod_screen_sync_lifecycle();
    if (!mod_screen_is_open()) {
        finish_modal_input_session();
        return;
    }
    g_modal_input_session = true;
    if (!ensure_imgui(chain) || !ensure_render_target(chain)) return;
    club_player_screen_set_device(g_game_device);
    player_search_screen_set_device(g_game_device);
    clubs_browser_device(g_game_device);
    leagues_browser_device(g_game_device);
    club_competitions_screen_device(g_game_device);
    trophy_room_device(g_game_device);
    sponsor_screen_device(g_game_device);
    coach_profile_device(g_game_device);
    next_match_device(g_game_device);
    career_operations_device(g_game_device);
    ZeroMemory(&controller, sizeof(controller));
    if (mod_screen_is_active("ranking") && g_original_xinput_get_state &&
        g_original_xinput_get_state(0, &controller) == ERROR_SUCCESS &&
        (controller.Gamepad.wButtons & XINPUT_GAMEPAD_B)) {
        overlay_close("closed by Xbox B; game input focus restored",
            XINPUT_GAMEPAD_B);
        return;
    }
    ImGui_ImplDX11_NewFrame();
    ImGui_ImplWin32_NewFrame();
    update_gamepad_navigation(); /* raw feed, not the game's filtered export */
    {
        ImGuiIO &io = ImGui::GetIO();
        POINT mouse;
        io.MouseDrawCursor = GetSystemMetrics(SM_MOUSEPRESENT) != 0;
        if (GetForegroundWindow() == g_game_window && GetCursorPos(&mouse) &&
            ScreenToClient(g_game_window, &mouse))
            io.AddMousePosEvent((float)mouse.x, (float)mouse.y);
    }
    ImGui::NewFrame();
    ImGui::SetMouseCursor(ImGuiMouseCursor_Arrow);
    mod_screen_draw();
    if (ImGui::IsKeyPressed(ImGuiKey_Escape, false))mod_screen_request_back();
    ImGui::Render();
    g_game_context->OMGetRenderTargets(1, &old_target, &old_depth);
    g_game_context->OMSetRenderTargets(1, &g_render_target, NULL);
    ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData());
    g_game_context->OMSetRenderTargets(1, &old_target, old_depth);
    if (old_target) old_target->Release();
    if (old_depth) old_depth->Release();
}

static HRESULT WINAPI overlay_present(IDXGISwapChain *chain,
    UINT sync_interval, UINT flags)
{
    if (g_original_present) {
        attach_overlay_window_from_chain(chain);
        render_overlay(chain);
    }
    return g_original_present
        ? g_original_present(chain, sync_interval, flags) : S_OK;
}

static HRESULT WINAPI overlay_present1(IDXGISwapChain1 *chain,
    UINT sync_interval, UINT present_flags,
    const DXGI_PRESENT_PARAMETERS *parameters)
{
    if (g_original_present1) {
        attach_overlay_window_from_chain((IDXGISwapChain *)chain);
        render_overlay((IDXGISwapChain *)chain);
    }
    return g_original_present1
        ? g_original_present1(chain, sync_interval, present_flags, parameters)
        : S_OK;
}

static HRESULT WINAPI overlay_resize_buffers(IDXGISwapChain *chain,
    UINT buffer_count, UINT width, UINT height, DXGI_FORMAT format,
    UINT swap_chain_flags)
{
    if (chain == g_render_target_chain) release_render_target();
    return g_original_resize_buffers
        ? g_original_resize_buffers(chain, buffer_count, width, height,
            format, swap_chain_flags)
        : E_FAIL;
}

extern "C" DWORD WINAPI ranking_overlay_start_thread(void *parameter)
{
    (void)parameter;
    if (InterlockedCompareExchange(&g_start_once, 1, 0) != 0) return 0;
    overlay_set_paths();
    ranking_input_set_logger(overlay_log);
    if (!g_overlay_enabled) {
        overlay_log("overlay disabled by ranking_overlay.ini");
        return 0;
    }
    if (!register_builtin_screens()) {
        overlay_log("failed to register built-in mod screens; overlay not started");
        return 1;
    }
    overlay_log("ranking overlay worker started");
    patch_xinput_import();
    bool present_ready = false;
    for (int attempt = 0; attempt < 120; ++attempt) {
        try_install_native_ranking_card_action();
        if (!present_ready) present_ready = install_present_hooks();
        if (present_ready &&
            InterlockedCompareExchange(&g_card_action_hook_state, 0, 0) != 0)
            return 0;
        Sleep(500);
    }
    if (!present_ready) {
        overlay_log("Direct3D Present hook installation failed after 120 attempts");
        return 1;
    }
    overlay_log("native ranking card command still pending; retrying during game frames");
    return 0;
}
