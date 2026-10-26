#ifndef FIFA16_PLAYER_SEARCH_SCREEN_H
#define FIFA16_PLAYER_SEARCH_SCREEN_H
#include "../club/club_player_screen.h"
#define FIFA16_PLAYER_SEARCH_ACTION "FifaModsOpenPlayerSearch"
#define PLAYER_SEARCH_RESULT_CAPACITY 60000

typedef struct PlayerSearchIndexRow {
    int player_id,team_id,number,position,age,overall;
    char name[128];
    char team_name[128];
} PlayerSearchIndexRow;
typedef struct PlayerSearchDetail {
    ClubPlayerRow player;
    char team_name[128];
} PlayerSearchDetail;

#ifdef __cplusplus
extern "C" {
#endif
BOOL player_search_screen_take_index_request(unsigned *serial);
void player_search_screen_publish_index(const PlayerSearchIndexRow *rows,size_t count,unsigned serial,int valid);
BOOL player_search_screen_take_detail_request(int *player,int *team,int *number,int *position,unsigned *serial);
void player_search_screen_publish_detail(const PlayerSearchDetail *detail,unsigned serial,int found);
void player_search_screen_invalidate(void);
void player_search_screen_request_native_refresh(void);
#ifdef __cplusplus
}
bool player_search_screen_register(const char *game_root,void (*log)(const char *));
void player_search_screen_set_device(struct ID3D11Device *device);
#endif
#endif
