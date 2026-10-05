#include "new_experience_rooms.h"
#include "../../../../ambientes3d/src/viewer_press_room.h"
#include "../../../../ambientes3d/src/viewer_training_center.h"
namespace fifa_player {
Model build_new_experience_room(Assets&assets,const std::string&root,const std::vector<std::shared_ptr<const Model>>&players,const std::vector<ClubPlayerRow>&rows,const CoachAsset&coach,ClubRoomKind kind){
    if(players.empty())return {};
    studio::Camera camera;Model room;int club=players.front()->team_id;
    if(kind==RoomPress||kind==RoomPressPair){studio::Settings settings;settings.club=club;settings.press_slots={0,-1,0,players.front()->player_id,0};
        auto resources=studio::load_press_resources(assets,root,club,0);
        room=studio::build_press_room(players,coach,resources,settings);studio::press_camera_view(camera,1);
    }else if(kind==RoomDressing){auto prints=studio::load_dressing_prints(assets,root,club);room=studio::build_dressing_room(players,rows,prints);studio::dressing_camera_view(camera,0);
    }else if(kind==RoomGym||kind==RoomTraining){auto resources=studio::load_training_resources(assets,root,club);room=studio::build_training_center(*players.front(),resources,kind==RoomTraining);studio::training_camera_view(camera,kind==RoomGym?6:7,0);
    }else return {};
    room.scene_camera_valid=true;room.scene_camera_position=camera.position;room.scene_camera_yaw=camera.yaw;room.scene_camera_pitch=camera.pitch;room.scene_camera_fov=camera.fov;
    room.diagnostic+=" | New Experience shared environments revision 20261004";return room;
}}
