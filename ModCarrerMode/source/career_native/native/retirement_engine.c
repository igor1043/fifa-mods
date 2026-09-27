#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "retirement_engine.h"

#define RETIREMENT_SIGNATURE "DB\0\x08\0\0\0\0"
#define RETIREMENT_SIGNATURE_SIZE 8U
#define RETIREMENT_CRC_OFFSET 0x84U
#define RETIREMENT_CRC_START 0xA0U
#define RETIREMENT_TABLE_CRC_SENTINEL 0xCDCDCDCDU
#define RETIREMENT_MAX_SAVE_SIZE (64ULL * 1024ULL * 1024ULL)
#define RETIREMENT_MAX_TABLES 4096U
#define RETIREMENT_MAX_RECORD_SIZE 4096U
#define RETIREMENT_CAREER_DATE_LOW 20080101U

typedef struct RetirementField {
    uint32_t bit_offset;
    uint32_t bit_depth;
    int found;
} RetirementField;

typedef struct RetirementTable {
    SIZE_T records_offset;
    SIZE_T table_crc_offset;
    SIZE_T table_crc_start;
    uint32_t record_size;
    uint16_t record_count;
    uint8_t field_count;
    RetirementField player_id;
    RetirementField birthdate;
    RetirementField is_retiring;
} RetirementTable;

typedef struct RetirementCalendar {
    SIZE_T records_offset;
    uint32_t record_size;
    uint16_t record_count;
    uint8_t field_count;
    RetirementField current_date;
} RetirementCalendar;

static SRWLOCK g_retirement_lock = SRWLOCK_INIT;
static HANDLE g_retirement_event;
static HANDLE g_retirement_thread;
static char g_retirement_mod_dir[MAX_PATH];
static char g_retirement_pending_path[1024];
static char g_retirement_requested_mode[64];
static volatile LONG g_retirement_running;

static void retirement_log_event(const char *event, const char *path);

#define RETIREMENT_WATCH_CAPACITY 64U

typedef struct RetirementWatchEntry {
    char path[1024];
    unsigned long long last_signature;
    unsigned long long pending_signature;
    ULONGLONG pending_since;
    int deferred_worker_started;
    int initialized;
} RetirementWatchEntry;

static RetirementWatchEntry g_retirement_watch[RETIREMENT_WATCH_CAPACITY];
static char g_retirement_save_root[MAX_PATH];
static int g_retirement_save_root_ready;
static ULONGLONG g_retirement_watch_start_filetime;
static char g_retirement_deferred_paths[RETIREMENT_WATCH_CAPACITY][1024];

static uint16_t retirement_u16(const unsigned char *p)
{
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static uint32_t retirement_u32(const unsigned char *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8)
        | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void retirement_put_u32(unsigned char *p, uint32_t value)
{
    p[0] = (unsigned char)value;
    p[1] = (unsigned char)(value >> 8);
    p[2] = (unsigned char)(value >> 16);
    p[3] = (unsigned char)(value >> 24);
}

static int retirement_name_is(const unsigned char *p, const char *name)
{
    return p[0] == (unsigned char)name[0] && p[1] == (unsigned char)name[1]
        && p[2] == (unsigned char)name[2] && p[3] == (unsigned char)name[3];
}

static int retirement_range_valid(SIZE_T offset, SIZE_T length, SIZE_T size)
{
    return offset <= size && length <= size - offset;
}

static uint32_t retirement_read_bits(const unsigned char *data,
    SIZE_T record_start, const RetirementField *field, uint32_t record_size)
{
    SIZE_T bit_base;
    uint32_t value = 0;
    uint32_t i;
    if (!field->found || !field->bit_depth || field->bit_depth > 32U
        || field->bit_offset > record_size * 8U
        || field->bit_depth > record_size * 8U - field->bit_offset)
        return 0;
    bit_base = record_start * 8U + field->bit_offset;
    for (i = 0; i < field->bit_depth; ++i) {
        SIZE_T absolute = bit_base + i;
        if ((data[absolute >> 3] >> (absolute & 7U)) & 1U)
            value |= 1U << i;
    }
    return value;
}

static int retirement_write_bits(unsigned char *data, SIZE_T record_start,
    const RetirementField *field, uint32_t record_size, uint32_t value)
{
    SIZE_T bit_base;
    uint32_t i;
    if (!field->found || !field->bit_depth || field->bit_depth > 32U
        || field->bit_offset > record_size * 8U
        || field->bit_depth > record_size * 8U - field->bit_offset
        || (field->bit_depth < 32U && value >= (1U << field->bit_depth)))
        return 0;
    bit_base = record_start * 8U + field->bit_offset;
    for (i = 0; i < field->bit_depth; ++i) {
        SIZE_T absolute = bit_base + i;
        unsigned char *byte = &data[absolute >> 3];
        unsigned char mask = (unsigned char)(1U << (absolute & 7U));
        if ((value >> i) & 1U) *byte |= mask;
        else *byte &= (unsigned char)~mask;
    }
    return 1;
}

static int retirement_find_field(const unsigned char *data,
    SIZE_T table_header, uint8_t field_count, uint32_t record_size,
    const char *name, RetirementField *field)
{
    uint32_t index;
    uint32_t total_bits = record_size * 8U;
    for (index = 0; index < field_count; ++index) {
        const unsigned char *descriptor = data + table_header + 36U
            + (SIZE_T)index * 16U;
        uint32_t storage_type = retirement_u32(descriptor);
        uint32_t offset = retirement_u32(descriptor + 4U);
        uint32_t depth = retirement_u32(descriptor + 12U);
        if (storage_type != 3U || !depth || depth > 32U
            || offset > total_bits || depth > total_bits - offset
            || !retirement_name_is(descriptor + 8U, name))
            continue;
        field->bit_offset = offset;
        field->bit_depth = depth;
        field->found = 1;
        return 1;
    }
    return 0;
}

static int retirement_find_tables(const unsigned char *data, SIZE_T size,
    RetirementTable *players, RetirementCalendar *calendar)
{
    SIZE_T cursor = 0;
    int players_found = 0;
    int calendar_found = 0;
    while (cursor + RETIREMENT_SIGNATURE_SIZE <= size) {
        SIZE_T db_offset;
        uint32_t db_size;
        uint32_t table_count;
        uint32_t table_index;
        const unsigned char *db;
        SIZE_T directory_end;
        SIZE_T table_data_offset;
        db_offset = cursor;
        while (db_offset + RETIREMENT_SIGNATURE_SIZE <= size
            && memcmp(data + db_offset, RETIREMENT_SIGNATURE,
                RETIREMENT_SIGNATURE_SIZE) != 0)
            ++db_offset;
        if (db_offset + 24U > size) break;
        db = data + db_offset;
        db_size = retirement_u32(db + 8U);
        table_count = retirement_u32(db + 16U);
        if (db_size < 24U || db_size > size - db_offset
            || table_count == 0U || table_count > RETIREMENT_MAX_TABLES)
            break;
        directory_end = 0x18U + (SIZE_T)table_count * 8U;
        table_data_offset = directory_end + 4U;
        if (table_data_offset > db_size) break;
        for (table_index = 0; table_index < table_count; ++table_index) {
            const unsigned char *entry = db + 0x18U
                + (SIZE_T)table_index * 8U;
            uint32_t relative = retirement_u32(entry + 4U);
            SIZE_T table_offset;
            uint32_t record_size;
            uint16_t record_count;
            uint8_t field_count;
            if ((SIZE_T)relative > db_size - table_data_offset)
                continue;
            table_offset = table_data_offset + relative;
            if (!retirement_range_valid(table_offset, 36U, db_size))
                continue;
            record_size = retirement_u32(db + table_offset + 4U);
            record_count = retirement_u16(db + table_offset + 18U);
            field_count = db[table_offset + 24U];
            if (!record_size || record_size > RETIREMENT_MAX_RECORD_SIZE
                || !field_count || field_count > 128U)
                continue;
            if ((SIZE_T)field_count > (SIZE_MAX - table_offset - 36U) / 16U)
                continue;
            if (!retirement_range_valid(table_offset + 36U,
                    (SIZE_T)field_count * 16U, db_size))
                continue;
            {
                SIZE_T records_offset = table_offset + 36U
                    + (SIZE_T)field_count * 16U;
                SIZE_T records_end;
                SIZE_T padded_compressed;
                uint32_t compressed_length = retirement_u32(
                    db + table_offset + 12U);
                if ((SIZE_T)record_count >
                        (SIZE_MAX - records_offset) / record_size
                    || !retirement_range_valid(records_offset,
                        (SIZE_T)record_count * record_size, db_size))
                    continue;
                records_end = records_offset + (SIZE_T)record_count * record_size;
                padded_compressed = compressed_length
                    ? ((SIZE_T)compressed_length + 7U) & ~(SIZE_T)7U : 0U;
                if (records_end > db_size
                    || padded_compressed > db_size - records_end
                    || db_size - records_end - padded_compressed < 4U)
                    continue;
                if (!players_found && retirement_name_is(entry, "CZUM")) {
                    memset(players, 0, sizeof(*players));
                    players->records_offset = db_offset + records_offset;
                    players->table_crc_start = db_offset + table_offset + 36U;
                    players->table_crc_offset = db_offset + records_end
                        + padded_compressed;
                    players->record_size = record_size;
                    players->record_count = record_count;
                    players->field_count = field_count;
                    retirement_find_field(db, table_offset, field_count,
                        record_size, "ykFq", &players->player_id);
                    retirement_find_field(db, table_offset, field_count,
                        record_size, "WVIU", &players->birthdate);
                    retirement_find_field(db, table_offset, field_count,
                        record_size, "kvuF", &players->is_retiring);
                    if (players->birthdate.found &&
                        players->is_retiring.found)
                        players_found = 1;
                }
                if (!calendar_found && retirement_name_is(entry, "GJUr")) {
                    memset(calendar, 0, sizeof(*calendar));
                    calendar->records_offset = db_offset + records_offset;
                    calendar->record_size = record_size;
                    calendar->record_count = record_count;
                    calendar->field_count = field_count;
                    retirement_find_field(db, table_offset, field_count,
                        record_size, "aLZZ", &calendar->current_date);
                    if (calendar->current_date.found)
                        calendar_found = 1;
                }
            }
        }
        cursor = db_offset + db_size;
        if (players_found && calendar_found) break;
    }
    return players_found;
}

/* Gregorian day conversion, relative to 1970-01-01. */
static int64_t retirement_days_from_civil(int year, unsigned month,
    unsigned day)
{
    int adjusted_year = year - (month <= 2U);
    int era = adjusted_year >= 0 ? adjusted_year / 400 : (adjusted_year - 399) / 400;
    unsigned year_of_era = (unsigned)(adjusted_year - era * 400);
    int month_adjusted = (int)month + (month > 2U ? -3 : 9);
    unsigned day_of_year = (153U * (unsigned)month_adjusted + 2U) / 5U
        + day - 1U;
    unsigned day_of_era = year_of_era * 365U + year_of_era / 4U
        - year_of_era / 100U + day_of_year;
    return (int64_t)era * 146097 + (int64_t)day_of_era - 719468;
}

static void retirement_civil_from_days(int64_t days, int *year,
    unsigned *month, unsigned *day)
{
    int64_t z = days + 719468;
    int64_t era = z >= 0 ? z / 146097 : (z - 146096) / 146097;
    unsigned day_of_era = (unsigned)(z - era * 146097);
    unsigned day_of_year = (day_of_era - day_of_era / 1460U
        + day_of_era / 36524U - day_of_era / 146096U) / 365U;
    int adjusted_year = (int)day_of_year + (int)era * 400;
    unsigned day_of_year2 = day_of_era - (365U * day_of_year
        + day_of_year / 4U - day_of_year / 100U);
    unsigned month_number = (5U * day_of_year2 + 2U) / 153U;
    *day = day_of_year2 - (153U * month_number + 2U) / 5U + 1U;
    {
        int month_value = (int)month_number + (month_number < 10U ? 3 : -9);
        *month = (unsigned)month_value;
    }
    *year = adjusted_year + (*month <= 2U);
}

static int retirement_parse_date(int yyyymmdd, int *year, unsigned *month,
    unsigned *day)
{
    int y = yyyymmdd / 10000;
    unsigned m = (unsigned)((yyyymmdd / 100) % 100);
    unsigned d = (unsigned)(yyyymmdd % 100);
    int64_t normalized;
    if (y < 1500 || y > 2500 || m < 1U || m > 12U || d < 1U || d > 31U)
        return 0;
    normalized = retirement_days_from_civil(y, m, d);
    retirement_civil_from_days(normalized, &y, &m, &d);
    if (y != yyyymmdd / 10000 || m != (unsigned)((yyyymmdd / 100) % 100)
        || d != (unsigned)(yyyymmdd % 100))
        return 0;
    *year = y; *month = m; *day = d;
    return 1;
}

static int retirement_days_in_month(int year, unsigned month)
{
    int64_t first = retirement_days_from_civil(year, month, 1U);
    unsigned next_month = month == 12U ? 1U : month + 1U;
    int next_year = month == 12U ? year + 1 : year;
    return (int)(retirement_days_from_civil(next_year, next_month, 1U) - first);
}

static uint32_t retirement_fifa_date_raw(int year, unsigned month,
    unsigned day)
{
    int64_t epoch = retirement_days_from_civil(1582, 10U, 14U);
    int64_t current = retirement_days_from_civil(year, month, day);
    return current >= epoch ? (uint32_t)(current - epoch) : 0U;
}

static uint32_t retirement_crc32(const unsigned char *data, SIZE_T size)
{
    static uint32_t table[256];
    static LONG initialized;
    uint32_t crc = 0xFFFFFFFFU;
    SIZE_T index;
    if (InterlockedCompareExchange(&initialized, 1, 0) == 0) {
        uint32_t i;
        for (i = 0; i < 256U; ++i) {
            uint32_t value = i;
            uint32_t bit;
            for (bit = 0; bit < 8U; ++bit)
                value = (value >> 1) ^ (0xEDB88320U & (uint32_t)-(int)(value & 1U));
            table[i] = value;
        }
        InterlockedExchange(&initialized, 2);
    } else {
        while (InterlockedCompareExchange(&initialized, 0, 0) != 2)
            Sleep(0);
    }
    for (index = 0; index < size; ++index)
        crc = table[(crc ^ data[index]) & 0xFFU] ^ (crc >> 8);
    return crc ^ 0xFFFFFFFFU;
}

static uint32_t retirement_fifa_crc32(const unsigned char *data, SIZE_T size)
{
    uint32_t crc = 0xFFFFFFFFU;
    SIZE_T index;
    for (index = 0; index < size; ++index) {
        uint32_t bit;
        crc ^= (uint32_t)data[index] << 24;
        for (bit = 0; bit < 8U; ++bit)
            crc = (crc & 0x80000000U)
                ? (crc << 1) ^ 0x04C11DB7U : crc << 1;
    }
    return crc;
}

static void retirement_result_clear(RetirementApplyResult *result)
{
    if (result) memset(result, 0, sizeof(*result));
}

static void retirement_result_message(RetirementApplyResult *result,
    int status, const char *message)
{
    if (!result) return;
    result->status = status;
    lstrcpynA(result->message, message ? message : "", sizeof(result->message));
}

static int retirement_read_file(const char *path, unsigned char **data,
    SIZE_T *size)
{
    HANDLE file;
    LARGE_INTEGER length;
    SIZE_T offset = 0;
    *data = NULL; *size = 0;
    file = CreateFileA(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
        NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE || !GetFileSizeEx(file, &length)
        || length.QuadPart <= 0 || (uint64_t)length.QuadPart > RETIREMENT_MAX_SAVE_SIZE) {
        if (file != INVALID_HANDLE_VALUE) CloseHandle(file);
        return 0;
    }
    *size = (SIZE_T)length.QuadPart;
    *data = (unsigned char *)HeapAlloc(GetProcessHeap(), 0, *size);
    if (!*data) { CloseHandle(file); return 0; }
    while (offset < *size) {
        DWORD request = (DWORD)((*size - offset) > 0x100000U
            ? 0x100000U : (*size - offset));
        DWORD got = 0;
        if (!ReadFile(file, *data + offset, request, &got, NULL) || !got) {
            HeapFree(GetProcessHeap(), 0, *data); *data = NULL; *size = 0;
            CloseHandle(file); return 0;
        }
        offset += got;
    }
    CloseHandle(file);
    return 1;
}

static int retirement_write_atomic(const char *path, const unsigned char *data,
    SIZE_T size)
{
    char temporary[1200];
    HANDLE file;
    SIZE_T offset = 0;
    DWORD tick = GetTickCount();
    snprintf(temporary, sizeof(temporary), "%s.retirement_tmp_%lu_%lu",
        path, (unsigned long)GetCurrentProcessId(), (unsigned long)tick);
    file = CreateFileA(temporary, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS,
        FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) return 0;
    while (offset < size) {
        DWORD request = (DWORD)((size - offset) > 0x100000U
            ? 0x100000U : (size - offset));
        DWORD written = 0;
        if (!WriteFile(file, data + offset, request, &written, NULL)
            || !written) {
            CloseHandle(file); DeleteFileA(temporary); return 0;
        }
        offset += written;
    }
    if (!FlushFileBuffers(file)) {
        CloseHandle(file); DeleteFileA(temporary); return 0;
    }
    CloseHandle(file);
    if (!MoveFileExA(temporary, path,
            MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) {
        DeleteFileA(temporary); return 0;
    }
    return 1;
}

static int retirement_copy_backup(const char *source, const char *suffix,
    char *destination, size_t capacity)
{
    SYSTEMTIME now;
    int attempt;
    GetLocalTime(&now);
    for (attempt = 0; attempt < 100; ++attempt) {
        snprintf(destination, capacity, "%s.retirement_backup_%04u%02u%02u_%02u%02u%02u_%02d%s",
            source, now.wYear, now.wMonth, now.wDay, now.wHour, now.wMinute,
            now.wSecond, attempt, suffix ? suffix : "");
        if (CopyFileA(source, destination, TRUE)) return 1;
        if (GetLastError() != ERROR_FILE_EXISTS) return 0;
    }
    return 0;
}

static int retirement_validate_written_file(const char *data_path,
    const char *mode, RetirementApplyResult *result)
{
    unsigned char *data = NULL;
    SIZE_T size = 0;
    RetirementTable players;
    RetirementCalendar calendar;
    uint32_t stored_crc;
    uint32_t calculated_crc;
    unsigned int row;
    int rejuvenate = mode && (_stricmp(mode, "remove_and_rejuvenate") == 0
        || _stricmp(mode, "rejuvenate") == 0);
    (void)rejuvenate;

    if (!retirement_read_file(data_path, &data, &size)) return 0;
    if (size < RETIREMENT_CRC_START
        || size < RETIREMENT_CRC_OFFSET + 4U) {
        HeapFree(GetProcessHeap(), 0, data);
        return 0;
    }
    stored_crc = retirement_u32(data + RETIREMENT_CRC_OFFSET);
    calculated_crc = retirement_crc32(data + RETIREMENT_CRC_START,
        size - RETIREMENT_CRC_START);
    if (stored_crc != calculated_crc
        || !retirement_find_tables(data, size, &players, &calendar)
        || !players.player_id.found || !players.is_retiring.found) {
        HeapFree(GetProcessHeap(), 0, data);
        return 0;
    }
    for (row = 0; row < players.record_count; ++row) {
        SIZE_T start = players.records_offset
            + (SIZE_T)row * players.record_size;
        if (data[start + players.record_size - 1U] & 0x80U) continue;
        if (retirement_read_bits(data, start, &players.is_retiring,
                players.record_size) != 0U) {
            HeapFree(GetProcessHeap(), 0, data);
            return 0;
        }
    }
    if (result) result->crc_after = stored_crc;
    HeapFree(GetProcessHeap(), 0, data);
    return 1;
}

static int retirement_restore_backup(const char *data_path,
    const char *backup_path)
{
    unsigned char *backup = NULL;
    SIZE_T size = 0;
    int ok;
    if (!backup_path || !*backup_path
        || !retirement_read_file(backup_path, &backup, &size))
        return 0;
    ok = retirement_write_atomic(data_path, backup, size);
    HeapFree(GetProcessHeap(), 0, backup);
    return ok;
}

static int retirement_get_config(const char *mod_dir, int *enabled,
    char *mode, size_t mode_capacity, int *target_age, unsigned *quiet_ms,
    int *defer_until_game_exit)
{
    char path[MAX_PATH];
    char line[256];
    FILE *file;
    *enabled = 0; *target_age = 18; *quiet_ms = 2500U;
    /* Safe by default: a post-save patch must never replace a DATA file while
     * FIFA is still alive.  The explicit config switch can only opt out for
     * controlled diagnostics. */
    if (defer_until_game_exit) *defer_until_game_exit = 1;
    lstrcpynA(mode, "remove_retirement", (int)mode_capacity);
    snprintf(path, sizeof(path), "%s\\career_retirement_background.ini", mod_dir);
    file = fopen(path, "rb");
    if (!file) return 0;
    while (fgets(line, sizeof(line), file)) {
        char key[64], value[160];
        if (sscanf(line, " %63[^=]= %159[^\r\n]", key, value) != 2)
            continue;
        if (_stricmp(key, "enabled") == 0) *enabled = atoi(value) != 0;
        else if (_stricmp(key, "mode") == 0)
            lstrcpynA(mode, value, (int)mode_capacity);
        else if (_stricmp(key, "target_age") == 0) *target_age = atoi(value);
        else if (_stricmp(key, "quiet_ms") == 0) *quiet_ms = (unsigned)atoi(value);
        else if (_stricmp(key, "defer_until_game_exit") == 0
            && defer_until_game_exit)
            *defer_until_game_exit = atoi(value) != 0;
    }
    fclose(file);
    if (*target_age < 1 || *target_age > 80) *target_age = 18;
    if (*quiet_ms < 1000U || *quiet_ms > 10000U) *quiet_ms = 2500U;
    return 1;
}

int retirement_engine_apply_file(const char *data_path, const char *mode,
    int target_age, RetirementApplyResult *result)
{
    unsigned char *data = NULL;
    SIZE_T size = 0;
    RetirementTable players;
    RetirementCalendar calendar;
    uint32_t stored_crc;
    uint32_t calculated_crc;
    int current_year = 2026;
    unsigned current_month = 1U, current_day = 1U;
    int current_date_valid = 0;
    int rejuvenate = mode && (_stricmp(mode, "remove_and_rejuvenate") == 0
        || _stricmp(mode, "rejuvenate") == 0);
    unsigned int row;
    if (!result || !data_path || !*data_path) return 0;
    retirement_result_clear(result);
    if (!retirement_read_file(data_path, &data, &size)) {
        retirement_result_message(result, 10, "DATA não pôde ser lido"); return 0;
    }
    if (size < RETIREMENT_CRC_START || size < RETIREMENT_CRC_OFFSET + 4U) {
        retirement_result_message(result, 11, "DATA pequeno demais"); goto fail;
    }
    stored_crc = retirement_u32(data + RETIREMENT_CRC_OFFSET);
    calculated_crc = retirement_crc32(data + RETIREMENT_CRC_START,
        size - RETIREMENT_CRC_START);
    result->crc_before = stored_crc;
    if (stored_crc != calculated_crc) {
        retirement_result_message(result, 12, "CRC original inválido; nada foi alterado"); goto fail;
    }
    if (!retirement_find_tables(data, size, &players, &calendar)
        || !players.player_id.found) {
        retirement_result_message(result, 13, "Tabela CZUM/fields não encontrados"); goto fail;
    }
    if (calendar.current_date.found && calendar.record_count > 0U) {
        SIZE_T start = calendar.records_offset;
        uint32_t raw = retirement_read_bits(data, start, &calendar.current_date,
            calendar.record_size);
        current_date_valid = retirement_parse_date(
            (int)(raw + RETIREMENT_CAREER_DATE_LOW), &current_year,
            &current_month, &current_day);
    }
    if (rejuvenate && (!current_date_valid || target_age < 12 || target_age > 50)) {
        retirement_result_message(result, 19,
            !current_date_valid ? "Data da carreira não encontrada; nada foi alterado"
                                : "Idade-alvo fora do intervalo seguro 12..50");
        goto fail;
    }
    for (row = 0; row < players.record_count; ++row) {
        SIZE_T start = players.records_offset + (SIZE_T)row * players.record_size;
        if (data[start + players.record_size - 1U] & 0x80U)
            continue;
        result->players_seen++;
        uint32_t retiring = retirement_read_bits(data, start,
            &players.is_retiring, players.record_size);
        if (retiring != 1U) continue;
        result->players_retiring++;
        if (!retirement_write_bits(data, start, &players.is_retiring,
                players.record_size, 0U)) {
            retirement_result_message(result, 14, "Falha ao escrever isretiring"); goto fail;
        }
        if (rejuvenate) {
            uint32_t old_raw = retirement_read_bits(data, start,
                &players.birthdate, players.record_size);
            int old_year; unsigned old_month, old_day;
            uint32_t new_raw;
            int birth_year;
            unsigned birth_month, birth_day;
            {
                int64_t epoch = retirement_days_from_civil(1582, 10U, 14U);
                int64_t birth_days = epoch + old_raw;
                retirement_civil_from_days(birth_days, &old_year, &old_month, &old_day);
            }
            birth_year = current_year - target_age;
            if (current_month < old_month
                || (current_month == old_month && current_day < old_day))
                birth_year--;
            birth_month = old_month; birth_day = old_day;
            if (birth_day > (unsigned)retirement_days_in_month(birth_year, birth_month))
                birth_day = (unsigned)retirement_days_in_month(birth_year, birth_month);
            new_raw = retirement_fifa_date_raw(birth_year, birth_month, birth_day);
            if (!retirement_write_bits(data, start, &players.birthdate,
                    players.record_size, new_raw)) {
                retirement_result_message(result, 15, "Falha ao escrever birthdate"); goto fail;
            }
        }
        result->players_changed++;
    }
    if (!result->players_changed) {
        result->crc_after = calculated_crc;
        retirement_result_message(result, 0, "Nenhum jogador marcado para aposentadoria");
        HeapFree(GetProcessHeap(), 0, data); return 1;
    }
    {
        char index_path[1200];
        char backup_index[1200];
        char backup_data[1200];
        char *slash;
        if (players.table_crc_offset <= size
            && players.table_crc_start <= players.table_crc_offset
            && players.table_crc_offset - players.table_crc_start >= 4U) {
            uint32_t table_crc = retirement_u32(data + players.table_crc_offset);
            if (table_crc != RETIREMENT_TABLE_CRC_SENTINEL)
                retirement_put_u32(data + players.table_crc_offset,
                    retirement_fifa_crc32(data + players.table_crc_start,
                        players.table_crc_offset - players.table_crc_start));
        }
        retirement_put_u32(data + RETIREMENT_CRC_OFFSET,
            retirement_crc32(data + RETIREMENT_CRC_START,
                size - RETIREMENT_CRC_START));
        result->crc_after = retirement_u32(data + RETIREMENT_CRC_OFFSET);
        if (!retirement_copy_backup(data_path, "", backup_data, sizeof(backup_data))) {
            retirement_result_message(result, 16, "Backup do DATA falhou; nada foi alterado"); goto fail;
        }
        lstrcpynA(result->backup_data, backup_data, sizeof(result->backup_data));
        lstrcpynA(index_path, data_path, sizeof(index_path));
        slash = strrchr(index_path, '\\');
        if (slash) { lstrcpyA(slash + 1, "INDEX"); }
        if (GetFileAttributesA(index_path) != INVALID_FILE_ATTRIBUTES) {
            if (!retirement_copy_backup(index_path, "", backup_index, sizeof(backup_index))) {
                retirement_result_message(result, 17, "Backup do INDEX falhou; DATA não foi alterado"); goto fail;
            }
            lstrcpynA(result->backup_index, backup_index, sizeof(result->backup_index));
        }
        if (!retirement_write_atomic(data_path, data, size)) {
            retirement_result_message(result, 18, "DATA bloqueado; backup preservado e nada foi alterado"); goto fail;
        }
        if (!retirement_validate_written_file(data_path, mode, result)) {
            int restored = retirement_restore_backup(data_path,
                result->backup_data);
            retirement_result_message(result, restored ? 22 : 23,
                restored
                    ? "Validacao pos-escrita falhou; backup restaurado"
                    : "Validacao pos-escrita falhou; restaure o backup manualmente");
            goto fail;
        }
    }
    retirement_result_message(result, 1, "Patch global concluído com backup");
    HeapFree(GetProcessHeap(), 0, data); return 1;
fail:
    HeapFree(GetProcessHeap(), 0, data);
    return 0;
}

int retirement_engine_apply_buffer(void *buffer, SIZE_T size,
    const char *mode, int target_age, RetirementApplyResult *result)
{
    unsigned char *data = (unsigned char *)buffer;
    RetirementTable players;
    RetirementCalendar calendar;
    uint32_t stored_crc;
    uint32_t calculated_crc;
    int current_year = 2026;
    unsigned current_month = 1U, current_day = 1U;
    int current_date_valid = 0;
    int rejuvenate = mode && (_stricmp(mode, "remove_and_rejuvenate") == 0
        || _stricmp(mode, "rejuvenate") == 0);
    unsigned int row;
    if (!result || !data || size < RETIREMENT_CRC_START
        || size < RETIREMENT_CRC_OFFSET + 4U)
        return 0;
    retirement_result_clear(result);
    stored_crc = retirement_u32(data + RETIREMENT_CRC_OFFSET);
    calculated_crc = retirement_crc32(data + RETIREMENT_CRC_START,
        size - RETIREMENT_CRC_START);
    result->crc_before = stored_crc;
    if (stored_crc != calculated_crc) {
        retirement_result_message(result, 12,
            "CRC original inválido; nada foi alterado");
        return 0;
    }
    if (!retirement_find_tables(data, size, &players, &calendar)
        || !players.player_id.found) {
        retirement_result_message(result, 13,
            "Tabela CZUM/fields não encontrados");
        return 0;
    }
    if (calendar.current_date.found && calendar.record_count > 0U) {
        SIZE_T start = calendar.records_offset;
        uint32_t raw = retirement_read_bits(data, start, &calendar.current_date,
            calendar.record_size);
        current_date_valid = retirement_parse_date(
            (int)(raw + RETIREMENT_CAREER_DATE_LOW), &current_year,
            &current_month, &current_day);
    }
    if (rejuvenate && (!current_date_valid || target_age < 12 || target_age > 50)) {
        retirement_result_message(result, 19,
            !current_date_valid ? "Data da carreira não encontrada; nada foi alterado"
                                : "Idade-alvo fora do intervalo seguro 12..50");
        return 0;
    }
    for (row = 0; row < players.record_count; ++row) {
        SIZE_T start = players.records_offset + (SIZE_T)row * players.record_size;
        uint32_t retiring;
        if (data[start + players.record_size - 1U] & 0x80U)
            continue;
        result->players_seen++;
        retiring = retirement_read_bits(data, start, &players.is_retiring,
            players.record_size);
        if (retiring != 1U) continue;
        result->players_retiring++;
        if (!retirement_write_bits(data, start, &players.is_retiring,
                players.record_size, 0U)) {
            retirement_result_message(result, 14,
                "Falha ao escrever isretiring");
            return 0;
        }
        if (rejuvenate) {
            uint32_t old_raw = retirement_read_bits(data, start,
                &players.birthdate, players.record_size);
            int old_year;
            unsigned old_month, old_day;
            uint32_t new_raw;
            int birth_year;
            unsigned birth_month, birth_day;
            {
                int64_t epoch = retirement_days_from_civil(1582, 10U, 14U);
                int64_t birth_days = epoch + old_raw;
                retirement_civil_from_days(birth_days, &old_year, &old_month,
                    &old_day);
            }
            birth_year = current_year - target_age;
            if (current_month < old_month
                || (current_month == old_month && current_day < old_day))
                birth_year--;
            birth_month = old_month;
            birth_day = old_day;
            if (birth_day > (unsigned)retirement_days_in_month(
                    birth_year, birth_month))
                birth_day = (unsigned)retirement_days_in_month(
                    birth_year, birth_month);
            new_raw = retirement_fifa_date_raw(birth_year, birth_month,
                birth_day);
            if (!retirement_write_bits(data, start, &players.birthdate,
                    players.record_size, new_raw)) {
                retirement_result_message(result, 15,
                    "Falha ao escrever birthdate");
                return 0;
            }
        }
        result->players_changed++;
    }
    if (!result->players_changed) {
        result->crc_after = calculated_crc;
        retirement_result_message(result, 0,
            "Nenhum jogador marcado para aposentadoria");
        return 1;
    }
    if (players.table_crc_offset <= size
        && players.table_crc_start <= players.table_crc_offset
        && players.table_crc_offset - players.table_crc_start >= 4U) {
        uint32_t table_crc = retirement_u32(data + players.table_crc_offset);
        if (table_crc != RETIREMENT_TABLE_CRC_SENTINEL)
            retirement_put_u32(data + players.table_crc_offset,
                retirement_fifa_crc32(data + players.table_crc_start,
                    players.table_crc_offset - players.table_crc_start));
    }
    retirement_put_u32(data + RETIREMENT_CRC_OFFSET,
        retirement_crc32(data + RETIREMENT_CRC_START,
            size - RETIREMENT_CRC_START));
    result->crc_after = retirement_u32(data + RETIREMENT_CRC_OFFSET);
    retirement_result_message(result, 1,
        "Patch em memória pronto para salvar");
    return 1;
}

int retirement_engine_apply_buffer_from_config(void *buffer, SIZE_T size,
    RetirementApplyResult *result)
{
    char mode[64];
    int enabled;
    int target_age;
    unsigned quiet_ms;
    int defer_until_game_exit;
    (void)quiet_ms;
    if (!retirement_get_config(g_retirement_mod_dir, &enabled, mode,
            sizeof(mode), &target_age, &quiet_ms,
            &defer_until_game_exit) || !enabled) {
        if (result) {
            retirement_result_clear(result);
            retirement_result_message(result, 20,
                "Engine desabilitado na configuração");
        }
        return 0;
    }
    /* Save mutation is intentionally owned by the external worker.  The
     * process-local WriteFile hook must pass FIFA's original buffer through;
     * changing it here can leave FIFA's in-memory save state out of sync with
     * the DATA/INDEX pair it later manages. */
    (void)buffer;
    (void)size;
    (void)mode;
    (void)target_age;
    (void)defer_until_game_exit;
    if (result) {
        retirement_result_clear(result);
        retirement_result_message(result, 21,
            "Patch delegado ao worker externo");
    }
    return 0;
}

int retirement_engine_backup_before_write(const char *data_path)
{
    char index_path[1200];
    char backup_data[1200];
    char backup_index[1200];
    char *slash;
    if (!data_path || !*data_path)
        return 0;
    /* FIFA commonly writes a fresh DATA file in a temporary career folder
     * and only replaces the old file after the write succeeds.  There is no
     * old DATA to copy in that case, so the absence of the target is itself
     * a safe/expected state.  Existing DATA files still require a real
     * backup before we allow the in-memory patch through. */
    if (GetFileAttributesA(data_path) != INVALID_FILE_ATTRIBUTES
        && !retirement_copy_backup(data_path, "", backup_data,
            sizeof(backup_data)))
        return 0;
    lstrcpynA(index_path, data_path, sizeof(index_path));
    slash = strrchr(index_path, '\\');
    if (slash) lstrcpyA(slash + 1, "INDEX");
    if (GetFileAttributesA(index_path) != INVALID_FILE_ATTRIBUTES
        && !retirement_copy_backup(index_path, "", backup_index,
            sizeof(backup_index)))
        return 0;
    return 1;
}

void retirement_engine_set_mod_dir(const char *mod_dir)
{
    if (!mod_dir || !*mod_dir) {
        g_retirement_mod_dir[0] = '\0';
        return;
    }
    lstrcpynA(g_retirement_mod_dir, mod_dir, sizeof(g_retirement_mod_dir));
}

static int retirement_claim_deferred_path(const char *path)
{
    unsigned int index;
    if (!path || !*path) return 0;
    AcquireSRWLockExclusive(&g_retirement_lock);
    for (index = 0; index < RETIREMENT_WATCH_CAPACITY; ++index) {
        if (g_retirement_deferred_paths[index][0]
            && _stricmp(g_retirement_deferred_paths[index], path) == 0) {
            ReleaseSRWLockExclusive(&g_retirement_lock);
            return 0;
        }
    }
    for (index = 0; index < RETIREMENT_WATCH_CAPACITY; ++index) {
        if (!g_retirement_deferred_paths[index][0]) {
            lstrcpynA(g_retirement_deferred_paths[index], path,
                sizeof(g_retirement_deferred_paths[index]));
            ReleaseSRWLockExclusive(&g_retirement_lock);
            return 1;
        }
    }
    ReleaseSRWLockExclusive(&g_retirement_lock);
    return 0;
}

static void retirement_release_deferred_path(const char *path)
{
    unsigned int index;
    if (!path || !*path) return;
    AcquireSRWLockExclusive(&g_retirement_lock);
    for (index = 0; index < RETIREMENT_WATCH_CAPACITY; ++index) {
        if (_stricmp(g_retirement_deferred_paths[index], path) == 0) {
            g_retirement_deferred_paths[index][0] = '\0';
            break;
        }
    }
    ReleaseSRWLockExclusive(&g_retirement_lock);
}

static int retirement_launch_deferred_worker(const char *data_path,
    const char *mode, int target_age, unsigned quiet_ms,
    int wait_for_parent_exit)
{
    char worker_path[MAX_PATH];
    char command_line[4096];
    STARTUPINFOA startup;
    PROCESS_INFORMATION process;
    if (!data_path || !*data_path || !g_retirement_mod_dir[0]) return 0;
    if (!retirement_claim_deferred_path(data_path)) return 1;
    snprintf(worker_path, sizeof(worker_path), "%s\\retirement_offline_worker.exe",
        g_retirement_mod_dir);
    if (GetFileAttributesA(worker_path) == INVALID_FILE_ATTRIBUTES) {
        retirement_release_deferred_path(data_path);
        return 0;
    }
    snprintf(command_line, sizeof(command_line),
        "\"%s\" --pid %lu --data \"%s\" --mode %s --age %d "
        "--quiet-ms %u --mod-dir \"%s\"%s",
        worker_path, (unsigned long)GetCurrentProcessId(), data_path,
        mode && *mode ? mode : "remove_retirement", target_age, quiet_ms,
        g_retirement_mod_dir, wait_for_parent_exit ? " --wait-parent-exit" : "");
    memset(&startup, 0, sizeof(startup));
    memset(&process, 0, sizeof(process));
    startup.cb = sizeof(startup);
    if (!CreateProcessA(NULL, command_line, NULL, NULL, FALSE,
            CREATE_NO_WINDOW, NULL, NULL, &startup, &process)) {
        retirement_release_deferred_path(data_path);
        return 0;
    }
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    return 1;
}

static void retirement_log_result(const RetirementApplyResult *result,
    const char *path)
{
    char log_path[MAX_PATH];
    FILE *file;
    snprintf(log_path, sizeof(log_path), "%s\\career_retirement_background.log",
        g_retirement_mod_dir);
    file = fopen(log_path, "ab");
    if (!file) return;
    fprintf(file, "status=%d changed=%u retiring=%u crc_before=%08X crc_after=%08X message=%s data=%s backup_data=%s backup_index=%s\n",
        result->status, result->players_changed, result->players_retiring,
        result->crc_before, result->crc_after, result->message, path,
        result->backup_data, result->backup_index);
    fclose(file);
}

static void retirement_log_event(const char *event, const char *path)
{
    char log_path[MAX_PATH];
    FILE *file;
    snprintf(log_path, sizeof(log_path), "%s\\career_retirement_background.log",
        g_retirement_mod_dir);
    file = fopen(log_path, "ab");
    if (!file) return;
    fprintf(file, "event=%s path=%s save_root=%s\n", event ? event : "",
        path ? path : "", g_retirement_save_root);
    fclose(file);
}

static void retirement_set_requested_mode(const char *mode)
{
    if (!mode || !*mode) return;
    AcquireSRWLockExclusive(&g_retirement_lock);
    lstrcpynA(g_retirement_requested_mode, mode,
        sizeof(g_retirement_requested_mode));
    ReleaseSRWLockExclusive(&g_retirement_lock);
}

static int retirement_take_requested_mode(char *mode, size_t capacity)
{
    int ready;
    if (!mode || capacity == 0) return 0;
    AcquireSRWLockExclusive(&g_retirement_lock);
    ready = g_retirement_requested_mode[0] != '\0';
    if (ready) {
        lstrcpynA(mode, g_retirement_requested_mode, (int)capacity);
        g_retirement_requested_mode[0] = '\0';
    }
    ReleaseSRWLockExclusive(&g_retirement_lock);
    return ready;
}

static int retirement_peek_requested_mode(char *mode, size_t capacity)
{
    int ready;
    if (!mode || capacity == 0) return 0;
    AcquireSRWLockShared(&g_retirement_lock);
    ready = g_retirement_requested_mode[0] != '\0';
    if (ready)
        lstrcpynA(mode, g_retirement_requested_mode, (int)capacity);
    ReleaseSRWLockShared(&g_retirement_lock);
    return ready;
}

static int retirement_card_mode_at_cursor(char *mode, size_t capacity)
{
    HWND foreground;
    DWORD process_id = 0;
    RECT client;
    POINT point;
    LONG width;
    LONG height;
    LONG logical_x;
    LONG logical_y;

    if (!mode || capacity == 0 || !GetCursorPos(&point)) return 0;
    foreground = GetForegroundWindow();
    if (!foreground) return 0;
    GetWindowThreadProcessId(foreground, &process_id);
    if (process_id != GetCurrentProcessId()
        || !GetClientRect(foreground, &client)
        || !ScreenToClient(foreground, &point))
        return 0;
    width = client.right - client.left;
    height = client.bottom - client.top;
    if (width <= 0 || height <= 0) return 0;
    logical_x = point.x * 1920L / width;
    logical_y = point.y * 1080L / height;
    if (logical_x < 965L || logical_x >= 1811L
        || logical_y < 278L || logical_y >= 696L)
        return 0;
    if (logical_y < 492L) {
        lstrcpynA(mode, "remove_retirement", (int)capacity);
        return 1;
    }
    lstrcpynA(mode, "remove_and_rejuvenate", (int)capacity);
    return 1;
}

static DWORD WINAPI retirement_input_worker(void *unused)
{
    SHORT previous_left = 0;
    SHORT previous_enter = 0;
    int input_armed = 0;
    (void)unused;
    while (InterlockedCompareExchange(&g_retirement_running, 0, 0)) {
        SHORT left = GetAsyncKeyState(VK_LBUTTON);
        SHORT enter = GetAsyncKeyState(VK_RETURN);
        char mode[64];
        int pressed = input_armed
            && (((left & 0x8000) && !(previous_left & 0x8000))
            || ((enter & 0x8000) && !(previous_enter & 0x8000)));
        if (!(left & 0x8000) && !(enter & 0x8000)) input_armed = 1;
        if (pressed && retirement_card_mode_at_cursor(mode, sizeof(mode))) {
            retirement_set_requested_mode(mode);
            retirement_log_event(
                _stricmp(mode, "remove_and_rejuvenate") == 0
                    ? "card_reset_age_request" : "card_remove_request",
                mode);
        }
        previous_left = left;
        previous_enter = enter;
        Sleep(25U);
    }
    return 0;
}

static int retirement_get_save_root(char *root, size_t capacity)
{
    char profile[MAX_PATH];
    DWORD length;
    if (!root || capacity == 0) return 0;
    length = GetEnvironmentVariableA("USERPROFILE", profile,
        (DWORD)sizeof(profile));
    if (!length || length >= sizeof(profile)) return 0;
    snprintf(root, capacity, "%s\\Documents\\FIFA 16\\0\\FIFA16", profile);
    return GetFileAttributesA(root) != INVALID_FILE_ATTRIBUTES;
}

static int retirement_file_signature(const char *path,
    unsigned long long *signature)
{
    WIN32_FILE_ATTRIBUTE_DATA attributes;
    ULARGE_INTEGER time_value;
    ULARGE_INTEGER size_value;
    if (!path || !signature || !GetFileAttributesExA(path,
            GetFileExInfoStandard, &attributes))
        return 0;
    time_value.LowPart = attributes.ftLastWriteTime.dwLowDateTime;
    time_value.HighPart = attributes.ftLastWriteTime.dwHighDateTime;
    size_value.LowPart = attributes.nFileSizeLow;
    size_value.HighPart = attributes.nFileSizeHigh;
    *signature = time_value.QuadPart ^ (size_value.QuadPart * 0x9E3779B97F4A7C15ULL);
    if (*signature == 0) *signature = 1;
    return 1;
}

static int retirement_file_is_new_save(const char *path)
{
    WIN32_FILE_ATTRIBUTE_DATA attributes;
    ULARGE_INTEGER time_value;
    ULARGE_INTEGER size_value;
    if (!path || !GetFileAttributesExA(path, GetFileExInfoStandard,
            &attributes))
        return 0;
    time_value.LowPart = attributes.ftLastWriteTime.dwLowDateTime;
    time_value.HighPart = attributes.ftLastWriteTime.dwHighDateTime;
    size_value.LowPart = attributes.nFileSizeLow;
    size_value.HighPart = attributes.nFileSizeHigh;
    return time_value.QuadPart > g_retirement_watch_start_filetime
        && size_value.QuadPart >= 1024ULL * 1024ULL;
}

static int retirement_watch_slot(const char *path)
{
    unsigned int index;
    int free_slot = -1;
    for (index = 0; index < RETIREMENT_WATCH_CAPACITY; ++index) {
        if (g_retirement_watch[index].path[0]
            && _stricmp(g_retirement_watch[index].path, path) == 0)
            return (int)index;
        if (free_slot < 0 && !g_retirement_watch[index].path[0])
            free_slot = (int)index;
    }
    if (free_slot >= 0)
        lstrcpynA(g_retirement_watch[free_slot].path, path,
            sizeof(g_retirement_watch[free_slot].path));
    return free_slot;
}

static void retirement_watch_observe(const char *path, const char *mode,
    int target_age, unsigned quiet_ms, int defer_until_game_exit)
{
    unsigned long long signature;
    ULONGLONG now;
    int slot;
    RetirementWatchEntry *entry;
    (void)mode;
    if (!retirement_file_signature(path, &signature)) return;
    slot = retirement_watch_slot(path);
    if (slot < 0) return;
    entry = &g_retirement_watch[slot];
    now = GetTickCount64();
    if (!entry->initialized) {
        if (retirement_file_is_new_save(path)) {
            /* A DATA created after the watcher started is a save candidate,
             * not a baseline. Keep the pending signature but leave the last
             * signature empty so the next stable poll actually enters the
             * quiet-time apply branch. */
            entry->last_signature = 0;
            entry->pending_signature = signature;
            entry->pending_since = now;
        } else {
            entry->last_signature = signature;
            entry->pending_signature = 0;
            entry->pending_since = 0;
        }
        entry->initialized = 1;
        return;
    }
    if (signature != entry->last_signature) {
        if (entry->pending_signature != signature) {
            entry->pending_signature = signature;
            entry->pending_since = now;
        } else if (now - entry->pending_since >= quiet_ms) {
            char requested_mode[64];
            if (!entry->deferred_worker_started
                && retirement_peek_requested_mode(requested_mode,
                    sizeof(requested_mode))
                && retirement_launch_deferred_worker(path, requested_mode,
                    target_age, quiet_ms, defer_until_game_exit)) {
                (void)retirement_take_requested_mode(requested_mode,
                    sizeof(requested_mode));
                entry->deferred_worker_started = 1;
                entry->last_signature = signature;
                entry->pending_signature = 0;
                entry->pending_since = 0;
                retirement_log_event("deferred_worker_started", path);
            }
        }
    }
}

static void retirement_watch_poll(const char *mode, int target_age,
    unsigned quiet_ms, int defer_until_game_exit)
{
    char pattern[MAX_PATH];
    WIN32_FIND_DATAA find_data;
    HANDLE search;
    if (!g_retirement_save_root_ready) {
        if (!retirement_get_save_root(g_retirement_save_root,
                sizeof(g_retirement_save_root)))
            return;
        g_retirement_save_root_ready = 1;
        retirement_log_event("watcher_started", g_retirement_save_root);
    }
    snprintf(pattern, sizeof(pattern), "%s\\*", g_retirement_save_root);
    search = FindFirstFileA(pattern, &find_data);
    if (search == INVALID_HANDLE_VALUE) return;
    do {
        char data_path[MAX_PATH];
        if ((find_data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)
            && strcmp(find_data.cFileName, ".") != 0
            && strcmp(find_data.cFileName, "..") != 0) {
            snprintf(data_path, sizeof(data_path), "%s\\%s\\DATA",
                g_retirement_save_root, find_data.cFileName);
            retirement_watch_observe(data_path, mode, target_age, quiet_ms,
                defer_until_game_exit);
        }
    } while (FindNextFileA(search, &find_data));
    FindClose(search);
}

static DWORD WINAPI retirement_engine_worker(void *unused)
{
    (void)unused;
    while (InterlockedCompareExchange(&g_retirement_running, 0, 0)) {
        char path[1024] = "";
        char mode[64];
        char requested_mode[64];
        int enabled, target_age;
        int defer_until_game_exit;
        unsigned quiet_ms;
        DWORD wait = WaitForSingleObject(g_retirement_event, 1000U);
        if (!retirement_get_config(g_retirement_mod_dir, &enabled,
                mode, sizeof(mode), &target_age, &quiet_ms,
                &defer_until_game_exit) || !enabled)
            continue;
        if (wait == WAIT_OBJECT_0) {
            Sleep(quiet_ms);
            AcquireSRWLockShared(&g_retirement_lock);
            lstrcpynA(path, g_retirement_pending_path, sizeof(path));
            ReleaseSRWLockShared(&g_retirement_lock);
            if (path[0] && retirement_take_requested_mode(requested_mode,
                    sizeof(requested_mode))) {
                if (retirement_launch_deferred_worker(path, requested_mode,
                        target_age, quiet_ms, defer_until_game_exit))
                    retirement_log_event("deferred_worker_started", path);
                else
                    retirement_set_requested_mode(requested_mode);
            }
        }
        retirement_watch_poll(mode, target_age, quiet_ms,
            defer_until_game_exit);
    }
    return 0;
}

int retirement_engine_start(const char *mod_dir)
{
    FILETIME start_time;
    if (!mod_dir || !*mod_dir) return 0;
    retirement_engine_set_mod_dir(mod_dir);
    GetSystemTimeAsFileTime(&start_time);
    g_retirement_watch_start_filetime =
        ((ULONGLONG)start_time.dwHighDateTime << 32)
        | (ULONGLONG)start_time.dwLowDateTime;
    if (InterlockedCompareExchange(&g_retirement_running, 1, 0) != 0)
        return 1;
    g_retirement_event = CreateEventA(NULL, FALSE, FALSE, NULL);
    if (!g_retirement_event) { InterlockedExchange(&g_retirement_running, 0); return 0; }
    g_retirement_thread = CreateThread(NULL, 0, retirement_engine_worker, NULL, 0, NULL);
    if (!g_retirement_thread) {
        CloseHandle(g_retirement_event); g_retirement_event = NULL;
        InterlockedExchange(&g_retirement_running, 0); return 0;
    }
    {
        HANDLE input_thread = CreateThread(NULL, 0,
            retirement_input_worker, NULL, 0, NULL);
        if (input_thread) CloseHandle(input_thread);
    }
    CloseHandle(g_retirement_thread); g_retirement_thread = NULL;
    return 1;
}

void retirement_engine_note_write(const char *data_path)
{
    const char *name;
    char mode[64];
    int enabled;
    int target_age;
    int defer_until_game_exit;
    unsigned quiet_ms;
    if (!data_path || !*data_path || !g_retirement_event) return;
    name = strrchr(data_path, '\\');
    if (!name || _stricmp(name + 1, "DATA") != 0) return;
    if (retirement_get_config(g_retirement_mod_dir, &enabled, mode,
            sizeof(mode), &target_age, &quiet_ms,
            &defer_until_game_exit) && enabled) {
        char requested_mode[64];
        if (retirement_take_requested_mode(requested_mode,
                sizeof(requested_mode))) {
            if (!retirement_launch_deferred_worker(data_path, requested_mode,
                    target_age, quiet_ms, defer_until_game_exit))
                retirement_set_requested_mode(requested_mode);
        }
    }
    AcquireSRWLockExclusive(&g_retirement_lock);
    lstrcpynA(g_retirement_pending_path, data_path, sizeof(g_retirement_pending_path));
    ReleaseSRWLockExclusive(&g_retirement_lock);
    SetEvent(g_retirement_event);
}
