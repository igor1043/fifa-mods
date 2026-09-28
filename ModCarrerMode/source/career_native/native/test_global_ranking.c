#include "global_ranking.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(test) do { if (!(test)) { \
    fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #test); return 1; \
} } while (0)

static const FceGlobalRankedClub *find_team(const FceGlobalRankedClub *rows,
                                            size_t count, int team) {
    for (size_t i = 0; i < count; ++i)
        if (rows[i].team == team) return rows + i;
    return NULL;
}

int main(void) {
    FceGlobalRankedClub *rows = NULL;
    size_t count = 0;
    FceModel empty;
    FceResult result;
    memset(&empty, 0, sizeof(empty));

    CHECK(fce_global_ranking_catalog_count() == 1305);
    result = fce_global_ranking_build(&empty, &rows, &count);
    CHECK(result == FCE_OK);
    CHECK(count == FCE_GLOBAL_RANK_LIMIT);
    for (size_t i = 1; i < count; ++i)
        CHECK(rows[i - 1].score_tenths >= rows[i].score_tenths);
    fce_global_ranking_free(rows);
    rows = NULL;

    {
        FceCompNode nodes[] = {{100, -1, 3, 0}};
        const int teams[] = {130121,130123,130151,120425,120424,130090,120439,120410};
        FceStanding standings[8];
        FceFixture fixtures[5];
        FceModel model;
        const FceGlobalRankedClub *underdog;
        memset(standings, 0, sizeof(standings));
        memset(fixtures, 0, sizeof(fixtures));
        memset(&model, 0, sizeof(model));
        for (size_t i = 0; i < 8; ++i) {
            standings[i].standing_id = (int32_t)i;
            standings[i].competition_object = 100;
            standings[i].team = teams[i];
            standings[i].played = i == 0 ? 5u : 1u;
            if (i == 0) standings[i].home_wins = 5;
            else standings[i].away_losses = 1;
        }
        for (size_t i = 0; i < 5; ++i) {
            fixtures[i].id = (int32_t)i + 1;
            fixtures[i].competition_object = 100;
            fixtures[i].date_raw = (int32_t)i + 1;
            fixtures[i].home = teams[0];
            fixtures[i].away = teams[i + 1];
            fixtures[i].home_score = 2;
            fixtures[i].away_score = 0;
            fixtures[i].played_raw = 1;
        }
        model.nodes = nodes; model.node_count = 1;
        model.standings = standings; model.standing_count = 8;
        model.fixtures = fixtures; model.fixture_count = 5;
        result = fce_global_ranking_build(&model, &rows, &count);
        CHECK(result == FCE_OK);
        CHECK(count == FCE_GLOBAL_RANK_LIMIT);
        underdog = find_team(rows, count, teams[0]);
        CHECK(underdog != NULL);
        CHECK(underdog->performance == 100);
        CHECK(underdog->form_score == 100);
        CHECK(underdog->current_title_score == 100);
        CHECK(strcmp(underdog->form, "VVVVV") == 0);
        CHECK(underdog->score_tenths >= 700);
        fce_global_ranking_free(rows);
        rows = NULL;
    }

    {
        FceModel invalid;
        memset(&invalid, 0, sizeof(invalid));
        invalid.standing_count = 65537;
        result = fce_global_ranking_build(&invalid, &rows, &count);
        CHECK(result == FCE_INVALID);
        CHECK(rows == NULL && count == 0);
    }

    {
        const size_t max_rows = 65536;
        FceCompNode node = {100, -1, 3, 0};
        FceStanding *standings = calloc(max_rows, sizeof(*standings));
        FceFixture *fixtures = calloc(max_rows, sizeof(*fixtures));
        FceModel model;
        CHECK(standings != NULL && fixtures != NULL);
        memset(&model, 0, sizeof(model));
        for (size_t i = 0; i < max_rows; ++i) {
            standings[i].competition_object = 100;
            standings[i].team = 200000 + (int32_t)i;
            fixtures[i].competition_object = 100;
            fixtures[i].id = (int32_t)i;
        }
        model.nodes = &node;
        model.node_count = 1;
        model.standings = standings;
        model.standing_count = max_rows;
        model.fixtures = fixtures;
        model.fixture_count = max_rows;
        result = fce_global_ranking_build(&model, &rows, &count);
        CHECK(result == FCE_OK);
        CHECK(count == FCE_GLOBAL_RANK_LIMIT);
        for (size_t i = 1; i < count; ++i)
            CHECK(rows[i - 1].score_tenths >= rows[i].score_tenths);
        fce_global_ranking_free(rows);
        rows = NULL;
        free(standings);
        free(fixtures);
    }

    puts("PASS: empty, 150-row, underdog/form/title, maximum-size, and over-limit guard cases");
    return 0;
}
