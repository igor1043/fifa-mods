#ifndef FIFA16_GLOBAL_RANKING_H
#define FIFA16_GLOBAL_RANKING_H

#include "fce_model.h"

enum { FCE_GLOBAL_RANK_LIMIT = 150, FCE_GLOBAL_FORM_LENGTH = 5 };

typedef struct {
    int32_t team;
    int32_t score_tenths;
    int32_t overall;
    int32_t competition_strength;
    int32_t performance;
    int32_t form_score;
    int32_t current_title_score;
    int32_t played;
    char form[FCE_GLOBAL_FORM_LENGTH + 1];
} FceGlobalRankedClub;

/* Returns the top 150 from a live career snapshot plus the static club
 * catalog. All allocations are owned by the caller and must be freed. */
FceResult fce_global_ranking_build(const FceModel *, FceGlobalRankedClub **,
                                   size_t *);
void fce_global_ranking_free(void *);
size_t fce_global_ranking_catalog_count(void);

#endif
