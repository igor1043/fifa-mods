#ifndef FIFA16_CAREER_NEWS_FEED_H
#define FIFA16_CAREER_NEWS_FEED_H

#include <stddef.h>
#include "career_web_dashboard.h"

#define CAREER_NEWS_CAPACITY 5
#define CAREER_NEWS_TEXT_CAPACITY 256
#define CAREER_NEWS_NAME_CAPACITY 96

typedef struct CareerNewsFacts {
    int club_id;
    int calendar_date;
    char club_name[CAREER_NEWS_NAME_CAPACITY];
    int club_reputation; /* 0..100, -1 when unavailable. */

    int next_valid;
    int next_date;
    int next_home;
    int next_opponent;
    char next_opponent_name[CAREER_NEWS_NAME_CAPACITY];
    int next_rivalry; /* 0..100, values from the FIFA rivalry database. */
    int next_opponent_reputation; /* 0..100, -1 when unavailable. */
    int next_knockout;
    int next_opponent_rank;

    int last_valid;
    int last_date;
    int last_home;
    int last_goals_for;
    int last_goals_against;
    char last_opponent_name[CAREER_NEWS_NAME_CAPACITY];

    int recent_games;
    int recent_wins;
    int recent_draws;
    int recent_losses;
    int recent_goals_for;
    int recent_goals_against;
    int recent_points;
    int streak_result; /* 1 win, 0 draw, -1 loss, 2 unbeaten, -2 winless. */
    int streak_length;

    int table_valid;
    int table_rank;
    int table_count;
    int table_played;
    int table_points;
    int table_leader_points;

    int goals_leader_valid;
    int goals_leader_goals;
    char goals_leader_name[CAREER_NEWS_NAME_CAPACITY];
    int assists_leader_valid;
    int assists_leader_assists;
    char assists_leader_name[CAREER_NEWS_NAME_CAPACITY];

    int squad_valid;
    int squad_total;
    int squad_average_age;
    int squad_average_overall;
} CareerNewsFacts;

typedef struct CareerNewsManagerFacts {
    int club_id;
    int calendar_date;
    int valid;
    int confidence; /* 0..100, -1 when unavailable. */
    int reputation; /* FIFA manager reputation, -1 when unavailable. */
    char name[CAREER_NEWS_NAME_CAPACITY];
    int season_record_valid;
    int games;
    int wins;
    int draws;
    int losses;
    int goals_for;
    int goals_against;
    int trophies;
} CareerNewsManagerFacts;

typedef struct CareerNewsItem {
    int category;
    int published_date;
    char title[CAREER_NEWS_TEXT_CAPACITY];
    char subtitle[CAREER_NEWS_TEXT_CAPACITY];
    char posting_date[24];
} CareerNewsItem;

typedef struct CareerClubStadiumFacts {
    int club_id;
    int valid;
    int capacity;
    char name[160];
    char location[128];
    char image_key[256];
} CareerClubStadiumFacts;

typedef struct CareerNextMatchFacts {
    int club_id;
    int valid;
    int fixture;
    int calendar_date;
    int match_date;
    int match_time; /* HHMM, -1 when unavailable. */
    int home_team;
    int away_team;
    int home_rank;
    int away_rank;
    int competition_asset;
    int venue_pending;
    char home_name[CAREER_NEWS_NAME_CAPACITY];
    char away_name[CAREER_NEWS_NAME_CAPACITY];
    char stadium[160];
    char location[96];
    char referee[96];
} CareerNextMatchFacts;

#ifdef __cplusplus
extern "C" {
#endif
void career_news_publish_facts(const CareerNewsFacts *facts);
void career_news_publish_manager(const CareerNewsManagerFacts *manager);
size_t career_news_copy(int club_id, CareerNewsItem *out, size_t capacity);
void career_next_match_publish(const CareerNextMatchFacts *match);
int career_next_match_copy(int club_id, CareerNextMatchFacts *out);
void career_club_stadium_publish(const CareerClubStadiumFacts *stadium);
int career_club_stadium_copy(int club_id, CareerClubStadiumFacts *out);
#ifdef __cplusplus
}
#endif

#endif
