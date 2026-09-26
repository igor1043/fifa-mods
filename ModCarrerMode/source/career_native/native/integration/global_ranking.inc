/* Publish the bounded top-150 payload for the custom ClubRanking APT. */
#include "../global_ranking.h"

static void native_publish_global_ranking(void *provider) {
    FceGlobalRankedClub *rows = NULL;
    size_t count = 0, published_count = 0;
    FceResult result;

    if (!provider) return;
    result = fce_global_ranking_build(&native_view, &rows, &count);
    if (result != FCE_OK || !rows || !count) {
        publish_int_field(provider, "CLUB_RANKING_COUNT", 0);
        fce_global_ranking_free(rows);
        return;
    }
    if (count > FCE_GLOBAL_RANK_LIMIT) count = FCE_GLOBAL_RANK_LIMIT;

    for (size_t i = 0; i < count; ++i) {
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
        ++published_count;
    }
    publish_int_field(provider, "CLUB_RANKING_COUNT", (int)published_count);
    fce_global_ranking_free(rows);
}
