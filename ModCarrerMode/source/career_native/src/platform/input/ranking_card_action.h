#ifndef FIFA16_RANKING_CARD_ACTION_H
#define FIFA16_RANKING_CARD_ACTION_H

#include <stddef.h>

#define FIFA16_RANKING_CARD_ACTION_NAME "FifaModsOpenRanking"

/* The native hook is shared by all registered mod-screen actions. */
typedef bool (*RankingCardMatchFn)(const char *action);
typedef void (*RankingCardOpenFn)(const char *action);
typedef void (*RankingCardLogFn)(const char *message);

enum RankingCardActionHookResult {
    RANKING_CARD_ACTION_PENDING = 0,
    RANKING_CARD_ACTION_READY = 1,
    RANKING_CARD_ACTION_UNSUPPORTED = -1,
    RANKING_CARD_ACTION_FAILED = -2
};

RankingCardActionHookResult ranking_card_action_install(
    unsigned char *module_base, size_t image_size,
    RankingCardMatchFn has_action, RankingCardOpenFn open_screen,
    RankingCardLogFn log_message);

#endif
