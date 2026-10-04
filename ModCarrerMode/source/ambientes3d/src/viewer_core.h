#pragma once
#define NOMINMAX
#include "fifa_player_renderer.h"
#include <filesystem>
#include <map>
#include <string>
#include <vector>
#include <array>

namespace studio {
namespace fs = std::filesystem;
using fifa_player::Vec3;
struct Element { std::string name; std::map<std::string,std::string> values; bool end=false; };
std::vector<Element> read_xml(const fs::path&);
std::string utf8(const std::wstring&);
std::wstring wide(const std::string&);
bool path_inside(const fs::path&file,const fs::path&folder);
struct JointEdit { std::string name; Vec3 rotation={},translation={}; float scale=1; };
struct Keyframe {float time=0;std::vector<JointEdit>joints;};
struct BoneMapping {std::string target,source;};
struct ObjectEdit { std::string name; Vec3 translation={},rotation={}; float scale=1; bool visible=true; };
struct ActorEdit {
    int player=0;
    Vec3 translation={},rotation={};
    float scale=1;
    unsigned pose=0; // Zero keeps this actor's original team-photo stance.
    std::vector<JointEdit>joints;
};
struct Camera {
    Vec3 position={0,155,650},target={0,140,0};
    float yaw=0,pitch=0,fov=45,speed=160,distance=650;
    bool orbit=true;
    Vec3 forward() const;
    void synchronize_orbit();
    void move(float right,float up,float forward,float dt);
    void look(float horizontal,float vertical);
};
struct CameraKey {
    float time=0;Vec3 position={},target={};float fov=60;
    int transition=0; // 0 smooth, 1 linear, 2 cut (with a short visual fade).
};
struct CameraScene {
    std::string id,name;int environment=1;std::vector<CameraKey>keys;
};
struct Settings {
    std::string game="U:\\fifa 16";
    int club=1043,player=0,scene=0;
    unsigned pose=205;
    bool coach_target=true;
    bool room_cutaway=false;
    // 0 = empty, -1 = club coach, -2 = selected player (legacy/default).
    std::array<int,5>press_slots={0,-1,0,-2,0};
    int press_competition=0;
    bool press_final=false,press_audience=true;
    Camera camera;
    std::vector<JointEdit> joints;
    std::vector<ObjectEdit> objects;
    std::vector<ActorEdit> actors;
    std::vector<Keyframe> keys;
    std::string fbx_file;
    int fbx_take=0;
    float fbx_time=0;
    bool root_motion=false;
    std::vector<BoneMapping>mapping;
    std::vector<CameraScene>camera_scenes;
};
Settings load_settings(const fs::path&);
void save_settings(const fs::path&,const Settings&);
struct Club { int id=0; std::string name; unsigned colors[3]={}; };
struct KitPrintInfo {int font=0,color=0,name_font=0;Vec3 name_color={1,1,1};};
std::map<int,KitPrintInfo> club_kit_prints(const fs::path&game,int club);
class Catalog {
public:
    std::vector<Club> clubs;
    std::map<int,std::vector<ClubPlayerRow>> rosters;
    void load(const fs::path&game);
};
struct Bounds {Vec3 low={},high={},center={}; float radius=1;};
Bounds bounds(const fifa_player::Model&);
void edit_objects(fifa_player::Model&,const std::vector<ObjectEdit>&);
bool save_png(ID3D11Device*,ID3D11DeviceContext*,ID3D11ShaderResourceView*,const fs::path&);
}
