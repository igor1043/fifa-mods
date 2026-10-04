#ifndef FIFA16_RANKING_OVERLAY_H
#define FIFA16_RANKING_OVERLAY_H

#include <stddef.h>
#include <windows.h>

typedef struct RankingOverlayRow {
    int rank;
    int team_id;
    int score_tenths;
    char name[128];
} RankingOverlayRow;

#ifdef __cplusplus
extern "C" {
#endif

void ranking_overlay_publish_rows(const RankingOverlayRow *rows, size_t count,
    int user_team_id);
DWORD WINAPI ranking_overlay_start_thread(void *parameter);
BOOL ranking_overlay_captures_input(void);

#ifdef __cplusplus
}
#endif

#endif
