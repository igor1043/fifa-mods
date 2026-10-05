#pragma once
#include "../../screens/club/club_player_screen.h"
#include "../../screens/player/player_competition_data.h"
#include <cstdint>
#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <array>
namespace fifa_player {
/* Read-only cached copy; no asset I/O or game query on the draw thread. */
player_competitions::Stats profile_competitions(int player,int club);
struct CompetitionIdentity {int root=0,asset=0;std::string name;};
struct Vec3 { float x, y, z; };
struct Vertex { Vec3 position; float u, v; uint16_t joints[8]={}; uint8_t weights[8]={}; Vec3 normal={}; };
struct Skeleton {
    std::vector<std::string> names;
    std::vector<uint16_t> parents;
    std::vector<std::array<float,16>> inverse_bind;
};
struct Texture { uint32_t width=0, height=0, format=0; std::vector<uint8_t> bytes; };
struct KitThumbnail {int type=0,variant=0;bool goalkeeper=false;Texture image;};
struct Part {
    std::string name, asset;
    std::vector<Vertex> vertices;
    std::vector<uint32_t> indices;
    int texture=-1;
    int hair_coeff_texture=-1;
    Vec3 color={1,1,1};
    Vec3 tint={1,1,1};
    bool blend=false;
    bool skinned=false;
    bool native_normals=false;
    float alpha_scale=1;
};
/* Optional hand contacts are in the final grounded actor-local centimetres.
 * The formation computes them from the neighbour's posed shoulder landmarks. */
struct PoseContacts {bool left=false,right=false;Vec3 left_target={},right_target={};float floor_cm=0;};
/* Stable pose IDs. Add a recipe in fifa_player_pose.cpp; the UI enumerates
 * this catalog and the worker includes its ID in the request/cache key. */
/* Coach poses are queried by stance/context: standing poses are for normal
 * coach views and sideline previews; seated poses belong to press-conference
 * scenes with furniture. PoseCoach remains the standing alias for old callers. */
enum PresentationPoseMode {
    PoseGroup=1,PoseIndividual=2,
    PoseStandingCoach=4,PoseCoach=PoseStandingCoach,
    PoseSeatedCoach=8,PosePressConferenceCoach=PoseSeatedCoach,
    PoseCoachAny=PoseStandingCoach|PoseSeatedCoach,
    PoseSeatedPlayer=16,PoseFullSquad=32
};
enum ClubRoomKind {RoomPhoto=0,RoomPress=1,RoomDressing=2,RoomTrophies=3,RoomPressPair=4,RoomArtifact=5,RoomStadium=6,RoomOfficeLineup=7,RoomFullSquadPhoto=8,RoomGym=9,RoomTraining=10};
struct PresentationPoseInfo {
    unsigned id,modes;const char*name;float column_spacing,back_z,front_z;
    unsigned back_count=6;int contact_pattern=0; /* 0 alternating, 1 none, 2 front back-links. */
};
size_t presentation_pose_count(unsigned mode=0);
const PresentationPoseInfo* presentation_pose_at(size_t index,unsigned mode=0);
const PresentationPoseInfo* presentation_pose_find(unsigned id);
struct Model {
    std::vector<Part> parts;
    std::vector<Texture> textures;
    std::string diagnostic;
    bool scene_camera_valid=false;
    Vec3 scene_camera_position={};
    float scene_camera_yaw=0,scene_camera_pitch=0,scene_camera_fov=60;
    bool specific_head=false;
    size_t player_count=1;
    std::shared_ptr<const Skeleton> skeleton;
    float bind_scale=1,bind_feet=0;
    bool presentation_pose=false;
    unsigned presentation_pose_id=0;
    float pose_floor_cm=0;
    Vec3 left_shoulder={},right_shoulder={},left_hand={},right_hand={};
    Vec3 left_elbow={},right_elbow={};
    Vec3 left_hip={},right_hip={},left_knee={},right_knee={};
    Vec3 left_fingers={},right_fingers={};
    float left_support_error_cm=0,right_support_error_cm=0;
    int player_id=0,height_cm=180;
    int team_id=0,crest_texture=-1;
    bool club_colors_valid=false;
    Vec3 club_colors[3]={{.12f,.19f,.23f},{.23f,.3f,.34f},{.8f,.8f,.8f}};
    bool goalkeeper=false;
    ClubRoomKind room=RoomPhoto;
    float stadium_focus_radius=0;
    int press_player_id=0;
    bool press_coach_present=false;
    struct Placement {int player_id,height_cm;bool goalkeeper,crouching;float x,z;bool linked_left=false,linked_right=false;float left_error=0,right_error=0;bool back_left=false,back_right=false;};
    std::vector<Placement> formation;
};
/* Base home/GK kit geometry, read-only. No FIFA table pointers or DB writes. */
bool read_kit_collars(const std::vector<uint8_t>&,std::unordered_map<unsigned,int>&);
bool read_kit_collar_override(const std::string&,int team,int kit,int&collar);
struct CoachAsset {std::string name,asset;std::shared_ptr<const Model>model;};
/* Read-only. Loose resources override BIG packages. Owns every decoded byte;
 * no pointer into FIFA tables, actor objects or borrowed graphic resources. */
class Assets {
    struct Entry { std::string archive; uint32_t offset, length; };
    std::string root_;
    std::unordered_map<std::string,Entry> entries_;
    bool indexed_=false;
    bool rig_checked_=false;
    std::shared_ptr<const Skeleton> rig_;
    std::unordered_map<int,Texture> crests_;
    std::unordered_map<int,bool> checked_crests_;
    std::unordered_map<int,Texture> portraits_;
    std::unordered_map<int,bool> checked_portraits_;
    bool nationalities_checked_=false;
    std::unordered_map<int,int> nationalities_;
    std::unordered_map<int,int> birthdates_;
    std::unordered_map<int,int> preferred_feet_,club_leagues_;
    std::unordered_map<int,std::string> league_names_;
    std::unordered_map<int,std::string> competition_names_;
    bool league_strength_checked_=false;
    std::unordered_map<int,float> league_strengths_;
    void load_player_identities();
    bool kits_checked_=false;
    std::unordered_map<unsigned,int> kit_collars_;
    std::unordered_map<unsigned,int> resolved_collars_;
    void index_archives();
public:
    explicit Assets(const std::string &root):root_(root) {}
    bool read(const std::string &name, std::vector<uint8_t> &decoded);
    bool read_packaged(const std::string&name,std::vector<uint8_t>&decoded);
    bool exists(const std::string &name);
    std::string first(const std::string &prefix, const std::string &suffix);
    bool crest(int team_id,Texture &);
    bool competition_icon(int asset_id,Texture &);
    bool trophy_icon(int trophy_id,Texture &);
    bool competition_movement_icon(bool up,Texture &);
    std::vector<CompetitionIdentity> profile_competition_names(int player,int club);
    bool portrait(int player_id,Texture &);
    int nationality(int player_id); /* Live sidecar first; installed DB for offline assets only. */
    int player_age(int player_id);
    int preferred_foot(int player_id);
    int league(int club_id,std::string &name);
    float league_strength(int club_id);
    bool nationality_flag(int nationality,Texture &);
    std::vector<KitThumbnail> kit_thumbnails(int team_id);
    void clear_portrait_cache(){portraits_.clear();checked_portraits_.clear();}
    int kit_collar(int team_id,int kit_type);
    CoachAsset coach(const ClubPlayerRow &club);
    Model trophy(int trophy_id);
    Model load(const ClubPlayerRow &row);
};
bool decode_container(const std::vector<uint8_t> &, std::vector<uint8_t> &,size_t byte_limit=64*1024*1024);
bool read_mesh(const std::vector<uint8_t> &, std::vector<Part> &);
/* Stadium-specific bounds and material groups, never actor decoder defaults. */
bool read_stadium(const std::vector<uint8_t>&mesh,const std::vector<uint8_t>&textures,Model&);
bool read_texture(const std::vector<uint8_t> &, const std::string &name, Texture &);
bool read_crest_dds(const std::vector<uint8_t> &, Texture &);
float hair_alpha_scale(const Texture &);
std::vector<std::string> texture_names(const std::vector<uint8_t> &);
Model assemble_team(const std::vector<std::shared_ptr<const Model>> &players,unsigned pose_id=1);
/* Full club photo contract. The generic assembler above also supports smaller
 * engineering previews; a career starting-XI screen must never show a subset. */
Model assemble_starting_eleven(const std::vector<std::shared_ptr<const Model>> &players,unsigned pose_id=1);
bool read_skeleton(const std::vector<uint8_t> &, Skeleton &);
bool read_coach_skeleton(const std::vector<uint8_t>&,Skeleton&);
bool apply_coach_pose(Model&,unsigned pose_id);
Model build_club_room(const std::vector<std::shared_ptr<const Model>>&,ClubRoomKind,std::shared_ptr<const Model>coach=nullptr,unsigned coach_pose=205);
/* Separate, all-roster official portrait. Requires every current-team model
 * and that club's own SLC coach; never substitutes starters or another club. */
Model build_full_squad_photo(const std::vector<std::shared_ptr<const Model>>&,std::shared_ptr<const Model>coach);
Model build_coach_arrival(const Model&club,const Model&coach);
Model build_trophy_room(const Model&club,const std::vector<std::shared_ptr<const Model>>&trophies);
bool apply_presentation_pose(Model &, bool crouching,const PoseContacts *contacts=nullptr,unsigned pose_id=1);
}
