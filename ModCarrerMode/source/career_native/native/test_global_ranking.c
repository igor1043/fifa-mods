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

    {
        unsigned char raw[64] = {0};
        FceCompNode node;
        raw[0x0a] = 1;
        raw[0x10] = 0x2c; raw[0x11] = 0x01;
        raw[0x12] = 4;
        raw[0x14] = 0x2b; raw[0x15] = 0x01;
        memcpy(raw + 0x1c, "FCE_Quarter_Finals", 19);
        CHECK(fce_decode_comp_raw(raw, sizeof(raw), &node) == FCE_OK);
        CHECK(node.stage_kind == FCE_STAGE_QUARTER_FINAL);
    }

    CHECK(fce_global_ranking_catalog_count() == 1305);
    result = fce_global_ranking_build(&empty, &rows, &count);
    CHECK(result == FCE_OK);
    CHECK(count == FCE_GLOBAL_RANK_LIMIT);
    for (size_t i = 1; i < count; ++i)
        CHECK(rows[i - 1].score_tenths >= rows[i].score_tenths);
    fce_global_ranking_free(rows);
    rows = NULL;

    result = fce_global_ranking_build_all(&empty, &rows, &count);
    CHECK(result == FCE_OK);
    CHECK(count == fce_global_ranking_catalog_count());
    CHECK(count > FCE_GLOBAL_RANK_LIMIT);
    for (size_t i = 1; i < count; ++i)
        CHECK(rows[i - 1].score_tenths >= rows[i].score_tenths);
    {
        const FceGlobalRankedClub *flamengo = find_team(rows, count, 1043);
        CHECK(flamengo != NULL);
        CHECK(flamengo->competition_strength == 80);
        CHECK(flamengo->score_tenths == 579);
    }
    {
        int lowest_team = rows[count - 1].team;
        CHECK(find_team(rows, count, lowest_team) == rows + count - 1);
        CHECK(find_team(rows, FCE_GLOBAL_RANK_LIMIT, lowest_team) == NULL);
    }
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
        result = fce_global_ranking_build_all(&model, &rows, &count);
        CHECK(result == FCE_OK);
        CHECK(count == fce_global_ranking_catalog_count());
        underdog = find_team(rows, count, teams[0]);
        CHECK(underdog != NULL);
        CHECK(underdog->performance == 100);
        CHECK(underdog->form_score == 100);
        CHECK(underdog->current_title_score == 100);
        CHECK(strcmp(underdog->form, "VVVVV") == 0);
        CHECK(underdog->score_tenths == 753);
        fce_global_ranking_free(rows);
        rows = NULL;
    }

    {
        FceCompNode nodes[] = {
            {300, -1, 3, 300, FCE_STAGE_UNKNOWN},
            {301, 300, 4, -1, FCE_STAGE_ROUND_16},
            {302, 300, 4, -1, FCE_STAGE_QUARTER_FINAL},
            {303, 300, 4, -1, FCE_STAGE_FINAL}
        };
        FceFixture fixtures[3];
        FceModel model;
        const FceGlobalRankedClub *round16;
        const FceGlobalRankedClub *quarter_final;
        const FceGlobalRankedClub *champion;
        const FceGlobalRankedClub *finalist;
        memset(fixtures, 0, sizeof(fixtures));
        memset(&model, 0, sizeof(model));
        fixtures[0].id = 1; fixtures[0].competition_object = 301;
        fixtures[0].stage = 301; fixtures[0].home = 383;
        fixtures[0].away = 1043; fixtures[0].home_score = 0;
        fixtures[0].away_score = 1; fixtures[0].played_raw = 1;
        fixtures[1].id = 2; fixtures[1].competition_object = 302;
        fixtures[1].stage = 302; fixtures[1].home = 1043;
        fixtures[1].away = 517; fixtures[1].played_raw = 0;
        fixtures[2].id = 3; fixtures[2].competition_object = 303;
        fixtures[2].stage = 303; fixtures[2].home = 1043;
        fixtures[2].away = 567; fixtures[2].home_score = 2;
        fixtures[2].away_score = 0; fixtures[2].played_raw = 1;
        model.nodes = nodes; model.node_count = sizeof(nodes) / sizeof(nodes[0]);
        model.fixtures = fixtures; model.fixture_count = sizeof(fixtures) / sizeof(fixtures[0]);
        result = fce_global_ranking_build_all(&model, &rows, &count);
        CHECK(result == FCE_OK);
        round16 = find_team(rows, count, 383);
        quarter_final = find_team(rows, count, 517);
        champion = find_team(rows, count, 1043);
        finalist = find_team(rows, count, 567);
        CHECK(round16 != NULL && quarter_final != NULL && champion != NULL);
        CHECK(finalist != NULL);
        CHECK(round16->cup_progress_score == 65);
        CHECK(quarter_final->cup_progress_score == 75);
        CHECK(finalist->cup_progress_score == 95);
        CHECK(champion->cup_progress_score == 100);
        CHECK(champion->current_title_score == 100);
        fce_global_ranking_free(rows);
        rows = NULL;
    }

    {
        FceCompNode nodes[] = {{200, -1, 3, 0}, {201, -1, 3, 0}};
        FceStanding standings[3];
        FceModel model;
        int catalog_club;
        int second_catalog_club;
        int baseline_overall;
        FceGlobalRankedClub *catalog = NULL;
        size_t catalog_count = 0;
        memset(standings, 0, sizeof(standings));
        memset(&model, 0, sizeof(model));

        result = fce_global_ranking_build_all(&empty, &catalog,
                                               &catalog_count);
        CHECK(result == FCE_OK && catalog_count > 0);
        catalog_club = catalog[0].team;
        second_catalog_club = catalog[1].team;
        baseline_overall = (catalog[0].overall + catalog[1].overall + 1) / 2;
        fce_global_ranking_free(catalog);

        standings[0].competition_object = 200;
        standings[0].team = catalog_club;
        standings[0].played = 1;
        standings[0].home_wins = 1;
        standings[1].competition_object = 200;
        standings[1].team = second_catalog_club;
        standings[1].played = 1;
        standings[1].home_wins = 1;
        standings[2].competition_object = 200;
        standings[2].team = 200000; /* custom club in a club competition */
        standings[2].played = 1;
        standings[2].away_wins = 1;
        standings[3].competition_object = 201;
        standings[3].team = 200001; /* selection in an isolated root */
        standings[3].played = 1;
        standings[3].home_wins = 1;
        model.nodes = nodes;
        model.node_count = 2;
        model.standings = standings;
        model.standing_count = 4;

        result = fce_global_ranking_build_all(&model, &rows, &count);
        CHECK(result == FCE_OK);
        CHECK(count == fce_global_ranking_catalog_count() + 1);
        CHECK(find_team(rows, count, catalog_club) != NULL);
        CHECK(find_team(rows, count, second_catalog_club) != NULL);
        CHECK(find_team(rows, count, 200000) != NULL);
        CHECK(find_team(rows, count, 200000)->overall == baseline_overall);
        CHECK(find_team(rows, count, 200001) == NULL);
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

    puts("PASS: club-only ranking, custom clubs in anchored competition roots, isolated selections, rebalanced score, form/title, and input guards");
    return 0;
}
