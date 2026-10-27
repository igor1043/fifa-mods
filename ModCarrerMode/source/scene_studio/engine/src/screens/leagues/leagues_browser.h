#ifndef FIFA16_LEAGUES_BROWSER_H
#define FIFA16_LEAGUES_BROWSER_H
#include "../clubs/clubs_browser.h"
#define FIFA16_LEAGUES_BROWSER_ACTION "FifaModsOpenLeagues"
#define LEAGUE_BROWSER_TABLE_CAPACITY 40
#define LEAGUE_BROWSER_CUP_CAPACITY 6
#define LEAGUE_BROWSER_LEADER_CAPACITY 3
typedef struct LeagueBrowserTableRow {
    int team,rank,played,won,drawn,lost,goals_for,goals_against,points;
    char name[128];
} LeagueBrowserTableRow;
typedef struct LeagueBrowserCup {
    int competition,asset,date;
} LeagueBrowserCup;
typedef struct LeagueBrowserLeader {
    int player,team,value;
    char name[128],team_name[128];
} LeagueBrowserLeader;
typedef struct LeagueBrowserSnapshot {
    int league,nation,date,table_available,cups_available,goals_available,assists_available;
    char league_name[128],nation_name[128];
    size_t table_count,cup_count,goals_count,assists_count;
    LeagueBrowserTableRow table[LEAGUE_BROWSER_TABLE_CAPACITY];
    LeagueBrowserCup cups[LEAGUE_BROWSER_CUP_CAPACITY];
    LeagueBrowserLeader goals[LEAGUE_BROWSER_LEADER_CAPACITY];
    LeagueBrowserLeader assists[LEAGUE_BROWSER_LEADER_CAPACITY];
} LeagueBrowserSnapshot;
#ifdef __cplusplus
struct ID3D11Device;
extern "C" {
#endif
BOOL leagues_browser_take_data_request(int *league);
void leagues_browser_publish(const LeagueBrowserSnapshot*);
#ifdef __cplusplus
}
bool leagues_browser_register(const char*,void(*)(const char*));
void leagues_browser_device(ID3D11Device*);
#ifdef LEAGUES_BROWSER_TEST
struct LeaguesBrowserTestView {int nation,league,focus;size_t table,cups,goals,assists;bool waiting;};
LeaguesBrowserTestView leagues_browser_test_view();
bool leagues_browser_test_center(int,float&,float&);
#endif
#endif
#endif
