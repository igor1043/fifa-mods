#ifndef FIFA_TRANSFER_CENTER_SCREEN_H
#define FIFA_TRANSFER_CENTER_SCREEN_H
#include "../club/club_player_screen.h"
#include <stddef.h>
struct ID3D11Device;
struct ClubBrowserRow;

bool transfer_center_screen_register(const char* game_root);
void transfer_center_screen_device(ID3D11Device*);
void transfer_center_screen_publish_roster(const ClubPlayerRow*,size_t,int,const char*);
void transfer_center_screen_publish_league_catalog(const ClubBrowserRow*,size_t,int);

#endif
