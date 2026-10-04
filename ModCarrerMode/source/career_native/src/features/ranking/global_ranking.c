#include "global_ranking.h"
#include <stdlib.h>
#include <string.h>

/* The game parser already rejects tables above 65,536 rows. Keep the same
 * explicit input ceiling here so malformed snapshots fail closed. */
enum { GLOBAL_INPUT_LIMIT = 65536, GLOBAL_DEFAULT_VALUE = 50 };

typedef struct {
    int32_t team_id;
    int32_t domestic_prestige;
    int32_t international_prestige;
    int32_t overall;
    int32_t base_competition_strength;
} GlobalClubBase;

#include "../../catalogs/global_clubs.inc"
#include "../../catalogs/global_brazil_league.inc"

typedef struct {
    int32_t team;
    int32_t static_record;
    int32_t domestic_prestige;
    int32_t international_prestige;
    int32_t overall;
    int32_t competition_strength;
    int32_t performance;
    int32_t form_score;
    int32_t title_score;
    int32_t league_position_score;
    int32_t cup_progress_score;
    int32_t played;
    int32_t live;
    char form[FCE_GLOBAL_FORM_LENGTH + 1];
    int32_t selected_league_size;
} RankingCandidate;

typedef struct {
    int32_t root;
    int32_t team;
    int32_t wins;
    int32_t draws;
    int32_t losses;
    int32_t played;
    int32_t points;
    int32_t performance;
    int32_t form_score;
    int32_t title_score;
    int32_t competition_strength;
    char form[FCE_GLOBAL_FORM_LENGTH + 1];
} LiveStanding;

typedef struct {
    int32_t root;
    int32_t team;
    int32_t date;
    int32_t fixture_id;
    char result;
} FormEvent;

typedef struct {
    int32_t root;
    int32_t team;
    int32_t score;
    int32_t count;
    char form[FCE_GLOBAL_FORM_LENGTH + 1];
} TeamForm;

typedef struct {
    int32_t root;
    int32_t fixture_count;
    int32_t unplayed_count;
} CompetitionStatus;

typedef struct {
    int32_t root;
    int32_t team;
    const GlobalClubBase *base;
} RootClubReference;

typedef struct {
    int32_t root;
    int32_t domestic_prestige;
    int32_t international_prestige;
    int32_t overall;
    int32_t competition_strength;
} RootClubBaseline;

static const size_t global_catalog_count =
    sizeof(g_global_club_catalog) / sizeof(g_global_club_catalog[0]);

/* The raw save average understates the competitive level of the Brazilian
 * top flight because it is based only on the roster OVR average. Keep a
 * conservative floor so the league is not pushed below its continental
 * context, while leaving strong seasons and individual performance decisive.
 */
enum { GLOBAL_BRAZIL_COMPETITION_FLOOR = 80 };

static int clamp_score(double value);

static int is_brazilian_league_team(int32_t team) {
    size_t i;
    for (i = 0; i < g_brazilian_league_team_count; ++i)
        if (g_brazilian_league_teams[i] == team) return 1;
    return 0;
}

static int calibrate_competition_strength(int32_t team, int strength) {
    if (is_brazilian_league_team(team) &&
        strength < GLOBAL_BRAZIL_COMPETITION_FLOOR)
        strength = GLOBAL_BRAZIL_COMPETITION_FLOOR;
    return clamp_score((double)strength);
}

static int is_brazilian_competition(const LiveStanding *rows,
                                    size_t start, size_t end) {
    size_t brazilian = 0;
    size_t total = end - start;
    if (total < 4) return 0;
    for (size_t i = start; i < end; ++i)
        if (is_brazilian_league_team(rows[i].team)) ++brazilian;
    return brazilian >= 4 && brazilian * 2 >= total;
}

static void *checked_calloc(size_t count, size_t size) {
    if (!count || !size || count > SIZE_MAX / size) return NULL;
    return calloc(count, size);
}

static const GlobalClubBase *base_for_team(int32_t team) {
    size_t low = 0, high = global_catalog_count;
    while (low < high) {
        size_t middle = low + (high - low) / 2;
        if (g_global_club_catalog[middle].team_id < team) low = middle + 1;
        else high = middle;
    }
    if (low < global_catalog_count &&
        g_global_club_catalog[low].team_id == team)
        return g_global_club_catalog + low;
    return NULL;
}

static int compare_candidate_team(const void *left, const void *right) {
    const RankingCandidate *a = left, *b = right;
    if (a->team != b->team) return a->team < b->team ? -1 : 1;
    if (a->static_record != b->static_record)
        return a->static_record > b->static_record ? -1 : 1;
    if (a->overall != b->overall) return a->overall > b->overall ? -1 : 1;
    if (a->domestic_prestige != b->domestic_prestige)
        return a->domestic_prestige > b->domestic_prestige ? -1 : 1;
    if (a->international_prestige != b->international_prestige)
        return a->international_prestige > b->international_prestige ? -1 : 1;
    return 0;
}

static int compare_live_root_team(const void *left, const void *right) {
    const LiveStanding *a = left, *b = right;
    if (a->root != b->root) return a->root < b->root ? -1 : 1;
    if (a->team != b->team) return a->team < b->team ? -1 : 1;
    if (a->played != b->played) return a->played > b->played ? -1 : 1;
    if (a->points != b->points) return a->points > b->points ? -1 : 1;
    return 0;
}

static int compare_live_rank(const void *left, const void *right) {
    const LiveStanding *a = left, *b = right;
    if (a->root != b->root) return a->root < b->root ? -1 : 1;
    if (a->points != b->points) return a->points > b->points ? -1 : 1;
    if (a->wins != b->wins) return a->wins > b->wins ? -1 : 1;
    if (a->team != b->team) return a->team < b->team ? -1 : 1;
    return 0;
}

static int compare_form_event(const void *left, const void *right) {
    const FormEvent *a = left, *b = right;
    if (a->root != b->root) return a->root < b->root ? -1 : 1;
    if (a->team != b->team) return a->team < b->team ? -1 : 1;
    if (a->date != b->date) return a->date > b->date ? -1 : 1;
    if (a->fixture_id != b->fixture_id)
        return a->fixture_id > b->fixture_id ? -1 : 1;
    return 0;
}

static int compare_competition_status(const void *left, const void *right) {
    const CompetitionStatus *a = left, *b = right;
    if (a->root != b->root) return a->root < b->root ? -1 : 1;
    return 0;
}

static int compare_int32(const void *left, const void *right) {
    int32_t a = *(const int32_t *)left;
    int32_t b = *(const int32_t *)right;
    return a < b ? -1 : a > b ? 1 : 0;
}

static int compare_root_club_reference(const void *left, const void *right) {
    const RootClubReference *a = left, *b = right;
    if (a->root != b->root) return a->root < b->root ? -1 : 1;
    if (a->team != b->team) return a->team < b->team ? -1 : 1;
    return 0;
}

static int int32_in_sorted(const int32_t *values, size_t count, int32_t value) {
    size_t low = 0, high = count;
    while (low < high) {
        size_t middle = low + (high - low) / 2;
        if (values[middle] < value) low = middle + 1;
        else high = middle;
    }
    return low < count && values[low] == value;
}

static FceResult build_root_club_baselines(const FceModel *model,
                                           RootClubBaseline **out,
                                           size_t *out_count) {
    RootClubReference *references = NULL;
    RootClubBaseline *baselines = NULL;
    size_t reference_count = 0, baseline_count = 0;

    *out = NULL;
    *out_count = 0;
    if (!model->standing_count) return FCE_OK;
    references = checked_calloc(model->standing_count, sizeof(*references));
    if (!references) return FCE_NO_MEMORY;
    for (size_t i = 0; i < model->standing_count; ++i) {
        const FceStanding *standing = model->standings + i;
        int root = fce_model_ancestor(model, standing->competition_object, 3);
        const GlobalClubBase *base = base_for_team(standing->team);
        if (root <= 0 || !base) continue;
        references[reference_count++] = (RootClubReference){
            root, standing->team, base
        };
    }
    if (!reference_count) {
        free(references);
        return FCE_OK;
    }
    qsort(references, reference_count, sizeof(*references),
          compare_root_club_reference);
    baselines = checked_calloc(reference_count, sizeof(*baselines));
    if (!baselines) {
        free(references);
        return FCE_NO_MEMORY;
    }
    for (size_t read = 0; read < reference_count;) {
        size_t next = read, unique_count = 0;
        int64_t domestic = 0, international = 0, overall = 0, strength = 0;
        RootClubBaseline *baseline = baselines + baseline_count++;
        baseline->root = references[read].root;
        while (next < reference_count &&
               references[next].root == baseline->root) {
            const RootClubReference *reference = references + next;
            size_t after_team = next + 1;
            while (after_team < reference_count &&
                   references[after_team].root == reference->root &&
                   references[after_team].team == reference->team)
                ++after_team;
            domestic += reference->base->domestic_prestige;
            international += reference->base->international_prestige;
            overall += reference->base->overall;
            strength += reference->base->base_competition_strength;
            ++unique_count;
            next = after_team;
        }
        baseline->domestic_prestige = (int32_t)((domestic + unique_count / 2) /
                                                 unique_count);
        baseline->international_prestige = (int32_t)(
            (international + unique_count / 2) / unique_count);
        baseline->overall = (int32_t)((overall + unique_count / 2) / unique_count);
        baseline->competition_strength = (int32_t)(
            (strength + unique_count / 2) / unique_count);
        read = next;
    }
    free(references);
    *out = baselines;
    *out_count = baseline_count;
    return FCE_OK;
}

static const RootClubBaseline *baseline_for_root(
    const RootClubBaseline *baselines, size_t count, int32_t root) {
    size_t low = 0, high = count;
    while (low < high) {
        size_t middle = low + (high - low) / 2;
        if (baselines[middle].root < root) low = middle + 1;
        else high = middle;
    }
    return low < count && baselines[low].root == root
        ? baselines + low : NULL;
}

static int64_t candidate_score_numerator(const RankingCandidate *candidate) {
    int64_t reputation = ((int64_t)candidate->domestic_prestige * 70 +
                          (int64_t)candidate->international_prestige * 30) / 20;

    /* Current campaign is deliberately more important than the static
     * profile.  A confirmed title is worth 20%; position in a league is
     * worth 20%; and progress in a cup is worth 15%.  The two campaign
     * signals default to 50 when the snapshot does not expose that
     * competition, so missing data does not create a free penalty. */
    return reputation * 10 + (int64_t)candidate->overall * 10 +
        (int64_t)candidate->competition_strength * 5 +
        (int64_t)candidate->performance * 15 +
        (int64_t)candidate->form_score * 5 +
        (int64_t)candidate->title_score * 20 +
        (int64_t)candidate->league_position_score * 20 +
        (int64_t)candidate->cup_progress_score * 15;
}

static int compare_candidate_score(const void *left, const void *right) {
    const RankingCandidate *a = left, *b = right;
    int64_t score_a = candidate_score_numerator(a);
    int64_t score_b = candidate_score_numerator(b);
    if (score_a != score_b) return score_a > score_b ? -1 : 1;
    if (a->team != b->team) return a->team < b->team ? -1 : 1;
    return 0;
}

static size_t find_candidate(const RankingCandidate *items, size_t count,
                             int32_t team) {
    size_t low = 0, high = count;
    while (low < high) {
        size_t middle = low + (high - low) / 2;
        if (items[middle].team < team) low = middle + 1;
        else high = middle;
    }
    return low < count && items[low].team == team ? low : count;
}

static size_t find_form(const TeamForm *items, size_t count,
                        int32_t root, int32_t team) {
    size_t low = 0, high = count;
    while (low < high) {
        size_t middle = low + (high - low) / 2;
        if (items[middle].root < root ||
            (items[middle].root == root && items[middle].team < team))
            low = middle + 1;
        else high = middle;
    }
    return low < count && items[low].root == root && items[low].team == team
        ? low : count;
}

static size_t find_competition_status(const CompetitionStatus *items,
                                     size_t count, int32_t root) {
    size_t low = 0, high = count;
    while (low < high) {
        size_t middle = low + (high - low) / 2;
        if (items[middle].root < root) low = middle + 1;
        else high = middle;
    }
    return low < count && items[low].root == root ? low : count;
}

static int clamp_score(double value) {
    if (value < 0.0) value = 0.0;
    if (value > 100.0) value = 100.0;
    return (int)(value + 0.5);
}

static void init_candidate(RankingCandidate *out, int32_t team,
                           const GlobalClubBase *base) {
    memset(out, 0, sizeof(*out));
    out->team = team;
    out->performance = GLOBAL_DEFAULT_VALUE;
    out->form_score = GLOBAL_DEFAULT_VALUE;
    out->title_score = GLOBAL_DEFAULT_VALUE;
    out->league_position_score = GLOBAL_DEFAULT_VALUE;
    out->cup_progress_score = GLOBAL_DEFAULT_VALUE;
    out->competition_strength = GLOBAL_DEFAULT_VALUE;
    out->overall = GLOBAL_DEFAULT_VALUE;
    out->form[0] = '-';
    if (base) {
        out->static_record = 1;
        out->domestic_prestige = base->domestic_prestige;
        out->international_prestige = base->international_prestige;
        out->overall = base->overall;
        out->competition_strength = calibrate_competition_strength(
            out->team, base->base_competition_strength);
    }
}

static int calculate_points(const FceStanding *standing) {
    return (int)(standing->home_wins + standing->away_wins) * 3 +
        (int)(standing->home_draws + standing->away_draws);
}

static int fill_live_table(const FceModel *model, LiveStanding *rows,
                           size_t *row_count_io, RankingCandidate *candidates,
                           size_t candidate_count, const TeamForm *forms,
                           size_t form_count,
                           const CompetitionStatus *statuses,
                           size_t status_count) {
    size_t row_count = row_count_io ? *row_count_io : 0;
    size_t start = 0;
    qsort(rows, row_count, sizeof(*rows), compare_live_root_team);

    /* Keep one authoritative record per team and competition root. When both
     * a phase and a root row exist, the row with more completed matches wins. */
    for (size_t read = 0; read < row_count;) {
        size_t next = read + 1;
        while (next < row_count && rows[next].root == rows[read].root &&
               rows[next].team == rows[read].team) ++next;
        rows[start++] = rows[read];
        read = next;
    }
    row_count = start;
    if (row_count_io) *row_count_io = row_count;
    if (!row_count) return 1;

    for (size_t i = 0; i < row_count; ++i) {
        size_t f = find_form(forms, form_count, rows[i].root, rows[i].team);
        if (f < form_count) {
            rows[i].form_score = forms[f].score;
            memcpy(rows[i].form, forms[f].form, sizeof(rows[i].form));
        } else {
            rows[i].form_score = GLOBAL_DEFAULT_VALUE;
            rows[i].form[0] = '-';
            rows[i].form[1] = 0;
        }
    }

    for (start = 0; start < row_count;) {
        size_t end = start + 1, team_count, status_index;
        int64_t sum_overall = 0;
        int complete = 0, leader_ties = 0;
        int best_points, best_wins;
        double average_overall;
        int competition_strength;
        while (end < row_count && rows[end].root == rows[start].root) ++end;
        team_count = end - start;

        for (size_t i = start; i < end; ++i) {
            size_t c = find_candidate(candidates, candidate_count, rows[i].team);
            if (c < candidate_count) sum_overall += candidates[c].overall;
        }
        average_overall = (double)sum_overall / (double)team_count;
        competition_strength = clamp_score(average_overall);

        status_index = find_competition_status(statuses, status_count,
                                              rows[start].root);
        if (status_index < status_count &&
            statuses[status_index].fixture_count > 0 &&
            statuses[status_index].unplayed_count == 0) {
            complete = 1;
            for (size_t i = start; i < end; ++i)
                if (rows[i].played <= 0) complete = 0;
        }

        qsort(rows + start, team_count, sizeof(*rows), compare_live_rank);
        best_points = rows[start].points;
        best_wins = rows[start].wins;
        for (size_t i = start; i < end; ++i)
            if (rows[i].points == best_points && rows[i].wins == best_wins)
                ++leader_ties;

        {
            size_t rank_position = 1;
            int previous_points = -1, previous_wins = -1;
            for (size_t i = start; i < end; ++i) {
            size_t c = find_candidate(candidates, candidate_count, rows[i].team);
            double points_percent = GLOBAL_DEFAULT_VALUE;
            double position_percent = GLOBAL_DEFAULT_VALUE;
            int title_score = GLOBAL_DEFAULT_VALUE;
            if (c >= candidate_count) continue;

            if (i > start && (rows[i].points != previous_points ||
                              rows[i].wins != previous_wins))
                rank_position = i - start + 1;
            previous_points = rows[i].points;
            previous_wins = rows[i].wins;

            if (rows[i].played > 0)
                points_percent = 100.0 * (double)rows[i].points /
                    (3.0 * (double)rows[i].played);
            if (team_count > 1)
                position_percent = 100.0 * (double)(team_count - rank_position) /
                    (double)(team_count - 1);
            if (rows[i].played <= 0) {
                points_percent = GLOBAL_DEFAULT_VALUE;
                position_percent = GLOBAL_DEFAULT_VALUE;
            }
            rows[i].performance = clamp_score(0.70 * points_percent +
                                               0.30 * position_percent);
            if (complete) title_score = leader_ties == 1 &&
                rows[i].points == best_points && rows[i].wins == best_wins
                ? 100 : 0;
            rows[i].title_score = title_score;
            rows[i].competition_strength = is_brazilian_competition(
                rows, start, end)
                ? calibrate_competition_strength(rows[i].team,
                                                 competition_strength)
                : competition_strength;

            /* Prefer the largest table for a club in more than one eligible
             * competition; break ties using measured competition strength. */
            if (!candidates[c].live || team_count >
                    (size_t)candidates[c].selected_league_size ||
                (team_count == (size_t)candidates[c].selected_league_size &&
                 competition_strength > candidates[c].competition_strength)) {
                candidates[c].live = 1;
                candidates[c].selected_league_size = (int32_t)team_count;
                candidates[c].competition_strength = competition_strength;
                candidates[c].performance = rows[i].performance;
                candidates[c].form_score = rows[i].form_score;
                candidates[c].title_score = rows[i].title_score;
                candidates[c].played = rows[i].played;
                memcpy(candidates[c].form, rows[i].form,
                       sizeof(candidates[c].form));
            }
        }
        }
        start = end;
    }
    (void)model;
    return 1;
}

static int cup_progress_score(int stage_kind) {
    switch (stage_kind) {
    case FCE_STAGE_SETUP: return 20;
    case FCE_STAGE_GROUP: return 35;
    case FCE_STAGE_ROUND_1: return 45;
    case FCE_STAGE_ROUND_2: return 50;
    case FCE_STAGE_ROUND_32: return 55;
    case FCE_STAGE_ROUND_16: return 65;
    case FCE_STAGE_QUARTER_FINAL: return 75;
    case FCE_STAGE_SEMI_FINAL: return 85;
    case FCE_STAGE_THIRD_PLACE: return 90;
    case FCE_STAGE_FINAL: return 95;
    default: return GLOBAL_DEFAULT_VALUE;
    }
}

static int root_has_stage_fixture(const FceModel *model, int32_t root) {
    for (size_t i = 0; i < model->fixture_count; ++i) {
        const FceFixture *fixture = model->fixtures + i;
        int fixture_root = fce_model_ancestor(model,
            fixture->competition_object, 3);
        if (fixture_root == root &&
            fce_model_stage_kind(model, fixture->stage) != FCE_STAGE_UNKNOWN)
            return 1;
    }
    return 0;
}

static int root_is_complete(const CompetitionStatus *statuses,
                            size_t status_count, int32_t root) {
    size_t index = find_competition_status(statuses, status_count, root);
    return index < status_count && statuses[index].fixture_count > 0 &&
        statuses[index].unplayed_count == 0;
}

typedef struct {
    int32_t team;
    int32_t goals_for;
    int32_t goals_against;
} FinalTeam;

static int final_winner_for_root(const FceModel *model, int32_t root) {
    FinalTeam teams[GLOBAL_INPUT_LIMIT / 1024];
    size_t team_count = 0;
    int final_found = 0;
    int final_complete = 1;
    for (size_t i = 0; i < model->fixture_count; ++i) {
        const FceFixture *fixture = model->fixtures + i;
        int fixture_root = fce_model_ancestor(model,
            fixture->competition_object, 3);
        int stage_kind;
        size_t home = 0, away = 0;
        if (fixture_root != root) continue;
        stage_kind = fce_model_stage_kind(model, fixture->stage);
        if (stage_kind != FCE_STAGE_FINAL) continue;
        final_found = 1;
        if (!fixture->played_raw || fixture->home_score < 0 ||
            fixture->away_score < 0) {
            final_complete = 0;
            continue;
        }
        while (home < team_count && teams[home].team != fixture->home) ++home;
        if (home == team_count && team_count < sizeof(teams) / sizeof(teams[0])) {
            teams[team_count++] = (FinalTeam){fixture->home, 0, 0};
        }
        while (away < team_count && teams[away].team != fixture->away) ++away;
        if (away == team_count && team_count < sizeof(teams) / sizeof(teams[0])) {
            teams[team_count++] = (FinalTeam){fixture->away, 0, 0};
        }
        if (home >= team_count || away >= team_count) continue;
        teams[home].goals_for += fixture->home_score;
        teams[home].goals_against += fixture->away_score;
        teams[away].goals_for += fixture->away_score;
        teams[away].goals_against += fixture->home_score;
    }
    if (!final_found || !final_complete || team_count < 2) return -1;
    {
        int best_difference = -1000000;
        int winner = -1;
        int ties = 0;
        for (size_t i = 0; i < team_count; ++i) {
            int difference = teams[i].goals_for - teams[i].goals_against;
            if (difference > best_difference) {
                best_difference = difference;
                winner = teams[i].team;
                ties = 1;
            } else if (difference == best_difference) {
                ties++;
            }
        }
        return ties == 1 ? winner : -1;
    }
}

static void apply_campaign_signals(
    const FceModel *model, const LiveStanding *rows, size_t row_count,
    RankingCandidate *candidates, size_t candidate_count,
    const CompetitionStatus *statuses, size_t status_count) {
    size_t start;

    /* A root with explicit stage nodes is a cup/tournament. A direct type-3
     * root with no stage fixture is treated as a league table. */
    for (start = 0; start < row_count;) {
        size_t end = start + 1;
        int32_t root = rows[start].root;
        int cup = root_has_stage_fixture(model, root);
        while (end < row_count && rows[end].root == root) ++end;
        if (!cup && end - start > 1) {
            int complete = root_is_complete(statuses, status_count, root);
            int leader_ties = 1;
            for (size_t i = start; complete && i < end; ++i)
                if (rows[i].played <= 0) complete = 0;
            if (complete) {
                for (size_t i = start + 1; i < end; ++i)
                    if (rows[i].points == rows[start].points &&
                        rows[i].wins == rows[start].wins)
                        ++leader_ties;
            }
            for (size_t i = start; i < end; ++i) {
                size_t c = find_candidate(candidates, candidate_count,
                                          rows[i].team);
                if (c < candidate_count) {
                    int position_score = clamp_score(100.0 *
                        (double)(end - i - 1) / (double)(end - start - 1));
                    if (position_score > candidates[c].league_position_score)
                        candidates[c].league_position_score = position_score;
                    if (complete && leader_ties == 1 && i == start)
                        candidates[c].title_score = 100;
                }
            }
        }
        start = end;
    }

    for (size_t i = 0; i < model->fixture_count; ++i) {
        const FceFixture *fixture = model->fixtures + i;
        int root = fce_model_ancestor(model, fixture->competition_object, 3);
        int stage_kind;
        int score;
        size_t home, away;
        if (root < 0) continue;
        stage_kind = fce_model_stage_kind(model, fixture->stage);
        score = cup_progress_score(stage_kind);
        if (stage_kind == FCE_STAGE_UNKNOWN) continue;
        home = find_candidate(candidates, candidate_count, fixture->home);
        away = find_candidate(candidates, candidate_count, fixture->away);
        if (home < candidate_count && score > candidates[home].cup_progress_score)
            candidates[home].cup_progress_score = score;
        if (away < candidate_count && score > candidates[away].cup_progress_score)
            candidates[away].cup_progress_score = score;
    }

    /* A cup title is awarded only when the final is present, complete and its
     * winner is unambiguous from the saved scoreline. Tied finals are left
     * neutral because the public fixture contract does not expose penalties. */
    for (size_t i = 0; i < model->fixture_count; ++i) {
        const FceFixture *fixture = model->fixtures + i;
        int root = fce_model_ancestor(model, fixture->competition_object, 3);
        int stage_kind = fce_model_stage_kind(model, fixture->stage);
        int winner;
        int seen = 0;
        if (root < 0 || stage_kind != FCE_STAGE_FINAL) continue;
        for (size_t j = 0; j < i; ++j) {
            const FceFixture *previous = model->fixtures + j;
            if (fce_model_ancestor(model, previous->competition_object, 3) == root &&
                fce_model_stage_kind(model, previous->stage) == FCE_STAGE_FINAL) {
                seen = 1;
                break;
            }
        }
        if (seen) continue;
        winner = final_winner_for_root(model, root);
        if (winner >= 0) {
            size_t c = find_candidate(candidates, candidate_count, winner);
            if (c < candidate_count) {
                candidates[c].title_score = 100;
                candidates[c].cup_progress_score = 100;
            }
        }
    }
}

static FceResult build_forms_and_status(
    const FceModel *model, FormEvent **out_events, size_t *out_event_count,
    TeamForm **out_forms, size_t *out_form_count,
    CompetitionStatus **out_statuses, size_t *out_status_count,
    const int32_t *club_roots, size_t club_root_count) {
    FormEvent *events = NULL;
    TeamForm *forms = NULL;
    CompetitionStatus *statuses = NULL;
    size_t event_capacity, event_count = 0, form_count = 0;
    size_t status_count = 0;

    *out_events = NULL; *out_event_count = 0;
    *out_forms = NULL; *out_form_count = 0;
    *out_statuses = NULL; *out_status_count = 0;
    if (model->fixture_count > GLOBAL_INPUT_LIMIT) return FCE_INVALID;
    if (model->fixture_count > SIZE_MAX / 2) return FCE_INVALID;
    event_capacity = model->fixture_count * 2;
    if (event_capacity) {
        events = checked_calloc(event_capacity, sizeof(*events));
        if (!events) return FCE_NO_MEMORY;
    }
    if (model->fixture_count) {
        statuses = checked_calloc(model->fixture_count, sizeof(*statuses));
        if (!statuses) { free(events); return FCE_NO_MEMORY; }
    }

    for (size_t i = 0; i < model->fixture_count; ++i) {
        const FceFixture *f = model->fixtures + i;
        int root = fce_model_ancestor(model, f->competition_object, 3);
        /* A catalog club anchors this root as a club competition. This admits
         * patched/custom clubs among its participants without pulling in
         * national-team-only competitions. */
        if (root <= 0 || !int32_in_sorted(club_roots, club_root_count, root) ||
            f->home <= 0 || f->away <= 0) continue;
        statuses[status_count].root = root;
        statuses[status_count].fixture_count = 1;
        statuses[status_count].unplayed_count = f->played_raw ? 0 : 1;
        ++status_count;
        if (!f->played_raw || f->home_score < 0 || f->away_score < 0) continue;

        events[event_count++] = (FormEvent){root, f->home, f->date_raw, f->id,
            f->home_score > f->away_score ? 'V' :
            f->home_score == f->away_score ? 'E' : 'D'};
        events[event_count++] = (FormEvent){root, f->away, f->date_raw, f->id,
            f->away_score > f->home_score ? 'V' :
            f->away_score == f->home_score ? 'E' : 'D'};
    }

    if (status_count) {
        qsort(statuses, status_count, sizeof(*statuses), compare_competition_status);
        size_t write = 0;
        for (size_t read = 0; read < status_count;) {
            size_t next = read + 1;
            CompetitionStatus value = statuses[read];
            while (next < status_count && statuses[next].root == value.root) {
                value.fixture_count += statuses[next].fixture_count;
                value.unplayed_count += statuses[next].unplayed_count;
                ++next;
            }
            statuses[write++] = value;
            read = next;
        }
        status_count = write;
    }

    if (event_count) {
        qsort(events, event_count, sizeof(*events), compare_form_event);
        forms = checked_calloc(event_count, sizeof(*forms));
        if (!forms) { free(events); free(statuses); return FCE_NO_MEMORY; }
        for (size_t read = 0; read < event_count;) {
            size_t next = read;
            TeamForm *form = forms + form_count++;
            int points = 0;
            memset(form, 0, sizeof(*form));
            form->root = events[read].root;
            form->team = events[read].team;
            while (next < event_count && events[next].root == form->root &&
                   events[next].team == form->team) {
                if (form->count < FCE_GLOBAL_FORM_LENGTH) {
                    char result = events[next].result;
                    form->form[form->count++] = result;
                    points += result == 'V' ? 3 : result == 'E' ? 1 : 0;
                }
                ++next;
            }
            form->form[form->count] = 0;
            form->score = form->count
                ? clamp_score(100.0 * (double)points /
                    (3.0 * (double)form->count))
                : GLOBAL_DEFAULT_VALUE;
            read = next;
        }
    }

    *out_events = events; *out_event_count = event_count;
    *out_forms = forms; *out_form_count = form_count;
    *out_statuses = statuses; *out_status_count = status_count;
    return FCE_OK;
}

static FceResult global_ranking_build_limit(const FceModel *model,
                                           size_t limit,
                                           FceGlobalRankedClub **out,
                                           size_t *out_count) {
    RankingCandidate *candidates = NULL;
    LiveStanding *live = NULL;
    FormEvent *events = NULL;
    TeamForm *forms = NULL;
    CompetitionStatus *statuses = NULL;
    int32_t *club_roots = NULL;
    RootClubBaseline *root_baselines = NULL;
    FceGlobalRankedClub *result = NULL;
    size_t candidate_capacity, candidate_count = 0, live_count = 0;
    size_t event_count = 0, form_count = 0, status_count = 0;
    size_t candidate_write = 0, result_count = 0, club_root_count = 0;
    size_t root_baseline_count = 0;
    FceResult status = FCE_INVALID;

    if (!out || !out_count) return FCE_INVALID;
    *out = NULL; *out_count = 0;
    if (!model || (!model->standings && model->standing_count) ||
        (!model->fixtures && model->fixture_count) ||
        (!model->nodes && model->node_count) ||
        model->standing_count > GLOBAL_INPUT_LIMIT ||
        model->fixture_count > GLOBAL_INPUT_LIMIT ||
        model->node_count > GLOBAL_INPUT_LIMIT) return FCE_INVALID;
    if (global_catalog_count > SIZE_MAX - model->standing_count)
        return FCE_INVALID;
    candidate_capacity = global_catalog_count + model->standing_count;

    candidates = checked_calloc(candidate_capacity, sizeof(*candidates));
    if (!candidates) return FCE_NO_MEMORY;
    for (size_t i = 0; i < global_catalog_count; ++i) {
        const GlobalClubBase *base = g_global_club_catalog + i;
        init_candidate(candidates + candidate_count++, base->team_id, base);
    }

    if (model->standing_count) {
        club_roots = checked_calloc(model->standing_count, sizeof(*club_roots));
        if (!club_roots) { status = FCE_NO_MEMORY; goto cleanup; }
        for (size_t i = 0; i < model->standing_count; ++i) {
            const FceStanding *standing = model->standings + i;
            int root = fce_model_ancestor(model,
                standing->competition_object, 3);
            if (root > 0 && base_for_team(standing->team))
                club_roots[club_root_count++] = root;
        }
        qsort(club_roots, club_root_count, sizeof(*club_roots), compare_int32);
        if (club_root_count) {
            size_t write = 1;
            for (size_t read = 1; read < club_root_count; ++read)
                if (club_roots[read] != club_roots[write - 1])
                    club_roots[write++] = club_roots[read];
            club_root_count = write;
        }
    }
    status = build_root_club_baselines(model, &root_baselines,
                                       &root_baseline_count);
    if (status != FCE_OK) goto cleanup;

    if (model->standing_count) {
        live = checked_calloc(model->standing_count, sizeof(*live));
        if (!live) { status = FCE_NO_MEMORY; goto cleanup; }
    }
    for (size_t i = 0; i < model->standing_count; ++i) {
        const FceStanding *s = model->standings + i;
        int root = fce_model_ancestor(model, s->competition_object, 3);
        const GlobalClubBase *base;
        if (s->team <= 0 || root <= 0) continue;
        base = base_for_team(s->team);
        if (!base) {
            /* Catalog membership anchors this as a club competition. Admit
             * all patched/custom clubs in that root, not only the manager's
             * club; unknown teams from national-team-only roots stay out. */
            if (!int32_in_sorted(club_roots, club_root_count, root)) continue;
            init_candidate(candidates + candidate_count++, s->team, NULL);
            {
                const RootClubBaseline *baseline = baseline_for_root(
                    root_baselines, root_baseline_count, root);
                if (baseline) {
                    RankingCandidate *custom = candidates + candidate_count - 1;
                    custom->domestic_prestige = baseline->domestic_prestige;
                    custom->international_prestige =
                        baseline->international_prestige;
                    custom->overall = baseline->overall;
                    custom->competition_strength =
                        baseline->competition_strength;
                }
            }
        }
        live[live_count].root = root;
        live[live_count].team = s->team;
        live[live_count].wins = (int)(s->home_wins + s->away_wins);
        live[live_count].draws = (int)(s->home_draws + s->away_draws);
        live[live_count].losses = (int)(s->home_losses + s->away_losses);
        live[live_count].played = (int)s->played;
        live[live_count].points = calculate_points(s);
        ++live_count;
    }

    qsort(candidates, candidate_count, sizeof(*candidates), compare_candidate_team);
    for (size_t read = 0; read < candidate_count;) {
        size_t next = read + 1;
        candidates[candidate_write++] = candidates[read];
        while (next < candidate_count &&
               candidates[next].team == candidates[read].team) ++next;
        read = next;
    }
    candidate_count = candidate_write;

    status = build_forms_and_status(model, &events, &event_count, &forms,
                                    &form_count, &statuses, &status_count,
                                    club_roots, club_root_count);
    if (status != FCE_OK) goto cleanup;
    if (!fill_live_table(model, live, &live_count, candidates, candidate_count,
                         forms, form_count, statuses, status_count)) {
        status = FCE_INVALID;
        goto cleanup;
    }
    apply_campaign_signals(model, live, live_count, candidates, candidate_count,
                           statuses, status_count);

    qsort(candidates, candidate_count, sizeof(*candidates), compare_candidate_score);
    result_count = limit && candidate_count > limit ? limit : candidate_count;
    result = checked_calloc(result_count, sizeof(*result));
    if (!result) { status = FCE_NO_MEMORY; goto cleanup; }
    for (size_t i = 0; i < result_count; ++i) {
        const RankingCandidate *c = candidates + i;
        int64_t score_numerator = candidate_score_numerator(c);
        result[i].team = c->team;
        result[i].score_tenths = (int32_t)((score_numerator + 5) / 10);
        result[i].overall = c->overall;
        result[i].competition_strength = c->competition_strength;
        result[i].performance = c->performance;
        result[i].form_score = c->form_score;
        result[i].current_title_score = c->title_score;
        result[i].league_position_score = c->league_position_score;
        result[i].cup_progress_score = c->cup_progress_score;
        result[i].played = c->played;
        memcpy(result[i].form, c->form, sizeof(result[i].form));
    }
    *out = result; result = NULL;
    *out_count = result_count;
    status = FCE_OK;

cleanup:
    free(candidates);
    free(live);
    free(events);
    free(forms);
    free(statuses);
    free(club_roots);
    free(root_baselines);
    free(result);
    return status;
}

FceResult fce_global_ranking_build(const FceModel *model,
                                   FceGlobalRankedClub **out,
                                   size_t *out_count) {
    return global_ranking_build_limit(model, FCE_GLOBAL_RANK_LIMIT,
                                      out, out_count);
}

FceResult fce_global_ranking_build_all(const FceModel *model,
                                      FceGlobalRankedClub **out,
                                      size_t *out_count) {
    return global_ranking_build_limit(model, 0, out, out_count);
}

void fce_global_ranking_free(void *rows) { free(rows); }
size_t fce_global_ranking_catalog_count(void) { return global_catalog_count; }
