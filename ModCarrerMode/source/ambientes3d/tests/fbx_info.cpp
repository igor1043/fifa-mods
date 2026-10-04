#include "ufbx.h"
#include <cstdio>
#include <fstream>
#include <filesystem>
#include <vector>
int wmain(int argc,wchar_t**argv){
    if(argc!=3)return 2;
    std::ifstream file(std::filesystem::path(argv[1]),std::ios::binary|std::ios::ate);
    if(!file)return 3;auto size=file.tellg();std::vector<char>bytes(size_t(size),0);file.seekg(0);file.read(bytes.data(),bytes.size());
    ufbx_load_opts opts={};opts.ignore_geometry=true;opts.ignore_embedded=true;opts.load_external_files=false;opts.target_axes=ufbx_axes_right_handed_y_up;opts.target_unit_meters=.01;
    ufbx_error error={};auto*s=ufbx_load_memory(bytes.data(),bytes.size(),&opts,&error);if(!s)return 4;
    std::ofstream out(std::filesystem::path(argv[2]),std::ios::binary);
    out<<"Nodes="<<s->nodes.count<<" bones="<<s->bones.count<<" poses="<<s->poses.count<<" fps="<<s->settings.frames_per_second<<" units="<<s->settings.unit_meters<<"\n";
    for(auto*a:s->anim_stacks)out<<"TAKE "<<a->name.data<<" "<<a->time_begin<<" "<<a->time_end<<"\n";
    for(auto*n:s->nodes){out<<n->typed_id<<"\t"<<n->name.data<<"\tparent="<<(n->parent?int(n->parent->typed_id):-1)<<"\tbone="<<(n->bone!=nullptr)<<"\tdefault="<<n->node_to_world.m03<<","<<n->node_to_world.m13<<","<<n->node_to_world.m23;
        for(auto*p:s->poses)if(p->is_bind_pose)for(auto&b:p->bone_poses)if(b.bone_node==n)out<<"\tbind="<<b.bone_to_world.m03<<","<<b.bone_to_world.m13<<","<<b.bone_to_world.m23;
        out<<"\n";
    }
    ufbx_free_scene(s);return out?0:5;
}
