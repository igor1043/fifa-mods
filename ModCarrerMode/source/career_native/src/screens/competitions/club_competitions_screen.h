#ifndef FIFA16_CLUB_COMPETITIONS_SCREEN_H
#define FIFA16_CLUB_COMPETITIONS_SCREEN_H
#include <stddef.h>
#define FIFA16_CLUB_COMPETITIONS_ACTION "FifaModsOpenClubCompetitions"
#define CLUB_COMPETITIONS_CAPACITY 5
#define CLUB_COMPETITION_GROUP_CAPACITY 16
#define CLUB_COMPETITION_TABLE_CAPACITY 20
#define CLUB_COMPETITION_FORM_SIZE 5
#define CLUB_COMPETITION_BRACKET_TIE_CAPACITY 64
#define CLUB_COMPETITION_BRACKET_TEAM_CAPACITY 128
#define CLUB_COMPETITION_MOVEMENT_UNKNOWN 2
enum {
    CLUB_COMPETITION_ZONE_NONE=0,
    CLUB_COMPETITION_ZONE_PRIMARY=1,
    CLUB_COMPETITION_ZONE_SECONDARY=2,
    CLUB_COMPETITION_ZONE_SAFE=3,
    CLUB_COMPETITION_ZONE_RELEGATION=4,
    CLUB_COMPETITION_ZONE_ADVANCE=5,
    CLUB_COMPETITION_ZONE_OUTSIDE=6
};

typedef struct ClubCompetitionTableRow {
    int team,rank,played,won,drawn,lost,goals_for,goals_against,points,status,movement,zone;
    int last_match_valid,last_match_result,last_goals_for,last_goals_against;
    int form[CLUB_COMPETITION_FORM_SIZE]; /* -1 loss, 0 draw, 1 win, 2 empty */
    char name[128];
} ClubCompetitionTableRow;
typedef struct ClubCompetitionGroup {
    int stage,current,classification_count;
    size_t row_count;
    ClubCompetitionTableRow rows[CLUB_COMPETITION_TABLE_CAPACITY];
} ClubCompetitionGroup;
typedef struct ClubCompetitionMatch {
    int visible,stage,round,home_team,away_team,date,time,played,home_score,away_score,fixture_id;
} ClubCompetitionMatch;
typedef struct ClubCompetitionBracketTeam {
    int id;
    char name[128];
} ClubCompetitionBracketTeam;
typedef struct ClubCompetitionBracketTie {
    int stage,stage_kind,round,team_a,team_b,leg_count;
    ClubCompetitionMatch legs[2];
} ClubCompetitionBracketTie;
typedef struct ClubCompetitionEntry {
    int competition,asset,trophy_asset,current_stage,current_stage_kind,is_cup;
    int table_available,has_group_phase,preferred_group;
    size_t table_count,group_count;
    char title_key[64];
    ClubCompetitionTableRow table[CLUB_COMPETITION_TABLE_CAPACITY];
    ClubCompetitionGroup groups[CLUB_COMPETITION_GROUP_CAPACITY];
    ClubCompetitionMatch previous,next;
    int aggregate_visible,aggregate_for,aggregate_against;
    size_t bracket_tie_count,bracket_team_count;
    ClubCompetitionBracketTie bracket_ties[CLUB_COMPETITION_BRACKET_TIE_CAPACITY];
    ClubCompetitionBracketTeam bracket_teams[CLUB_COMPETITION_BRACKET_TEAM_CAPACITY];
} ClubCompetitionEntry;
typedef struct ClubCompetitionsSnapshot {
    int club,date;
    size_t count;
    ClubCompetitionEntry entries[CLUB_COMPETITIONS_CAPACITY];
} ClubCompetitionsSnapshot;
/* Compact, render-safe standings data for the office social card. This avoids
 * copying the much larger full competition snapshot on every rendered frame. */
typedef struct ClubCompetitionSocialSnapshot {
    int club,date,competition,available,is_group,cup_competition,cup_state;
    int rank,team_count,played,won,drawn,lost,goals_for,goals_against,points;
    int form[CLUB_COMPETITION_FORM_SIZE];
} ClubCompetitionSocialSnapshot;
#ifdef __cplusplus
struct ID3D11Device;
extern "C" {
#endif
void club_competitions_publish(const ClubCompetitionsSnapshot*);
size_t club_competitions_table_read(int club,int competition,ClubCompetitionTableRow*out,size_t capacity);
int club_competitions_social_read(int club,ClubCompetitionSocialSnapshot*out);
#ifdef __cplusplus
}
bool club_competitions_screen_register(const char*,void(*)(const char*));
void club_competitions_screen_device(ID3D11Device*);
void club_competitions_screen_draw_office(float x,float y,float width,float height,
    int next_match_asset,int horizontal,int vertical,bool confirm,bool input_ready);
#endif
#endif
