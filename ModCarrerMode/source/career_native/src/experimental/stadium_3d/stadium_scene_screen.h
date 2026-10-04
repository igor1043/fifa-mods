#pragma once
#include <windows.h>
#define FIFA_STADIUM_SCENE_ACTION "FifaModsOpenStadium3D"
#ifdef __cplusplus
struct ID3D11Device;
extern "C" {
#endif
BOOL stadium_scene_take_refresh(void);
void stadium_scene_publish(int club,const char*name,const char*key);
#ifdef __cplusplus
}
bool stadium_scene_register(const char*root,void(*logger)(const char*));
void stadium_scene_device(ID3D11Device*);
#ifdef STADIUM_SCENE_TEST
struct StadiumSceneTestView {bool ready,model,orbit;int club;float yaw,zoom;bool free_camera;float x,y,z,pitch;};
StadiumSceneTestView stadium_scene_test_view();
#endif
#endif
