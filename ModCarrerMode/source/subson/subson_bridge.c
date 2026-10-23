#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <bcrypt.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#include "subson_friendly.h"

/* Keep FIFA Friends' dinput8.dll and its L9 chain unchanged. Load the exact
 * WorkLab payload under a distinct root name, through the existing mod API.
 * WorkLab resolves SubsOn.ini beside its own DLL and patches from DllMain.
 */
static volatile LONG started;
static HMODULE payload;
static char log_path[MAX_PATH];
static const unsigned char expected_sha256[32] = {
    0xc6,0x6e,0xe4,0xe6,0x4a,0x48,0x23,0xc9,0x9b,0x5f,0x3a,0x74,0xa7,0xb5,0xa4,0xe5,
    0x85,0x37,0x13,0x0b,0xf8,0x10,0x49,0x2e,0x34,0xd6,0xd3,0x47,0x10,0xdd,0xed,0x77
};

static void log_event(const char *message)
{
    FILE *file = NULL;
    if (log_path[0] && fopen_s(&file, log_path, "ab") == 0 && file) {
        fprintf(file, "reference_only pid=%lu %s\r\n", GetCurrentProcessId(), message);
        fclose(file);
    }
}

static int verify_payload(const wchar_t *path)
{
    BCRYPT_ALG_HANDLE alg = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    unsigned char buffer[4096], digest[32];
    LARGE_INTEGER size;
    DWORD received;
    int ok = 0;
    HANDLE file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL,
        OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) return 0;
    if (!GetFileSizeEx(file, &size) || size.QuadPart != 49664) goto done;
    if (BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, NULL, 0) < 0)
        goto done;
    if (BCryptCreateHash(alg, &hash, NULL, 0, NULL, 0, 0) < 0) goto done;
    do {
        if (!ReadFile(file, buffer, sizeof(buffer), &received, NULL)) goto done;
        if (received && BCryptHashData(hash, buffer, received, 0) < 0) goto done;
    } while (received);
    if (BCryptFinishHash(hash, digest, sizeof(digest), 0) >= 0)
        ok = memcmp(digest, expected_sha256, sizeof(digest)) == 0;
done:
    if (hash) BCryptDestroyHash(hash);
    if (alg) BCryptCloseAlgorithmProvider(alg, 0);
    CloseHandle(file);
    return ok;
}

static int valid_options(const wchar_t *path, unsigned *configured)
{
    FILE *file = NULL;
    char line[512];
    int bench = -1, minimum = -1, bench_seen = 0, minimum_seen = 0, ok = 1;
    if (_wfopen_s(&file, path, L"rb") != 0 || !file) return 0;
    while (fgets(line, sizeof(line), file)) {
        char *key = line, *equal, *end, *value;
        long parsed;
        while (*key == ' ' || *key == '\t') ++key;
        if (*key == ';' || *key == '#' || *key == '\r' || *key == '\n' || !*key)
            continue;
        equal = strchr(key, '=');
        if (!equal) { ok = 0; break; }
        *equal = '\0';
        end = equal;
        while (end > key && (end[-1] == ' ' || end[-1] == '\t')) *--end = '\0';
        value = equal + 1;
        parsed = strtol(value, &end, 10);
        if (end == value) { ok = 0; break; }
        while (*end == ' ' || *end == '\t' || *end == '\r' || *end == '\n') ++end;
        if (*end && *end != ';' && *end != '#') { ok = 0; break; }
        if (_stricmp(key, "BENCH_SIZE") == 0) {
            if (bench_seen++ || parsed < 7 || parsed > 12) { ok = 0; break; }
            bench = (int)parsed;
        } else if (_stricmp(key, "MIN_PLAYERS") == 0) {
            if (minimum_seen++ || (parsed != 0 && (parsed < 11 || parsed > 30))) {
                ok = 0; break;
            }
            minimum = (int)parsed;
        } else { ok = 0; break; }
    }
    if (ferror(file)) ok = 0;
    fclose(file);
    if (ok && bench >= 7 && minimum >= 0 && bench_seen == 1 && minimum_seen == 1) {
        *configured=(unsigned)bench;
        return 1;
    }
    return 0;
}

__declspec(dllexport) unsigned int WINAPI Fifa16ModGetApiVersion(void)
{ return 1U; }

__declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char *mods_root)
{
    wchar_t root[MAX_PATH], path[MAX_PATH], options[MAX_PATH], *slash;
    DWORD length;
    unsigned configured=0;
    if (!mods_root || !mods_root[0]) return FALSE;
    if (InterlockedCompareExchange(&started, 1, 0) != 0) return payload != NULL;
    _snprintf_s(log_path, sizeof(log_path), _TRUNCATE,
        "%s\\..\\logs\\subson_integration.log", mods_root);
    if (GetModuleHandleA("bench_native12.dll")) {
        log_event("blocked: bench_native12 already loaded; remove its enabled.txt entry and restart");
        goto failed;
    }
    length = GetModuleFileNameW(NULL, root, MAX_PATH);
    if (!length || length >= MAX_PATH) goto failed;
    slash = wcsrchr(root, L'\\');
    if (!slash) goto failed;
    *slash = L'\0';
    if (_snwprintf_s(path, MAX_PATH, _TRUNCATE, L"%s\\SubsOn.dll", root) < 0 ||
        _snwprintf_s(options, MAX_PATH, _TRUNCATE, L"%s\\SubsOn.ini", root) < 0)
        goto failed;
    if (!valid_options(options,&configured)) {
        log_event("blocked: SubsOn.ini requires BENCH_SIZE=7..12 and MIN_PLAYERS=0 or 11..30");
        goto failed;
    }
    if (!verify_payload(path)) {
        log_event("blocked: SubsOn.dll differs from the verified WorkLab payload");
        goto failed;
    }
    payload = LoadLibraryExW(path, NULL,
        LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32);
    if (!payload) {
        log_event("failed: could not load root SubsOn.dll");
        goto failed;
    }
    /* Keep the LoadLibrary reference for the entire process: WorkLab starts
     * background workers. Its own log reports whether patches were applied.
     */
    log_event("loaded original WorkLab payload; friendly rule adapter v2; career optional bench v1; rendering and animations=WorkLab");
    if(!subson_friendly_start(configured,log_path)){log_event("failed to start friendly rule adapter");return FALSE;}
    if(!subson_career_start(configured,log_path)){log_event("failed to start career bench adapter");return FALSE;}
    return TRUE;
failed:
    InterlockedExchange(&started, 0);
    return FALSE;
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) DisableThreadLibraryCalls(instance);
    return TRUE;
}
