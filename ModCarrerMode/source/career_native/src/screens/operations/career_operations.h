#ifndef FIFA_CAREER_OPERATIONS_H
#define FIFA_CAREER_OPERATIONS_H
#include <windows.h>
#include <stddef.h>
#include <stdint.h>
#include "../club/club_player_screen.h"
#define FIFA_RETIREMENT_ACTION "FifaModsOpenRetirement"
#define FIFA_LOANS_ACTION "FifaModsOpenLoans"
#define FIFA_TRANSFER_MARKET_ACTION "FifaModsOpenTransferMarket"
#define FIFA_MY_TRANSFERS_ACTION "FifaModsOpenMyTransfers"
#define FIFA_TRANSFER_LEAGUES_ACTION "FifaModsOpenTransferLeagues"
#define FIFA_TRANSFER_LEAGUE_DETAIL_ACTION "FifaModsOpenTransferLeagueDetail"
typedef struct RetirementUiPlayer {unsigned int id;int age,retiring,in_club;char name[128];int team_id;char club_name[128];} RetirementUiPlayer;
typedef struct CareerTransferUiContext {
    uint32_t club,date,transfer_budget,wage_budget,currency;
    uint32_t first_window_end_mmdd,second_window_end_mmdd;
    int save_valid,window_ends_valid;
} CareerTransferUiContext;
#ifdef __cplusplus
extern "C" {
#endif
void career_operations_note_access(const char *path,const char *operation);
void career_operations_publish_context(int club,int date);
BOOL career_operations_get_transfer_context(CareerTransferUiContext *out);
/* Enqueue only. Native database work stays on the existing provider boundary. */
void career_operations_request_native_refresh(void);
BOOL retirement_screen_take_refresh(void);
void retirement_screen_publish(const RetirementUiPlayer*,size_t,int club,int date,int valid);
BOOL retirement_profile_take_request(unsigned *player,int *club,int *date);
void retirement_profile_publish(const ClubPlayerRow*,const char *team_name,int club,int date,int valid);
#ifdef __cplusplus
}
bool career_operations_register(const char *game_root,void (*log)(const char*));
void career_operations_device(ID3D11Device*);
#ifdef CAREER_OPS_SCREEN_TEST
struct CareerOpsScreenTestView {int scope,row,age;size_t selected;bool keyboard,confirm,queued,snapshot_valid;size_t filtered,portraits;bool profile,profile_valid;int plan;bool profile_model;float yaw,zoom;int profile_view,profile_category;float profile_scroll,competition_scroll;};
CareerOpsScreenTestView career_operations_test_view();
size_t career_operations_test_ids(unsigned *out,size_t capacity);
bool career_operations_test_row_center(int i,float&x,float&y,bool details=false);
bool career_operations_test_loan_center(int i,float&x,float&y);
bool career_operations_test_set_search(const char*);
bool career_operations_test_profile_tab_center(int,float&,float&);
#endif
#endif
#endif
