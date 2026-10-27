#ifndef FIFA16_COACH_PROFILE_SCREEN_H
#define FIFA16_COACH_PROFILE_SCREEN_H
#include <windows.h>
#include <stddef.h>
#include "../../core/fce_contracts.h"
#define FIFA16_COACH_PROFILE_ACTION "FifaModsOpenCoachProfile"
#define COACH_PROFILE_CAPACITY 256
/* Identity domains are separate: user 0 is not club coach 0. National-team
 * appointments are explicit, never inferred from a league ID or nationality. */
enum CoachProfileKind {COACH_CAREER_USER=1,COACH_CLUB_MANAGER=2,COACH_NATIONAL_MANAGER=3};
enum CoachTeamKind {COACH_TEAM_CLUB=0,COACH_TEAM_NATIONAL=1};
enum CoachProfileStatsScope {COACH_STATS_NONE=0,COACH_STATS_CAREER=1,COACH_STATS_CURRENT_CLUB=2};
typedef struct CoachMatchStats {int games,wins,draws,losses,goals_for,goals_against;} CoachMatchStats;
typedef struct CoachCareerRow {
    int key,team,team_kind,season,league;
    char team_name[128];
    CoachMatchStats total,home,away;
    int splits_valid,league_titles,domestic_titles,continental_titles;
    int season_valid;
} CoachCareerRow;
typedef struct CoachProfileContext {
    int valid,kind,id,club,national_team,nationality,season,history_valid;
    int confidence,reputation,wage;
    /* Display-only rating inputs. Explicit validity avoids treating a missing
     * league or unavailable recent schedule as zero reputation. */
    int league_strength_valid,recent_valid,recent_games,recent_points;
    float league_strength;
    char name[128],club_name[128],national_name[128];
    unsigned int colors[3];int colors_valid;
    int stats_scope;
} CoachProfileContext;
#ifdef __cplusplus
struct ID3D11Device;
extern "C" {
#endif
/* Native provider publishes owned copies. No save writes and no retained
 * game table/actor pointers. Explicit generic opens never consume user history. */
void coach_profile_publish_career(const CoachProfileContext*,const CoachCareerRow*,size_t);
void coach_profile_publish_team_fixtures(int club,const char*team_name,const FceFixture*,size_t,int today);
BOOL coach_profile_take_refresh(void);
BOOL coach_profile_open(const CoachProfileContext*,const CoachCareerRow*,size_t);
void coach_profile_bind_splits(CoachCareerRow*,size_t,const FceFixture*,size_t,int today,int club,int season);
void coach_profile_bind_form(CoachProfileContext*,const FceFixture*,size_t,int today);
#ifdef __cplusplus
}
#include "../../render/assets/fifa_player_assets.h"
struct CoachCardData {
    CoachProfileContext context={};std::vector<CoachCareerRow>rows;
    fifa_player::Texture photo,flag;std::string nationality_name,league_name;
    std::shared_ptr<const fifa_player::Model>model;
};
/* Worker owns every resource. Embedded pages share the parent's modal and
 * never open/close the host or release input to the native game underneath. */
CoachCardData coach_profile_prepare_card(fifa_player::Assets&,const ClubPlayerRow&,const char*club_name);
bool coach_profile_begin_embedded(const CoachCardData&);
void coach_profile_draw_embedded();
void coach_profile_end_embedded();
unsigned coach_profile_card_revision();
bool coach_profile_register(const char*,void(*log)(const char*));
void coach_profile_device(ID3D11Device*);
#ifdef COACH_PROFILE_TEST
struct CoachProfileTestView {int kind,id,club,page;size_t rows;bool model,photo,external;float yaw,zoom,pan,scroll;};
CoachProfileTestView coach_profile_test_view();
bool coach_profile_test_tab_center(int,float&,float&);
#endif
#endif
#endif
