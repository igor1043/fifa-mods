#ifndef FIFA_TROPHY_ROOM_H
#define FIFA_TROPHY_ROOM_H
#include <stddef.h>
#include "../club/club_player_screen.h"
#define FIFA_TROPHY_ROOM_ACTION "FifaModsOpenTrophyRoom"
/* -1 count means unresolvable history, never a guessed zero. One row per
 * competition, including an unwon tournament the managed club participates in. */
typedef struct TrophyRoomRow {int competition,trophy,count;int logo,title_asset;char name[128];} TrophyRoomRow;
#ifdef __cplusplus
struct ID3D11Device;
extern "C" {
#endif
void trophy_room_publish(const TrophyRoomRow*,size_t,const ClubPlayerRow*,int known,int unresolved);
#ifdef __cplusplus
}
bool trophy_room_register(const char*root,void(*log)(const char*));
void trophy_room_device(ID3D11Device*);
#ifdef CAREER_OPS_SCREEN_TEST
struct TrophyRoomTestView {size_t rows,models;int selected,page;bool detail;float yaw,zoom;};
TrophyRoomTestView trophy_room_test_view();
#endif
#endif
#endif
