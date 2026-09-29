/* Publish the top five plus the career user's own position when outside the
 * top five. Keep the legacy raw payload limited to its original first 20. */
#include "../global_ranking.h"

enum {
    NATIVE_GLOBAL_RANKING_TOP_COUNT = 5,
    NATIVE_GLOBAL_RANKING_PREVIEW_LIMIT = 6,
    NATIVE_GLOBAL_RANKING_RAW_LIMIT = 20
};

static void native_clear_global_ranking_preview(void *provider) {
    size_t i;
    if (!provider) return;
    for (i = 0; i < NATIVE_GLOBAL_RANKING_PREVIEW_LIMIT; ++i) {
        char key[64];
        snprintf(key, sizeof(key), "CLUB_RANK_PREVIEW_ROW%u", (unsigned)i);
        publish_visibility_field(provider, key, FALSE);
        snprintf(key, sizeof(key), "CLUB_RANK_PREVIEW_RANK%u", (unsigned)i);
        publish_int_field(provider, key, 0);
        publish_visibility_field(provider, key, FALSE);
        snprintf(key, sizeof(key), "CLUB_RANK_PREVIEW_LOGO%u", (unsigned)i);
        publish_int_field(provider, key, FORM_ASSET_EMPTY);
        publish_visibility_field(provider, key, FALSE);
        snprintf(key, sizeof(key), "CLUB_RANK_PREVIEW_NAME%u", (unsigned)i);
        publish_string_field(provider, key, "");
        publish_visibility_field(provider, key, FALSE);
        snprintf(key, sizeof(key), "CLUB_RANK_PREVIEW_SCORE%u", (unsigned)i);
        publish_string_field(provider, key, "");
        publish_visibility_field(provider, key, FALSE);
    }
}

static void native_publish_global_ranking_preview_row(
    void *provider, const FceGlobalRankedClub *row, size_t preview_index,
    size_t actual_rank, BOOL is_user_club) {
    char name[128] = {0};
    char display_name[160];
    char key[48];
    char score_value[32];

    native_team_name(row->team, name, sizeof(name));
    if (!name[0]) snprintf(name, sizeof(name), "Clube %d", row->team);
    for (size_t j = 0; name[j]; ++j)
        if (name[j] == '^' || name[j] == '\r' || name[j] == '\n') name[j] = ' ';
    if (is_user_club)
        snprintf(display_name, sizeof(display_name), "Meu time: %.128s", name);
    else
        snprintf(display_name, sizeof(display_name), "%.159s", name);

    snprintf(key, sizeof(key), "CLUB_RANK_PREVIEW_ROW%u", (unsigned)preview_index);
    publish_visibility_field(provider, key, TRUE);
    snprintf(key, sizeof(key), "CLUB_RANK_PREVIEW_RANK%u", (unsigned)preview_index);
    publish_int_field(provider, key, (int)actual_rank);
    publish_visibility_field(provider, key, TRUE);
    snprintf(key, sizeof(key), "CLUB_RANK_PREVIEW_LOGO%u", (unsigned)preview_index);
    publish_int_field(provider, key, row->team > 0 ? row->team : FORM_ASSET_EMPTY);
    publish_visibility_field(provider, key, row->team > 0);
    snprintf(key, sizeof(key), "CLUB_RANK_PREVIEW_NAME%u", (unsigned)preview_index);
    publish_string_field(provider, key, display_name);
    publish_visibility_field(provider, key, TRUE);
    snprintf(score_value, sizeof(score_value), "%d.%d",
        row->score_tenths / 10, row->score_tenths % 10);
    snprintf(key, sizeof(key), "CLUB_RANK_PREVIEW_SCORE%u", (unsigned)preview_index);
    publish_string_field(provider, key, score_value);
    publish_visibility_field(provider, key, TRUE);
}

static void native_publish_global_ranking(void *provider) {
    FceGlobalRankedClub *rows = NULL;
    size_t count = 0, raw_count, top_count, user_rank = 0;
    FceResult result;

    if (!provider) return;
    native_clear_global_ranking_preview(provider);
    result = fce_global_ranking_build_all(&native_view, &rows, &count);
    if (result != FCE_OK || !rows || !count) {
        publish_int_field(provider, "CLUB_RANKING_COUNT", 0);
        fce_global_ranking_free(rows);
        return;
    }
    raw_count = count < NATIVE_GLOBAL_RANKING_RAW_LIMIT
        ? count : NATIVE_GLOBAL_RANKING_RAW_LIMIT;
    top_count = count < NATIVE_GLOBAL_RANKING_TOP_COUNT
        ? count : NATIVE_GLOBAL_RANKING_TOP_COUNT;

    /* Preserve the existing ordered top-20 payload for any legacy consumer. */
    for (size_t i = 0; i < raw_count; ++i) {
        char name[96] = {0};
        char record[256];
        char key[40];
        int written;
        native_team_name(rows[i].team, name, sizeof(name));
        if (!name[0]) snprintf(name, sizeof(name), "Clube %d", rows[i].team);
        for (size_t j = 0; name[j]; ++j)
            if (name[j] == '^' || name[j] == '\r' || name[j] == '\n') name[j] = ' ';
        written = snprintf(record, sizeof(record),
            "%u^%d^%d^%d^%d^%d^%d^%s^%s",
            (unsigned)(i + 1), rows[i].team, rows[i].score_tenths,
            rows[i].overall, rows[i].competition_strength,
            rows[i].performance, rows[i].form_score, rows[i].form, name);
        if (written < 0 || (size_t)written >= sizeof(record)) break;
        snprintf(key, sizeof(key), "CLUB_RANK_ROW_%u", (unsigned)i);
        publish_string_field(provider, key, record);
    }

    for (size_t i = 0; i < top_count; ++i)
        native_publish_global_ranking_preview_row(provider, rows + i, i,
                                                   i + 1, FALSE);

    if (native_club > 0) {
        for (size_t i = 0; i < count; ++i) {
            if (rows[i].team == native_club) {
                user_rank = i + 1;
                break;
            }
        }
    }
    if (user_rank > NATIVE_GLOBAL_RANKING_TOP_COUNT)
        native_publish_global_ranking_preview_row(provider,
            rows + user_rank - 1, NATIVE_GLOBAL_RANKING_TOP_COUNT,
            user_rank, TRUE);

    publish_int_field(provider, "CLUB_RANKING_COUNT", (int)raw_count);
    fce_global_ranking_free(rows);
}
