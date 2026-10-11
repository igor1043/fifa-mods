#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include "fifa16_mod_api.h"

#define SCAN_CHUNK_BYTES (1024U * 1024U)
#define RESCAN_DELAY_MS 15000U
#define SCAN_WINDOW_MS 600000ULL
#define NOTICE_STABILITY_MS 1250ULL

static const unsigned char notice_text[] =
    "Pedimos desculpas, mas os servidores deste jogo foram desligados. "
    "Muito obrigado por jogar!";

static volatile LONG started;
static char log_path[MAX_PATH];

typedef struct NoticeMatch {
    uintptr_t address;
    BOOL wide;
} NoticeMatch;

static void write_log(const char *format, ...)
{
    FILE *file = NULL;
    SYSTEMTIME now;
    va_list args;

    if (!log_path[0] || fopen_s(&file, log_path, "ab") != 0 || !file)
        return;
    GetLocalTime(&now);
    fprintf(file, "%04u-%02u-%02u %02u:%02u:%02u pid=%lu ",
        now.wYear, now.wMonth, now.wDay, now.wHour, now.wMinute,
        now.wSecond, GetCurrentProcessId());
    va_start(args, format);
    vfprintf(file, format, args);
    va_end(args);
    fputs("\r\n", file);
    fclose(file);
}

static BOOL readable_region(const MEMORY_BASIC_INFORMATION *info)
{
    DWORD protection;

    if (!info || info->State != MEM_COMMIT || info->Type != MEM_PRIVATE ||
        (info->Protect & (PAGE_GUARD | PAGE_NOACCESS)))
        return FALSE;

    protection = info->Protect & 0xFFU;
    return protection == PAGE_READONLY ||
        protection == PAGE_READWRITE ||
        protection == PAGE_WRITECOPY ||
        protection == PAGE_EXECUTE_READ ||
        protection == PAGE_EXECUTE_READWRITE ||
        protection == PAGE_EXECUTE_WRITECOPY;
}

static BOOL find_pattern(const unsigned char *bytes, SIZE_T length,
    uintptr_t base, NoticeMatch *match)
{
    const SIZE_T text_length = sizeof(notice_text) - 1U;
    SIZE_T index;

    if (!bytes || !match)
        return FALSE;

    if (length >= text_length) {
        for (index = 0; index <= length - text_length; ++index) {
            if (bytes[index] == notice_text[0] &&
                memcmp(bytes + index, notice_text, text_length) == 0) {
                match->address = base + index;
                match->wide = FALSE;
                return TRUE;
            }
        }
    }

    if (length >= text_length * 2U) {
        for (index = 0; index <= length - text_length * 2U; ++index) {
            SIZE_T character;
            if (bytes[index] != notice_text[0] || bytes[index + 1U] != 0)
                continue;
            for (character = 0; character < text_length; ++character) {
                if (bytes[index + character * 2U] != notice_text[character] ||
                    bytes[index + character * 2U + 1U] != 0)
                    break;
            }
            if (character == text_length) {
                match->address = base + index;
                match->wide = TRUE;
                return TRUE;
            }
        }
    }
    return FALSE;
}

static BOOL search_region(uintptr_t region_start, uintptr_t region_end,
    unsigned char *buffer, NoticeMatch *match)
{
    const SIZE_T text_length = sizeof(notice_text) - 1U;
    SIZE_T carry = 0;
    uintptr_t cursor = region_start;
    SYSTEM_INFO system_info;
    uintptr_t page_size;

    GetSystemInfo(&system_info);
    page_size = system_info.dwPageSize ? system_info.dwPageSize : 4096U;

    while (cursor < region_end) {
        SIZE_T wanted = (SIZE_T)(region_end - cursor);
        SIZE_T received = 0;
        SIZE_T available;

        if (wanted > SCAN_CHUNK_BYTES)
            wanted = SCAN_CHUNK_BYTES;
        if (ReadProcessMemory(GetCurrentProcess(), (const void *)cursor,
                buffer + carry, wanted, &received) == FALSE && received == 0) {
            uintptr_t advance = page_size;
            carry = 0;
            if (advance > region_end - cursor)
                advance = (uintptr_t)(region_end - cursor);
            cursor += advance;
            continue;
        }
        if (!received) {
            carry = 0;
            cursor += (uintptr_t)(wanted < page_size ? wanted : page_size);
            continue;
        }

        available = carry + received;
        if (find_pattern(buffer, available, cursor - carry, match))
            return TRUE;

        cursor += received;
        carry = available < text_length * 2U
            ? available : text_length * 2U - 1U;
        memmove(buffer, buffer + available - carry, carry);
    }
    return FALSE;
}

static BOOL find_notice(NoticeMatch *match)
{
    SYSTEM_INFO system_info;
    MEMORY_BASIC_INFORMATION info;
    uintptr_t cursor;
    uintptr_t maximum;
    unsigned char *buffer;
    BOOL found = FALSE;

    if (!match)
        return FALSE;

    GetSystemInfo(&system_info);
    cursor = 0x10000U;
    maximum = (uintptr_t)system_info.lpMaximumApplicationAddress;
    buffer = (unsigned char *)HeapAlloc(GetProcessHeap(), 0,
        SCAN_CHUNK_BYTES + sizeof(notice_text) * 2U);
    if (!buffer)
        return FALSE;

    while (cursor < maximum) {
        SIZE_T queried = VirtualQuery((const void *)cursor, &info, sizeof(info));
        uintptr_t base;
        uintptr_t end;

        if (!queried)
            break;
        base = (uintptr_t)info.BaseAddress;
        if (info.RegionSize > UINTPTR_MAX - base)
            break;
        end = base + info.RegionSize;
        if (end <= cursor)
            break;
        if (readable_region(&info) &&
            search_region(cursor, end, buffer, match)) {
            found = TRUE;
            break;
        }
        cursor = end;
    }
    HeapFree(GetProcessHeap(), 0, buffer);
    return found;
}

static BOOL notice_still_at(const NoticeMatch *match)
{
    const SIZE_T text_length = sizeof(notice_text) - 1U;
    unsigned char local[sizeof(notice_text) * 2U];
    SIZE_T received = 0;
    SIZE_T index;
    SIZE_T bytes_to_read;

    if (!match || !match->address)
        return FALSE;
    bytes_to_read = match->wide ? text_length * 2U : text_length;
    if (!ReadProcessMemory(GetCurrentProcess(),
            (const void *)match->address, local, bytes_to_read, &received) ||
        received != bytes_to_read)
        return FALSE;
    if (!match->wide)
        return memcmp(local, notice_text, text_length) == 0;

    for (index = 0; index < text_length; ++index) {
        if (local[index * 2U] != notice_text[index] ||
            local[index * 2U + 1U] != 0)
            return FALSE;
    }
    return TRUE;
}

static BOOL game_is_foreground(void)
{
    HWND window = GetForegroundWindow();
    DWORD process_id = 0;

    if (!window)
        return FALSE;
    GetWindowThreadProcessId(window, &process_id);
    return process_id == GetCurrentProcessId();
}

static BOOL send_confirm_once(void)
{
    INPUT input[2];

    if (!game_is_foreground())
        return FALSE;
    ZeroMemory(input, sizeof(input));
    input[0].type = INPUT_KEYBOARD;
    input[0].ki.wVk = VK_RETURN;
    input[1] = input[0];
    input[1].ki.dwFlags = KEYEVENTF_KEYUP;
    return SendInput(2, input, sizeof(input[0])) == 2;
}

static DWORD WINAPI worker(void *unused)
{
    ULONGLONG deadline = GetTickCount64() + SCAN_WINDOW_MS;
    NoticeMatch match;
    ULONGLONG first_seen = 0;
    BOOL have_match = FALSE;

    (void)unused;
    ZeroMemory(&match, sizeof(match));
    write_log("started; waiting for exact server-shutdown notice");

    while (GetTickCount64() < deadline) {
        if (!have_match) {
            if (!game_is_foreground()) {
                Sleep(1000U);
                continue;
            }
            ZeroMemory(&match, sizeof(match));
            if (!find_notice(&match)) {
                Sleep(RESCAN_DELAY_MS);
                continue;
            }
            have_match = TRUE;
            first_seen = GetTickCount64();
            write_log("notice found address=%p encoding=%s",
                (void *)match.address, match.wide ? "utf16" : "ascii");
            continue;
        }

        if (!notice_still_at(&match)) {
            write_log("notice text disappeared before confirmation");
            have_match = FALSE;
            Sleep(1000U);
            continue;
        }

        if (GetTickCount64() - first_seen >= NOTICE_STABILITY_MS &&
            game_is_foreground()) {
            if (send_confirm_once())
                write_log("one Enter confirmation sent to foreground FIFA");
            else
                write_log("confirmation input was not accepted");
            return 0;
        }
        Sleep(250U);
    }

    write_log("notice not confirmed within startup scan window");
    return 0;
}

__declspec(dllexport) unsigned WINAPI Fifa16ModGetApiVersion(void)
{
    return FIFA16_MOD_API_VERSION;
}

__declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char *mods_root)
{
    char module_root[MAX_PATH];
    char *slash;
    HANDLE thread;
    HMODULE pinned;

    if (!mods_root || strlen(mods_root) >= sizeof(module_root) - 8U)
        return FALSE;
    if (InterlockedCompareExchange(&started, 1, 0))
        return TRUE;

    strcpy_s(module_root, sizeof(module_root), mods_root);
    slash = strrchr(module_root, '\\');
    if (!slash)
        return FALSE;
    *slash = '\0';
    if (_snprintf_s(log_path, sizeof(log_path), _TRUNCATE,
            "%s\\logs\\skip_server_shutdown_notice.log", module_root) < 0)
        return FALSE;

    if (!GetModuleHandleExA(
            GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
            GET_MODULE_HANDLE_EX_FLAG_PIN,
            (LPCSTR)&started, &pinned))
        return FALSE;
    thread = CreateThread(NULL, 0, worker, NULL, 0, NULL);
    if (!thread)
        return FALSE;
    CloseHandle(thread);
    return TRUE;
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH)
        DisableThreadLibraryCalls(instance);
    return TRUE;
}
