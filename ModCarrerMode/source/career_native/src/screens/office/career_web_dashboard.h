#ifndef FIFA_CAREER_WEB_DASHBOARD_H
#define FIFA_CAREER_WEB_DASHBOARD_H
#include <stddef.h>
typedef struct CareerWebLeader {int player,club,value;char name[128];} CareerWebLeader;
typedef struct CareerWebStanding {int team,rank,games,wins,draws,losses,goals_for,goals_against,points;char name[128];} CareerWebStanding;
typedef struct CareerWebCompetition {int root,asset;size_t row_count,goal_count,assist_count;CareerWebStanding rows[20];CareerWebLeader goals[5],assists[5];} CareerWebCompetition;
typedef struct CareerWebMatch {int home,away,asset;char home_name[128],away_name[128],date[64],time[32],score[32];} CareerWebMatch;
typedef struct CareerWebInjury {int player;char name[128],injury[128],return_label[64];} CareerWebInjury;
typedef struct CareerWebRecord {int games,wins,draws,losses,goals_for,goals_against,points;} CareerWebRecord;
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
