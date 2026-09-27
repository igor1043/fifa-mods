#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "native/retirement_engine.h"

static const char *argument_value(int argc, char **argv, const char *name)
{
    int index;
    for (index = 1; index + 1 < argc; ++index) {
        if (_stricmp(argv[index], name) == 0)
            return argv[index + 1];
    }
    return NULL;
}

static int parse_unsigned(const char *value, unsigned long *result)
{
    char *end = NULL;
    unsigned long parsed;
    if (!value || !*value || !result) return 0;
    parsed = strtoul(value, &end, 10);
    if (end == value || *end != '\0') return 0;
    *result = parsed;
    return 1;
}

static int parse_process_id(const char *value, DWORD *result)
{
    unsigned long parsed;
    if (!parse_unsigned(value, &parsed) || parsed == 0UL
        || parsed > 0xFFFFFFFFUL)
        return 0;
    *result = (DWORD)parsed;
    return 1;
}

static int wait_for_parent_exit(DWORD process_id)
{
    HANDLE process;
    if (!process_id) return 1;
    process = OpenProcess(SYNCHRONIZE, FALSE, process_id);
    if (!process) {
        /* The parent may already have exited between CreateProcess and this
         * call.  There is no process handle to wait on in that case. */
        return GetLastError() == ERROR_INVALID_PARAMETER;
    }
    (void)WaitForSingleObject(process, INFINITE);
    CloseHandle(process);
    return 1;
}

static int read_file_state(const char *path, ULONGLONG *size,
    ULONGLONG *write_time)
{
    WIN32_FILE_ATTRIBUTE_DATA attributes;
    ULARGE_INTEGER file_size;
    ULARGE_INTEGER timestamp;
    if (!path || !size || !write_time
        || !GetFileAttributesExA(path, GetFileExInfoStandard, &attributes))
        return 0;
    file_size.LowPart = attributes.nFileSizeLow;
    file_size.HighPart = attributes.nFileSizeHigh;
    timestamp.LowPart = attributes.ftLastWriteTime.dwLowDateTime;
    timestamp.HighPart = attributes.ftLastWriteTime.dwHighDateTime;
    *size = file_size.QuadPart;
    *write_time = timestamp.QuadPart;
    return 1;
}

static int can_open_exclusive(const char *path)
{
    HANDLE file;
    if (!path || !*path) return 0;
    file = CreateFileA(path, GENERIC_READ, 0, NULL, OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) return 0;
    CloseHandle(file);
    return 1;
}

static int wait_for_stable_data(const char *path, unsigned quiet_ms)
{
    ULONGLONG last_size = 0;
    ULONGLONG last_write_time = 0;
    ULONGLONG last_index_size = 0;
    ULONGLONG last_index_write_time = 0;
    unsigned stable_ms = 0;
    unsigned waited_ms = 0;
    char index_path[2048];
    char *slash;
    lstrcpynA(index_path, path, sizeof(index_path));
    slash = strrchr(index_path, '\\');
    if (!slash) return 0;
    lstrcpyA(slash + 1, "INDEX");
    if (quiet_ms < 1000U) quiet_ms = 2500U;
    if (quiet_ms > 10000U) quiet_ms = 10000U;
    while (waited_ms < 120000U) {
        ULONGLONG size;
        ULONGLONG write_time;
        ULONGLONG index_size;
        ULONGLONG index_write_time;
        if (read_file_state(path, &size, &write_time)
            && read_file_state(index_path, &index_size, &index_write_time)
            && size >= 1024ULL * 1024ULL
            && can_open_exclusive(path)
            && can_open_exclusive(index_path)) {
            if (size == last_size && write_time == last_write_time
                && index_size == last_index_size
                && index_write_time == last_index_write_time)
                stable_ms += 250U;
            else {
                last_size = size;
                last_write_time = write_time;
                last_index_size = index_size;
                last_index_write_time = index_write_time;
                stable_ms = 0;
            }
            if (stable_ms >= quiet_ms) return 1;
        } else {
            last_size = 0;
            last_write_time = 0;
            last_index_size = 0;
            last_index_write_time = 0;
            stable_ms = 0;
        }
        Sleep(250U);
        waited_ms += 250U;
    }
    return 0;
}

static void print_result(const char *path, const RetirementApplyResult *result)
{
    printf("status=%d message=%s changed=%u retiring=%u crc_before=%08X "
           "crc_after=%08X data=%s backup_data=%s backup_index=%s\n",
        result->status, result->message, result->players_changed,
        result->players_retiring, result->crc_before, result->crc_after,
        path ? path : "", result->backup_data, result->backup_index);
}

int main(int argc, char **argv)
{
    const char *pid_text = argument_value(argc, argv, "--pid");
    const char *data_path = argument_value(argc, argv, "--data");
    const char *mode = argument_value(argc, argv, "--mode");
    const char *age_text = argument_value(argc, argv, "--age");
    const char *quiet_text = argument_value(argc, argv, "--quiet-ms");
    const char *mod_dir = argument_value(argc, argv, "--mod-dir");
    int wait_parent = argument_value(argc, argv, "--wait-parent-exit") != NULL;
    DWORD process_id;
    unsigned long age_value = 18UL;
    unsigned long quiet_value = 2500UL;
    RetirementApplyResult result;
    if (!data_path || !*data_path || !parse_process_id(pid_text, &process_id)) {
        fprintf(stderr, "usage: retirement_offline_worker.exe --pid PID "
            "--data DATA --mode MODE --age AGE --quiet-ms MS --mod-dir DIR\n");
        return 2;
    }
    if (age_text && (!parse_unsigned(age_text, &age_value) || age_value > 80UL))
        age_value = 18UL;
    if (quiet_text && (!parse_unsigned(quiet_text, &quiet_value)
            || quiet_value < 1000UL || quiet_value > 10000UL))
        quiet_value = 2500UL;
    if (mod_dir && *mod_dir)
        retirement_engine_set_mod_dir(mod_dir);
    if (wait_parent && !wait_for_parent_exit(process_id)) return 3;
    if (!wait_for_stable_data(data_path, (unsigned)quiet_value)) {
        fprintf(stderr, "DATA não estabilizou: %s\n", data_path);
        return 4;
    }
    memset(&result, 0, sizeof(result));
    if (!retirement_engine_apply_file(data_path,
            mode && *mode ? mode : "remove_retirement", (int)age_value,
            &result)) {
        print_result(data_path, &result);
        return 5;
    }
    print_result(data_path, &result);
    return 0;
}
