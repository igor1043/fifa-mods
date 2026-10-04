#ifndef FIFA16_SPONSOR_SCREEN_H
#define FIFA16_SPONSOR_SCREEN_H
#include "../club/club_player_screen.h"
#define FIFA16_SPONSOR_ACTION "FifaModsOpenSponsors"
#ifdef __cplusplus
struct ID3D11Device;
extern "C" {
#endif
/* Owned current-career roster. No database pointers or contract/save writes. */
void sponsor_screen_publish(const ClubPlayerRow*,size_t,int club,const char*name);
BOOL sponsor_screen_take_refresh_request(void);
#ifdef __cplusplus
}
bool sponsor_screen_register(const char*root,void(*log)(const char*));
void sponsor_screen_device(ID3D11Device*);
#ifdef CAREER_OPS_SCREEN_TEST
struct SponsorScreenTestView {int club,player,rendered_player,selected;size_t roster,slots;bool model;unsigned pose;bool portrait;float yaw,height,zoom;bool full_view;};
SponsorScreenTestView sponsor_screen_test_view();
bool sponsor_screen_test_slot_center(int i,float&x,float&y);
#endif
#endif
#endif
