#define NOMINMAX
#include "../assets/fifa_player_assets.h"
#include <algorithm>
#include <cmath>
#include <limits>

namespace fifa_player {
namespace {
struct RoomBuilder {
    Model room;
    void face(const char*name,Vec3 a,Vec3 b,Vec3 c,Vec3 d,Vec3 n,Vec3 color,int texture=-1,bool blend=false) {
        Part p;p.name=name;p.asset="mod/club-room/"+std::string(name);p.color=color;p.texture=texture;p.blend=blend;p.native_normals=true;
        Vec3 points[]={a,b,c,d};float uv[][2]={{0,0},{1,0},{1,1},{0,1}};
        for(int i=0;i<4;++i){Vertex v={};v.position=points[i];v.normal=n;v.u=uv[i][0];v.v=uv[i][1];p.vertices.push_back(v);}
        p.indices={0,1,2,0,2,3};room.parts.push_back(std::move(p));
    }
    void box(const char*name,Vec3 p,Vec3 size,Vec3 color) {
        float x=p.x-size.x/2,X=p.x+size.x/2,y=p.y-size.y/2,Y=p.y+size.y/2,z=p.z-size.z/2,Z=p.z+size.z/2;
        face(name,{x,Y,Z},{X,Y,Z},{X,y,Z},{x,y,Z},{0,0,1},color);
        face(name,{X,Y,z},{x,Y,z},{x,y,z},{X,y,z},{0,0,-1},color);
        face(name,{x,Y,z},{x,Y,Z},{x,y,Z},{x,y,z},{-1,0,0},color);
        face(name,{X,Y,Z},{X,Y,z},{X,y,z},{X,y,Z},{1,0,0},color);
        face(name,{x,Y,z},{X,Y,z},{X,Y,Z},{x,Y,Z},{0,1,0},color);
        face(name,{x,y,Z},{X,y,Z},{X,y,z},{x,y,z},{0,-1,0},color);
    }
    void crest(float x,float y,float z,float height) {
        int t=room.crest_texture;if(t<0)return;const auto&tex=room.textures[t];float w=height*tex.width/tex.height;
        face("club-emblem",{x-w/2,y+height/2,z},{x+w/2,y+height/2,z},{x+w/2,y-height/2,z},{x-w/2,y-height/2,z},{0,0,1},{1,1,1},t,true);
    }
    void tube(const char*name,Vec3 a,Vec3 b,float radius,Vec3 color) {
        Vec3 axis={b.x-a.x,b.y-a.y,b.z-a.z};float len=sqrtf(axis.x*axis.x+axis.y*axis.y+axis.z*axis.z);if(len<.01f)return;
        axis={axis.x/len,axis.y/len,axis.z/len};Vec3 u=fabsf(axis.y)<.9f?Vec3{-axis.z,0,axis.x}:Vec3{axis.y,-axis.x,0};
        len=sqrtf(u.x*u.x+u.y*u.y+u.z*u.z);u={u.x/len,u.y/len,u.z/len};
        Vec3 v={axis.y*u.z-axis.z*u.y,axis.z*u.x-axis.x*u.z,axis.x*u.y-axis.y*u.x};
        for(int i=0;i<12;++i){float t=i*6.2831853f/12,T=(i+1)*6.2831853f/12;
            Vec3 n={u.x*cosf(t)+v.x*sinf(t),u.y*cosf(t)+v.y*sinf(t),u.z*cosf(t)+v.z*sinf(t)};
            Vec3 N={u.x*cosf(T)+v.x*sinf(T),u.y*cosf(T)+v.y*sinf(T),u.z*cosf(T)+v.z*sinf(T)};
            face(name,{a.x+n.x*radius,a.y+n.y*radius,a.z+n.z*radius},{a.x+N.x*radius,a.y+N.y*radius,a.z+N.z*radius},
                {b.x+N.x*radius,b.y+N.y*radius,b.z+N.z*radius},{b.x+n.x*radius,b.y+n.y*radius,b.z+n.z*radius},n,color);}
    }
};
}
Model build_coach_arrival(const Model&club,const Model&source) {
    RoomBuilder b;auto&room=b.room;auto coach=source;
    if(club.team_id<=0||coach.team_id!=club.team_id||!apply_coach_pose(coach,207))return room;
    room.team_id=club.team_id;room.room=RoomPress;room.player_count=1;room.press_coach_present=true;room.presentation_pose_id=207;
    room.club_colors_valid=club.club_colors_valid;std::copy(std::begin(club.club_colors),std::end(club.club_colors),room.club_colors);
    if(club.crest_texture>=0&&size_t(club.crest_texture)<club.textures.size()){room.crest_texture=0;room.textures.push_back(club.textures[club.crest_texture]);}
    Vec3 white={.96f,.97f,.98f},soft={.88f,.91f,.94f},accent=room.club_colors[0],secondary=room.club_colors[1],dark={.10f,.13f,.16f};
    b.box("arrival-wall",{0,136,-85},{370,272,6},white);
    b.box("arrival-floor",{0,-3,5},{380,6,220},{.68f,.72f,.75f});
    b.box("arrival-door",{-99,110,-80},{75,220,3},dark);
    b.box("arrival-door-trim",{-140,110,-77},{4,224,5},accent);
    b.tube("arrival-handle",{-72,90,-73},{-72,104,-73},1.1f,{.65f,.69f,.72f});
    /* A wider sponsor-media wall like a real pre-match press corridor. Keep
     * the marks abstract; only the selected club crest is team-specific. */
    for(int y=0;y<6;++y)for(int x=0;x<8;++x){float X=-144+x*41.f,Y=38+y*40.f;
        Vec3 tile=(x+y)%2?soft:white;
        b.face("arrival-media-tile",{X-18,Y+14,-80},{X+18,Y+14,-80},{X+18,Y-14,-80},{X-18,Y-14,-80},{0,0,1},tile);
        if((x*7+y*3)%13==0)b.crest(X,Y,-78,15);
        else {
            float bar=7.f+float((x*11+y*5)%15);Vec3 mark=(x+y)%3==0?accent:(x+y)%3==1?secondary:dark;
            b.face("arrival-media-mark",{X-bar,Y+5,-78},{X+bar,Y+5,-78},{X+bar,Y+2,-78},{X-bar,Y+2,-78},{0,0,1},mark);
            b.face("arrival-media-mark",{X-10,Y-2,-78},{X+10,Y-2,-78},{X+10,Y-5,-78},{X-10,Y-5,-78},{0,0,1},dark);
        }
    }
    b.box("arrival-club-stripe",{25,252,-78},{300,10,2},accent);
    int offset=(int)room.textures.size();room.textures.insert(room.textures.end(),coach.textures.begin(),coach.textures.end());
    for(auto p:coach.parts){p.asset="mod/coach-arrival/source/"+p.asset;p.skinned=false;
        if(p.texture>=0)p.texture+=offset;if(p.hair_coeff_texture>=0)p.hair_coeff_texture+=offset;
        for(auto&v:p.vertices)v.position.z+=15;room.parts.push_back(std::move(p));}
    room.diagnostic="coach arrival: exact club identity, static native rig pose 207, no animation or save writes";return room;
}
Model build_club_room(const std::vector<std::shared_ptr<const Model>>&players,ClubRoomKind kind,std::shared_ptr<const Model>coach,unsigned coach_pose) {
    RoomBuilder b;b.room.player_count=0;if(players.empty()||!players[0]||(kind!=RoomPress&&kind!=RoomDressing&&kind!=RoomPressPair))return b.room;
    for(const auto&p:players)if(p&&p->team_id!=players[0]->team_id){b.room.diagnostic="mixed clubs rejected";return b.room;}
    const auto&club=*players[0];auto&room=b.room;room.team_id=club.team_id;room.room=kind;room.player_count=0;
    room.club_colors_valid=club.club_colors_valid;std::copy(std::begin(club.club_colors),std::end(club.club_colors),room.club_colors);
    if(club.crest_texture>=0&&size_t(club.crest_texture)<club.textures.size()){room.crest_texture=0;room.textures.push_back(club.textures[club.crest_texture]);}
    Vec3 white={.97f,.98f,1},dark={.065f,.08f,.10f},accent=room.club_colors[0],secondary=room.club_colors[1],silver={.55f,.60f,.65f};
    b.box("white-back-wall",{0,150,-225},{820,300,10},white);
    b.box("white-left-wall",{-410,150,0},{10,300,450},white);
    b.box("white-right-wall",{410,150,0},{10,300,450},white);
    b.box("white-floor",{0,-4,0},{830,8,460},{.82f,.86f,.88f});
    for(float x=-400;x<=400;x+=50)b.box("tile-joint",{x,.05f,0},{.35f,.1f,450},{.62f,.68f,.72f});
    for(float z=-200;z<=200;z+=50)b.box("tile-joint",{0,.05f,z},{810,.1f,.35f},{.62f,.68f,.72f});
    b.box("club-wall-stripe",{0,276,-218},{810,12,2},accent);
    b.box("club-wall-stripe-secondary",{0,263,-218},{810,5,2},secondary);
    b.box("light-soffit",{0,295,0},{820,8,450},white);
    for(float z:{-145.f,0.f,145.f})b.box("led-strip",{0,289,z},{790,2,3},{1.5f,1.5f,1.35f});
    for(float x:{-395.f,395.f})b.box("club-side-stripe",{x,15,0},{2,15,440},accent);
    if(kind==RoomPress||kind==RoomPressPair) {
        const bool pair=kind==RoomPressPair;
        Model seated_player;
        bool player_ready=false;
        if(pair&&players[0]->player_id>0) {
            seated_player=*players[0];
            player_ready=apply_presentation_pose(seated_player,false,nullptr,coach_pose==206?302:301);
        }
        b.box("press-media-panel",{0,168,-214},{610,168,3},white);
        for(int row=0;row<3;++row)for(int col=0;col<8;++col){float x=(col-3.5f)*70,y=114.f+row*50.f;
            b.box("media-tile",{x,y,-211},{68,48,1},(row+col)%2?Vec3{.9f,.93f,.96f}:white);b.crest(x,y,-209,28);}
        b.crest(0,241,-208,36);
        b.box("press-desk-front",{0,42,90},{325,82,6},accent);
        b.box("press-desk-foot",{0,5,92},{338,10,12},secondary);
        b.box("press-desk-left",{-158,40,50},{6,80,80},white);
        b.box("press-desk-right",{158,40,50},{6,80,80},white);
        b.box("press-desktop",{0,86,50},{350,7,100},white);
        b.box("press-desktop-edge",{0,82,101},{352,3,3},dark);
        b.crest(0,44,94,53);
        std::vector<float>seats=pair?std::vector<float>{-64.f,64.f}:std::vector<float>{0.f};
        for(float x:seats) {
            float seat_y=48;
            if(pair&&x>0&&player_ready)seat_y=std::max(35.f,std::min(65.f,(seated_player.left_hip.y+seated_player.right_hip.y)*.5f-5.f));
            b.box("chair-seat",{x,seat_y,-12},{58,8,52},dark);
            b.box("chair-back",{x,seat_y+46,-38},{56,88,10},dark);
            b.box("chair-accent",{x,seat_y+68,-32},{44,5,2},accent);
            b.tube("chair-pedestal",{x,4,-12},{x,seat_y-2,-12},3,silver);
            for(int leg=0;leg<5;++leg){float angle=leg*6.2831853f/5;
                Vec3 end={x+27*cosf(angle),4,-12+27*sinf(angle)};b.tube("chair-base",{x,7,-12},end,2,dark);b.box("caster",end,{7,6,7},dark);}
            b.box("microphone-base",{x-10,92,70},{15,4,12},dark);
            b.tube("microphone-stem",{x-10,94,70},{x-10,111,57},.45f,dark);
            b.tube("microphone-foam",{x-10,111,57},{x-8,118,52},1.15f,dark);
            b.box("microphone-club-flag",{x-10,105,64},{14,9,3},white);b.crest(x-10,105,66,8);
            b.box("media-notepad",{x+24,91,48},{20,1,26},white);
            b.tube("water-bottle",{x+45,91,59},{x+45,110,59},3.2f,{.2f,.45f,.75f});
            b.tube("bottle-cap",{x+45,110,59},{x+45,113,59},2.3f,white);
        }
        b.box("screen-left-frame",{-351,169,-214},{86,108,6},dark);
        b.box("screen-right-frame",{351,169,-214},{86,108,6},dark);
        b.crest(-351,169,-209,64);b.crest(351,169,-209,64);
        if(coach&&coach->team_id==room.team_id&&presentation_pose_find(coach_pose)&&
            (presentation_pose_find(coach_pose)->modes&PoseSeatedCoach)) {
            auto seated=*coach;
            if(apply_coach_pose(seated,coach_pose)) {
                int offset=(int)room.textures.size();room.textures.insert(room.textures.end(),seated.textures.begin(),seated.textures.end());
                for(auto p:seated.parts){p.asset="mod/club-room/seated-coach/source/"+p.asset;p.skinned=false;
                    if(p.texture>=0)p.texture+=offset;for(auto&v:p.vertices){v.position.z-=12;if(pair)v.position.x-=64;}room.parts.push_back(std::move(p));}
                room.presentation_pose_id=coach_pose;
                room.press_coach_present=true;
            }
        }
        if(player_ready) {
            int offset=(int)room.textures.size();room.textures.insert(room.textures.end(),seated_player.textures.begin(),seated_player.textures.end());
            for(auto p:seated_player.parts) {
                p.asset="mod/club-room/seated-player/source/"+p.asset;p.skinned=false;
                if(p.texture>=0)p.texture+=offset;if(p.hair_coeff_texture>=0)p.hair_coeff_texture+=offset;
                for(auto&v:p.vertices){v.position.x+=64;v.position.z-=12;}
                room.parts.push_back(std::move(p));
            }
            room.press_player_id=seated_player.player_id;
        }
        if(pair)room.player_count=(room.press_coach_present?1:0)+(room.press_player_id?1:0);
    } else {
        const size_t count=std::min(size_t(11),players.size());float spacing=66;
        for(size_t i=0;i<count;++i){float x=(float(i)-float(count-1)*.5f)*spacing;
            b.box("locker-white-back",{x,128,-212},{63,246,9},white);
            b.box("locker-colored-interior",{x,152,-206},{58,173,2},secondary);
            b.box("locker-divider",{x-32,128,-164},{3,246,97},white);
            b.box("locker-top-shelf",{x,236,-163},{63,4,100},white);
            for(int layer=0;layer<3;++layer)b.box("folded-towels",{x+10,241.f+layer*2,-160},{30,2,25},layer==1?accent:white);
            b.box("locker-shoe-shelf",{x,29,-165},{61,3,91},white);
            b.box("locker-nameplate",{x,248,-113},{61,16,3},accent);b.crest(x,248,-110,12);
            b.tube("hanging-rail",{x-27,204,-159},{x+27,204,-159},1.2f,silver);
            b.tube("hanger",{x-18,191,-157},{x,201,-157},.7f,dark);b.tube("hanger",{x,201,-157},{x+18,191,-157},.7f,dark);
            b.tube("hanger-hook",{x,200,-157},{x,206,-157},.7f,dark);
            Model dressed;if(players[i]){dressed=*players[i];apply_presentation_pose(dressed,false,nullptr,1);}
            if(players[i])for(const auto&original:dressed.parts)if(original.asset.find("/jersey_")!=original.asset.npos) {
                Part shirt=original;shirt.asset="mod/club-room/hanging-shirt/source/"+original.asset;shirt.skinned=false;
                float low=10000,high=-10000;for(const auto&v:shirt.vertices){low=std::min(low,v.position.y);high=std::max(high,v.position.y);}
                for(auto&v:shirt.vertices){v.position.x=x+v.position.x*.92f;v.position.y=194+(v.position.y-high)*.92f;v.position.z=-153+v.position.z*.92f;}
                if(original.texture>=0&&size_t(original.texture)<players[i]->textures.size()){shirt.texture=(int)room.textures.size();room.textures.push_back(players[i]->textures[original.texture]);}else shirt.texture=-1;
                shirt.hair_coeff_texture=-1;room.parts.push_back(std::move(shirt));break;
            }
            b.box("shoe-storage",{x,19,-173},{45,16,43},dark);
            b.box("bench-seat",{x,45,-75},{63,5,50},{.86f,.74f,.57f});
            b.box("bench-leg",{x-24,21,-75},{4,42,35},white);
            b.box("bench-leg",{x+24,21,-75},{4,42,35},white);
            b.box("bench-color-trim",{x,41,-48},{63,3,2},accent);
            b.box("kit-bag",{x+8,67,-92},{27,39,23},dark);
            b.box("kit-bag-panel",{x+8,67,-79},{21,28,2},secondary);b.crest(x+8,67,-77,13);
            b.tube("bag-handle",{x+1,89,-90},{x+15,89,-90},1.5f,dark);
            b.tube("locker-bottle",{x-23,48,-83},{x-23,68,-83},3,white);
            b.tube("locker-bottle-cap",{x-23,68,-83},{x-23,71,-83},2.5f,accent);
            if(players[i])for(const auto&original:players[i]->parts)if(original.asset.find("/shoe/")!=original.asset.npos) {
                Part shoes=original;shoes.asset="mod/club-room/stored-boots/source/"+original.asset;shoes.skinned=false;
                for(auto&v:shoes.vertices){v.position.x=x+v.position.x*.75f;v.position.y=31+v.position.y*.75f;v.position.z=-149+v.position.z*.75f;}
                if(original.texture>=0&&size_t(original.texture)<players[i]->textures.size()){shoes.texture=(int)room.textures.size();room.textures.push_back(players[i]->textures[original.texture]);}else shoes.texture=-1;
                room.parts.push_back(std::move(shoes));break;
            }
        }
        for(float x:{-145.f,145.f}){b.box("center-bench",{x,43,106},{220,6,57},{.86f,.74f,.57f});
            for(float dx:{-92.f,92.f})b.box("center-bench-leg",{x+dx,20,106},{5,40,39},white);}
        b.box("locker-ceiling-emblem-panel",{0,268,-110},{150,45,2},white);b.crest(0,268,-107,42);
    }
    room.diagnostic="club_room="+std::to_string(kind)+" team="+std::to_string(room.team_id)+" seated_coach_pose="+std::to_string(room.presentation_pose_id)+" press_player="+std::to_string(room.press_player_id)+" coach_present="+std::to_string(room.press_coach_present)+" procedural prototype; native crest/kit textures; no save writes";
    /* Batch repeated static surfaces. Thousands of tiny D3D buffers/draws
     * are unnecessary for tiles, furniture and lockers; vertices already
     * contain each object's transform. Preserve each material and UV. */
    std::vector<Part>batch;
    for(auto&part:room.parts){auto it=std::find_if(batch.begin(),batch.end(),[&](const Part&p){
        return p.name==part.name&&p.texture==part.texture&&p.blend==part.blend&&p.color.x==part.color.x&&p.color.y==part.color.y&&p.color.z==part.color.z;
    });
        if(it==batch.end())batch.push_back(std::move(part));
        else {uint32_t offset=(uint32_t)it->vertices.size();it->vertices.insert(it->vertices.end(),part.vertices.begin(),part.vertices.end());
            for(uint32_t index:part.indices)it->indices.push_back(index+offset);}
    }
    room.parts=std::move(batch);
    return std::move(room);
}
Model build_full_squad_photo(const std::vector<std::shared_ptr<const Model>>&players,std::shared_ptr<const Model>coach) {
    auto unavailable=[](const char*reason){Model out;out.player_count=0;out.room=RoomFullSquadPhoto;out.diagnostic=std::string("full squad photo unavailable: ")+reason;return out;};
    if(players.empty()||players.size()>100||!players[0])return unavailable("current roster is empty or outside the supported bound");
    const int team=players[0]->team_id;if(team<=0)return unavailable("invalid current club identity");
    std::vector<int>ids;ids.reserve(players.size());
    for(const auto&p:players) {
        if(!p||p->parts.empty()||p->player_id<=0||p->team_id!=team)return unavailable("one or more current-club player models are missing");
        if(std::find(ids.begin(),ids.end(),p->player_id)!=ids.end())return unavailable("duplicate player identity in current roster");
        ids.push_back(p->player_id);
    }
    if(!coach||coach->parts.empty()||coach->team_id!=team)return unavailable("the SLC manager model for this exact club is unavailable");

    Model out;out.team_id=team;out.room=RoomFullSquadPhoto;out.player_count=players.size()+1;out.specific_head=true;
    out.presentation_pose=true;out.presentation_pose_id=120;out.press_coach_present=true;
    out.club_colors_valid=players[0]->club_colors_valid;std::copy(std::begin(players[0]->club_colors),std::end(players[0]->club_colors),out.club_colors);
    if(players[0]->crest_texture>=0&&size_t(players[0]->crest_texture)<players[0]->textures.size()) {
        out.crest_texture=0;out.textures.push_back(players[0]->textures[players[0]->crest_texture]);
    }
    auto material=[&](const Texture&t) {
        size_t i=0;for(;i<out.textures.size();++i){const auto&old=out.textures[i];
            if(old.width==t.width&&old.height==t.height&&old.format==t.format&&old.bytes==t.bytes)break;}
        if(i==out.textures.size())out.textures.push_back(t);return (int)i;
    };
    auto append_actor=[&](const Model&actor,float x,float z) {
        std::vector<int>materials;materials.reserve(actor.textures.size());for(const auto&t:actor.textures)materials.push_back(material(t));
        for(auto p:actor.parts) {
            p.skinned=false;
            if(p.texture>=0){if(size_t(p.texture)>=materials.size())return false;p.texture=materials[p.texture];}
            if(p.hair_coeff_texture>=0){if(size_t(p.hair_coeff_texture)>=materials.size())return false;p.hair_coeff_texture=materials[p.hair_coeff_texture];}
            for(auto&v:p.vertices){v.position.x+=x;v.position.z+=z;}
            out.parts.push_back(std::move(p));
        }
        out.specific_head=out.specific_head&&actor.specific_head;
        return true;
    };

    /* Keep each line close to a real team-photo row instead of stretching a
     * 40-100 player squad across the whole camera. The coach occupies one
     * additional place in the front row. */
    const size_t row_count=std::max<size_t>(1,(players.size()+8)/9);
    std::vector<size_t>row_sizes(row_count,players.size()/row_count);
    for(size_t i=0;i<players.size()%row_count;++i)++row_sizes[i];
    size_t player_index=0;const float spacing=58.f;
    for(size_t row=0;row<row_count;++row) {
        const bool front_row=row+1==row_count,front=front_row&&row_count>1;
        const size_t slots=row_sizes[row]+(front_row?1:0),coach_slot=front_row?slots/2:slots;
        const float z=-22.f-float(row_count-1-row)*92.f;
        for(size_t slot=0;slot<slots;++slot) {
            const float x=(float(slot)-float(slots-1)*.5f)*spacing;
            if(front&&slot==coach_slot)continue;
            auto posed=std::make_shared<Model>(*players[player_index]);
            if(!apply_presentation_pose(*posed,front,nullptr,120))return unavailable("a current-roster player could not take the dedicated photo pose");
            if(!append_actor(*posed,x,z))return unavailable("a player texture reference is invalid");
            out.formation.push_back({posed->player_id,posed->height_cm,posed->goalkeeper,front,x,z,false,false,0,0,false,false});
            ++player_index;
        }
        if(front_row) {
            auto posed=std::make_shared<Model>(*coach);
            bool coach_posed=apply_coach_pose(*posed,201);
            const float x=(float(coach_slot)-float(slots-1)*.5f)*spacing;
            /* The coach stands a fraction behind the kneeling row, centered
             * like the staff member in an official club portrait. */
            const float coach_z=z-22.f;
            if(!append_actor(*posed,x,coach_z))return unavailable("the exact club coach texture reference is invalid");
            out.formation.push_back({0,posed->height_cm,false,false,x,coach_z,false,false,0,0,false,false});
            if(!coach_posed)out.diagnostic="coach static SLC pose retained; dedicated player-photo pose applied";
        }
    }
    if(player_index!=players.size())return unavailable("not every current-roster player was placed in the photo");
    if(!out.diagnostic.empty())out.diagnostic+="; ";
    out.diagnostic+="official full-roster portrait; private photo pose 120; exact club SLC coach ID="+std::to_string(team)+
        "; players="+std::to_string(players.size())+" coach=1; no other scene or save state changed";
    return out;
}
Model build_trophy_room(const Model&club,const std::vector<std::shared_ptr<const Model>>&trophies) {
    std::vector<std::shared_ptr<const Model>>empty_lockers(11,std::make_shared<Model>(club));
    RoomBuilder b;b.room=build_club_room(empty_lockers,RoomDressing);auto&room=b.room;room.room=RoomTrophies;
    Vec3 white={.97f,.98f,1},silver={.50f,.56f,.61f},accent=room.club_colors[0];
    b.box("trophy-cabinet-back",{0,154,-43},{754,220,5},{.075f,.095f,.115f});
    b.box("trophy-cabinet-left",{-378,154,-12},{4,224,68},white);
    b.box("trophy-cabinet-right",{378,154,-12},{4,224,68},white);
    for(float y:{50.f,118.f,186.f,254.f}) {
        b.box("trophy-shelf",{0,y,-9},{756,3,71},white);
        b.box("trophy-shelf-front",{0,y,28},{756,4,3},accent);
        b.box("trophy-shelf-light",{0,y-3,22},{748,1,2},{1.3f,1.3f,1.15f});
    }
    for(size_t i=0;i<trophies.size()&&i<30;++i){if(!trophies[i]||trophies[i]->parts.empty())continue;
        float low=10000,high=-10000,min_x=10000,max_x=-10000,min_z=10000,max_z=-10000;
        for(const auto&p:trophies[i]->parts)for(const auto&v:p.vertices){low=std::min(low,v.position.y);high=std::max(high,v.position.y);
            min_x=std::min(min_x,v.position.x);max_x=std::max(max_x,v.position.x);min_z=std::min(min_z,v.position.z);max_z=std::max(max_z,v.position.z);}
        if(high-low<.01f)continue;
        float scale=std::min(56.f/(high-low),58.f/std::max(.01f,max_x-min_x));
        size_t row_count=std::min(size_t(10),trophies.size()-(i/10)*10);
        float x=((float)(i%10)-(float)(row_count-1)*.5f)*73,y=52.f+(float)(i/10)*68;
        b.box("trophy-pedestal",{x,y+1,-3},{57,2,45},silver);
        int offset=(int)room.textures.size();room.textures.insert(room.textures.end(),trophies[i]->textures.begin(),trophies[i]->textures.end());
        for(auto p:trophies[i]->parts){if(p.texture>=0)p.texture+=offset;p.hair_coeff_texture=-1;
            for(auto&v:p.vertices){v.position.x=x+(v.position.x-(min_x+max_x)*.5f)*scale;
                v.position.y=y+2+(v.position.y-low)*scale;v.position.z=-3+(v.position.z-(min_z+max_z)*.5f)*scale;}
            room.parts.push_back(std::move(p));}
    }
    room.diagnostic="trophy-room native models; trophies on page="+std::to_string(trophies.size())+"; 30/page; club="+std::to_string(club.team_id);
    return std::move(room);
}
}
