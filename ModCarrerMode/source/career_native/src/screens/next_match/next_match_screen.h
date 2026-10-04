#pragma once
#include "../club/club_player_screen.h"
#define FIFA_NEXT_MATCH_ACTION "FifaModsOpenNextMatch"
typedef struct NextMatchSide {
    int team, count, roster_valid;
    char name[128], manager[128], formation[96];
    ClubPlayerRow rows[CLUB_PLAYER_CAPACITY];
    /* Current career energy, not the static stamina attribute. Missing values
     * stay explicitly unavailable. Indexed by the corresponding roster row. */
    int condition[CLUB_PLAYER_CAPACITY], condition_valid[CLUB_PLAYER_CAPACITY];
} NextMatchSide;
typedef struct NextMatchSnapshot {
    int valid, fixture, date, time, capacity, attendance, venue_pending;
    char competition[128], stadium[512], stadium_key[256], venue_note[160];
    NextMatchSide sides[2];
} NextMatchSnapshot;
#ifdef __cplusplus
struct ID3D11Device;
extern "C" {
#endif
BOOL next_match_take_refresh(void);
void next_match_publish(const NextMatchSnapshot*);
#ifdef __cplusplus
}
bool next_match_register(const char*,void(*)(const char*));
void next_match_device(ID3D11Device*);
struct NextMatchTestView {int view;size_t xi[2];bool ready,image;int teams[2];unsigned team_pose[2],coach_pose[2];size_t portraits[2],pitch[2],team_players[2],conditions[2],numbers[2];};
#ifdef NEXT_MATCH_SCREEN_TEST
NextMatchTestView next_match_test_view();
#endif
#endif
