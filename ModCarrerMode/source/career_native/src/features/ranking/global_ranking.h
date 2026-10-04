#ifndef FIFA16_GLOBAL_RANKING_H
#define FIFA16_GLOBAL_RANKING_H

#include "../../core/fce_model.h"

enum { FCE_GLOBAL_RANK_LIMIT = 150, FCE_GLOBAL_FORM_LENGTH = 5 };

typedef struct {
    int32_t team;
    int32_t score_tenths;
    int32_t overall;
    int32_t competition_strength;
    int32_t performance;
    int32_t form_score;
    int32_t current_title_score;
    int32_t league_position_score;
    int32_t cup_progress_score;
    int32_t played;
    char form[FCE_GLOBAL_FORM_LENGTH + 1];
} FceGlobalRankedClub;

/* Returns the top 150 from the static club catalog plus custom teams from
 * competition roots anchored by catalog clubs. All output is caller-owned. */
FceResult fce_global_ranking_build(const FceModel *, FceGlobalRankedClub **,
                                   size_t *);
/* Returns the complete ordered ranking. Intended for lookups beyond the
 * top-150 window (for example, the career user's actual position). */
FceResult fce_global_ranking_build_all(const FceModel *, FceGlobalRankedClub **,
                                       size_t *);
void fce_global_ranking_free(void *);
size_t fce_global_ranking_catalog_count(void);

#endif
