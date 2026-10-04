#pragma once
#include "viewer_core.h"
namespace studio {
std::vector<CameraScene> cinematic_catalog(int environment,const fifa_player::Model&,const std::vector<ClubPlayerRow>&,int player);
void validate_camera_scene(const CameraScene&);
Camera sample_camera_scene(const CameraScene&,float time);
float camera_scene_duration(const CameraScene&);
float camera_scene_fade(const CameraScene&,float time);
CameraKey capture_camera_key(const Camera&,float time);
void load_camera_library(const fs::path&,Settings&);
void save_camera_library(const fs::path&,const Settings&);
}
