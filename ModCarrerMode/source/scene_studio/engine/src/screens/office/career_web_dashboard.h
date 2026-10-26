#ifndef FIFA_CAREER_WEB_DASHBOARD_H
#define FIFA_CAREER_WEB_DASHBOARD_H
#include <stddef.h>
typedef struct CareerWebLeader {int player,club,value;char name[128];} CareerWebLeader;
typedef struct CareerWebRecord {int games,wins,draws,losses,goals_for,goals_against,points;} CareerWebRecord;
typedef struct CareerWebStanding {int team,rank,games,wins,draws,losses,goals_for,goals_against,points,zone,movement,form[5];char name[128];} CareerWebStanding;
typedef struct CareerWebCupGroup {int stage,classification_count;size_t row_count;CareerWebStanding rows[20];} CareerWebCupGroup;
typedef struct CareerWebCupMatch {int home,away,date,time,played,home_score,away_score;} CareerWebCupMatch;
typedef struct CareerWebCupTie {int stage,stage_kind,round,team_a,team_b,leg_count;char team_a_name[128],team_b_name[128];CareerWebCupMatch legs[2];} CareerWebCupTie;
typedef struct CareerWebCompetition {int root,asset,is_cup,has_group_phase,current_stage_kind,record_valid;CareerWebRecord record;size_t row_count,goal_count,assist_count,group_count,bracket_tie_count;CareerWebStanding rows[20];CareerWebCupGroup groups[16];CareerWebCupTie bracket_ties[64];CareerWebLeader goals[5],assists[5];} CareerWebCompetition;
typedef struct CareerWebMatch {int home,away,asset;char home_name[128],away_name[128],date[64],time[32],score[32];} CareerWebMatch;
typedef struct CareerWebInjury {int player;char name[128],injury[128],return_label[64];} CareerWebInjury;
typedef struct CareerWebDashboard {int club,date,current,season_valid,next_fixture,capacity,attendance;CareerWebRecord season,home_record,away_record;size_t count,upcoming_count,previous_count;CareerWebCompetition competitions[5];CareerWebMatch upcoming[10],previous[10];size_t metric_counts[5],injury_count;CareerWebLeader metrics[5][5];CareerWebInjury injuries[10];} CareerWebDashboard;
#ifdef __cplusplus
extern "C" {
#endif
void career_web_dashboard_publish(const CareerWebDashboard*);
int career_web_dashboard_copy(int,CareerWebDashboard*);
#ifdef __cplusplus
}
#endif
#endif
