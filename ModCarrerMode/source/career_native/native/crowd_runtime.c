#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "crowd_runtime.h"
#include "retirement_engine.h"

#define CROWD_DEFAULT_FACTOR 0.90f
#define CROWD_MIN_FACTOR 0.09f
#define CROWD_MAX_FACTOR 0.90f
#define CROWD_TARGET_CAPACITY 64
#define CROWD_REPUTATION_CAPACITY 2048
#define CROWD_LEAGUE_LINK_CAPACITY 2048
#define CROWD_LEAGUE_DEFINITION_CAPACITY 512
#define CROWD_RIVAL_CAPACITY 4096

/* The schema places this hash immediately before the known default value.
 * The full serialized record is useful as evidence, but FIFA can retain a
 * compact runtime copy with only this property key and its float value. */
static const unsigned char g_crowd_signature[] = {
    0x2E,0x4B,0x96,0xD2,0x25,0x96,0x20,0xA0,
    0x66,0x66,0x66,0x3F,
    0x00,0x00,0x00,0x00,
    0x00,0x00,0x40,0x00,
    0x00,0x00,0x00,0x00,
    0x00,0x00,0x88,0xD3,0x25,0x9F,0xA9,0xB4,0x13,0x49
};

typedef struct CrowdTarget
{
    unsigned char *value_address;
    float last_value;
} CrowdTarget;

typedef struct CrowdReputation
{
    int team_id;
    int domestic;
    int international;
} CrowdReputation;

typedef struct CrowdLeagueLink
{
    int team_id;
    int league_id;
} CrowdLeagueLink;

typedef struct CrowdLeagueDefinition
{
    int league_id;
    int level;
} CrowdLeagueDefinition;

typedef struct CrowdLeagueRating
{
    int team_id;
    int level;
} CrowdLeagueRating;

typedef struct CrowdRival
{
    int team_id1;
    int team_id2;
    int type;
} CrowdRival;

static CrowdTarget g_targets[CROWD_TARGET_CAPACITY];
static SIZE_T g_target_count;
static SRWLOCK g_target_lock = SRWLOCK_INIT;
static volatile LONG g_enabled;
static volatile LONG g_factor_bits;
static volatile LONG g_started;
static volatile LONG g_last_logged_enabled = 0;
static volatile LONG g_log_enabled;
static volatile LONG g_last_feedback_valid;
static int g_last_feedback_club;
static int g_last_feedback_opponent;
static int g_last_feedback_date;
static int g_last_feedback_round;
static DWORD g_last_scan_tick;
static char g_log_dir[MAX_PATH];
static CrowdReputation g_reputations[CROWD_REPUTATION_CAPACITY];
static SIZE_T g_reputation_count;
static CrowdLeagueRating g_league_ratings[CROWD_LEAGUE_LINK_CAPACITY];
static SIZE_T g_league_rating_count;
static CrowdRival g_rivals[CROWD_RIVAL_CAPACITY];
static SIZE_T g_rival_count;
static volatile LONG g_reputation_loaded;

static float clamp_factor(float value)
{
    if (value < CROWD_MIN_FACTOR)
        return CROWD_MIN_FACTOR;
    if (value > CROWD_MAX_FACTOR)
        return CROWD_MAX_FACTOR;
    return value;
}

static LONG float_bits(float value)
{
    LONG bits;
    memcpy(&bits, &value, sizeof(bits));
    return bits;
}

static float bits_float(LONG bits)
{
    float value;
    memcpy(&value, &bits, sizeof(value));
    return value;
}

static BOOL readable_protection(DWORD protection)
{
    if (protection & (PAGE_GUARD | PAGE_NOACCESS))
        return FALSE;
    protection &= 0xFF;
    return protection == PAGE_READONLY
        || protection == PAGE_READWRITE
        || protection == PAGE_WRITECOPY
        || protection == PAGE_EXECUTE_READ
        || protection == PAGE_EXECUTE_READWRITE
        || protection == PAGE_EXECUTE_WRITECOPY;
}

static BOOL readable_range(const void *address, SIZE_T size)
{
    MEMORY_BASIC_INFORMATION info;
    uintptr_t start = (uintptr_t)address;
    uintptr_t end;
    if (!size || start > UINTPTR_MAX - size)
        return FALSE;
    end = start + size;
    if (!VirtualQuery(address, &info, sizeof(info)))
        return FALSE;
    return info.State == MEM_COMMIT
        && readable_protection(info.Protect)
        && start >= (uintptr_t)info.BaseAddress
        && end <= (uintptr_t)info.BaseAddress + info.RegionSize;
}

static BOOL write_factor(unsigned char *address, float value)
{
    DWORD old_protection;
    DWORD ignored;
    if (!readable_range(address, sizeof(value)))
        return FALSE;
    if (!VirtualProtect(address, sizeof(value), PAGE_READWRITE, &old_protection))
        return FALSE;
    __try {
        memcpy(address, &value, sizeof(value));
    } __except(EXCEPTION_EXECUTE_HANDLER) {
        VirtualProtect(address, sizeof(value), old_protection, &ignored);
        return FALSE;
    }
    FlushInstructionCache(GetCurrentProcess(), address, sizeof(value));
    VirtualProtect(address, sizeof(value), old_protection, &ignored);
    return TRUE;
}

static FILE *open_log(void)
{
    char path[MAX_PATH];
    if (!g_log_dir[0]
        || InterlockedCompareExchange(&g_log_enabled, 0, 0) == 0)
        return NULL;
    snprintf(path, sizeof(path), "%s\\crowd_attendance_runtime.log", g_log_dir);
    return fopen(path, "ab");
}

static uint16_t database_u16(const unsigned char *address)
{
    return (uint16_t)address[0]
        | ((uint16_t)address[1] << 8);
}

static uint32_t database_u32(const unsigned char *address)
{
    return (uint32_t)address[0]
        | ((uint32_t)address[1] << 8)
        | ((uint32_t)address[2] << 16)
        | ((uint32_t)address[3] << 24);
}

static BOOL database_name_is(const unsigned char *address, const char *name)
{
    return address[0] == (unsigned char)name[0]
        && address[1] == (unsigned char)name[1]
        && address[2] == (unsigned char)name[2]
        && address[3] == (unsigned char)name[3];
}

static BOOL database_range_valid(SIZE_T offset, SIZE_T length, SIZE_T size)
{
    return offset <= size && length <= size - offset;
}

static uint32_t database_packed_integer(const unsigned char *record,
    SIZE_T record_size, uint32_t bit_offset, uint32_t bit_depth)
{
    SIZE_T byte_offset = (SIZE_T)(bit_offset / 8U);
    uint32_t shift = bit_offset % 8U;
    uint64_t packed = 0;
    uint32_t mask;
    uint32_t byte_index;

    if (!bit_depth || bit_depth > 32U || byte_offset >= record_size)
        return 0;
    if (bit_depth > 32U - shift || byte_offset + 5U > record_size)
        return 0;
    for (byte_index = 0; byte_index < 5U; ++byte_index)
        packed |= (uint64_t)record[byte_offset + byte_index]
            << (byte_index * 8U);
    mask = bit_depth == 32U ? UINT32_MAX : ((1U << bit_depth) - 1U);
    return (uint32_t)((packed >> shift) & (uint64_t)mask);
}

static void log_database_reputation(const char *path, const char *status)
{
    FILE *log = open_log();
    if (!log)
        return;
    fprintf(log,
        "reputation_source database_%s loaded=%llu leagues=%llu rivals=%llu path=%s\\n",
        status, (unsigned long long)g_reputation_count,
        (unsigned long long)g_league_rating_count,
        (unsigned long long)g_rival_count, path);
    fclose(log);
}

typedef struct DatabaseTableView
{
    SIZE_T records_offset;
    uint32_t record_size;
    uint16_t written_count;
    uint8_t field_count;
} DatabaseTableView;

static BOOL database_find_table_view(const unsigned char *database,
    SIZE_T database_size, DWORD table_count, const char *short_name,
    DatabaseTableView *view)
{
    DWORD table_index;
    SIZE_T directory_end = 0x18U + (SIZE_T)table_count * 8U;
    SIZE_T table_data_offset = directory_end + 4U;

    if (!database_range_valid(0, table_data_offset, database_size))
        return FALSE;
    for (table_index = 0; table_index < table_count; ++table_index) {
        const unsigned char *entry = database + 0x18U
            + (SIZE_T)table_index * 8U;
        SIZE_T table_offset;
        SIZE_T descriptor_offset;
        SIZE_T records_offset;
        uint32_t relative_offset = database_u32(entry + 4U);
        uint32_t record_size;
        uint16_t record_count;
        uint16_t written_count;
        uint8_t field_count;

        if (!database_name_is(entry, short_name)
            || (SIZE_T)relative_offset > database_size - table_data_offset)
            continue;
        table_offset = table_data_offset + (SIZE_T)relative_offset;
        if (!database_range_valid(table_offset, 36U, database_size))
            continue;
        record_size = database_u32(database + table_offset + 4U);
        record_count = database_u16(database + table_offset + 16U);
        written_count = database_u16(database + table_offset + 18U);
        field_count = database[table_offset + 24U];
        if (!record_size || record_size > 4096U || !field_count
            || field_count > 128U || written_count > record_count)
            continue;
        descriptor_offset = table_offset + 36U;
        if ((SIZE_T)field_count > (SIZE_MAX - descriptor_offset) / 16U)
            continue;
        records_offset = descriptor_offset + (SIZE_T)field_count * 16U;
        if ((SIZE_T)written_count >
                (SIZE_MAX - records_offset) / (SIZE_T)record_size
            || !database_range_valid(records_offset,
                (SIZE_T)written_count * (SIZE_T)record_size, database_size))
            continue;
        view->records_offset = records_offset;
        view->record_size = record_size;
        view->written_count = written_count;
        view->field_count = field_count;
        return TRUE;
    }
    return FALSE;
}

static BOOL database_find_field(const unsigned char *database,
    const DatabaseTableView *table, const char *short_name,
    uint32_t *bit_offset, uint32_t *bit_depth)
{
    uint32_t field_index;
    uint32_t total_bits = table->record_size * 8U;
    for (field_index = 0; field_index < table->field_count; ++field_index) {
        const unsigned char *descriptor = database + table->records_offset
            - (SIZE_T)table->field_count * 16U
            + (SIZE_T)field_index * 16U;
        uint32_t storage_type = database_u32(descriptor);
        uint32_t offset = database_u32(descriptor + 4U);
        uint32_t depth = database_u32(descriptor + 12U);
        if (storage_type != 3U || !depth || depth > 32U
            || offset > total_bits || depth > total_bits - offset
            || !database_name_is(descriptor + 8U, short_name))
            continue;
        *bit_offset = offset;
        *bit_depth = depth;
        return TRUE;
    }
    return FALSE;
}

static void append_rival(int team_id1, int team_id2, int type)
{
    if (team_id1 <= 0 || team_id2 <= 0 || team_id1 == team_id2
        || g_rival_count >= CROWD_RIVAL_CAPACITY)
        return;
    g_rivals[g_rival_count].team_id1 = team_id1;
    g_rivals[g_rival_count].team_id2 = team_id2;
    g_rivals[g_rival_count].type = type;
    ++g_rival_count;
}

/* FIFA 16 stores reputation, league tier and rivalries in its proprietary
 * T3DB database. This reader intentionally covers only the verified fields
 * required by the crowd model. */
static BOOL load_team_reputation_from_database(void)
{
    char path[MAX_PATH];
    HANDLE file = INVALID_HANDLE_VALUE;
    LARGE_INTEGER file_size;
    unsigned char *database = NULL;
    SIZE_T database_size;
    SIZE_T read_offset;
    DWORD table_count;
    DatabaseTableView teams_table;
    DatabaseTableView leagues_table;
    DatabaseTableView links_table;
    DatabaseTableView rivals_table;
    CrowdLeagueDefinition league_definitions[CROWD_LEAGUE_DEFINITION_CAPACITY];
    CrowdLeagueLink league_links[CROWD_LEAGUE_LINK_CAPACITY];
    SIZE_T league_definition_count = 0;
    SIZE_T league_link_count = 0;
    BOOL success = FALSE;

    if (!g_log_dir[0])
        return FALSE;
    snprintf(path, sizeof(path), "%s\\..\\data\\db\\fifa_ng_db.db",
        g_log_dir);
    file = CreateFileA(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
        NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE)
        goto cleanup;
    if (!GetFileSizeEx(file, &file_size) || file_size.QuadPart < 0 ||
        (uint64_t)file_size.QuadPart > 64ULL * 1024ULL * 1024ULL)
        goto cleanup;
    database_size = (SIZE_T)file_size.QuadPart;
    if (database_size < 0x20U)
        goto cleanup;
    database = (unsigned char *)HeapAlloc(GetProcessHeap(), 0, database_size);
    if (!database)
        goto cleanup;
    read_offset = 0;
    while (read_offset < database_size) {
        DWORD request = (DWORD)((database_size - read_offset) > 0x100000U
            ? 0x100000U : database_size - read_offset);
        DWORD bytes_read = 0;
        if (!ReadFile(file, database + read_offset, request, &bytes_read, NULL)
            || !bytes_read)
            goto cleanup;
        read_offset += bytes_read;
    }
    if (database[0] != 0x44 || database[1] != 0x42
        || database[2] != 0x00 || database[3] != 0x08
        || database[4] != 0x00 || database[5] != 0x00
        || database[6] != 0x00 || database[7] != 0x00)
        goto cleanup;
    if (database_u32(database + 0x08) > database_size
        || database_u32(database + 0x08) < 0x20U)
        goto cleanup;
    table_count = database_u32(database + 0x10);
    if (!table_count || table_count > 4096U)
        goto cleanup;

    memset(league_definitions, 0, sizeof(league_definitions));
    memset(league_links, 0, sizeof(league_links));
    if (!database_find_table_view(database, database_size, table_count,
            "lyxL", &teams_table))
        goto cleanup;
    {
        uint32_t team_bit, team_depth, domestic_bit, domestic_depth;
        uint32_t international_bit, international_depth;
        uint32_t rival_bit, rival_depth;
        BOOL rival_field;
        uint16_t row;
        if (!database_find_field(database, &teams_table, "mCXg",
                &team_bit, &team_depth)
            || !database_find_field(database, &teams_table, "ppLE",
                &domestic_bit, &domestic_depth)
            || !database_find_field(database, &teams_table, "edvw",
                &international_bit, &international_depth))
            goto cleanup;
        rival_field=database_find_field(database, &teams_table, "erSL",
            &rival_bit, &rival_depth);
        for (row = 0; row < teams_table.written_count
            && g_reputation_count < CROWD_REPUTATION_CAPACITY; ++row) {
            const unsigned char *record = database + teams_table.records_offset
                + (SIZE_T)row * (SIZE_T)teams_table.record_size;
            uint32_t team;
            uint32_t domestic;
            uint32_t international;
            if (record[teams_table.record_size - 1U] & 0x80U)
                continue;
            team = database_packed_integer(record, teams_table.record_size,
                team_bit, team_depth) + 1U;
            domestic = database_packed_integer(record, teams_table.record_size,
                domestic_bit, domestic_depth);
            international = database_packed_integer(record, teams_table.record_size,
                international_bit, international_depth);
            if (!team || domestic > 20U || international > 20U)
                continue;
            g_reputations[g_reputation_count].team_id = (int)team;
            g_reputations[g_reputation_count].domestic = (int)domestic;
            g_reputations[g_reputation_count].international = (int)international;
            ++g_reputation_count;
            if (rival_field) {
                uint32_t rival = database_packed_integer(record,
                    teams_table.record_size, rival_bit, rival_depth) + 1U;
                append_rival((int)team, (int)rival, 1);
            }
        }
    }

    if (database_find_table_view(database, database_size, table_count,
            "LbKk", &rivals_table)) {
        uint32_t team1_bit, team1_depth, team2_bit, team2_depth;
        uint32_t type_bit, type_depth;
        uint16_t row;
        if (database_find_field(database, &rivals_table, "fmFo",
                &team1_bit, &team1_depth)
            && database_find_field(database, &rivals_table, "afAW",
                &team2_bit, &team2_depth)
            && database_find_field(database, &rivals_table, "ytXF",
                &type_bit, &type_depth)) {
            for (row = 0; row < rivals_table.written_count; ++row) {
                const unsigned char *record = database + rivals_table.records_offset
                    + (SIZE_T)row * (SIZE_T)rivals_table.record_size;
                uint32_t team1, team2, type;
                if (record[rivals_table.record_size - 1U] & 0x80U)
                    continue;
                team1=database_packed_integer(record,rivals_table.record_size,
                    team1_bit,team1_depth)+1U;
                team2=database_packed_integer(record,rivals_table.record_size,
                    team2_bit,team2_depth)+1U;
                type=database_packed_integer(record,rivals_table.record_size,
                    type_bit,type_depth);
                append_rival((int)team1,(int)team2,(int)type);
            }
        }
    }

    if (database_find_table_view(database, database_size, table_count,
            "onMQ", &leagues_table)) {
        uint32_t league_id_bit, league_id_depth, level_bit, level_depth;
        uint16_t row;
        if (database_find_field(database, &leagues_table, "aQrQ",
                &league_id_bit, &league_id_depth)
            && database_find_field(database, &leagues_table, "paPI",
                &level_bit, &level_depth)) {
            for (row = 0; row < leagues_table.written_count
                && league_definition_count < CROWD_LEAGUE_DEFINITION_CAPACITY;
                ++row) {
                const unsigned char *record = database + leagues_table.records_offset
                    + (SIZE_T)row * (SIZE_T)leagues_table.record_size;
                int league_id, level;
                if (record[leagues_table.record_size - 1U] & 0x80U)
                    continue;
                league_id=(int)database_packed_integer(record,
                    leagues_table.record_size,league_id_bit,league_id_depth)+1;
                level=(int)database_packed_integer(record,
                    leagues_table.record_size,level_bit,level_depth)+1;
                if (league_id>0 && level>=1 && level<=7) {
                    league_definitions[league_definition_count].league_id=league_id;
                    league_definitions[league_definition_count].level=level;
                    ++league_definition_count;
                }
            }
        }
    }

    if (database_find_table_view(database, database_size, table_count,
            "qdZF", &links_table)) {
        uint32_t team_bit, team_depth, league_id_bit, league_id_depth;
        uint16_t row;
        if (database_find_field(database, &links_table, "mCXg",
                &team_bit, &team_depth)
            && database_find_field(database, &links_table, "aQrQ",
                &league_id_bit, &league_id_depth)) {
            for (row = 0; row < links_table.written_count
                && league_link_count < CROWD_LEAGUE_LINK_CAPACITY; ++row) {
                const unsigned char *record = database + links_table.records_offset
                    + (SIZE_T)row * (SIZE_T)links_table.record_size;
                if (record[links_table.record_size - 1U] & 0x80U)
                    continue;
                league_links[league_link_count].team_id=(int)
                    (database_packed_integer(record,links_table.record_size,
                        team_bit,team_depth)+1U);
                league_links[league_link_count].league_id=(int)
                    (database_packed_integer(record,links_table.record_size,
                        league_id_bit,league_id_depth)+1U);
                ++league_link_count;
            }
        }
    }

    {
        SIZE_T link_index, definition_index;
        for (link_index = 0; link_index < league_link_count
            && g_league_rating_count < CROWD_LEAGUE_LINK_CAPACITY; ++link_index) {
            for (definition_index = 0; definition_index < league_definition_count;
                ++definition_index) {
                if (league_links[link_index].league_id ==
                    league_definitions[definition_index].league_id) {
                    g_league_ratings[g_league_rating_count].team_id=
                        league_links[link_index].team_id;
                    g_league_ratings[g_league_rating_count].level=
                        league_definitions[definition_index].level;
                    ++g_league_rating_count;
                    break;
                }
            }
        }
    }

    success = g_reputation_count != 0;
    if (!success)
        goto cleanup;
    log_database_reputation(path, "loaded");

cleanup:
    if (database)
        HeapFree(GetProcessHeap(), 0, database);
    if (file != INVALID_HANDLE_VALUE)
        CloseHandle(file);
    if (!success)
        log_database_reputation(path, "unavailable");
    return success;
}

static void load_team_reputation(void)
{
    if (InterlockedCompareExchange(&g_reputation_loaded, 1, 0) != 0)
        return;
    (void)load_team_reputation_from_database();
}

float crowd_runtime_team_reputation(int team_id)
{
    SIZE_T index;
    load_team_reputation();
    for(index=0;index<g_reputation_count;++index) {
        const CrowdReputation *item=g_reputations+index;
        if(item->team_id==team_id)
            return ((float)item->domestic+(float)item->international)/40.0f;
    }
    return 0.50f;
}

int crowd_runtime_team_reputation_available(int team_id)
{
    SIZE_T index;
    load_team_reputation();
    for (index = 0; index < g_reputation_count; ++index)
        if (g_reputations[index].team_id == team_id)
            return 1;
    return 0;
}

float crowd_runtime_league_reputation(int team_id)
{
    SIZE_T index;
    load_team_reputation();
    for (index = 0; index < g_league_rating_count; ++index) {
        const CrowdLeagueRating *item = g_league_ratings + index;
        if (item->team_id == team_id) {
            float level = (float)item->level;
            /* Keep lower leagues relevant: level 1 is 1.00, level 7 is
             * 0.30, with a linear scale between them. */
            return 0.30f + 0.70f * (1.0f - ((level - 1.0f) / 6.0f));
        }
    }
    return 0.50f;
}

float crowd_runtime_rivalry(int team_id, int opponent_id)
{
    SIZE_T index;
    float best = 0.0f;
    load_team_reputation();
    if (team_id <= 0 || opponent_id <= 0 || team_id == opponent_id)
        return 0.0f;
    for (index = 0; index < g_rival_count; ++index) {
        const CrowdRival *item = g_rivals + index;
        BOOL matches = (item->team_id1 == team_id
                && item->team_id2 == opponent_id)
            || (item->team_id1 == opponent_id
                && item->team_id2 == team_id);
        float score;
        if (!matches)
            continue;
        /* Type 1 is the database's strongest derby/classic category.
         * Type 2 is a regional rivalry; type 0 is a lighter rivalry. */
        score = item->type == 1 ? 1.0f :
            (item->type == 2 ? 0.75f : 0.45f);
        if (score > best)
            best = score;
    }
    return best;
}

static void log_decision(const CrowdDecision *decision)
{
    FILE *log = open_log();
    if (!log)
        return;
    if (decision) {
        fprintf(log,
            "decision enabled=%d club=%d competition=%d rank=%d/%d played=%d "
            "form=%.3f reputation=%.3f league=%.3f rivalry=%.3f "
            "position=%.3f progress=%.3f danger=%.3f "
            "last_result=%d last_margin=%d streak=%d streak_sign=%d gap_safety=%d "
            "momentum=%.3f escape=%.3f importance=%.3f phase=%.3f factor=%.3f "
            "next_opponent=%d home=%d date=%d round=%d\\n",
            decision->enabled, decision->club_id, decision->competition_id,
            decision->rank, decision->team_count, decision->played,
            decision->form, decision->reputation, decision->league_reputation,
            decision->rivalry, decision->position_score,
            decision->season_progress, decision->danger,
            decision->last_result, decision->last_margin, decision->streak,
            decision->streak_sign, decision->points_gap_to_safety,
            decision->momentum, decision->escape_opportunity,
            decision->importance, decision->phase,
            decision->factor, decision->next_opponent, decision->next_is_home,
            decision->next_date, decision->next_round);
    } else {
        fputs("decision enabled=0 reason=context_reset\\n", log);
    }
    fclose(log);
}

static BOOL target_known(unsigned char *address)
{
    SIZE_T index;
    for (index = 0; index < g_target_count; ++index)
        if (g_targets[index].value_address == address)
            return TRUE;
    return FALSE;
}

static void scan_region_safe(unsigned char *base, SIZE_T size)
{
    SYSTEM_INFO system_info;
    unsigned char page_buffer[0x1000 + 32];
    SIZE_T page_size;
    SIZE_T page_offset;
    const SIZE_T key_size = 8;
    GetSystemInfo(&system_info);
    page_size = system_info.dwPageSize ? (SIZE_T)system_info.dwPageSize : 0x1000U;
    if (page_size > 0x1000U)
        page_size = 0x1000U;
    for (page_offset = 0; page_offset < size
        && g_target_count < CROWD_TARGET_CAPACITY;
        page_offset += page_size) {
        SIZE_T request = size - page_offset;
        SIZE_T bytes_read = 0;
        SIZE_T index;
        if (request > page_size + key_size + sizeof(float) - 1U)
            request = page_size + key_size + sizeof(float) - 1U;
        /* Read through the OS into a private page buffer. If the game unloads
         * the source between VirtualQuery calls, this fails safely instead of
         * dereferencing the stale address in the scanner thread. */
        if (!ReadProcessMemory(GetCurrentProcess(), base + page_offset,
                page_buffer, request, &bytes_read) ||
            bytes_read < key_size + sizeof(float))
            continue;
        for (index = 0; index + key_size + sizeof(float) <= bytes_read;
            ++index) {
            unsigned char *value = base + page_offset + index + key_size;
            float loaded_value;
            if (memcmp(page_buffer + index, g_crowd_signature, key_size) != 0)
                continue;
            /* The actual game record must contain a plausible multiplier. */
            memcpy(&loaded_value, page_buffer + index + key_size,
                sizeof(loaded_value));
            if (!(loaded_value >= 0.05f && loaded_value <= 1.20f))
                continue;
            if (!target_known(value) && g_target_count < CROWD_TARGET_CAPACITY) {
                g_targets[g_target_count].value_address = value;
                g_targets[g_target_count].last_value = loaded_value;
                ++g_target_count;
            }
            index += key_size - 1U;
        }
    }
}

static void scan_loaded_attribdb(void)
{
    SYSTEM_INFO system_info;
    unsigned char *cursor;
    uintptr_t maximum;
    GetSystemInfo(&system_info);
    cursor = (unsigned char *)system_info.lpMinimumApplicationAddress;
    maximum = (uintptr_t)system_info.lpMaximumApplicationAddress;
    while ((uintptr_t)cursor < maximum && g_target_count < CROWD_TARGET_CAPACITY) {
        MEMORY_BASIC_INFORMATION info;
        SIZE_T queried = VirtualQuery(cursor, &info, sizeof(info));
        uintptr_t next;
        if (!queried)
            break;
        next = (uintptr_t)info.BaseAddress + info.RegionSize;
        if (next <= (uintptr_t)cursor)
            break;
        /* Resource sections can be MEM_IMAGE. Do not inspect executable
         * image pages, but include non-executable read-only resource data. */
        if (info.State == MEM_COMMIT && readable_protection(info.Protect)
            && (info.Protect & (PAGE_EXECUTE | PAGE_EXECUTE_READ |
                PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY)) == 0)
            scan_region_safe((unsigned char *)info.BaseAddress, info.RegionSize);
        cursor = (unsigned char *)next;
    }
}

static void prune_targets(void)
{
    SIZE_T read = 0;
    SIZE_T index;
    for (index = 0; index < g_target_count; ++index) {
        CrowdTarget target = g_targets[index];
        if (!readable_range(target.value_address, sizeof(float)))
            continue;
        g_targets[read++] = target;
    }
    g_target_count = read;
}

static void restore_targets(void)
{
    SIZE_T index;
    prune_targets();
    for (index = 0; index < g_target_count; ++index) {
        if (write_factor(g_targets[index].value_address, CROWD_DEFAULT_FACTOR))
            g_targets[index].last_value = CROWD_DEFAULT_FACTOR;
    }
    g_target_count = 0;
}

static void apply_targets(float factor)
{
    SIZE_T index;
    for (index = 0; index < g_target_count; ++index) {
        if (write_factor(g_targets[index].value_address, factor))
            g_targets[index].last_value = factor;
    }
}

static void log_patch_state(float factor)
{
    FILE *log = open_log();
    if (!log)
        return;
    fprintf(log, "patch targets=%llu factor=%.3f\\n",
        (unsigned long long)g_target_count, factor);
    fclose(log);
}

static DWORD WINAPI crowd_worker(void *unused)
{
    (void)unused;
    for (;;) {
        BOOL enabled = InterlockedCompareExchange(&g_enabled, 0, 0) != 0;
        AcquireSRWLockExclusive(&g_target_lock);
        if (!enabled) {
            if (g_target_count)
                restore_targets();
        } else {
            prune_targets();
            if (!g_target_count
                && GetTickCount() - g_last_scan_tick >= 500) {
                g_last_scan_tick = GetTickCount();
                scan_loaded_attribdb();
                log_patch_state(bits_float(InterlockedCompareExchange(
                    &g_factor_bits, float_bits(CROWD_DEFAULT_FACTOR), 0)));
            }
            if (g_target_count) {
                float factor = clamp_factor(bits_float(
                    InterlockedCompareExchange(&g_factor_bits,
                        float_bits(CROWD_DEFAULT_FACTOR), 0)));
                apply_targets(factor);
            }
        }
        ReleaseSRWLockExclusive(&g_target_lock);
        Sleep(750);
    }
}

void crowd_runtime_start(const char *log_dir)
{
    if (log_dir)
        lstrcpynA(g_log_dir, log_dir, sizeof(g_log_dir));
    InterlockedExchange(&g_log_enabled,
        retirement_engine_local_logging_enabled(g_log_dir));
    if (InterlockedCompareExchange(&g_started, 1, 0) != 0)
        return;
    InterlockedExchange(&g_factor_bits, float_bits(CROWD_DEFAULT_FACTOR));
    /* The dump confirmed that the heuristic runtime memory write can select a
     * false positive and corrupt a game object. Keep the career decision
     * engine active, but do not scan or write arbitrary FIFA memory until a
     * deterministic game-owned target is available. */
    {
        FILE *log = open_log();
        if (log) {
            fputs("attendance_scanner disabled_after_dump_safe_mode\n", log);
            fclose(log);
        }
    }
}

void crowd_runtime_disable(void)
{
    InterlockedExchange(&g_enabled, 0);
    InterlockedExchange(&g_last_feedback_valid, 0);
    if (InterlockedCompareExchange(&g_last_logged_enabled, 0, 1) == 1)
        log_decision(NULL);
}

void crowd_runtime_set_decision(const CrowdDecision *decision)
{
    CrowdDecision copy;
    int feedback_changed;
    int percent;
    char feedback[256];
    if (!decision || !decision->enabled) {
        crowd_runtime_disable();
        return;
    }
    copy = *decision;
    copy.factor = clamp_factor(copy.factor);
    feedback_changed = !InterlockedCompareExchange(&g_last_feedback_valid, 0, 0)
        || g_last_feedback_club != copy.club_id
        || g_last_feedback_opponent != copy.next_opponent
        || g_last_feedback_date != copy.next_date
        || g_last_feedback_round != copy.next_round;
    if (feedback_changed && copy.next_opponent > 0 && copy.next_date > 0) {
        percent = (int)(copy.factor * 100.0f + 0.5f);
        if (percent < 9) percent = 9;
        if (percent > 90) percent = 90;
        snprintf(feedback, sizeof(feedback),
            "Torcida calculada: %d%%.\nPesos aplicados para a proxima partida.",
            percent);
        retirement_engine_show_feedback(feedback, 0);
        g_last_feedback_club = copy.club_id;
        g_last_feedback_opponent = copy.next_opponent;
        g_last_feedback_date = copy.next_date;
        g_last_feedback_round = copy.next_round;
        InterlockedExchange(&g_last_feedback_valid, 1);
    }
    InterlockedExchange(&g_factor_bits, float_bits(copy.factor));
    InterlockedExchange(&g_enabled, 1);
    if (InterlockedCompareExchange(&g_last_logged_enabled, 1, 0) == 0)
        log_decision(&copy);
    else {
        FILE *log = open_log();
        if (log) {
            fprintf(log, "decision_update club=%d competition=%d rank=%d/%d reputation=%.3f league=%.3f rivalry=%.3f position=%.3f progress=%.3f danger=%.3f last_result=%d last_margin=%d streak=%d gap_safety=%d momentum=%.3f escape=%.3f factor=%.3f\\n",
                copy.club_id, copy.competition_id, copy.rank, copy.team_count,
                copy.reputation, copy.league_reputation, copy.rivalry,
                copy.position_score, copy.season_progress,
                copy.danger, copy.last_result, copy.last_margin, copy.streak,
                copy.points_gap_to_safety, copy.momentum,
                copy.escape_opportunity, copy.factor);
            fclose(log);
        }
    }
}
