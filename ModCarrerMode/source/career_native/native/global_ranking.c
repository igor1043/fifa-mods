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

#include "integration/global_clubs.inc"

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

static const size_t global_catalog_count =
    sizeof(g_global_club_catalog) / sizeof(g_global_club_catalog[0]);

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

static int compare_candidate_score(const void *left, const void *right) {
    const RankingCandidate *a = left, *b = right;
    int64_t score_a, score_b;
    int32_t rep_a, rep_b;
    rep_a = (a->international_prestige * 70 + a->domestic_prestige * 30) / 20;
    rep_b = (b->international_prestige * 70 + b->domestic_prestige * 30) / 20;
    score_a = rep_a * 15 + a->overall * 15 +
        a->competition_strength * 15 + a->performance * 30 +
        a->form_score * 15 + a->title_score * 10;
    score_b = rep_b * 15 + b->overall * 15 +
        b->competition_strength * 15 + b->performance * 30 +
        b->form_score * 15 + b->title_score * 10;
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
    out->competition_strength = GLOBAL_DEFAULT_VALUE;
    out->overall = GLOBAL_DEFAULT_VALUE;
    out->form[0] = '-';
    if (base) {
        out->static_record = 1;
        out->domestic_prestige = base->domestic_prestige;
        out->international_prestige = base->international_prestige;
        out->overall = base->overall;
        out->competition_strength = base->base_competition_strength;
    }
}

static int calculate_points(const FceStanding *standing) {
    return (int)(standing->home_wins + standing->away_wins) * 3 +
        (int)(standing->home_draws + standing->away_draws);
}

static int fill_live_table(const FceModel *model, LiveStanding *rows,
                           size_t row_count, RankingCandidate *candidates,
                           size_t candidate_count, const TeamForm *forms,
                           size_t form_count,
                           const CompetitionStatus *statuses,
                           size_t status_count) {
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
            rows[i].competition_strength = competition_strength;

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

static FceResult build_forms_and_status(
    const FceModel *model, FormEvent **out_events, size_t *out_event_count,
    TeamForm **out_forms, size_t *out_form_count,
    CompetitionStatus **out_statuses, size_t *out_status_count) {
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
        if (root <= 0) continue;
        statuses[status_count].root = root;
        statuses[status_count].fixture_count = 1;
        statuses[status_count].unplayed_count = f->played_raw ? 0 : 1;
        ++status_count;
        if (!f->played_raw || f->home <= 0 || f->away <= 0 ||
            f->home_score < 0 || f->away_score < 0) continue;

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

FceResult fce_global_ranking_build(const FceModel *model,
                                   FceGlobalRankedClub **out,
                                   size_t *out_count) {
    RankingCandidate *candidates = NULL;
    LiveStanding *live = NULL;
    FormEvent *events = NULL;
    TeamForm *forms = NULL;
    CompetitionStatus *statuses = NULL;
    FceGlobalRankedClub *result = NULL;
    size_t candidate_capacity, candidate_count = 0, live_count = 0;
    size_t event_count = 0, form_count = 0, status_count = 0;
    size_t candidate_write = 0, result_count = 0;
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
        live = checked_calloc(model->standing_count, sizeof(*live));
        if (!live) { status = FCE_NO_MEMORY; goto cleanup; }
    }
    for (size_t i = 0; i < model->standing_count; ++i) {
        const FceStanding *s = model->standings + i;
        int root = fce_model_ancestor(model, s->competition_object, 3);
        const GlobalClubBase *base;
        if (s->team <= 0 || root <= 0) continue;
        live[live_count].root = root;
        live[live_count].team = s->team;
        live[live_count].wins = (int)(s->home_wins + s->away_wins);
        live[live_count].draws = (int)(s->home_draws + s->away_draws);
        live[live_count].losses = (int)(s->home_losses + s->away_losses);
        live[live_count].played = (int)s->played;
        live[live_count].points = calculate_points(s);
        ++live_count;
        base = base_for_team(s->team);
        if (!base) {
            init_candidate(candidates + candidate_count++, s->team, NULL);
        }
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
                                    &form_count, &statuses, &status_count);
    if (status != FCE_OK) goto cleanup;
    if (!fill_live_table(model, live, live_count, candidates, candidate_count,
                         forms, form_count, statuses, status_count)) {
        status = FCE_INVALID;
        goto cleanup;
    }

    qsort(candidates, candidate_count, sizeof(*candidates), compare_candidate_score);
    result_count = candidate_count < FCE_GLOBAL_RANK_LIMIT
        ? candidate_count : FCE_GLOBAL_RANK_LIMIT;
    result = checked_calloc(result_count, sizeof(*result));
    if (!result) { status = FCE_NO_MEMORY; goto cleanup; }
    for (size_t i = 0; i < result_count; ++i) {
        const RankingCandidate *c = candidates + i;
        int32_t reputation = (c->international_prestige * 70 +
                              c->domestic_prestige * 30) / 20;
        double score = (double)reputation * 0.15 +
            (double)c->overall * 0.15 +
            (double)c->competition_strength * 0.15 +
            (double)c->performance * 0.30 +
            (double)c->form_score * 0.15 +
            (double)c->title_score * 0.10;
        result[i].team = c->team;
        result[i].score_tenths = (int32_t)(score * 10.0 + 0.5);
        result[i].overall = c->overall;
        result[i].competition_strength = c->competition_strength;
        result[i].performance = c->performance;
        result[i].form_score = c->form_score;
        result[i].current_title_score = c->title_score;
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
    free(result);
    return status;
}

void fce_global_ranking_free(void *rows) { free(rows); }
size_t fce_global_ranking_catalog_count(void) { return global_catalog_count; }
