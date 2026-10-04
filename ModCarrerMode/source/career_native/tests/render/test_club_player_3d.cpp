#define NOMINMAX
#include "../../src/render/renderer/fifa_player_renderer.h"
#include <cstdio>
#include <algorithm>
#include <cstring>
#include <cassert>
#include <limits>
#include <string>
#include <DirectXMath.h>
using namespace fifa_player;
static void require(bool value,const char *message){if(!value){fprintf(stderr,"FAIL: %s\n",message);exit(1);}}
/* The offline C3DQA003 roster predates six career-only identity fields. Keep
 * its original 420-byte ABI local to QA and upgrade in memory; never rewrite
 * the user's fixture or guess birth/contract values. */
struct LegacyClubPlayerRow {
    int player_id,team_id,number,position,age,overall;
    int head_type,head_class,hair_type,hair_color,skin_tone,skin_type;
    int facial_hair_type,facial_hair_color,shoe_type,shoe_design;
    int gender,height,weight,body_type;
    int eye_color,eyebrow,sideburns,sleeve_length,jersey_fit,jersey_style;
    int sock_length,short_style,glove_type;
    unsigned int club_colors[3];int club_colors_valid;
    int attributes[CLUB_PLAYER_ATTRIBUTE_COUNT];char name[128];
    int captain,squad_position,secondary_positions[3],secondary_positions_valid;
};
static_assert(sizeof(LegacyClubPlayerRow)==420,"legacy QA roster row ABI");
static ClubPlayerRow upgrade_legacy_row(const LegacyClubPlayerRow&old) {
    ClubPlayerRow row{};
    memcpy(&row,&old,offsetof(ClubPlayerRow,head_type));
    row.birthdate_raw=row.join_team_date_raw=row.career_date=row.retiring=row.weekly_wage=-1;
    row.career_data_valid=0;
    memcpy(reinterpret_cast<unsigned char*>(&row)+offsetof(ClubPlayerRow,head_type),
        reinterpret_cast<const unsigned char*>(&old)+offsetof(LegacyClubPlayerRow,head_type),
        sizeof(old)-offsetof(LegacyClubPlayerRow,head_type));
    return row;
}
static void write32(std::vector<uint8_t>&b,size_t p,uint32_t n){for(int i=0;i<4;++i)b[p+i]=(uint8_t)(n>>(8*i));}
static uint32_t le(const uint8_t*p){return p[0]|uint32_t(p[1])<<8|uint32_t(p[2])<<16|uint32_t(p[3])<<24;}
static void alpha_statistics(const Texture&t,const char*name) {
    size_t zero=0,total=0;unsigned long long sum=0;
    for(size_t block=0;block<t.bytes.size();block+=t.format?16:8) {
        const uint8_t*p=t.bytes.data()+block;
        uint8_t values[8]={p[0],p[1]};uint64_t indices=0;
        if(t.format==2) {
            for(int k=1;k<=6;++k)values[k+1]=(p[0]>p[1]?((7-k)*p[0]+k*p[1])/7:0);
            if(p[0]<=p[1]){for(int k=1;k<=4;++k)values[k+1]=((5-k)*p[0]+k*p[1])/5;values[6]=0;values[7]=255;}
            for(int k=0;k<6;++k)indices|=uint64_t(p[k+2])<<(k*8);
        }
        for(int pixel=0;pixel<16;++pixel) {
            unsigned a=255;
            if(t.format==2)a=values[(indices>>(pixel*3))&7];
            else if(t.format==1)a=((p[pixel/2]>>(4*(pixel%2)))&15)*17;
            else {unsigned c0=p[0]|p[1]<<8,c1=p[2]|p[3]<<8;unsigned i=p[4+pixel/4]>>(2*(pixel%4));if(c0<=c1&&(i&3)==3)a=0;}
            ++total;sum+=a;if(a<12)++zero;
        }
    }
    printf("hair texture %s BC=%u size=%ux%u alphaMean=%.2f nearZero=%.2f%%\n",name,t.format,t.width,t.height,double(sum)/total,100.*zero/total);
}
/* Inspect the ORIGINAL channels in a contact sheet: RGB | R | G | B | A.
 * QA only; these bitmaps never enter the game or replace its textures. */
static void texture_channels(const Texture&t,const char*path) {
    require(t.width&&t.height&&t.format<=2,"diagnostic BC texture");
    const unsigned panel=512,w=panel*5,h=256;
    std::vector<uint8_t>pixels(w*h*4,255);
    for(unsigned y=0;y<h;++y)for(unsigned x=0;x<w;++x) {
        unsigned tx=(x%panel)*t.width/panel,ty=y*t.height/h;
        size_t block=(ty/4*((t.width+3)/4)+tx/4)*(t.format?16:8);
        require(block+(t.format?16:8)<=t.bytes.size(),"diagnostic bounded BC block");
        const uint8_t*p=t.bytes.data()+block,*c=p+(t.format?8:0);
        unsigned c0=c[0]|c[1]<<8,c1=c[2]|c[3]<<8;
        unsigned rgb[4][3]={{((c0>>11)&31)*255/31,((c0>>5)&63)*255/63,(c0&31)*255/31},
            {((c1>>11)&31)*255/31,((c1>>5)&63)*255/63,(c1&31)*255/31},{},{}};
        for(int k=0;k<3;++k) {
            if(c0>c1||t.format){rgb[2][k]=(2*rgb[0][k]+rgb[1][k])/3;rgb[3][k]=(rgb[0][k]+2*rgb[1][k])/3;}
            else rgb[2][k]=(rgb[0][k]+rgb[1][k])/2;
        }
        unsigned pixel=(ty%4)*4+tx%4,ci=(c[4+pixel/4]>>(2*(pixel%4)))&3,a=255;
        if(t.format==2) {
            unsigned av[8]={p[0],p[1]};uint64_t indices=0;
            if(p[0]>p[1])for(unsigned k=1;k<=6;++k)av[k+1]=((7-k)*p[0]+k*p[1])/7;
            else {for(unsigned k=1;k<=4;++k)av[k+1]=((5-k)*p[0]+k*p[1])/5;av[6]=0;av[7]=255;}
            for(int k=0;k<6;++k)indices|=uint64_t(p[k+2])<<(8*k);
            a=av[(indices>>(pixel*3))&7];
        } else if(t.format==1)a=((p[pixel/2]>>(4*(pixel%2)))&15)*17;
        else if(c0<=c1&&ci==3)a=0;
        auto*out=pixels.data()+(y*w+x)*4;unsigned channel=x/panel;
        if(!channel){out[0]=rgb[ci][2];out[1]=rgb[ci][1];out[2]=rgb[ci][0];}
        else out[0]=out[1]=out[2]=uint8_t(channel==4?a:rgb[ci][channel-1]);
    }
    FILE*f=nullptr;require(!fopen_s(&f,path,"wb")&&f,"diagnostic channel output");
    BITMAPFILEHEADER file={0x4d42,54+w*h*4,0,0,54};BITMAPINFOHEADER info={40,(LONG)w,-(LONG)h,1,32,BI_RGB,w*h*4};
    fwrite(&file,1,sizeof(file),f);fwrite(&info,1,sizeof(info),f);fwrite(pixels.data(),1,pixels.size(),f);fclose(f);
}
static void tests(Assets &a) {
    std::vector<uint8_t>b;require(a.read("data/sceneassets/heads/head_0_0.rx3",b),"real generic head decode");
    std::vector<Part>parts;require(read_mesh(b,parts)&&!parts.empty(),"real head parse");
    float min_y=10000,max_y=-10000;for(auto&p:parts)for(auto&v:p.vertices){min_y=std::min(min_y,v.position.y);max_y=std::max(max_y,v.position.y);}
    printf("head bounds y %.3f .. %.3f\n",min_y,max_y);require(min_y>100&&max_y<220,"bind pose coordinates");
    auto broken=b;write32(broken,12,0xffffffff);require(!read_mesh(broken,parts),"reject section-count overflow");
    broken=b;write32(broken,20,0xfffffff0);require(!read_mesh(broken,parts),"reject section range overflow");
    for(size_t length=0;length<b.size();length+=311){broken.assign(b.begin(),b.begin()+length);read_mesh(broken,parts);}
    uint32_t seed=123;for(int i=0;i<2000;++i){seed=1664525*seed+1013904223;broken=b;
        size_t offset=seed%std::min(size_t(1024),b.size());broken[offset]^=uint8_t(seed>>24);read_mesh(broken,parts);}
    require(a.read("data/sceneassets/body/legs_0_0_0.rx3",b),"chunkzip real legs decode");
    require(read_mesh(b,parts),"chunkzip legs parse");
    std::vector<uint8_t>ref={0x10,0xfb,0,0,5,0xe0,'a','b','c','d',0xfd,'e'},decoded;
    require(decode_container(ref,decoded)&&std::string(decoded.begin(),decoded.end())=="abcde","RefPack literal fixture");
    ref={0x10,0xfb,0,0,8,0xe0,'a','b','c','d',0x04,0x03,0xfc};
    require(decode_container(ref,decoded)&&std::string(decoded.begin(),decoded.end())=="abcdabcd","RefPack overlapping backreference fixture");
    ref={0x10,0xfb,0,0,3,0,0,0xfc};require(!decode_container(ref,decoded),"reject invalid backreference");
    ref.assign(40,0);memcpy(ref.data(),"chunkzip",8);require(!decode_container(ref,decoded),"reject invalid chunkzip");
    Texture crest,other;
    require(a.crest(112893,crest)&&a.crest(1043,other)&&crest.bytes!=other.bytes,"crest resolved by club ID, not one shared logo");
    require(!a.crest(-1,other)&&!a.crest(9999999,other),"missing/invalid club hides crest instead of using another club");
    Texture face_a,face_b;
    require(a.portrait(225645,face_a)&&a.portrait(227275,face_b)&&face_a.bytes!=face_b.bytes,"real 2D portraits resolve independently by player ID");
    require(a.portrait(1001,face_b)&&face_b.width>0,"archive-only chunkzip 2D portrait decompresses before DDS parsing");
    require(!a.portrait(-1,face_b)&&!a.portrait(9999999,face_b),"invalid/missing portraits never reuse another player's face");
    b.assign(144,0);memcpy(b.data(),"DDS ",4);write32(b,4,124);write32(b,76,32);
    write32(b,12,4);write32(b,16,4);write32(b,80,4);write32(b,84,0x35545844);
    require(read_crest_dds(b,other)&&other.width==4&&other.format==2,"valid first-mip DXT5 crest");
    auto previous=other;broken=b;broken.resize(143);require(!read_crest_dds(broken,other)&&other.bytes==previous.bytes,"truncated crest is rejected atomically");
    broken=b;write32(broken,16,0xffffffff);require(!read_crest_dds(broken,other),"oversized crest rejected before allocation");
    broken=b;write32(broken,84,0x30315844);require(!read_crest_dds(broken,other),"unsupported DDS never misread as DXT");
    Texture alpha;alpha.format=2;alpha.width=alpha.height=4;alpha.bytes.assign(16,0);alpha.bytes[0]=3;
    require(fabs(hair_alpha_scale(alpha)-85)<.001f,"low-range hair mask is normalized without changing its bytes");
    alpha.bytes[0]=255;require(hair_alpha_scale(alpha)==1,"full-range alpha is not boosted");
    alpha.bytes[0]=0;require(hair_alpha_scale(alpha)==1,"fully transparent mask is not invented");
    alpha.bytes[0]=3;alpha.bytes[1]=255;require(fabs(hair_alpha_scale(alpha)-85)<.001f,"unused opaque palette endpoint is not mistaken for used coverage");
    alpha.bytes.resize(15);require(hair_alpha_scale(alpha)==1,"truncated BC alpha does not read out of range");
}
static void image(ID3D11Device *d,ID3D11DeviceContext *context,ID3D11ShaderResourceView *srv,const char*path) {
    ID3D11Resource *resource=nullptr;srv->GetResource(&resource);
    ID3D11Texture2D*t=nullptr;require(SUCCEEDED(resource->QueryInterface(__uuidof(ID3D11Texture2D),(void**)&t)),"rendered texture");resource->Release();
    D3D11_TEXTURE2D_DESC desc;t->GetDesc(&desc);desc.Usage=D3D11_USAGE_STAGING;desc.BindFlags=0;desc.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
    ID3D11Texture2D*staging=nullptr;require(SUCCEEDED(d->CreateTexture2D(&desc,nullptr,&staging)),"staging");context->CopyResource(staging,t);t->Release();
    D3D11_MAPPED_SUBRESOURCE m;require(SUCCEEDED(context->Map(staging,0,D3D11_MAP_READ,0,&m)),"readback");
    FILE*f=nullptr;require(fopen_s(&f,path,"wb")==0&&f,"screenshot output");
    BITMAPFILEHEADER file={0x4d42,UINT(54+desc.Width*desc.Height*4),0,0,54};
    BITMAPINFOHEADER info={40,(LONG)desc.Width,-(LONG)desc.Height,1,32,BI_RGB,desc.Width*desc.Height*4};
    fwrite(&file,1,sizeof(file),f);fwrite(&info,1,sizeof(info),f);size_t nonbackground=0;
    std::vector<uint8_t>row(desc.Width*4);for(UINT y=0;y<desc.Height;++y){auto*src=(uint8_t*)m.pData+y*m.RowPitch;
        for(UINT x=0;x<desc.Width;++x){row[x*4]=src[x*4+2];row[x*4+1]=src[x*4+1];row[x*4+2]=src[x*4];row[x*4+3]=255;
            if(abs(int(src[x*4])-27)>3||abs(int(src[x*4+1])-48)>3||abs(int(src[x*4+2])-57)>3)++nonbackground;}
        fwrite(row.data(),1,row.size(),f);}
    fclose(f);context->Unmap(staging,0);staging->Release();
    printf("rendered non-background pixels=%zu\n",nonbackground);require(nonbackground>10000,"3D visible");
}
static bool unchanged(const Model&a,const Model&b) {
    if(a.parts.size()!=b.parts.size()||a.presentation_pose!=b.presentation_pose)return false;
    for(size_t i=0;i<a.parts.size();++i)if(a.parts[i].vertices.size()!=b.parts[i].vertices.size()||
        memcmp(a.parts[i].vertices.data(),b.parts[i].vertices.data(),a.parts[i].vertices.size()*sizeof(Vertex)))return false;
    return true;
}
static float head_top(const Model&m) {
    float top=0;for(const auto&p:m.parts)if(p.asset.find("/heads/")!=p.asset.npos&&p.name!="eyes")
        for(const auto&v:p.vertices)top=std::max(top,v.position.y);return top;
}
/* QA-only fingerprints make a scoped pose change comparable to its baseline.
 * Hash the deformed positions/normals, never padding or GPU resources. */
static uint64_t pose_geometry_fingerprint(const Model&m) {
    uint64_t hash=14695981039346656037ull;
    for(const auto&p:m.parts)for(const auto&v:p.vertices)for(float n:{v.position.x,v.position.y,v.position.z,v.normal.x,v.normal.y,v.normal.z}) {
        uint32_t bits;memcpy(&bits,&n,sizeof(bits));
        for(unsigned shift=0;shift<32;shift+=8){hash^=(bits>>shift)&255;hash*=1099511628211ull;}
    }
    return hash;
}
static void pose_tests(const Model&base,const Model&keeper) {
    require(base.skeleton&&base.skeleton->names.size()==400,"native player skeleton attached");
    for(unsigned id:{1u,2u,3u,4u,104u})for(bool front:{false,true}) {
        if(front&&id==104)continue;
        auto sample=base;require(apply_presentation_pose(sample,front,nullptr,id),"scoped pose fingerprint");
        printf("POSE_FINGERPRINT id=%u front=%d geometry=%016llx\n",id,front,(unsigned long long)pose_geometry_fingerprint(sample));
        if(id==4&&!front)for(bool left:{true,false}) {
            const auto&s=left?sample.left_shoulder:sample.right_shoulder;
            const auto&e=left?sample.left_elbow:sample.right_elbow;
            const auto&w=left?sample.left_hand:sample.right_hand;
            const auto&f=left?sample.left_fingers:sample.right_fingers;
            printf("POSE4_ARM left=%d shoulder=%.2f,%.2f,%.2f elbow=%.2f,%.2f,%.2f hand=%.2f,%.2f,%.2f fingers=%.2f,%.2f,%.2f\n",left,s.x,s.y,s.z,e.x,e.y,e.z,w.x,w.y,w.z,f.x,f.y,f.z);
        }
    }
    Model invalid=base;invalid.skeleton.reset();Model before=invalid;
    require(!apply_presentation_pose(invalid,true)&&unchanged(invalid,before),"unknown rig cannot publish a partial pose");
    invalid=base;auto cycle=std::make_shared<Skeleton>(*invalid.skeleton);cycle->parents[1]=1;invalid.skeleton=cycle;before=invalid;
    require(!apply_presentation_pose(invalid,true)&&unchanged(invalid,before),"cyclic hierarchy rejected before walking descendants");
    invalid=base;invalid.parts.back().vertices.back().joints[7]=400;invalid.parts.back().vertices.back().weights[7]=1;before=invalid;
    require(!apply_presentation_pose(invalid,true)&&unchanged(invalid,before),"eighth out-of-range influence rejected atomically");
    invalid=base;memset(invalid.parts.back().vertices.back().weights,0,8);before=invalid;
    require(!apply_presentation_pose(invalid,true)&&unchanged(invalid,before),"zero weight sum rejected atomically");
    invalid=base;invalid.parts.clear();require(!apply_presentation_pose(invalid,true),"empty geometry cannot claim a pose");
    Model standing=base,crouching=base;
    require(apply_presentation_pose(standing,false)&&apply_presentation_pose(crouching,true),"standing and hands-on-thighs poses applied");
    auto elbow_flex=[](Vec3 s,Vec3 e,Vec3 w) {
        Vec3 a={s.x-e.x,s.y-e.y,s.z-e.z},b={w.x-e.x,w.y-e.y,w.z-e.z};
        float dot=(a.x*b.x+a.y*b.y+a.z*b.z)/sqrtf((a.x*a.x+a.y*a.y+a.z*a.z)*(b.x*b.x+b.y*b.y+b.z*b.z));
        return 180.f-acosf(std::max(-1.f,std::min(1.f,dot)))*180.f/3.14159265f;
    };
    require(elbow_flex(crouching.left_shoulder,crouching.left_elbow,crouching.left_hand)>=27.99f&&
        elbow_flex(crouching.right_shoulder,crouching.right_elbow,crouching.right_hand)>=27.99f,"knee supports preserve a gentle elbow bend instead of locked straight arms");
    require(crouching.left_support_error_cm<3&&crouching.right_support_error_cm<3,"knee supports no longer target a point fifteen centimetres beyond arm reach");
    printf("support error %.2f %.2f elbow flex %.2f %.2f\n",crouching.left_support_error_cm,crouching.right_support_error_cm,
        elbow_flex(crouching.left_shoulder,crouching.left_elbow,crouching.left_hand),elbow_flex(crouching.right_shoulder,crouching.right_elbow,crouching.right_hand));
    for(size_t part=0;part<standing.parts.size();++part) {
        const auto&p=standing.parts[part];
        if(p.asset.find("/heads/")==p.asset.npos&&p.asset.find("/legs_")==p.asset.npos&&
            p.asset.find("/shoe/")==p.asset.npos&&p.asset.find("/shorts_")==p.asset.npos)continue;
        for(size_t i=0;i<p.vertices.size();++i) {
            bool follows_standing_arm=false;
            for(int influence=0;influence<8;++influence)if(p.vertices[i].weights[influence]) {
                unsigned bone=p.vertices[i].joints[influence];
                for(;;) {
                    if(base.skeleton->names[bone]=="LeftArm"||base.skeleton->names[bone]=="RightArm"){follows_standing_arm=true;break;}
                    if(base.skeleton->parents[bone]==0xffff)break;bone=base.skeleton->parents[bone];
                }
            }
            if(follows_standing_arm)continue; /* Some custom head/neck seams share arm influences. */
            Vec3 a=base.parts[part].vertices[i].position,b=p.vertices[i].position;
            require(fabs(a.x-b.x)+fabs(a.z-b.z)+fabs(a.y-b.y-standing.pose_floor_cm)<.005f,
                "front-row torso/knee refinements do not deform standing non-arm head/body/leg/boot influences");
        }
    }
    require(presentation_pose_count(PoseGroup)==7&&presentation_pose_count(PoseIndividual)==14&&presentation_pose_count(PoseStandingCoach)==8&&presentation_pose_count(PosePressConferenceCoach)==2&&presentation_pose_count(PoseCoachAny)==10,"seven collective, fourteen individual, eight standing coach and two seated press-conference recipes");
    const auto*full_squad_pose=presentation_pose_find(120);
    require(full_squad_pose&&(full_squad_pose->modes&PoseFullSquad)&&presentation_pose_count(PoseFullSquad)==1,
        "exclusive full-squad photo pose exists for its dedicated scene");
    require(presentation_pose_count(PoseGroup)==7&&presentation_pose_count(PoseIndividual)==14,
        "exclusive full-squad pose stays out of existing group and player pose carousels");
    for(size_t i=0;i<presentation_pose_count(PoseCoachAny);++i){const auto*p=presentation_pose_at(i,PoseCoachAny);
        require(p&&bool(p->modes&PoseStandingCoach)!=bool(p->modes&PosePressConferenceCoach),"every coach pose belongs to exactly one stance/context bucket");}
    invalid=base;before=invalid;require(!apply_presentation_pose(invalid,false,nullptr,999999)&&unchanged(invalid,before),"unknown pose cannot damage a model");
    for(const char*missing:{"LeftShoulder","RM_LeftArmTwist1","RM_RightArm_Sleeve2","RM_RightElbow"}) {
        invalid=base;auto rig=std::make_shared<Skeleton>(*base.skeleton);
        for(auto&name:rig->names)if(name==missing)name="missing-helper";
        invalid.skeleton=rig;before=invalid;
        require(!apply_presentation_pose(invalid,false,nullptr,104)&&unchanged(invalid,before),"incomplete anatomical rig fails without publishing a partial individual pose");
    }
    for(size_t i=0;i<presentation_pose_count(PoseIndividual);++i) {
        Model individual=base;const auto*info=presentation_pose_at(i,PoseIndividual);
        require(apply_presentation_pose(individual,false,nullptr,info->id)&&individual.presentation_pose_id==info->id,"each individual pose deforms its native rig");
        for(const auto&p:individual.parts)for(const auto&v:p.vertices)require(std::isfinite(v.position.x)&&std::isfinite(v.position.y)&&std::isfinite(v.position.z),"individual poses keep finite geometry");
        require(assemble_team({std::make_shared<Model>(base)},info->id).player_count==0,"individual pose cannot leak into the eleven-player group");
        for(const Model*source:{&base,&keeper})for(int height:{150,205}) {
            auto sized=*source;float scale=height/head_top(sized);sized.bind_scale*=scale;
            for(auto&p:sized.parts)for(auto&v:p.vertices){v.position.x*=scale;v.position.y*=scale;v.position.z*=scale;}
            require(apply_presentation_pose(sized,false,nullptr,info->id),"every portrait supports short/tall outfield players and goalkeeper gloves");
            for(bool left:{true,false}) {
                const auto&s=left?sized.left_shoulder:sized.right_shoulder;
                const auto&e=left?sized.left_elbow:sized.right_elbow;
                const auto&w=left?sized.left_hand:sized.right_hand;
                auto vector=[](Vec3 a,Vec3 b){return DirectX::XMVectorSet(a.x-b.x,a.y-b.y,a.z-b.z,0);};
                auto joint=[&](const char*name) {
                    size_t index=0;while(index<sized.skeleton->names.size()&&sized.skeleton->names[index]!=name)++index;
                    require(index<sized.skeleton->names.size(),"native audit joint exists");
                    DirectX::XMFLOAT4X4 inv;memcpy(&inv,sized.skeleton->inverse_bind[index].data(),64);
                    DirectX::XMFLOAT4X4 bind;DirectX::XMStoreFloat4x4(&bind,DirectX::XMMatrixInverse(nullptr,DirectX::XMLoadFloat4x4(&inv)));
                    return Vec3{bind._41*sized.bind_scale,bind._42*sized.bind_scale,bind._43*sized.bind_scale};
                };
                const std::string side=left?"Left":"Right";
                auto native_s=joint((side+"Arm").c_str()),native_e=joint((side+"ForeArm").c_str()),native_w=joint((side+"Hand").c_str());
                float upper=DirectX::XMVectorGetX(DirectX::XMVector3Length(vector(e,s)));
                float lower=DirectX::XMVectorGetX(DirectX::XMVector3Length(vector(w,e)));
                require(fabsf(upper-DirectX::XMVectorGetX(DirectX::XMVector3Length(vector(native_e,native_s))))<.005f&&
                    fabsf(lower-DirectX::XMVectorGetX(DirectX::XMVector3Length(vector(native_w,native_e))))<.005f,"individual shoulder/elbow refinement never stretches either native arm bone");
                float cosine=DirectX::XMVectorGetX(DirectX::XMVector3Dot(DirectX::XMVector3Normalize(vector(e,s)),DirectX::XMVector3Normalize(vector(w,e))));
                float bend=DirectX::XMConvertToDegrees(acosf(std::clamp(cosine,-1.f,1.f)));
                require(std::isfinite(bend)&&bend>=8.f&&bend<=150.f,"individual elbows stay gently flexed and never over-fold");
                if(info->id==101||(!left&&(info->id==103||info->id==105||info->id==108||info->id==109||info->id==112))) {
                    auto side_axis=DirectX::XMVector3Normalize(vector(sized.left_shoulder,sized.right_shoulder));
                    auto forward=DirectX::XMVector3Normalize(DirectX::XMVector3Cross(side_axis,DirectX::XMVectorSet(0,1,0,0)));
                    require(DirectX::XMVectorGetX(DirectX::XMVector3Dot(vector(w,e),forward))>1.f*sized.bind_scale,
                        "resting forearm flexes forward, never backward / inward, regardless of body yaw");
                }
            }
            require(sized.parts.size()==source->parts.size()&&sized.textures.size()==source->textures.size(),"portraits preserve all native parts and materials");
            float feet=10000;for(const auto&p:sized.parts)for(const auto&v:p.vertices) {
                require(std::isfinite(v.position.x)&&std::isfinite(v.position.y)&&std::isfinite(v.position.z)&&fabs(v.position.x)<250&&fabs(v.position.y)<300&&fabs(v.position.z)<250,"portrait posture remains bounded at different heights");
                if(p.asset.find("/shoe/")!=p.asset.npos)feet=std::min(feet,v.position.y);
                if(p.native_normals){float length=sqrtf(v.normal.x*v.normal.x+v.normal.y*v.normal.y+v.normal.z*v.normal.z);require(fabs(length-1)<.001f,"portrait twist/finger corrections keep normalized native normals");}
            }
            require(fabs(feet)<.001f,"every portrait keeps its boot soles on the ground");
        }
    }
    require(head_top(crouching)<head_top(standing)-10&&head_top(crouching)>head_top(standing)*.6f,"front players lower without an excessive squat");
    for(const auto*m:{&standing,&crouching}) {
        float feet=10000;for(const auto&p:m->parts)for(const auto&v:p.vertices) {
            require(std::isfinite(v.position.x)&&std::isfinite(v.position.y)&&std::isfinite(v.position.z)&&fabs(v.position.x)<200&&fabs(v.position.y)<250&&fabs(v.position.z)<200,"finite bounded skeletal deformation");
            if(p.asset.find("/shoe/")!=p.asset.npos)feet=std::min(feet,v.position.y);
            if(p.native_normals){float length=sqrtf(v.normal.x*v.normal.x+v.normal.y*v.normal.y+v.normal.z*v.normal.z);
                require(std::isfinite(length)&&fabs(length-1)<.001f,"native normals remain normalized through skeletal pose");}
        }
        require(fabs(feet)<.001f,"posed feet remain on the ground");
        require(m->parts.size()==base.parts.size()&&m->textures.size()==base.textures.size(),"posing retains hair, eyes, tattoos, kit and materials");
    }
    size_t hand=0;while(hand<base.skeleton->names.size()&&base.skeleton->names[hand]!="LeftHand")++hand;
    require(hand<base.skeleton->names.size(),"named native hand");
    Model first,eighth;first.skeleton=base.skeleton;first.bind_scale=1;Part p;p.skinned=true;p.asset="data/sceneassets/shoe/test.rx3";
    Vertex v={};v.position={58.6588f,120.809f,15.3024f};v.joints[0]=(uint16_t)hand;v.weights[0]=255;p.vertices.push_back(v);
    v={};v.joints[0]=2;v.weights[0]=255;p.vertices.push_back(v);first.parts.push_back(p);eighth=first;
    auto&last=eighth.parts[0].vertices[0];last.weights[0]=0;last.joints[7]=(uint16_t)hand;last.weights[7]=255;
    require(apply_presentation_pose(first,false)&&apply_presentation_pose(eighth,false),"first/eighth native influence fixtures");
    auto x=first.parts[0].vertices[0].position,y=eighth.parts[0].vertices[0].position;
    require(fabs(x.x-y.x)+fabs(x.y-y.y)+fabs(x.z-y.z)<.001f,"all eight native weights are used");
    Model gk=keeper;require(apply_presentation_pose(gk,false),"goalkeeper standing pose");
    bool glove=false;for(const auto&part:gk.parts)if(part.asset.find("/gkglove/")!=part.asset.npos) {
        glove=true;for(const auto&vertex:part.vertices)require(vertex.position.y>45&&vertex.position.y<150,"gloves follow lowered hand bones");
    }
    require(glove,"posed goalkeeper retains gloves");
    std::vector<std::shared_ptr<const Model>>players;
    const int heights[11]={168,182,185,174,191,180,171,186,172,178,193};
    for(int i=0;i<11;++i){auto m=std::make_shared<Model>(i==10?keeper:base);m->player_id=100+i;m->height_cm=heights[i];
        float scale=heights[i]/head_top(*m);m->bind_scale*=scale;
        for(auto&p:m->parts)for(auto&v:p.vertices){v.position.x*=scale;v.position.y*=scale;v.position.z*=scale;}
        players.push_back(m);}
    auto team=assemble_team(players);require(team.player_count==11&&team.formation.size()==11&&team.presentation_pose,"eleven native posed models assembled");
    auto complete=assemble_starting_eleven(players);
    require(complete.player_count==11&&complete.formation.size()==11&&complete.presentation_pose,"starting-XI contract accepts eleven complete unique native actors");
    auto rejected=[](const Model&m){return m.parts.empty()&&m.formation.empty()&&m.player_count==0&&!m.presentation_pose&&m.diagnostic.find("starting XI photo unavailable")!=m.diagnostic.npos;};
    auto incomplete=players;incomplete.pop_back();require(rejected(assemble_starting_eleven(incomplete)),"ten models cannot masquerade as the current eleven");
    incomplete=players;incomplete.push_back(players[0]);require(rejected(assemble_starting_eleven(incomplete)),"twelve models cannot be silently truncated");
    incomplete=players;incomplete[3].reset();require(rejected(assemble_starting_eleven(incomplete)),"missing actor does not reduce photo to ten");
    incomplete=players;incomplete[3]=std::make_shared<Model>();require(rejected(assemble_starting_eleven(incomplete)),"empty decoded geometry suppresses partial photo");
    incomplete=players;incomplete[3]=players[2];require(rejected(assemble_starting_eleven(incomplete)),"duplicate player cannot satisfy count of eleven");
    incomplete=players;auto different_club=std::make_shared<Model>(*players[3]);different_club->team_id+=1;incomplete[3]=different_club;
    require(rejected(assemble_starting_eleven(incomplete)),"another club's model is not a replacement for a missing starter");
    incomplete=players;auto no_rig=std::make_shared<Model>(*players[3]);no_rig->skeleton.reset();incomplete[3]=no_rig;
    require(rejected(assemble_starting_eleven(incomplete)),"one unposeable actor cannot appear in bind pose among ten posed players");
    require(rejected(assemble_starting_eleven(players,101)),"individual recipe cannot pretend to be a completed team photo");
    puts("PASS: complete starting XI contract; no missing, duplicate, mixed-club, truncated or unposed actors");
    for(size_t i=0;i<presentation_pose_count(PoseGroup);++i) {
        const auto*info=presentation_pose_at(i,PoseGroup);auto variant=assemble_team(players,info->id);
        require(variant.player_count==11&&variant.formation.size()==11&&variant.presentation_pose_id==info->id,"every collective recipe retains all eleven actual models");
        require(variant.formation.front().goalkeeper&&!variant.formation.front().crouching,"keeper remains standing on the edge in every collective pose");
        size_t back=0;for(const auto&r:variant.formation)if(!r.crouching)++back;
        require(back==info->back_count,"recipe controls the row distribution independently of the roster");
        for(const auto&p:variant.parts)for(const auto&v:p.vertices)
            require(std::isfinite(v.position.x)&&std::isfinite(v.position.y)&&std::isfinite(v.position.z),"all collective geometry remains finite");
    }
    Model keeper_control=*players[10];require(apply_presentation_pose(keeper_control,false),"standing keeper control");
    require(team.formation.front().player_id==players[10]->player_id&&!team.formation.front().crouching,"keeper remains at the standing edge");
    for(size_t part=0;part<keeper_control.parts.size();++part)for(size_t v=0;v<keeper_control.parts[part].vertices.size();++v) {
        Vec3 a=keeper_control.parts[part].vertices[v].position,b=team.parts[part].vertices[v].position;
        const auto&place=team.formation.front();
        require(fabs(a.x+place.x-b.x)+fabs(a.y-b.y)+fabs(a.z+place.z-b.z)<.005f,
            "collective front-row refinements leave the keeper's complete standing geometry and gloves unchanged");
    }
    for(int height:{150,170,205}) {
        auto sized=base;float scale=height/head_top(sized);sized.bind_scale*=scale;
        for(auto&p:sized.parts)for(auto&v:p.vertices){v.position.x*=scale;v.position.y*=scale;v.position.z*=scale;}
        require(apply_presentation_pose(sized,true)&&sized.left_support_error_cm/sized.bind_scale<3&&sized.right_support_error_cm/sized.bind_scale<3,
            "knee support and reach scale with short, medium and tall native models");
        require(elbow_flex(sized.left_shoulder,sized.left_elbow,sized.left_hand)>=27.99f&&
            elbow_flex(sized.right_shoulder,sized.right_elbow,sized.right_hand)>=27.99f,"height changes do not lock the elbow straight");
    }
    for(const Model*source:{&base,&keeper})for(int height:{150,170,205}) {
        auto crossed=*source;float scale=height/head_top(crossed);crossed.bind_scale*=scale;
        for(auto&p:crossed.parts)for(auto&v:p.vertices){v.position.x*=scale;v.position.y*=scale;v.position.z*=scale;}
        require(apply_presentation_pose(crossed,false,nullptr,4),"collective crossed arms support different heights and gloves");
        for(bool left:{true,false}) {
            const auto&s=left?crossed.left_shoulder:crossed.right_shoulder;
            const auto&e=left?crossed.left_elbow:crossed.right_elbow;
            const auto&w=left?crossed.left_hand:crossed.right_hand;
            const auto&f=left?crossed.left_fingers:crossed.right_fingers;
            float fx=f.x-w.x,fy=f.y-w.y,fz=f.z-w.z;
            require(s.y-e.y>15*crossed.bind_scale&&fabs(e.x)<=fabs(s.x)+6*crossed.bind_scale,
                "pose four elbows remain down and close to the body, not winged out");
            require((left?w.x<0:w.x>0)&&w.y<s.y-15*crossed.bind_scale,"crossed wrists stop on the opposite side below the shoulders");
            require(fabs(fy)<sqrtf(fx*fx+fz*fz)*.7f,"crossed fingers no longer stand upright beside the biceps");
            float ax=w.x-e.x,ay=w.y-e.y,az=w.z-e.z;
            float dot=(ax*fx+ay*fy+az*fz)/sqrtf((ax*ax+ay*ay+az*az)*(fx*fx+fy*fy+fz*fz));
            require(dot>.75f,"crossed wrist follows the forearm with a gentle bend instead of a right-angle kink");
        }
    }
    int shortest_back=1000,tallest_front=0,linked=0,unlinked_front=0,back_contacts=0;for(size_t i=0;i<team.formation.size();++i) {
        const auto&r=team.formation[i];require(r.crouching==(i>=6),"six standing behind, five crouching in front");
        if(r.goalkeeper)require(!r.crouching&&(i==0||i==5),"keeper on a back-row edge");
        else if(r.crouching)tallest_front=std::max(tallest_front,r.height_cm);else shortest_back=std::min(shortest_back,r.height_cm);
        if(r.linked_left){++linked;require(r.left_error<.05f,"left hand reaches the different-height neighbour's actual shoulder");}
        if(r.linked_right){++linked;require(r.right_error<.05f,"right hand reaches the different-height neighbour's actual shoulder");}
        if(r.crouching&&!r.linked_left&&!r.linked_right)++unlinked_front;
        if(r.back_left)++back_contacts;if(r.back_right)++back_contacts;
    }
    require(shortest_back>=tallest_front,"height-based dynamic ordering, not a fixed club/player list");
    require(linked>=4&&unlinked_front>=2,"natural mixed poses, not all eleven with hands on thighs");
    require(back_contacts==linked&&back_contacts>0,"all neighbour supports are on the back, none on shoulders/neck");
    printf("photo neighbour contacts=%d (all on back); front thigh stances=%d\n",linked,unlinked_front);
    auto second=std::make_shared<Model>(keeper);second->height_cm=170;second->player_id=200;players[0]=second;team=assemble_team(players);
    require(team.formation[0].goalkeeper&&team.formation[5].goalkeeper,"two selected keepers occupy both back-row ends");
    auto tiny=std::make_shared<Model>(*players[2]);tiny->height_cm=130;float scale=130/head_top(*tiny);tiny->bind_scale*=scale;
    for(auto&p:tiny->parts)for(auto&v:p.vertices){v.position.x*=scale;v.position.y*=scale;v.position.z*=scale;}
    auto huge=std::make_shared<Model>(*players[3]);huge->height_cm=230;scale=230/head_top(*huge);huge->bind_scale*=scale;
    for(auto&p:huge->parts)for(auto&v:p.vertices){v.position.x*=scale;v.position.y*=scale;v.position.z*=scale;}
    auto extreme=assemble_team({tiny,huge,tiny,huge,tiny,huge});require(extreme.presentation_pose,"large height differences do not break the formation");
    for(const auto&r:extreme.formation)require((!r.linked_left||r.left_error<=3)&&(!r.linked_right||r.right_error<=3),"unreachable shoulders fall back without stretching arms");
    require(assemble_team({}).player_count==0,"empty formation safe");
    puts("PASS: native skinning, atomic rejection, hands-on-thighs pose, foot grounding and dynamic formation");
}
static void uniform_tests(Assets&a,const ClubPlayerRow&row) {
    const std::string collar=std::to_string(a.kit_collar(row.team_id,0));
    float hem[2]={};
    for(int tuck=0;tuck<2;++tuck) {
        auto variant=row;variant.jersey_style=tuck;auto m=a.load(variant);
        std::string path="data/sceneassets/body/jersey_0_"+collar+"_0_0_"+std::to_string(tuck)+"_0_0.rx3";
        bool found=false;hem[tuck]=10000;for(const auto&p:m.parts)if(p.asset==path){found=true;for(const auto&v:p.vertices)hem[tuck]=std::min(hem[tuck],v.position.y);}
        require(found,"tucked/untucked shirt follows career field and real asset");
    }
    printf("shirt lower edge: style 0 %.2f, style 1 %.2f\n",hem[0],hem[1]);
    for(int sock=0;sock<3;++sock) {
        auto variant=row;variant.sock_length=sock;auto m=a.load(variant);
        bool found=false;std::string path="data/sceneassets/body/sock_0_"+std::to_string(sock)+"_0.rx3";
        for(const auto&p:m.parts)if(p.asset==path)found=true;require(found,"all three sock heights use distinct native assets");
    }
    for(int code=0;code<5;++code) {
        auto variant=row;variant.sleeve_length=code;auto m=a.load(variant);int sleeve=code==1||code==2?1:0;
        bool shirt=false,arms=false,underarms=false,underneck=false;
        for(const auto&p:m.parts) {
            if(p.asset=="data/sceneassets/body/jersey_0_"+collar+"_"+std::to_string(sleeve)+"_0_0_0_0.rx3")shirt=true;
            if(p.asset=="data/sceneassets/body/arms_0_"+std::to_string(code?1:0)+"_0.rx3")arms=true;
            if(p.asset.find("/underarms_")!=p.asset.npos)underarms=true;if(p.asset.find("/underneck_")!=p.asset.npos)underneck=true;
        }
        require(shirt&&arms,"sleeve code maps to mesh length and corresponding skin geometry");
        require(underarms==(code==3||code==4)&&underneck==(code==2||code==4),"thermal variants follow native player recipe");
    }
    auto variant=row;variant.jersey_fit=1;auto m=a.load(variant);bool tight=false;
    for(const auto&p:m.parts)if(p.asset=="data/sceneassets/body/jersey_0_"+collar+"_0_0_0_1_0.rx3")tight=true;
    require(tight,"tight shirt is not replaced with default loose shirt");
    for(int flag:{0,1,-1}) {
        variant=row;variant.captain=flag;m=a.load(variant);
        const std::string path="data/sceneassets/body/jersey_0_"+collar+"_0_"+std::to_string(flag==1?1:0)+"_0_0_0.rx3";
        bool found=false;for(const auto&p:m.parts)if(p.asset==path&&p.texture>=0)found=true;
        require(found,"armband follows only a validated captain flag and uses native jersey atlas");
        require(apply_presentation_pose(m,true),"captain sleeve follows the same native skeletal pose");
    }
    puts("PASS: native captain/non-captain/unknown jersey variants and posing");
    variant=row;variant.short_style=1;m=a.load(variant);bool pants=false,socks=false;
    for(const auto&p:m.parts){if(p.asset.find("/shorts_0_1_")!=p.asset.npos)pants=true;if(p.asset.find("/sock_")!=p.asset.npos)socks=true;}
    require(pants&&!socks,"long pants retain their native model without an exposed sock overlay");
    puts("PASS: career shirt style, fit, sock heights and sleeve variants");
    std::vector<uint8_t>last_shoe;
    for(int type:{1,10,15}) {
        variant=row;variant.shoe_type=type;m=a.load(variant);bool found=false;
        for(const auto&p:m.parts)if(p.asset=="data/sceneassets/shoe/shoe_"+std::to_string(type)+".rx3"&&p.texture>=0) {
            found=true;const auto&bytes=m.textures[p.texture].bytes;
            require(bytes!=last_shoe,"individual shoe types do not share the same default diffuse");last_shoe=bytes;
        }
        require(found,"shoe geometry and texture follow the player's native shoe type");
    }
    puts("PASS: distinct per-player shoe meshes and diffuse textures");
}
#ifndef CLUB_PLAYER_SCREEN_QA
/* Read-only, multi-angle native mesh audit. No game process or save access. */
static int individual_pose_audit(Assets&a) {
    ClubPlayerRow row={};row.player_id=158023;row.team_id=112893;row.position=24;
    row.skin_tone=3;row.shoe_type=15;row.height=170;row.club_colors_valid=1;
    row.club_colors[0]=0xf7b5cd;row.club_colors[1]=0x18181b;row.club_colors[2]=0xeeeeee;
    auto base=a.load(row);require(!base.parts.empty(),"audit real short-sleeve player");
    for(unsigned id=1;id<=7;++id)for(bool front:{false,true}) {
        auto sample=base;require(apply_presentation_pose(sample,front,nullptr,id),"group baseline audit");
        printf("GROUP_FINGERPRINT id=%u front=%d geometry=%016llx\n",id,front,(unsigned long long)pose_geometry_fingerprint(sample));
    }
    std::vector<ClubPlayerRow>rows={row};
    row.player_id=227275;row.team_id=1043;row.position=0;row.height=193;row.head_type=2506;
    row.hair_type=123;row.hair_color=1;row.skin_tone=5;row.glove_type=18;row.shoe_type=28;
    row.sleeve_length=3;row.jersey_style=1;row.sock_length=2;
    row.club_colors[0]=0xdb142a;row.club_colors[1]=0x18181b;rows.push_back(row);
    {
        FILE*f=nullptr;require(!fopen_s(&f,"J:/mods/fifa 16/estudos fifa 16/02_ENGENHARIA_REVERSA/clube_3d_20261001/flamengo_preview.bin","rb")&&f,"actual club appearance audit fixture");
        char magic[8],name[128];uint32_t count=0,team=0,size=0;
        require(fread(magic,1,8,f)==8&&!memcmp(magic,"C3DQA003",8)&&fread(&count,4,1,f)==1&&fread(&team,4,1,f)==1&&fread(&size,4,1,f)==1&&team==1043&&count<=100&&size==sizeof(ClubPlayerRow)&&fread(name,1,128,f)==128,"bounded actual appearance schema");
        std::vector<ClubPlayerRow>fixture(count);require(fread(fixture.data(),sizeof(ClubPlayerRow),count,f)==count&&fgetc(f)==EOF,"complete appearance fixture bytes");fclose(f);
        auto found=std::find_if(fixture.begin(),fixture.end(),[](const ClubPlayerRow&r){return r.squad_position>0&&r.squad_position<28&&r.skin_tone>=5;});
        require(found!=fixture.end(),"native outfield appearance distinct from short-sleeve and keeper audit");rows.push_back(*found);
    }
    ID3D11Device*d=nullptr;ID3D11DeviceContext*context=nullptr;
    require(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&d,nullptr,&context)),"pose audit device");
    {
        Renderer renderer;renderer.device(d);
        for(size_t player=0;player<rows.size();++player) {
            auto bind=a.load(rows[player]);
            printf("AUDIT_PLAYER id=%d name=%s team=%d\n",rows[player].player_id,rows[player].name,rows[player].team_id);
            if(!player) {
                for(size_t bone=0;bone<bind.skeleton->names.size();++bone) {
                    const auto&name=bind.skeleton->names[bone];
                    if(name.find("Arm")==name.npos&&name.find("Elbow")==name.npos&&name.find("Shoulder")==name.npos)continue;
                    unsigned weights=0;for(const auto&p:bind.parts)for(const auto&v:p.vertices)
                        for(int i=0;i<8;++i)if(v.joints[i]==bone)weights+=v.weights[i];
                    if(weights)printf("ARM_SKIN bone=%zu name=%s weight=%u\n",bone,name.c_str(),weights);
                }
            }
            for(size_t pose=0;pose<presentation_pose_count(PoseIndividual);++pose) {
                auto info=presentation_pose_at(pose,PoseIndividual);
                auto posed=std::make_shared<Model>(bind);
                /* Invisible point probes follow the exact native elbow skin
                 * helpers, so pole direction is auditable, not inferred from
                 * only the shoulder/hand coordinates in a front screenshot. */
                Part probes;probes.skinned=true;probes.asset="qa/elbow-poles";
                for(const char*name:{"RM_LeftElbow","RM_RightElbow","LeftHandIndex1","LeftHandPinky1","RightHandIndex1","RightHandPinky1","LeftHandThumb1","RightHandThumb1"}) {
                    size_t bone=0;while(bone<bind.skeleton->names.size()&&bind.skeleton->names[bone]!=name)++bone;
                    require(bone<bind.skeleton->names.size(),"elbow pole probe helper");
                    DirectX::XMFLOAT4X4 inv,world;memcpy(&inv,bind.skeleton->inverse_bind[bone].data(),64);
                    DirectX::XMStoreFloat4x4(&world,DirectX::XMMatrixInverse(nullptr,DirectX::XMLoadFloat4x4(&inv)));
                    Vertex v;v.position={world._41*bind.bind_scale,(world._42-bind.bind_feet)*bind.bind_scale,world._43*bind.bind_scale};
                    v.joints[0]=(uint16_t)bone;v.weights[0]=255;probes.vertices.push_back(v);
                }
                posed->parts.push_back(probes);
                require(apply_presentation_pose(*posed,false,nullptr,info->id),"audit posed pole probes");
                for(bool left:{true,false}) {
                    const auto&s=left?posed->left_shoulder:posed->right_shoulder;
                    const auto&e=left?posed->left_elbow:posed->right_elbow;
                    const auto&w=left?posed->left_hand:posed->right_hand;
                    auto tip=posed->parts.back().vertices[left?0:1].position;
                    auto side=DirectX::XMVectorSet(posed->left_shoulder.x-posed->right_shoulder.x,0,posed->left_shoulder.z-posed->right_shoulder.z,0);
                    auto outward=DirectX::XMVectorScale(DirectX::XMVector3Normalize(side),left?1.f:-1.f);
                    if(info->id==101)printf("NEUTRAL_POLE player=%d left=%d E=%.2f,%.2f,%.2f TIP=%.2f,%.2f,%.2f\n",rows[player].player_id,left,e.x,e.y,e.z,tip.x,tip.y,tip.z);
                    if(info->id==101){
                        float side_sign=left?1.f:-1.f;
                        float upper=sqrtf((e.x-s.x)*(e.x-s.x)+(e.y-s.y)*(e.y-s.y)+(e.z-s.z)*(e.z-s.z));
                        require((w.x-s.x)*side_sign>upper*.20f,"neutral arms slightly open on both sides, proportional to native limbs");
                        require(w.y<e.y&&e.y<s.y&&e.z<s.z,"neutral elbows relax behind shoulders, hands below elbows");
                        const auto&probe=posed->parts.back().vertices;
                        auto ix=probe[left?2:4].position,pk=probe[left?3:5].position,th=probe[left?6:7].position;
                        auto palm=DirectX::XMVector3Normalize(DirectX::XMVector3Cross(
                            DirectX::XMVectorSet(ix.x-w.x,ix.y-w.y,ix.z-w.z,0),DirectX::XMVectorSet(pk.x-w.x,pk.y-w.y,pk.z-w.z,0)));
                        printf("NEUTRAL_HAND player=%d left=%d palm=%.3f,%.3f,%.3f thumb_forward=%.3f\n",rows[player].player_id,left,
                            DirectX::XMVectorGetX(palm),DirectX::XMVectorGetY(palm),DirectX::XMVectorGetZ(palm),th.z-w.z);
                        require(DirectX::XMVectorGetX(palm)>.80f,"neutral native mirrored palm reference faces thigh, not camera");
                        require(th.z>w.z,"neutral thumb stays toward the front rather than twisting behind wrist");
                    }
                    require(DirectX::XMVectorGetX(DirectX::XMVector3Dot(DirectX::XMVectorSet(tip.x-e.x,tip.y-e.y,tip.z-e.z,0),outward))>0,
                        "native elbow skin tip points outward, not into the trunk, in every individual recipe");
                    printf("ELBOW_POLE player=%d pose=%u left=%d S=%.2f,%.2f,%.2f E=%.2f,%.2f,%.2f W=%.2f,%.2f,%.2f TIP=%.2f,%.2f,%.2f\n",rows[player].player_id,info->id,left,s.x,s.y,s.z,e.x,e.y,e.z,w.x,w.y,w.z,tip.x,tip.y,tip.z);
                }
                posed->parts.pop_back();
                require(renderer.model(posed),"audit all individual native poses");
                printf("INDIVIDUAL_AUDIT player=%d pose=%u geometry=%016llx\n",rows[player].player_id,info->id,(unsigned long long)pose_geometry_fingerprint(*posed));
                for(int angle=0;angle<5;++angle) {
                    const float yaw[]={0,DirectX::XM_PIDIV2,-DirectX::XM_PIDIV2,DirectX::XM_PI,DirectX::XM_PIDIV4};
                    require(renderer.render(600,800,yaw[angle],1,true),"audit front, sides, back and three-quarter");
                    char path[100];sprintf_s(path,"individual-%d-%u-angle-%d.bmp",rows[player].player_id,info->id,angle);
                    image(d,context,renderer.image(),path);
                }
                fflush(stdout);
            }
        }
    }
    context->Release();d->Release();puts("PASS: 12 individual poses, 3 native bodies, 5 angles; collective fingerprints");return 0;
}
int main(int argc,char**argv) {
    require(argc==3,"usage: test_club_player_3d game_root screenshot.bmp");Assets a(argv[1]);
    if(!strcmp(argv[2],"--individual-pose-audit"))return individual_pose_audit(a);
    if(!strcmp(argv[2],"--coach-probe")) {
        std::vector<uint8_t>raw;std::vector<Part>parts;Skeleton rig;
        require(a.read("data/sceneassets/slc/specificmanager_1043_0_0.rx3",raw)&&read_mesh(raw,parts),"real coach mesh probe");
        auto mesh_raw=raw;
        bool used[1024]={};float low=10000,high=-10000;
        for(const auto&p:parts)for(const auto&v:p.vertices){low=std::min(low,v.position.y);high=std::max(high,v.position.y);
            for(int i=0;i<8;++i)if(v.weights[i])used[v.joints[i]]=true;}
        printf("coach parts=%zu bounds=%.2f..%.2f\n",parts.size(),low,high);
        for(int j=0;j<31;++j){float sum=0,x=0,y=0,z=0;
            for(const auto&p:parts)for(const auto&v:p.vertices)for(int k=0;k<8;++k)if(v.joints[k]==j&&v.weights[k]){float w=v.weights[k];sum+=w;x+=v.position.x*w;y+=v.position.y*w;z+=v.position.z*w;}
            if(sum)printf("WEIGHT %d center=%.2f,%.2f,%.2f\n",j,x/sum,y/sum,z/sum);}
        for(const char*name:{"skeleton_ant.rx3","skeleton_player.rx3"}) {
            require(a.read(std::string("data/sceneassets/rig/")+name,raw)&&read_skeleton(raw,rig),"native coach candidate rig");
            printf("RIG %s\n",name);for(size_t i=0;i<1024;++i)if(used[i])printf(" %zu %s\n",i,i<rig.names.size()?rig.names[i].c_str():"OUTSIDE RIG");
            if(!strcmp(name,"skeleton_ant.rx3"))for(size_t s=0;s<le(mesh_raw.data()+12);++s) {
                const uint8_t*d=mesh_raw.data()+16+s*16;if(le(d)!=0xdf9aec1e)continue;
                size_t off=le(d+4),count=le(mesh_raw.data()+off+4);
                for(size_t i=0;i<count;++i) {
                    float best=1e30f;size_t index=0;float m[16];memcpy(m,mesh_raw.data()+off+16+i*64,64);
                    for(size_t j=0;j<rig.names.size();++j){float error=0;for(int k=0;k<16;++k)error+=fabsf(m[k]-rig.inverse_bind[j][k]);if(error<best){best=error;index=j;}}
                    printf("EMBEDDED %zu nearest=%zu %s error=%.5f t=%.2f,%.2f,%.2f\n",i,index,rig.names[index].c_str(),best,m[12],m[13],m[14]);
                    m[15]=1;DirectX::XMFLOAT4X4 mat,inv;memcpy(&mat,m,64);DirectX::XMStoreFloat4x4(&inv,DirectX::XMMatrixInverse(nullptr,DirectX::XMLoadFloat4x4(&mat)));
                    printf(" WORLD %.2f,%.2f,%.2f\n",inv._41,inv._42,inv._43);
                }
            }
        }
        require(a.read("data/sceneassets/slc/specificmanager_1043_0_0_textures.rx3",raw),"coach textures");
        for(const auto&name:texture_names(raw))printf("material %s\n",name.c_str());return 0;
    }
    tests(a);
    {
        std::vector<uint8_t>b;FILE*f=nullptr;std::string path=std::string(argv[1])+"/data/db/fifa_ng_db.db";
        require(!fopen_s(&f,path.c_str(),"rb")&&f,"read-only native kit database");
        _fseeki64(f,0,SEEK_END);b.resize((size_t)_ftelli64(f));rewind(f);require(fread(b.data(),1,b.size(),f)==b.size(),"kit database bytes");fclose(f);
        std::unordered_map<unsigned,int>collars;require(read_kit_collars(b,collars)&&collars.count(1043*32)&&collars.count(112893*32),"verified packed teamkits collars per club");
        printf("KIT COLLARS home Flamengo=%d Miami=%d Arsenal=%d Real=%d GK Flamengo=%d entries=%zu\n",a.kit_collar(1043,0),a.kit_collar(112893,0),a.kit_collar(1,0),a.kit_collar(243,0),a.kit_collar(1043,2),collars.size());
        auto original=collars;auto broken=b;broken.resize(40);require(!read_kit_collars(broken,collars)&&collars==original,"truncated kit DB rejected atomically");
        broken=b;write32(broken,16,0xffffffff);require(!read_kit_collars(broken,collars)&&collars==original,"malformed DB directory bounded");
        int c=-1;const std::string lua="-- assignKitDetails(1,0,0,0,0,0,0,0,0,90)\n--[=[\nassignKitDetails(1,0,0,0,0,0,0,0,0,91)\n]=]\nassignKitDetails(1,0,0,\"ffffff\",0,0,0,0,0,8)\nassignKitDetails(2,0,0,0,0,0,0,0,0,2)\nassignKitDetails(1,0,0,0,0,0,0,0,0,12)";
        require(read_kit_collar_override(lua,1,0,c)&&c==12,"last matching literal kit assignment wins; comments and other clubs ignored");
        c=-1;require(!read_kit_collar_override("if test then\nassignKitDetails(1,0,0,0,0,0,0,0,0,8)\nend",1,0,c)&&c==-1,"conditional Lua is not executed or guessed");
        require(!read_kit_collar_override("assignKitDetails(1,0,0,0,0,0,0,0,0,-1)",1,0,c),"minus one preserves the native database collar");
        require(!read_kit_collar_override("assignKitDetails(1,0,0,0,0,0,0,0,0,8)\nassignKitDetails(1,0,0,0,0,0,0,0,0,-1)",1,0,c)&&c==-1,"last minus one cancels previous literal override, matching native GetKitCollar");
        require(!read_kit_collar_override("assignKitDetails(1,0,0,0,0,0,0,0,0,8)\nif test then\nend",1,0,c)&&c==-1,"unsupported Lua leaves caller's fallback unchanged atomically");
        puts("PASS: read-only kit collars, bounded DB decode and literal Revolution overrides");
    }
    for(const auto &path:{a.first("data/sceneassets/faces/face_158023_","_textures.rx3"),
        std::string("data/sceneassets/hair/hair_158023_0_textures.rx3"),
        std::string("data/sceneassets/body/playerskin_20801_textures.rx3"),
        std::string("data/sceneassets/body/playerskin_158023_textures.rx3"),
        std::string("data/sceneassets/globaltex/globaltex_0.rx3")}) {
        std::vector<uint8_t>b;if(a.read(path,b)){printf("Texture names in %s:",path.c_str());
            for(const auto &name:texture_names(b))printf(" [%s]",name.c_str());puts("");}
    }
    ClubPlayerRow row={};row.player_id=158023;row.team_id=112893;row.position=24;row.head_type=0;row.skin_tone=3;row.hair_type=0;row.shoe_type=15;
    /* Explicit QA colours only. Runtime obtains all nine channels from teams. */
    row.club_colors_valid=1;row.club_colors[0]=0xf7b5cd;row.club_colors[1]=0x18181b;row.club_colors[2]=0xeeeeee;
    auto model=std::make_shared<Model>(a.load(row));printf("%s\n",model->diagnostic.c_str());
    require(model->team_id==112893&&model->crest_texture>=0&&model->club_colors_valid&&fabs(model->club_colors[0].x-247/255.f)<.001f,"club backdrop uses the supplied current-club data");
    auto changed=row;changed.team_id=1043;changed.club_colors[0]=0xdb142a;auto changed_model=a.load(changed);
    bool correct_collar=false;for(const auto&p:changed_model.parts)if(p.asset=="data/sceneassets/body/jersey_0_8_0_0_0_0_0.rx3")correct_collar=true;
    require(correct_collar&&a.kit_collar(1043,2)==0,"club's native collar eight mesh, distinct from goalkeeper collar zero");
    require(changed_model.team_id==1043&&changed_model.crest_texture>=0&&changed_model.club_colors[0].x!=model->club_colors[0].x&&
        changed_model.textures[changed_model.crest_texture].bytes!=model->textures[model->crest_texture].bytes,"same player changing club reloads colours and crest");
    bool has_eyes=false,has_skin=false,has_hair=false;
    for(const auto &p:model->parts) {
        if(p.name=="eyes" && p.texture>=0)has_eyes=true;
        if(p.asset.find("/hair/")!=std::string::npos && p.texture>=0)has_hair=true;
        if((p.asset.find("/arms_")!=std::string::npos||p.asset.find("/legs_")!=std::string::npos) && p.texture>=0)has_skin=true;
    }
    require(has_eyes,"real eye diffuse associated with eye submesh");
    require(has_skin,"custom playerskin/tattoos associated with arms/legs");
    require(has_hair,"real hair diffuse associated with hair geometry");
    size_t hair_parts=0;for(const auto&p:model->parts)if(p.asset.find("/hair/")!=p.asset.npos){++hair_parts;printf("hair submesh %s blend=%d\n",p.name.c_str(),p.blend);}
    require(hair_parts==2,"both real hair cap and strands retained");
    bool strands_blend=false;for(const auto&p:model->parts)if(p.asset.find("/hair/")!=p.asset.npos&&p.blend)strands_blend=true;
    require(strands_blend,"custom named hair strands use transparency");
    for(const auto&p:model->parts)if(p.asset.find("/hair/")!=p.asset.npos) {
        std::vector<uint8_t>raw;std::vector<Part>original;
        require(a.read(p.asset,raw)&&read_mesh(raw,original),"original high-detail hair reload");
        auto found=std::find_if(original.begin(),original.end(),[&](const Part&q){return p.name==q.name;});
        require(found!=original.end()&&p.vertices.size()==found->vertices.size()&&p.indices==found->indices,"every original hair vertex and triangle retained, including strands");
        require(p.native_normals,"native high-detail hair normals available");
    }
    ClubPlayerRow keeper=row;keeper.player_id=167495;keeper.position=0;keeper.glove_type=1;keeper.height=193;
    auto keeper_model=std::make_shared<Model>(a.load(keeper));printf("GOALKEEPER\n%s\n",keeper_model->diagnostic.c_str());
    require(keeper_model->diagnostic.find("kit_112893_2_0.rx3")!=std::string::npos,"goalkeeper kit, never outfield kit");
    bool gloves=false;for(const auto&p:keeper_model->parts)if(p.asset.find("/gkglove/")!=p.asset.npos&&p.texture>=0) {
        gloves=true;float low=10000,high=-10000;
        for(const auto&v:p.vertices){low=std::min(low,v.position.y);high=std::max(high,v.position.y);}
        printf("glove submesh %s y=%.2f..%.2f\n",p.name.c_str(),low,high);
        require(low>80&&high<170,"gloves remain attached to native bind-pose hands");
    }
    require(gloves,"goalkeeper genuine glove mesh and diffuse");
    /* Read-only appearance regression from the explicit Flamengo QA fixture.
     * Never used by the runtime club provider. */
    ClubPlayerRow rossi=keeper;rossi.player_id=227275;rossi.team_id=1043;rossi.head_type=2506;
    rossi.head_class=0;rossi.hair_type=123;rossi.hair_color=1;rossi.skin_tone=5;
    rossi.glove_type=18;rossi.shoe_type=28;rossi.sleeve_length=3;rossi.jersey_style=1;rossi.sock_length=2;
    auto rossi_model=std::make_shared<Model>(a.load(rossi));
    printf("ROSSI HAIR\n%s\n",rossi_model->diagnostic.c_str());
    {
        std::vector<uint8_t>raw;Texture tex;
        require(a.read("data/sceneassets/hair/hair_227275_0_textures.rx3",raw),"example original hair material");
        for(const char*name:{"hair_cm","hair_coeff"})if(read_texture(raw,name,tex)) {
            alpha_statistics(tex,name);texture_channels(tex,(std::string("club-rossi-")+name+"-channels.bmp").c_str());
        }
    }
    for(const auto&p:rossi_model->parts)if(p.asset.find("/hair/")!=p.asset.npos) {
        std::vector<uint8_t>raw;float low=10000,high=-10000;
        for(const auto&v:p.vertices){low=std::min(low,v.position.y);high=std::max(high,v.position.y);}
        printf("Rossi hair part %s y=%.2f..%.2f\n",p.name.c_str(),low,high);
        if(p.texture>=0)alpha_statistics(rossi_model->textures[p.texture],p.name.c_str());
    }
    pose_tests(*model,*keeper_model);uniform_tests(a,row);
    ClubPlayerRow tall=row;tall.height=205;auto tall_model=std::make_shared<Model>(a.load(tall));
    float top=0;for(const auto&p:tall_model->parts)if(p.asset.find("/heads/")!=p.asset.npos&&p.name!="eyes")
        for(const auto&v:p.vertices)top=std::max(top,v.position.y);
    require(fabs(top-205.f)<.01f,"height follows head reference; full hair is not cropped/scaled away");
    require(model->parts.size()>=8,"assembled body/head meshes");require(model->textures.size()>=3,"real kit and head textures");
    ID3D11Device*d=nullptr;ID3D11DeviceContext*context=nullptr;
    require(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&d,nullptr,&context)),"offline WARP renderer");
    D3D11_TEXTURE2D_DESC sentinel_desc={};sentinel_desc.Width=sentinel_desc.Height=4;sentinel_desc.MipLevels=sentinel_desc.ArraySize=1;
    sentinel_desc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;sentinel_desc.SampleDesc.Count=1;sentinel_desc.BindFlags=D3D11_BIND_SHADER_RESOURCE;
    ID3D11Texture2D*sentinel_texture=nullptr;ID3D11ShaderResourceView*sentinel_view=nullptr;
    require(SUCCEEDED(d->CreateTexture2D(&sentinel_desc,nullptr,&sentinel_texture))&&
        SUCCEEDED(d->CreateShaderResourceView(sentinel_texture,nullptr,&sentinel_view)),"foreign pipeline sentinel");sentinel_texture->Release();
    context->PSSetShaderResources(1,1,&sentinel_view);context->PSSetShaderResources(2,1,&sentinel_view);
    D3D11_VIEWPORT foreign_viewport={3,5,23,29,.2f,.8f};context->RSSetViewports(1,&foreign_viewport);
    {Renderer renderer;renderer.device(d);require(renderer.model(model),"upload mesh");
        auto club=row;club.team_id=1043;club.club_colors[0]=0xdb142a;club.club_colors[1]=0x151515;
        auto coach=a.coach(club);require(coach.model&&!coach.name.empty()&&coach.asset.find("specificmanager_1043_")!=coach.asset.npos,"real club-associated sideline coach and name");
        require(coach.model->skeleton&&coach.model->skeleton->names.size()==31&&coach.model->formation.empty()&&!coach.model->goalkeeper,"coach uses only its own compact rig, never player rig or starting XI");
        require(renderer.model(coach.model)&&renderer.render(640,800,0,1),"original SLC coach static 3D preview");image(d,context,renderer.image(),"club-coach-flamengo.bmp");
        printf("%s\n",coach.model->diagnostic.c_str());club.team_id=9;auto other_coach=a.coach(club);
        require(other_coach.model&&other_coach.asset!=coach.asset&&other_coach.name!=coach.name,"coach dynamically changes with club, not a hardcoded Flamengo model");
        for(const auto&entry:{std::make_pair(coach,"flamengo"),std::make_pair(other_coach,"liverpool")}) {
            uint64_t previous=0;
            for(size_t i=0;i<presentation_pose_count(PoseCoachAny);++i) {
                auto posed=std::make_shared<Model>(*entry.first.model);unsigned id=presentation_pose_at(i,PoseCoachAny)->id;
                require(apply_coach_pose(*posed,id),"coach poses use real embedded SLC bind matrices and weights");
                require(posed->parts.size()==entry.first.model->parts.size()&&posed->textures.size()==entry.first.model->textures.size(),"coach poses preserve original materials and parts");
                for(const auto&p:posed->parts)for(const auto&v:p.vertices)require(std::isfinite(v.position.x)&&std::isfinite(v.position.y)&&std::isfinite(v.position.z)&&fabs(v.position.x)<200&&v.position.y>=0&&v.position.y<250&&fabs(v.position.z)<200,"coach IK remains finite and bounded");
                uint64_t fingerprint=pose_geometry_fingerprint(*posed);require(fingerprint!=previous,"coach poses differ in real mesh geometry");previous=fingerprint;
                require(renderer.model(posed)&&renderer.render(800,1000,0,1),"posed coach renders natively");
                char file[100];sprintf_s(file,"club-coach-%s-pose-%u.bmp",entry.second,id);image(d,context,renderer.image(),file);
            }
            auto invalid=*entry.first.model,before=invalid;
            require(!apply_coach_pose(invalid,104)&&unchanged(invalid,before),"coach rejects player pose atomically");
            invalid.skeleton.reset();before=invalid;
            require(!apply_coach_pose(invalid,201)&&unchanged(invalid,before),"missing coach rig stays unchanged instead of borrowing a player rig");
        }
        require(renderer.model(other_coach.model)&&renderer.render(640,800,0,1),"second club coach preview");image(d,context,renderer.image(),"club-coach-liverpool.bmp");
        club.team_id=199999;require(!a.coach(club).model,"missing coach hides entry, no unrelated fallback");
        for(int club_id:{1043,112893}) {
            std::vector<std::shared_ptr<const Model>>roster;
            FILE*f=nullptr;char path[260];sprintf_s(path,"J:/mods/fifa 16/estudos fifa 16/02_ENGENHARIA_REVERSA/clube_3d_20261001/%s_preview.bin",club_id==1043?"flamengo":"miami");
            require(!fopen_s(&f,path,"rb")&&f,"offline club roster for room QA");char magic[8],name[128];uint32_t count=0,id=0,row_size=0;
            bool header_ok=fread(magic,1,8,f)==8&&!memcmp(magic,"C3DQA003",8)&&fread(&count,4,1,f)==1&&fread(&id,4,1,f)==1&&fread(&row_size,4,1,f)==1;
            size_t name_bytes=header_ok?fread(name,1,128,f):0;
            require(header_ok&&count>=11&&count<=512&&(row_size==sizeof(ClubPlayerRow)||row_size==sizeof(LegacyClubPlayerRow))&&id==(unsigned)club_id&&name_bytes==128,"compatible exact-club room fixture");
            std::vector<ClubPlayerRow>rows(count);
            if(row_size==sizeof(ClubPlayerRow))require(fread(rows.data(),sizeof(ClubPlayerRow),count,f)==count,"current fixture bytes");
            else {std::vector<LegacyClubPlayerRow>legacy(count);require(fread(legacy.data(),sizeof(LegacyClubPlayerRow),count,f)==count,"legacy fixture bytes");
                for(size_t i=0;i<legacy.size();++i)rows[i]=upgrade_legacy_row(legacy[i]);}
            require(fgetc(f)==EOF,"exact fixture end");fclose(f);
            for(const auto&r:rows)if(r.squad_position>=0&&r.squad_position<28)roster.push_back(std::make_shared<Model>(a.load(r)));
            require(roster.size()==11,"eleven actual current-club uniforms for locker room");
            auto staff=a.coach(rows[0]);
            if(club_id==1043) {
                std::vector<std::shared_ptr<const Model>>full_roster;full_roster.reserve(rows.size());
                for(const auto&r:rows)full_roster.push_back(std::make_shared<Model>(a.load(r)));
                auto photo=std::make_shared<Model>(build_full_squad_photo(full_roster,staff.model));
                require(photo->room==RoomFullSquadPhoto&&photo->team_id==club_id&&photo->player_count==rows.size()+1&&photo->formation.size()==rows.size()+1,
                    "full club photo includes every real roster record and its exact-club SLC coach");
                require(photo->presentation_pose&&photo->presentation_pose_id==120&&photo->press_coach_present,
                    "full club photo uses its private collective pose and includes the coach");
                for(const auto&r:rows)require(std::count_if(photo->formation.begin(),photo->formation.end(),[&](const auto&p){return p.player_id==r.player_id;})==1,
                    "full club photo places each roster player exactly once");
                require(std::count_if(photo->formation.begin(),photo->formation.end(),[](const auto&p){return p.player_id==0;})==1,
                    "full club photo places the coach exactly once");
                require(renderer.model(photo)&&renderer.render(1400,800,0,1),"native full-squad photo renders without external 3D software");
                image(d,context,renderer.image(),"club-full-squad-flamengo.bmp");
            } else {
                auto missing_coach=build_full_squad_photo(roster,staff.model);
                require(missing_coach.player_count==0&&missing_coach.parts.empty(),
                    "full club photo refuses to substitute another club's missing SLC coach");
            }
            for(auto kind:{RoomPress,RoomDressing}) {
                auto room=std::make_shared<Model>(build_club_room(roster,kind,staff.model));size_t shirts=0;
                require(room->room==kind&&room->team_id==club_id&&room->player_count==0&&room->formation.empty()&&!room->skeleton&&room->club_colors_valid&&room->crest_texture>=0,"room contains current club metadata, not invented players or borrowed rig");
                require(room->parts.size()<100,"static room surfaces batched for bounded draw count");
                for(const auto&p:room->parts) {
                    if(p.asset.find("/hanging-shirt/")!=p.asset.npos){++shirts;require(p.texture>=0&&size_t(p.texture)<room->textures.size(),"hanging shirt retains actual native kit texture and UV");}
                    for(auto index:p.indices)require(index<p.vertices.size(),"batched room indices in bounds");
                    for(const auto&v:p.vertices)require(std::isfinite(v.position.x)&&std::isfinite(v.position.y)&&std::isfinite(v.position.z)&&fabs(v.position.x)<1000&&fabs(v.position.y)<1000&&fabs(v.position.z)<1000,"room geometry finite and bounded");
                }
                require(shirts==(kind==RoomDressing?11:0),"dressing room has eleven actual RX3 shirts including goalkeeper kit");
                if(kind==RoomPress&&club_id==1043)require(room->presentation_pose_id==205&&std::any_of(room->parts.begin(),room->parts.end(),[](const Part&p){return p.asset.find("/seated-coach/")!=p.asset.npos;}),"press room contains actual club coach posed sitting at the microphone");
                if(kind==RoomPress&&club_id==112893)require(!room->presentation_pose_id,"missing coach leaves the room empty, never another club's coach");
                require(renderer.model(room)&&renderer.render(1400,800,0,1),"native procedural club room renders without Blender");
                char file[100];sprintf_s(file,"club-room-%s-%d.bmp",club_id==1043?"flamengo":"miami",kind);image(d,context,renderer.image(),file);
                if(kind==RoomPress&&staff.model){
                    auto speaking=std::make_shared<Model>(build_club_room(roster,kind,staff.model,206));
                    require(speaking->presentation_pose_id==206&&renderer.model(speaking)&&renderer.render(1400,800,0,1),"second seated pose renders in press room");
                    sprintf_s(file,"club-room-%s-seated-206.bmp",club_id==1043?"flamengo":"miami");image(d,context,renderer.image(),file);
                }
            }
            auto mixed=roster;auto wrong_club=std::make_shared<Model>(*roster[1]);wrong_club->team_id=club_id==1043?112893:1043;mixed[1]=wrong_club;
            require(build_club_room(mixed,RoomDressing).parts.empty()&&build_club_room({},RoomPress).parts.empty()&&build_club_room(roster,(ClubRoomKind)999).parts.empty(),"empty, mixed and unknown rooms fail safely");
        }
        require(renderer.model(model),"restore player after coach QA");
        require(renderer.render(640,800,0,1),"offscreen render");image(d,context,renderer.image(),argv[2]);
        ID3D11ShaderResourceView*restored=nullptr;context->PSGetShaderResources(1,1,&restored);
        require(restored==sentinel_view,"shadow SRV does not leak into the game's shader slots");if(restored)restored->Release();
        restored=nullptr;context->PSGetShaderResources(2,1,&restored);
        require(restored==sentinel_view,"hair coefficient SRV does not leak into the game's shader slots");if(restored)restored->Release();
        D3D11_VIEWPORT actual_viewport={};UINT viewport_count=1;context->RSGetViewports(&viewport_count,&actual_viewport);
        require(viewport_count==1&&!memcmp(&foreign_viewport,&actual_viewport,sizeof(foreign_viewport)),"shadow viewport does not replace the game viewport");
        ID3D11RasterizerState*before=nullptr,*after=nullptr;context->RSGetState(&before);
        require(renderer.render(640,800,.5f,1),"second preview frame");context->RSGetState(&after);
        require(before==after,"original pipeline state restored");if(before)before->Release();if(after)after->Release();
        require(renderer.model(keeper_model)&&renderer.render(640,800,0,1),"goalkeeper preview");
        image(d,context,renderer.image(),"club-goalkeeper-test.bmp");
        require(apply_presentation_pose(*rossi_model,false)&&renderer.model(rossi_model)&&renderer.render(800,1000,.1f,1.25f),"Rossi native hair/keeper preview");
        image(d,context,renderer.image(),"club-rossi-hair-test.bmp");
        ClubPlayerRow curly=row;curly.player_id=179944;curly.height=189;curly.shoe_type=10;
        auto curly_model=std::make_shared<Model>(a.load(curly));require(apply_presentation_pose(*curly_model,false),"curly hair follows native skeleton");
        printf("HAIR DETAIL\n%s\n",curly_model->diagnostic.c_str());
        std::vector<uint8_t>hair_bytes;Texture hair_texture;
        require(a.read("data/sceneassets/hair/hair_179944_0_textures.rx3",hair_bytes),"real detailed hair textures");
        for(const char*name:{"hair_cm","hair_coeff"})if(read_texture(hair_bytes,name,hair_texture))alpha_statistics(hair_texture,name);
        size_t locks=0;for(const auto&p:curly_model->parts)if(p.asset.find("/hair/")!=p.asset.npos)locks+=p.vertices.size();
        require(locks>1000,"voluminous original curly hair is loaded, not a low-detail cap");
        bool coverage=false;for(const auto&p:curly_model->parts)if(p.asset.find("/hair/")!=p.asset.npos) {
            require(p.hair_coeff_texture>=0&&p.alpha_scale==1,"coefficient coverage bypasses low diffuse alpha boosting");coverage=true;
        }
        require(coverage,"real curly hair uses its own coefficient coverage");
        require(renderer.model(curly_model)&&renderer.render(800,1000,.20f,1),"high-detail curly hair preview");image(d,context,renderer.image(),"club-curly-hair-test.bmp");
        require(renderer.render(800,1000,2.7f,1),"back of high-detail hair preview");image(d,context,renderer.image(),"club-hair-back-test.bmp");
        auto geometry=std::make_shared<Model>(*curly_model);
        for(auto&p:geometry->parts)if(p.asset.find("/hair/")!=p.asset.npos){p.texture=-1;p.hair_coeff_texture=-1;p.alpha_scale=1;p.blend=false;p.color={.30f,.20f,.10f};
            float lo=10000,hi=-10000;for(const auto&v:p.vertices){lo=std::min(lo,v.position.y);hi=std::max(hi,v.position.y);}
            printf("hair geometry %s bounds %.2f..%.2f\n",p.name.c_str(),lo,hi);}
        require(renderer.model(geometry)&&renderer.render(800,1000,.20f,1),"unmasked original hair geometry inspection");image(d,context,renderer.image(),"club-hair-geometry-test.bmp");
        auto photo=std::make_shared<Model>(*model);require(apply_presentation_pose(*photo,true),"photo preview pose");
        require(renderer.model(photo)&&renderer.render(640,800,0,1),"hands-on-thighs preview");image(d,context,renderer.image(),"club-photo-pose.bmp");
        require(renderer.render(800,800,1.3f,1),"side knee support preview");image(d,context,renderer.image(),"club-photo-pose-side.bmp");
        for(size_t pose=0;pose<presentation_pose_count(PoseIndividual);++pose) {
            unsigned id=presentation_pose_at(pose,PoseIndividual)->id;
            auto individual=std::make_shared<Model>(*model);require(apply_presentation_pose(*individual,false,nullptr,id),"individual recipe QA");
            require(renderer.model(individual)&&renderer.render(640,800,0,1),"all individual poses rendered");
            char file[80];sprintf_s(file,"club-individual-pose-%u.bmp",id);image(d,context,renderer.image(),file);
            if(id==105||id==103||id==102) {
                require(renderer.render(800,1000,0,1,true),"individual hand/cuff close detail");
                sprintf_s(file,"club-individual-detail-%u.bmp",id);image(d,context,renderer.image(),file);
                require(renderer.render(800,1000,1.7f,1,true),"individual hand/cuff side detail");
                sprintf_s(file,"club-individual-side-%u.bmp",id);image(d,context,renderer.image(),file);
            }
        }
        for(const auto&entry:{std::make_pair(model,"outfield"),std::make_pair(rossi_model,"keeper")}) {
            auto crossed=std::make_shared<Model>(*entry.first);
            /* Rossi's earlier hair preview was already posed; reload a clean bind model. */
            if(entry.first==rossi_model)*crossed=a.load(rossi);
            require(apply_presentation_pose(*crossed,false,nullptr,4),"collective crossed-arm detail preview");
            require(renderer.model(crossed)&&renderer.render(800,1000,0,1,true),"crossed-arm frontal detail");
            image(d,context,renderer.image(),(std::string("club-pose4-")+entry.second+"-front.bmp").c_str());
            require(renderer.render(800,1000,1.15f,1,true),"crossed-arm side detail");
            image(d,context,renderer.image(),(std::string("club-pose4-")+entry.second+"-side.bmp").c_str());
        }
        require(!renderer.render(640,800,0,NAN)&&!renderer.render(640,800,0,1,false,NAN,0),"invalid camera zoom/pan rejected before issuing commands");
        renderer.clear();require(!renderer.render(640,800,0,1),"empty renderer safe");}
    ID3D11ShaderResourceView*empty=nullptr;context->PSSetShaderResources(1,1,&empty);context->PSSetShaderResources(2,1,&empty);sentinel_view->Release();
    context->Release();d->Release();puts("PASS: assets, malformed input, offscreen renderer and pipeline restore");return 0;
}
#endif
