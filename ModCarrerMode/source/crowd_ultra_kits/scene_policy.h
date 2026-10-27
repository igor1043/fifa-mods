#pragma once
#include <stdint.h>

struct UltraSceneTeams { int index = -1, home = 0, away = 0; };

// The RNA event passes 32 ints to 4398560. That function copies them to
// scene state + 4; offset 0x40 is the scene index, followed by club IDs.
static inline bool ultra_scene_teams(const int32_t* fields, UltraSceneTeams& teams) {
    teams = {};
    if (!fields || fields[16] < 0 || fields[16] > 1 ||
        fields[17] <= 0 || fields[17] > 1000000 ||
        fields[18] <= 0 || fields[18] > 1000000) return false;
    teams.index = fields[16]; teams.home = fields[17]; teams.away = fields[18];
    return true;
}
