#ifndef FIFA16_CLUBS_BROWSER_H
#define FIFA16_CLUBS_BROWSER_H
#include "../club/club_player_screen.h"
#define FIFA16_CLUBS_BROWSER_ACTION "FifaModsOpenOtherClubs"
#define CLUB_BROWSER_CAPACITY 10000
typedef struct ClubBrowserRow {
    int team,league,nation,attack,midfield,defense,prestige;
    char name[128],league_name[128],nation_name[128];
} ClubBrowserRow;
#ifdef __cplusplus
extern "C" {
#endif
BOOL clubs_browser_take_catalog_request(void);
BOOL clubs_browser_take_roster_request(int *club,unsigned *token);
void clubs_browser_publish_catalog(const ClubBrowserRow*,size_t,int own_club);
/* Read-only copied catalog shared with league browsing; never exposes DB-owned pointers. */
size_t clubs_browser_copy_catalog(ClubBrowserRow*,size_t,unsigned *revision);
void clubs_browser_request_catalog(void);
/* Open the shared club screen focused on this team, including its roster view. */
BOOL clubs_browser_open_team(int team);
int clubs_browser_own_league(void);
void clubs_browser_publish_roster(int club,unsigned token,const ClubPlayerRow*,size_t,const char*);
void clubs_browser_invalidate(void);
void clubs_browser_request_native_refresh(void);
#ifdef __cplusplus
}
bool clubs_browser_register(const char*,void(*log)(const char*));
void clubs_browser_device(ID3D11Device*);
#ifdef CLUBS_BROWSER_TEST
struct ClubsBrowserTestView {int team,league,nation,focus;size_t count;bool child,waiting;};
ClubsBrowserTestView clubs_browser_test_view();
bool clubs_browser_test_center(int,float&,float&);
#endif
#endif
#endif
