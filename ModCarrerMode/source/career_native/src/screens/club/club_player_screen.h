#ifndef FIFA16_CLUB_PLAYER_SCREEN_H
#define FIFA16_CLUB_PLAYER_SCREEN_H
#include <stddef.h>
#include <windows.h>
#define FIFA16_CLUB_PLAYER_ACTION "FifaModsOpenClubPlayers"
#define FIFA16_CLUB_SQUAD_ACTION "FifaModsOpenClubSquad"
#define FIFA16_FULL_SQUAD_ACTION "FifaModsOpenFullSquad"
#define FIFA16_PRESS_CONFERENCE_ACTION "FifaModsOpenPressConference"
#define FIFA16_MY_OFFICE_ACTION "FifaModsOpenMyOffice"
#define CLUB_PLAYER_CAPACITY 100
#define CLUB_PLAYER_ATTRIBUTE_COUNT 34
typedef struct ClubPlayerRow {
    int player_id, team_id, number, position, age, overall;
    /* Career-only identity/contract data. -1 means the source did not provide
     * a value; career_data_valid keeps base-database rows from masquerading
     * as live save data. */
    int birthdate_raw, join_team_date_raw, career_date, retiring, weekly_wage;
    int career_data_valid;
    int head_type, head_class, hair_type, hair_color, skin_tone, skin_type;
    int facial_hair_type, facial_hair_color, shoe_type, shoe_design;
    int gender, height, weight, body_type;
    int eye_color, eyebrow, sideburns, sleeve_length, jersey_fit, jersey_style;
    int sock_length, short_style, glove_type;
    unsigned int club_colors[3];
    int club_colors_valid;
    int attributes[CLUB_PLAYER_ATTRIBUTE_COUNT];
    char name[128];
    int captain; /* Current club's teams.captainid == player_id; never inferred. */
    int squad_position; /* teamplayerlinks.position: 0..27 pitch, 28 bench, 29 reserves; -1 unknown. */
    int secondary_positions[3]; /* players.preferredposition2..4, not tactical squad slots. */
    int secondary_positions_valid; /* Zero means absent source: never interpret zero-filled rows as extra GOL. */
} ClubPlayerRow;
#ifdef __cplusplus
struct ID3D11Device;
struct ImFont;
extern "C" {
#endif
const char *club_player_attribute_field(size_t index);
/* Sidecar identity: keep the owned roster ABI and saved QA fixtures unchanged.
 * Called only by the existing native DB provider, never by Present. */
void player_profile_publish_nationality(int player_id, int nationality);
void player_profile_publish_birthdate(int player_id,int raw_birthdate,int career_date);
void player_profile_publish_career_date(int career_date);
void player_profile_publish_foot(int player_id,int preferredfoot);
void player_profile_publish_league(int club_id,int league_id,const char*league_name);
void player_profile_publish_league_strength(int club_id,int league_id,float strength);
void club_player_screen_publish(const ClubPlayerRow *, size_t, int team_id,
    const char *team_name);
/* Consume on the existing FIFA provider thread, never query from Present. */
BOOL club_player_screen_take_refresh_request(void);
#ifdef __cplusplus
}
bool club_player_screen_register(const char *game_root, void (*log)(const char *));
void club_player_screen_set_device(ID3D11Device *device);
void club_player_screen_set_number_font(ImFont *font);
bool club_player_screen_open_search_profile(const ClubPlayerRow *row,const char *team_name);
/* Open an existing game-rendered room from the New Experience HTML host. */
void club_player_screen_request_web_room(int room_kind);
void club_player_screen_request_web_player(int player_id);
/* Other clubs share the modal host but NEVER replace the career-owned roster. */
bool club_player_begin_embedded(const ClubPlayerRow*,size_t,int,const char*);
void club_player_draw_embedded();
bool club_player_back_embedded();
void club_player_end_embedded();
#ifdef CLUB_PLAYER_SCREEN_TEST
struct ClubOfficeTestView {bool active;int focus,menu,item,slide;bool coach_scene;int social_index,social_posts;unsigned long long followers;bool social_table,manager_valid;int manager_games,manager_wins,manager_draws,manager_losses,manager_confidence,manager_reputation;};
struct ClubOfficeSquadTestSummary {int players,average_age,average_overall,goalkeepers,defenders,midfielders,attackers;};
ClubOfficeTestView club_office_test_view();
bool club_office_test_center(int,float&,float&);
ClubOfficeSquadTestSummary club_office_test_squad_summary(const ClubPlayerRow*,size_t);
bool club_office_test_social_next_center(float&,float&);
bool club_office_test_social_dot_center(int,float&,float&);
int club_office_test_social_source_count(int);
bool club_office_test_menu_center(int,float&,float&);
bool club_office_test_dot_center(int,float&,float&);
/* Read-only render-thread snapshot; not compiled/exported into the game DLL. */
struct ClubPlayerScreenTestView {bool group;int selected,page;unsigned pose;float yaw,zoom,pan_x,pan_y;size_t roster,starters,portraits;bool valid;int selected_id;bool coach,coach_selected;int room;float profile_pan_y,scroll_y,scroll_max;size_t flags;bool home,coach_child;int focus;float card_coach_yaw,card_coach_zoom;bool card_coach_model;int card_club,card_nationality;int profile_view;};
bool club_player_screen_test_card_center(int,float&,float&);
ClubPlayerScreenTestView club_player_screen_test_view();
bool club_player_screen_test_starter(int player_id);
bool club_player_screen_test_select_pose(unsigned id);
bool club_player_screen_test_select_room(int kind);
int club_player_screen_test_press_player();
int club_player_screen_test_press_rendered();
bool club_player_screen_test_resample_press_player();
#endif
#endif
#endif

void club_player_screen_request_web_pose(int id);
