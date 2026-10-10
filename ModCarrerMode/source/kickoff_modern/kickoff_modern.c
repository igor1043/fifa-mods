#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>

#define MOD_API_VERSION 1U
#define IMAGE_TIMESTAMP 0x577DE45CU
#define MIN_IMAGE_SIZE 0x9524000U
#define MAX_IMAGE_SIZE 0x9525000U
#define KICKOFF_FUNCTION_RVA 0x052E5860U
#define SCALE_RVA 0x033EE264U
#define ANGLE_RVA 0x033EE268U
#define ANGLE_DELTA_RVA 0x033EE26CU
#define RETRY_COUNT 300U
#define RETRY_DELAY_MS 200U

static const unsigned char kickoff_function_signature[16] = {
    0x48,0x89,0x5C,0x24,0x18,0x57,0x48,0x83,
    0xEC,0x50,0x48,0x8B,0x05,0xEF,0x2B,0xFB
};

static volatile LONG started;
static uintptr_t image_base;
static char log_path[MAX_PATH];

static void log_event(const char *format, ...)
{
    FILE *file = NULL;
    SYSTEMTIME now;
    va_list args;
    if (!log_path[0] || fopen_s(&file, log_path, "ab") != 0 || !file)
        return;
    GetLocalTime(&now);
    fprintf(file, "%04u-%02u-%02u %02u:%02u:%02u ", now.wYear,
        now.wMonth, now.wDay, now.wHour, now.wMinute, now.wSecond);
    va_start(args, format);
    vfprintf(file, format, args);
    va_end(args);
    fputs("\r\n", file);
    fclose(file);
}

static BOOL read_memory(uintptr_t address, void *out, SIZE_T size)
{
    SIZE_T received = 0;
    return address && out && size &&
        ReadProcessMemory(GetCurrentProcess(), (const void *)address,
            out, size, &received) && received == size;
}

static BOOL supported_image(void)
{
    IMAGE_DOS_HEADER dos;
    IMAGE_NT_HEADERS64 nt;
    image_base = (uintptr_t)GetModuleHandleA(NULL);
    if (!image_base || !read_memory(image_base, &dos, sizeof(dos)) ||
        dos.e_magic != IMAGE_DOS_SIGNATURE || dos.e_lfanew < 0 ||
        dos.e_lfanew > 0x1000 ||
        !read_memory(image_base + (uintptr_t)dos.e_lfanew, &nt, sizeof(nt)))
        return FALSE;
    return nt.Signature == IMAGE_NT_SIGNATURE &&
        nt.FileHeader.Machine == IMAGE_FILE_MACHINE_AMD64 &&
        nt.FileHeader.TimeDateStamp == IMAGE_TIMESTAMP &&
        nt.OptionalHeader.Magic == IMAGE_NT_OPTIONAL_HDR64_MAGIC &&
        nt.OptionalHeader.SizeOfImage >= MIN_IMAGE_SIZE &&
        nt.OptionalHeader.SizeOfImage <= MAX_IMAGE_SIZE;
}

static BOOL patch_backpass_candidate(void)
{
    unsigned char code[sizeof(kickoff_function_signature)];
    float scale = 0.0f, angle = 0.0f, delta = 0.0f;
    const float expected_scale = 4.0f;
    const float expected_angle = 1.57079637f;
    const float expected_delta = 0.17453292f;
    const float replacement = 4.71238898f;
    uintptr_t scale_address, angle_address, delta_address;
    DWORD previous = 0, ignored = 0;
    LONG desired_bits = 0, actual_bits;
    LONG expected_bits = 0;
    BOOL flushed, restored;

    if (!supported_image()) return FALSE;
    if (!read_memory(image_base + KICKOFF_FUNCTION_RVA, code, sizeof(code)) ||
        memcmp(code, kickoff_function_signature, sizeof(code)) != 0)
        return FALSE;

    scale_address = image_base + SCALE_RVA;
    angle_address = image_base + ANGLE_RVA;
    delta_address = image_base + ANGLE_DELTA_RVA;
    if (!read_memory(scale_address, &scale, sizeof(scale)) ||
        !read_memory(angle_address, &angle, sizeof(angle)) ||
        !read_memory(delta_address, &delta, sizeof(delta)) ||
        memcmp(&scale, &expected_scale, sizeof(scale)) != 0 ||
        memcmp(&delta, &expected_delta, sizeof(delta)) != 0)
        return FALSE;
    if (memcmp(&angle, &expected_angle, sizeof(angle)) != 0 &&
        memcmp(&angle, &replacement, sizeof(angle)) != 0)
        return FALSE;
    if (memcmp(&angle, &replacement, sizeof(angle)) == 0) {
        log_event("already_patched angle=%.8f kickoff_target_rotated_degrees=180 receiver_position_changed=0",
            (double)angle);
        return TRUE;
    }

    memcpy(&desired_bits, &replacement, sizeof(replacement));
    memcpy(&expected_bits, &expected_angle, sizeof(expected_angle));
    if (!VirtualProtect((void *)angle_address, sizeof(float),
            PAGE_EXECUTE_READWRITE, &previous))
        return FALSE;
    actual_bits = InterlockedExchange((volatile LONG *)angle_address,
        desired_bits);
    flushed = FlushInstructionCache(GetCurrentProcess(),
        (const void *)angle_address, sizeof(float));
    restored = VirtualProtect((void *)angle_address, sizeof(float),
        previous, &ignored);
    if (!flushed || !restored || actual_bits != expected_bits ||
        !read_memory(angle_address, &angle, sizeof(angle)) ||
        memcmp(&angle, &replacement, sizeof(angle)) != 0)
        return FALSE;

    log_event("installed build_timestamp=0x%08lX kickoff_target_angle=%.8f previous=%.8f delta=%.8f target_rotation_degrees=180 receiver_position_changed=0 first_pass_behavior_unverified=1",
        (unsigned long)IMAGE_TIMESTAMP, (double)replacement,
        (double)expected_angle, (double)delta);
    return TRUE;
}

static DWORD WINAPI worker(LPVOID unused)
{
    unsigned int attempt;
    (void)unused;
    for (attempt = 0; attempt < RETRY_COUNT; ++attempt) {
        if (patch_backpass_candidate()) return 0;
        Sleep(RETRY_DELAY_MS);
    }
    log_event("not_installed build_or_kickoff_signature_mismatch; game_memory_unchanged=1");
    return 0;
}

__declspec(dllexport) unsigned int WINAPI Fifa16ModGetApiVersion(void)
{
    return MOD_API_VERSION;
}

__declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char *mods_root)
{
    HANDLE thread;
    HMODULE pinned = NULL;
    char logs_dir[MAX_PATH];
    if (!mods_root || !mods_root[0]) return FALSE;
    if (InterlockedCompareExchange(&started, 1, 0) != 0) return TRUE;
    if (_snprintf_s(logs_dir, sizeof(logs_dir), _TRUNCATE,
            "%s\\..\\logs", mods_root) < 0 ||
        _snprintf_s(log_path, sizeof(log_path), _TRUNCATE,
            "%s\\kickoff_modern.log", logs_dir) < 0) {
        InterlockedExchange(&started, 0);
        return FALSE;
    }
    CreateDirectoryA(logs_dir, NULL);
    log_event("candidate_start build_sha256=889772d3192c74ce4c1f2b7b3467cc96f9f1123aaf347bce7b199333dbac7a9d mode=reverse_existing_kickoff_target receiver_position_changed=0");
    if (!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
            GET_MODULE_HANDLE_EX_FLAG_PIN, (LPCSTR)&started, &pinned)) {
        log_event("not_installed module_lifetime_pin_failed error=%lu",
            GetLastError());
        InterlockedExchange(&started, 0);
        return FALSE;
    }
    thread = CreateThread(NULL, 0, worker, NULL, 0, NULL);
    if (!thread) {
        log_event("not_installed worker_create_failed error=%lu", GetLastError());
        InterlockedExchange(&started, 0);
        return FALSE;
    }
    CloseHandle(thread);
    return TRUE;
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) DisableThreadLibraryCalls(instance);
    return TRUE;
}
