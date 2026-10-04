#define NOMINMAX
#include "../assets/fifa_player_assets.h"
#include <DirectXMath.h>
#include <algorithm>
#include <cmath>
#include <limits>
using namespace DirectX;
namespace fifa_player {
namespace {
enum ArmStyle {TeamPhotoArms,BackArms,OneKneeArms,CrossedArms,PortraitArms,
    PortraitBackArms,PortraitHipArm,ThumbsUpArm,PortraitHipsArms,SaluteArm,WaveArm,PortraitFrontHands,MediaPointArm,MediaBadgeArm,GestureRestArm,RaisedFistArm,PointUpArm};
enum CoachPoseStyle {CoachPoseDefault,CoachPoseCrossed,CoachPoseHandsBehind,CoachPoseTactical,
    CoachPoseSeatedHands,CoachPoseSeatedGesture,CoachPoseArrival,CoachPoseHandsOnHips,
    CoachPoseCalmDown,CoachPoseExplaining};
struct PortraitStance {
    float body_yaw=0,head_yaw=0,knee_bend=0,head_pitch=0;
    float leg_spread=0,left_knee_offset=0,right_knee_offset=0,torso_roll=0;
};
struct PhotoPoseRecipe {
    PresentationPoseInfo info;
    float thigh_bend,knee_bend,foot_bend,torso_lean,leg_spread;
    float wrist_ratio,wrist_lift,wrist_clearance,finger_curl,fingertip_curl;
    ArmStyle individual_arms;
    ArmStyle front_arms=TeamPhotoArms;
    PortraitStance portrait;
    CoachPoseStyle coach_pose=CoachPoseDefault;
};
const PhotoPoseRecipe recipes[]={
    {{1,PoseGroup,"Pose 1 - foto da equipe",54,-12,16,6,0},-32,52,-20,62,4,.70f,.04f,.24f,12,7,TeamPhotoArms},
    {{2,PoseGroup,"Pose 2 - apoio nos joelhos",54,-14,16,6,1},-29,49,-20,60,3,.70f,.04f,.24f,12,7,BackArms},
    {{3,PoseGroup,"Pose 3 - equipe unida",52,-12,20,6,2},-52,104,-52,32,6,.70f,.04f,.24f,12,7,BackArms},
    {{4,PoseGroup,"Pose 4 - um joelho no gramado",56,-14,22,6,1},-88,90,-2,8,4,.70f,.04f,.20f,12,7,CrossedArms,OneKneeArms},
    {{5,PoseGroup,"Pose 5 - formação em pé",44,-10,10,11,1},0,0,0,0,0,.70f,.04f,.24f,12,7,BackArms},
    {{6,PoseGroup,"Pose 6 - duas fileiras compactas",54,-10,16,5,1},-30,50,-20,56,3,.70f,.05f,.24f,12,7,CrossedArms},
    {{7,PoseGroup,"Pose 7 - equipe de braços cruzados",46,-10,10,11,1},0,0,0,0,0,.70f,.04f,.24f,12,7,CrossedArms},
    /* Kept out of the shared pose carousel: this silhouette and row treatment
     * belong only to the dedicated full-roster team-photo scene. */
    {{120,PoseFullSquad,"Foto oficial - elenco completo",58,-165,20,0,1},-24,38,-14,54,4,.70f,.04f,.24f,12,7,BackArms,TeamPhotoArms},
    {{101,PoseIndividual,"Postura natural",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,22,12,PortraitArms,TeamPhotoArms,{0,0,2}},
    {{102,PoseIndividual,"Mãos nas costas",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,22,12,PortraitBackArms,TeamPhotoArms,{-12,8,2}},
    {{103,PoseIndividual,"Mão na cintura",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,24,14,PortraitHipArm,TeamPhotoArms,{-14,10,3}},
    {{104,PoseIndividual,"Braços cruzados",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,28,18,CrossedArms,TeamPhotoArms,{22,-16,2}},
    {{105,PoseIndividual,"Joinha",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,75,65,ThumbsUpArm,TeamPhotoArms,{-12,8,3}},
    {{106,PoseIndividual,"Mãos na cintura",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,24,14,PortraitHipsArms,TeamPhotoArms,{-10,6,2}},
    {{107,PoseIndividual,"Braços cruzados - perfil",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,28,18,CrossedArms,TeamPhotoArms,{52,-38,2}},
    {{108,PoseIndividual,"Saudação",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,4,2,SaluteArm,TeamPhotoArms,{-8,4,2}},
    {{109,PoseIndividual,"Aceno",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,3,2,WaveArm,TeamPhotoArms,{-10,7,2}},
    {{110,PoseIndividual,"Mãos à frente",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,22,12,PortraitFrontHands,TeamPhotoArms,{12,-8,2}},
    {{111,PoseIndividual,"Media day - indicadores elevados",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,75,65,MediaPointArm,TeamPhotoArms,{6,-4,2}},
    {{112,PoseIndividual,"Media day - mão no escudo",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,26,16,MediaBadgeArm,TeamPhotoArms,{8,-6,2}},
    {{113,PoseIndividual,"Punho erguido",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,48,35,RaisedFistArm,TeamPhotoArms,{8,-5,0,0,14,0,5,4}},
    {{114,PoseIndividual,"Indicador para cima",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,12,7,PointUpArm,TeamPhotoArms,{8,-14,0,-16,14,0,3,4}},
    {{201,PoseStandingCoach,"Técnico - postura natural",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,0,0,PortraitArms,TeamPhotoArms,{},CoachPoseDefault},
    {{202,PoseStandingCoach,"Técnico - braços cruzados",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,0,0,CrossedArms,TeamPhotoArms,{},CoachPoseCrossed},
    {{203,PoseStandingCoach,"Técnico - mãos nas costas",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,0,0,PortraitBackArms,TeamPhotoArms,{},CoachPoseHandsBehind},
    {{204,PoseStandingCoach,"Técnico - orientação tática",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,0,0,WaveArm,TeamPhotoArms,{},CoachPoseTactical},
    {{205,PosePressConferenceCoach,"Técnico - sentado à mesa",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,0,0,PortraitFrontHands,TeamPhotoArms,{},CoachPoseSeatedHands},
    {{206,PosePressConferenceCoach,"Técnico - sentado gesticulando",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,0,0,WaveArm,TeamPhotoArms,{},CoachPoseSeatedGesture},
    {{207,PoseStandingCoach,"Técnico - chegada à coletiva",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,0,0,PortraitArms,TeamPhotoArms,{},CoachPoseArrival},
    {{208,PoseStandingCoach,"Técnico - mãos na cintura",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,0,0,PortraitArms,TeamPhotoArms,{},CoachPoseHandsOnHips},
    {{209,PoseStandingCoach,"Técnico - gesto para acalmar",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,0,0,PortraitArms,TeamPhotoArms,{},CoachPoseCalmDown},
    {{210,PoseStandingCoach,"Técnico - explicando com as mãos",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,0,0,PortraitArms,TeamPhotoArms,{},CoachPoseExplaining},
    {{301,PoseSeatedPlayer,"Jogador - sentado na coletiva",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,12,7,PortraitFrontHands},
    {{302,PoseSeatedPlayer,"Jogador - respondendo na coletiva",52,-24,32},0,0,0,0,0,.56f,.08f,.20f,12,7,PortraitFrontHands}
};
const PhotoPoseRecipe* recipe(unsigned id){for(const auto&r:recipes)if(r.info.id==id)return &r;return nullptr;}
bool recipe_visible(const PhotoPoseRecipe&r,unsigned mode){
    if(r.info.modes&PoseFullSquad)return (mode&PoseFullSquad)!=0;
    return !mode||(r.info.modes&mode)!=0;
}
}
size_t presentation_pose_count(unsigned mode){size_t n=0;for(const auto&r:recipes)if(recipe_visible(r,mode))++n;return n;}
const PresentationPoseInfo* presentation_pose_at(size_t index,unsigned mode){for(const auto&r:recipes)if(recipe_visible(r,mode)){if(!index--)return &r.info;}return nullptr;}
const PresentationPoseInfo* presentation_pose_find(unsigned id){const auto*r=recipe(id);return r?&r->info:nullptr;}
bool apply_presentation_pose(Model&model,bool crouching,const PoseContacts*contacts,unsigned pose_id) {
    const auto*style=recipe(pose_id);if(!style||(style->info.modes&PoseCoachAny)||(crouching&&!(style->info.modes&(PoseGroup|PoseFullSquad))))return false;
    if(model.presentation_pose)return model.presentation_pose_id==pose_id;
    const auto&rig=model.skeleton;
    if(!rig||rig->parents.empty()||rig->parents.size()>1024||model.parts.empty()||rig->names.size()!=rig->parents.size()||
        rig->inverse_bind.size()!=rig->parents.size()||!std::isfinite(model.bind_scale)||!std::isfinite(model.bind_feet)||model.bind_scale<=0)return false;
    if(contacts&&!std::isfinite(contacts->floor_cm))return false;
    size_t count=rig->parents.size();
    for(size_t i=0;i<count;++i)if(rig->parents[i]!=0xffff&&rig->parents[i]>=i)return false;
    std::vector<XMFLOAT4X4>rest(count),pose(count),delta(count);
    float support_error[2]={};
    for(size_t i=0;i<count;++i) {
        XMFLOAT4X4 inverse;std::copy(rig->inverse_bind[i].begin(),rig->inverse_bind[i].end(),&inverse._11);
        XMVECTOR det;XMMATRIX bind=XMMatrixInverse(&det,XMLoadFloat4x4(&inverse));
        if(!std::isfinite(XMVectorGetX(det))||fabs(XMVectorGetX(det))<1e-6f)return false;
        XMStoreFloat4x4(&rest[i],bind);pose[i]=rest[i];
    }
    auto find=[&](const char*name)->size_t{for(size_t i=0;i<count;++i)if(rig->names[i]==name)return i;return count;};
    auto position=[&](size_t joint){const auto&m=pose[joint];return XMVectorSet(m._41,m._42,m._43,0);};
    auto rotate_joint=[&](size_t joint,FXMMATRIX rotation)->bool {
        if(joint==count)return false;
        auto&world=pose[joint];
        XMMATRIX transform=XMMatrixTranslation(-world._41,-world._42,-world._43)*
            rotation*
            XMMatrixTranslation(world._41,world._42,world._43);
        for(size_t i=joint;i<count;++i) {
            size_t parent=i;while(parent!=joint&&rig->parents[parent]!=0xffff)parent=rig->parents[parent];
            if(parent==joint)XMStoreFloat4x4(&pose[i],XMLoadFloat4x4(&pose[i])*transform);
        }
        return true;
    };
    auto rotate=[&](const char*name,float x,float z){return rotate_joint(find(name),
        XMMatrixRotationX(XMConvertToRadians(x))*XMMatrixRotationZ(XMConvertToRadians(z)));};
    auto align=[&](size_t joint,FXMVECTOR from,FXMVECTOR to)->bool {
        if(XMVectorGetX(XMVector3LengthSq(from))<1e-6f||XMVectorGetX(XMVector3LengthSq(to))<1e-6f)return false;
        XMVECTOR a=XMVector3Normalize(from),b=XMVector3Normalize(to);
        float dot=std::max(-1.f,std::min(1.f,XMVectorGetX(XMVector3Dot(a,b))));
        if(dot>.99999f)return true;
        XMVECTOR axis=XMVector3Cross(a,b);
        if(dot<-.99999f)axis=XMVector3Cross(a,fabs(XMVectorGetY(a))<.9f?XMVectorSet(0,1,0,0):XMVectorSet(1,0,0,0));
        return rotate_joint(joint,XMMatrixRotationAxis(axis,acosf(dot)));
    };
    const bool seated_player=(style->info.modes&PoseSeatedPlayer)!=0;
    const bool individual_player=(style->info.modes&PoseIndividual)!=0;
    const bool neutral_rest=individual_player&&pose_id==101;
    float seated_floor=0;
    if(seated_player) {
        /* Dedicated athlete rig recipe. Do not borrow the coach's 31-bone
         * indices or alter any standing/photo pose. Grounding below lowers
         * the pelvis by the native thigh length without stretching bones. */
        size_t lf=find("LeftFoot"),rf=find("RightFoot");
        if(lf==count||rf==count)return false;
        for(const char*side:{"Left","Right"}) {
            std::string prefix=side;
            if(!rotate((prefix+"UpLeg").c_str(),-90,0)||
                !rotate((prefix+"Leg").c_str(),90,0))return false;
        }
        seated_floor=(pose[lf]._42-rest[lf]._42+pose[rf]._42-rest[rf]._42)*.5f+model.bind_feet;
    }
    /* Photo stance: shallow knee flexion and a forward-leaning torso. Positive
     * Z is the player's front. All accessory and hair descendants follow the
     * same native 400-bone rig; nothing is moved as an independent mesh. */
    if(crouching) {
        bool kneeling=style->front_arms==OneKneeArms;
        if(!rotate("LeftUpLeg",style->thigh_bend,style->leg_spread)||!rotate("RightUpLeg",kneeling?10.f:style->thigh_bend,-style->leg_spread)||
            !rotate("LeftLeg",style->knee_bend,0)||!rotate("RightLeg",kneeling?108.f:style->knee_bend,0)||
            !rotate("LeftFoot",style->foot_bend,-style->leg_spread)||!rotate("RightFoot",kneeling?-108.f:style->foot_bend,style->leg_spread)||
            !rotate("Spine",style->torso_lean,0)||!rotate("Head",-style->torso_lean*.80f,0))return false;
    }
    {
        /* Two-bone IK positions the wrists on the upper thighs. Fingers point
         * down toward the knees, instead of leaving the bind-pose palms up.
         * Lengths come from FIFA's skeleton, not a club/player-specific offset. */
        for(bool left:{true,false}) {
            const std::string prefix=left?"Left":"Right";
            bool linked=contacts&&(left?contacts->left:contacts->right);
            ArmStyle arm_style=crouching?style->front_arms:style->individual_arms;
            if(!left&&(arm_style==PortraitHipArm||arm_style==ThumbsUpArm||arm_style==SaluteArm||arm_style==WaveArm||arm_style==MediaBadgeArm)) {
                const bool gesture_support=individual_player&&
                    ((pose_id==105&&arm_style==ThumbsUpArm)||
                     (pose_id==108&&arm_style==SaluteArm)||
                     (pose_id==109&&arm_style==WaveArm));
                arm_style=gesture_support?GestureRestArm:PortraitArms;
            }
            /* The raised celebration poses use the player's right arm
             * (screen-left in the reference); keep the other arm relaxed. */
            if(left&&(arm_style==RaisedFistArm||arm_style==PointUpArm))arm_style=GestureRestArm;
            const bool photo_crossed=!linked&&arm_style==CrossedArms;
            const bool portrait_arm=arm_style>=PortraitArms;
            const bool hip_support=arm_style==PortraitHipArm||arm_style==PortraitHipsArms;
            const bool thumbs_up=arm_style==ThumbsUpArm;
            const bool raised_fist=arm_style==RaisedFistArm;
            const bool point_up=arm_style==PointUpArm;
            const bool support_fist=individual_player&&pose_id==113&&left;
            bool knee_support=crouching&&!linked&&(arm_style==TeamPhotoArms||(arm_style==OneKneeArms&&left));
            bool side_arm=!linked&&((!crouching&&arm_style==TeamPhotoArms)||(arm_style==OneKneeArms&&!left));
            if(side_arm) {
                if(!rotate((prefix+"Arm").c_str(),0,left?-58.f:58.f))return false;
                continue;
            }
            size_t shoulder=find((prefix+"Arm").c_str()),elbow=find((prefix+"ForeArm").c_str()),hand=find((prefix+"Hand").c_str());
            size_t hip=find((prefix+"UpLeg").c_str()),knee=find((prefix+"Leg").c_str());
            size_t middle=find((prefix+"HandMiddleEnd").c_str()),index=find((prefix+"HandIndex1").c_str()),pinky=find((prefix+"HandPinky1").c_str());
            if(shoulder==count||elbow==count||hand==count||hip==count||knee==count||middle==count||index==count||pinky==count)return false;
            /* Keep the native clavicle/neck seam intact. Anatomical rotation
             * is distributed through the humerus helpers below instead of
             * tugging the custom head mesh through a different collar seam. */
            if(individual_player&&find((prefix+"Shoulder").c_str())==count)return false;
            XMVECTOR s=position(shoulder),e=position(elbow),w=position(hand);
            float upper=XMVectorGetX(XMVector3Length(e-s)),lower=XMVectorGetX(XMVector3Length(w-e));
            if(upper<1||lower<1)return false;
            XMVECTOR thigh=position(knee)-position(hip);
            /* Lift wrists slightly and clear the front of the shorts. Fingers
             * still follow the thigh toward the knee; do not bury the palm in
             * the fabric when body height or the shirt fit changes. */
            /* Wrist above the knee, palm following the front of the thigh.
             * Ratio is relative to this rig's leg length; avoid waist-level
             * splayed hands and a deep squat on short/tall players. */
            const float thigh_length=XMVectorGetX(XMVector3Length(thigh));
            XMVECTOR target=position(hip)+thigh*style->wrist_ratio+
                XMVectorSet(0,thigh_length*style->wrist_lift,thigh_length*style->wrist_clearance,0);
            if(arm_style==BackArms)target=position(hip)+XMVectorSet(left?-6.f:6.f,-3,-15,0);
            if(arm_style==PortraitArms)target=s+XMVectorSet(left?upper*.1f:-upper*.1f,-(upper+lower)*.97f,upper*.12f,0);
            if(arm_style==GestureRestArm)target=s+XMVectorSet(left?upper*.18f:-upper*.18f,-(upper+lower)*.965f,upper*.10f,0);
            if(arm_style==PortraitBackArms) {
                size_t pelvis=find("Hips");if(pelvis==count)return false;
                target=position(pelvis)+XMVectorSet(left?upper*.1f:-upper*.1f,upper*.10f,-upper*.55f,0);
            }
            if(hip_support)target=position(hip)+XMVectorSet(left?upper*.35f:-upper*.35f,upper*.40f,upper*.55f,0);
            if(thumbs_up)target=s+XMVectorSet(left?-upper*.25f:upper*.25f,-upper*.35f,upper*.88f,0);
            if(arm_style==SaluteArm){size_t head=find("Head");if(head==count)return false;target=position(head)+XMVectorSet(left?19.f:-19.f,10,10,0);}
            if(arm_style==WaveArm)target=s+XMVectorSet(left?upper*.65f:-upper*.65f,upper*.12f,upper*.8f,0);
            if(arm_style==PortraitFrontHands)target=position(hip)+XMVectorSet(left?-7.f:7.f,upper*.40f,upper*.70f,0);
            if(seated_player) {
                target=XMVectorSet((left?11.f:-11.f)/model.bind_scale,
                    93.f/model.bind_scale+seated_floor,53.f/model.bind_scale,0);
                if(pose_id==302&&!left)target=s+XMVectorSet(-upper*.45f,-upper*.05f,upper*1.05f,0);
            }
            if(arm_style==MediaPointArm)target=s+XMVectorSet(left?upper*.65f:-upper*.65f,upper*.12f,upper*.8f,0);
            if(arm_style==MediaBadgeArm)target=s+XMVectorSet(-upper*.25f,-upper*.45f,upper*.72f,0);
            if(photo_crossed) {
                size_t opposite=find(left?"RightArm":"LeftArm");if(opposite==count)return false;
                /* Cross the FOREARMS, not upright hands beside the shoulders.
                 * Wrists stop near the opposite side of the chest; the fingers
                 * finish the support on/under the upper arm. A staggered depth
                 * separates the crossing limbs, including goalkeeper gloves.
                 * Scale from native shoulder span and humerus length, never
                 * player IDs, fixed heights or translated/stretchable bones. */
                if(pose_id==107) {
                    /* In the profile variant the wrists finish nearer the
                     * opposite upper arms, with a small vertical stagger so
                     * the hands read as resting on the crossed sleeves. */
                    target=s+(position(opposite)-s)*.75f+
                        XMVectorSet(0,-upper*(left?.64f:.80f),upper*(left?.50f:.66f),0);
                } else target=s+(position(opposite)-s)*.67f+
                    XMVectorSet(0,-upper*(left?.75f:.93f),upper*(left?.46f:.64f),0);
            }
            if(individual_player) {
                /* All targets use native limb lengths. Keep hands clear of
                 * the trunk and keep a gentle bend in the resting arm. */
                const float side=left?1.f:-1.f;
                if(arm_style==PortraitArms)target=s+XMVectorSet(side*upper*.13f,-(upper+lower)*.955f,upper*.16f,0);
                if(arm_style==GestureRestArm)target=s+XMVectorSet(side*upper*.18f,-(upper+lower)*.965f,upper*.10f,0);
                /* A neutral stance is not a bent-arm presentation gesture.
                 * Keep the hand below its own shoulder and only a small flex;
                 * large IK hinge rolls twist the relaxed sleeve unnaturally. */
                if(neutral_rest)target=s+XMVectorSet(side*upper*.26f,-(upper+lower)*.98f,upper*.10f,0);
                if(arm_style==PortraitBackArms)target=position(find("Hips"))+XMVectorSet(side*upper*.18f,upper*.16f,-upper*.63f,0);
                if(hip_support) {
                    const float waist_lift=pose_id==106?.30f:.42f;
                    const float waist_clearance=pose_id==106?.40f:.47f;
                    target=position(hip)+XMVectorSet(side*upper*.40f,upper*waist_lift,upper*waist_clearance,0);
                }
                if(arm_style==PortraitFrontHands) {
                    if(pose_id==110) {
                        /* Stack the hands at the lower abdomen instead of
                         * intersecting them wrist-to-wrist. Keep a small
                         * height and depth offset so one palm visibly rests
                         * over the other from the front and three-quarter views. */
                        target=position(hip)+XMVectorSet(-side*upper*.22f,
                            upper*(left?.48f:.20f),upper*(left?.84f:.72f),0);
                    } else target=position(hip)+XMVectorSet(-side*upper*.22f,upper*.30f,upper*.78f,0);
                }
                if(arm_style==SaluteArm) {
                    /* Put the wrist just outside and below the temple. The
                     * fingertips then travel diagonally inward/up, instead
                     * of laying flat across the forehead like a sun visor. */
                    size_t head=find("Head");if(head==count)return false;
                    target=position(head)+XMVectorSet(side*upper*.75f,upper*.05f,upper*.22f,0);
                }
                if(raised_fist||point_up)
                    /* Reference: bend the arm above the shoulder, not out
                     * sideways. Keep the wrist close to the head's vertical
                     * line so the elbow reads as a natural raised-arm hinge. */
                    target=s+XMVectorSet(side*upper*.04f,upper*(raised_fist?1.30f:1.22f),upper*.12f,0);
                if(arm_style==WaveArm||arm_style==MediaPointArm)target=s+XMVectorSet(side*upper*.78f,upper*.25f,upper*.62f,0);
                if(photo_crossed)target+=XMVectorSet(0,-upper*.04f,upper*.12f,0);
            }
            if(linked) {
                const Vec3&at=left?contacts->left_target:contacts->right_target;
                if(!std::isfinite(at.x)||!std::isfinite(at.y)||!std::isfinite(at.z))return false;
                target=XMVectorSet(at.x/model.bind_scale,(at.y+contacts->floor_cm)/model.bind_scale,at.z/model.bind_scale,0);
            }
            const XMVECTOR support_target=target;
            XMVECTOR direction=target-s;
            float distance=XMVectorGetX(XMVector3Length(direction));if(distance<1e-4f)return false;
            direction=XMVector3Normalize(direction);
            float reach=upper+lower-.1f;
            /* Keep a gentle 28-degree elbow flex on the knee supports.
             * This is the two-bone reach from the actual upper/forearm
             * lengths, not a forced translation or stretched limb. */
            if(knee_support)reach=sqrtf(upper*upper+lower*lower+
                2*upper*lower*cosf(XMConvertToRadians(28.f)));
            distance=std::max(fabsf(upper-lower)+.1f,std::min(reach,distance));target=s+direction*distance;
            XMVECTOR pole=linked?XMVectorSet(0,-.15f,-1,0):XMVectorSet(left?.8f:-.8f,0,.6f,0);
            if(knee_support)pole=XMVectorSet(left?.40f:-.40f,0,.85f,0);
            if(arm_style==BackArms)pole=XMVectorSet(left?1.f:-1.f,0,-1,0);
            if(photo_crossed)pole=XMVectorSet(left?1.f:-1.f,-1.f,.1f,0);
            if(arm_style==PortraitArms)pole=XMVectorSet(left?.5f:-.5f,-.15f,.85f,0);
            if(arm_style==GestureRestArm)pole=XMVectorSet(left?.20f:-.20f,-.08f,-1.f,0);
            if(arm_style==PortraitBackArms)pole=XMVectorSet(left?1.f:-1.f,-.3f,-1.f,0);
            if(hip_support)pole=XMVectorSet(left?1.f:-1.f,.2f,.15f,0);
            if(thumbs_up)pole=XMVectorSet(left?.25f:-.25f,-1.f,.3f,0);
            if(seated_player)pole=XMVectorSet(left?1.f:-1.f,-1,.15f,0);
            if(individual_player) {
                const float side=left?1.f:-1.f;
                /* A relaxed human elbow points BACK, with the wrist slightly
                 * forward. A positive-Z pole folds the resting arm the wrong
                 * way even if its frontal silhouette initially looks fine. */
                if(arm_style==PortraitArms)pole=XMVectorSet(side*.55f,-.10f,-.9f,0);
                if(arm_style==GestureRestArm)pole=XMVectorSet(side*.20f,-.08f,-1.f,0);
                if(neutral_rest)pole=XMVectorSet(side*.12f,-.08f,-1.f,0);
                if(arm_style==PortraitBackArms)pole=XMVectorSet(side*.85f,-.1f,-.6f,0);
                if(hip_support)pole=XMVectorSet(side,0,-.20f,0);
                if(photo_crossed)pole=XMVectorSet(side*.85f,-1.f,.1f,0);
                if(raised_fist||point_up)pole=XMVectorSet(side*.35f,-.18f,.24f,0);
                if(arm_style==SaluteArm||arm_style==WaveArm||arm_style==MediaPointArm)pole=XMVectorSet(side*.85f,-1.f,.12f,0);
                if(arm_style==PortraitFrontHands||arm_style==MediaBadgeArm)pole=XMVectorSet(side*.6f,-1.f,.2f,0);
            }
            pole=pole-direction*XMVectorGetX(XMVector3Dot(pole,direction));
            if(XMVectorGetX(XMVector3LengthSq(pole))<1e-6f) {
                /* A near-collinear pole must not produce a NaN pose. */
                pole=XMVector3Cross(direction,fabsf(XMVectorGetY(direction))<.9f?XMVectorSet(0,1,0,0):XMVectorSet(0,0,1,0));
            }
            pole=XMVector3Normalize(pole);
            float along=(upper*upper-lower*lower+distance*distance)/(2*distance);
            float outward=sqrtf(std::max(0.f,upper*upper-along*along));
            XMVECTOR desired_elbow=s+direction*along+pole*outward;
            if(!align(shoulder,e-s,desired_elbow-s))return false;
            if(individual_player) {
                /* Swing alone positions an elbow, but does NOT align its
                 * hinge. Orient the humerus to the IK bend plane first, then
                 * flex the forearm. This avoids an oblique elbow / collapsing
                 * sleeve when viewed from the side or back. */
                XMVECTOR upper_axis=XMVector3Normalize(position(elbow)-s);
                XMVECTOR current=position(hand)-position(elbow),wanted=target-position(elbow);
                current-=upper_axis*XMVectorGetX(XMVector3Dot(current,upper_axis));
                wanted-=upper_axis*XMVectorGetX(XMVector3Dot(wanted,upper_axis));
                if(XMVectorGetX(XMVector3LengthSq(current))<1e-6f||XMVectorGetX(XMVector3LengthSq(wanted))<1e-6f)return false;
                current=XMVector3Normalize(current);wanted=XMVector3Normalize(wanted);
                float twist=atan2f(XMVectorGetX(XMVector3Dot(upper_axis,XMVector3Cross(current,wanted))),XMVectorGetX(XMVector3Dot(current,wanted)));
                if(neutral_rest)twist=std::clamp(twist,-XMConvertToRadians(25.f),XMConvertToRadians(25.f));
                if(!rotate_joint(shoulder,XMMatrixRotationAxis(upper_axis,twist)))return false;
                const float amount[]={.25f,.65f,1.f};
                for(int helper=0;helper<3;++helper) {
                    auto correction=XMMatrixRotationAxis(upper_axis,-twist*(1-amount[helper]));
                    std::string twist_name="RM_"+prefix+"ArmTwist"+std::to_string(helper+1);
                    std::string sleeve_name="RM_"+prefix+"Arm_Sleeve"+std::to_string(helper+1);
                    if(!rotate_joint(find(twist_name.c_str()),correction)||!rotate_joint(find(sleeve_name.c_str()),correction))return false;
                }
            }
            const XMMATRIX forearm_before=XMLoadFloat4x4(&pose[elbow]);
            if(!align(elbow,position(hand)-position(elbow),target-position(elbow)))return false;
            const XMMATRIX elbow_bend_delta=XMMatrixInverse(nullptr,forearm_before)*XMLoadFloat4x4(&pose[elbow]);
            if(knee_support)support_error[left?0:1]=XMVectorGetX(XMVector3Length(position(hand)-support_target))*model.bind_scale;
            XMVECTOR fingers=linked?XMVectorSet(0,-1,.15f,0):thigh;
            if(arm_style==BackArms)fingers=XMVectorSet(left?-1.f:1.f,-.6f,0,0);
            if(arm_style==PortraitArms)fingers=XMVector3Normalize(position(hand)-position(elbow))*.6f+XMVectorSet(0,-.4f,-.03f,0);
            if(arm_style==GestureRestArm)fingers=XMVector3Normalize(position(hand)-position(elbow))*.92f+XMVectorSet(0,-.08f,0,0);
            if(neutral_rest)fingers=XMVector3Normalize(position(hand)-position(elbow))*.92f+XMVectorSet(0,-.08f,0,0);
            if(arm_style==PortraitBackArms)fingers=XMVectorSet(left?-.65f:.65f,-.75f,.05f,0);
            if(hip_support)fingers=XMVectorSet(left?-1.f:1.f,-.25f,.10f,0);
            if(thumbs_up)fingers=XMVectorSet(left?-.2f:.2f,.8f,.5f,0);
            if(point_up)fingers=XMVectorSet(0,1,0,0);
            if(raised_fist||support_fist)fingers=XMVector3Normalize(position(hand)-position(elbow));
                if(arm_style==SaluteArm)fingers=XMVectorSet(left?-.78f:.78f,.62f,.05f,0);
            if(arm_style==WaveArm)fingers=XMVectorSet(left?-.15f:.15f,1.f,0,0);
            if(arm_style==PortraitFrontHands)fingers=XMVectorSet(left?-1.f:1.f,-.10f,0,0);
            if(seated_player)fingers=XMVectorSet(left?-.08f:.08f,-.04f,1,0);
            if(arm_style==MediaPointArm)fingers=XMVectorSet(left?-.05f:.05f,1,0,0);
            if(arm_style==MediaBadgeArm)fingers=XMVectorSet(-.35f,.8f,-.05f,0);
            if(photo_crossed) {
                XMVECTOR forearm_axis=XMVector3Normalize(position(hand)-position(elbow));
                fingers=forearm_axis*.55f+XMVector3Normalize(XMVectorSet(left?-1.f:1.f,.28f,-.22f,0))*.45f;
            }
            if(knee_support) {
                XMVECTOR forearm_axis=XMVector3Normalize(position(hand)-position(elbow));
                fingers=forearm_axis*.55f+XMVector3Normalize(thigh)*.45f;
            }
            const bool gesture_hand_aligned=individual_player&&
                (thumbs_up||raised_fist||support_fist||point_up||arm_style==WaveArm||arm_style==GestureRestArm||arm_style==SaluteArm);
            if(gesture_hand_aligned&&!align(hand,position(middle)-position(hand),fingers))return false;
            bool forearm_roll=knee_support||photo_crossed||portrait_arm||thumbs_up||
                (individual_player&&(arm_style==WaveArm||arm_style==SaluteArm));
            if(forearm_roll) {
                XMVECTOR forearm_axis=XMVector3Normalize(position(hand)-position(elbow));
                /* Palm pronation belongs to the forearm, not a 90-degree
                 * twist at the wrist. Roll its native descendants together
                 * so the skin remains continuous at the cuff. */
                XMVECTOR palm=XMVector3Cross(position(index)-position(hand),position(pinky)-position(hand));
                palm=XMVector3Normalize(palm-forearm_axis*XMVectorGetX(XMVector3Dot(palm,forearm_axis)));
                XMVECTOR facing=XMVectorSet(0,0,left?1.f:-1.f,0);
                if(raised_fist)facing=XMVectorSet(left?.32f:-.32f,0,-1.f,0);
                if(point_up||support_fist)facing=XMVectorSet(left?.42f:-.42f,0,1.f,0);
                if(arm_style==PortraitArms)facing=XMVectorSet(left?1.f:-1.f,0,0,0);
                if(arm_style==SaluteArm)facing=XMVectorSet(left?.55f:-.55f,-.30f,.78f,0);
                /* FIFA's mirrored finger-root ordering changes the palm
                 * cross-product convention. In this relaxed stance BOTH
                 * reference normals use +X; using -X on RightHand turns its
                 * thumb behind the wrist despite a convincing front view. */
                if(neutral_rest)facing=XMVectorSet(1,0,0,0);
                if(arm_style==GestureRestArm)facing=XMVectorSet(1,0,0,0);
                if(arm_style==PortraitBackArms)facing=XMVectorSet(0,0,left?-1.f:1.f,0);
                facing=XMVector3Normalize(facing-forearm_axis*XMVectorGetX(XMVector3Dot(facing,forearm_axis)));
                float roll=atan2f(XMVectorGetX(XMVector3Dot(forearm_axis,XMVector3Cross(palm,facing))),XMVectorGetX(XMVector3Dot(palm,facing)));
                if(!rotate_joint(elbow,XMMatrixRotationAxis(forearm_axis,roll)))return false;
                if(style->info.modes&(PoseIndividual|PoseSeatedPlayer)) {
                    /* FIFA skins the forearm with three native twist helpers.
                     * Distribute pronation from the elbow towards the wrist;
                     * rotating all helpers by the full amount collapses the
                     * proximal skin into a candy-wrapper seam. Hand/gloves
                     * retain the complete wrist-end roll. */
                    const float fraction[]={.25f,.60f,.90f};
                    for(int twist=0;twist<3;++twist) {
                        std::string name="RM_"+prefix+"ForeArmTwist"+std::to_string(twist+1);
                        if(!rotate_joint(find(name.c_str()),XMMatrixRotationAxis(forearm_axis,-roll*(1-fraction[twist]))))return false;
                    }
                }
            }
            if(!gesture_hand_aligned&&!align(hand,position(middle)-position(hand),fingers))return false;
            XMVECTOR axis=XMVector3Normalize(fingers);
            XMVECTOR normal=XMVector3Cross(position(index)-position(hand),position(pinky)-position(hand));
            normal=XMVector3Normalize(normal-axis*XMVectorGetX(XMVector3Dot(normal,axis)));
            XMVECTOR desired=XMVectorSet(0,0,left?1.f:-1.f,0);
            desired=XMVector3Normalize(desired-axis*XMVectorGetX(XMVector3Dot(desired,axis)));
            float angle=atan2f(XMVectorGetX(XMVector3Dot(axis,XMVector3Cross(normal,desired))),XMVectorGetX(XMVector3Dot(normal,desired)));
            if(!forearm_roll)if(!rotate_joint(hand,XMMatrixRotationAxis(axis,angle)))return false;
            if(forearm_roll) {
                /* The elbow skin helper is a sibling of ForeArm, not its
                 * descendant. Follow half the bend, but NOT the pronation;
                 * adding that roll here would swell/twist the elbow skin.
                 * Applied to knee supports and the portrait arm solver. */
                XMVECTOR half=XMQuaternionSlerp(XMQuaternionIdentity(),XMQuaternionRotationMatrix(elbow_bend_delta),.5f);
                size_t helper=find(("RM_"+prefix+"Elbow").c_str());
                if(individual_player) {
                    if(helper==count)return false;
                    /* This helper is OFFSET behind the elbow. Bend around
                     * the real hinge, not around the skin helper's own centre,
                     * so the joint retains volume on both sides of the arm. */
                    auto hinge=position(elbow);
                    auto bend=XMMatrixTranslationFromVector(-hinge)*XMMatrixRotationQuaternion(half)*XMMatrixTranslationFromVector(hinge);
                    for(size_t i=helper;i<count;++i) {
                        size_t parent=i;while(parent!=helper&&rig->parents[parent]!=0xffff)parent=rig->parents[parent];
                        if(parent==helper)XMStoreFloat4x4(&pose[i],XMLoadFloat4x4(&pose[i])*bend);
                    }
                    if(neutral_rest){
                        /* Reducing the humerus roll must not turn its sibling
                         * elbow-volume helper inward. Keep that small skin
                         * offset behind the hinge; its length stays native. */
                        auto from=XMVector3Normalize(position(helper)-hinge);
                        auto to=XMVector3Normalize(XMVectorSet(left?.18f:-.18f,0,-1,0));
                        float dot=std::clamp(XMVectorGetX(XMVector3Dot(from,to)),-1.f,1.f);
                        auto axis=XMVector3Cross(from,to);
                        if(dot<.99999f&&XMVectorGetX(XMVector3LengthSq(axis))>1e-6f){
                            auto turn=XMMatrixTranslationFromVector(-hinge)*XMMatrixRotationAxis(axis,acosf(dot))*XMMatrixTranslationFromVector(hinge);
                            for(size_t i=helper;i<count;++i){size_t parent=i;
                                while(parent!=helper&&rig->parents[parent]!=0xffff)parent=rig->parents[parent];
                                if(parent==helper)XMStoreFloat4x4(&pose[i],XMLoadFloat4x4(&pose[i])*turn);
                            }
                        }
                    }
                } else if(!rotate_joint(helper,XMMatrixRotationQuaternion(half)))return false;
            }
            if(!linked) {
                /* Relax and gather the fingers instead of preserving the
                 * rigid, widely spread bind-pose hand. All rotations affect
                 * the native finger descendants, not detached geometry. */
                XMVECTOR curl_axis=XMVector3Normalize(XMVector3Cross(axis,XMVectorSet(0,0,-1,0)));
                for(const char*finger:{"Index","Middle","Ring","Pinky"}) {
                    const std::string name=prefix+"Hand"+finger;
                    size_t first=find((name+"1").c_str()),second=find((name+"2").c_str()),third=find((name+"3").c_str());
                    if(first==count||second==count||third==count)return false;
                    XMVECTOR segment=position(second)-position(first);
                    if(individual_player) {
                        size_t end=find((name+"End").c_str());if(end==count)return false;
                        const bool pointing=(arm_style==MediaPointArm||point_up)&&!strcmp(finger,"Index");
                        const bool fist=thumbs_up||raised_fist||support_fist||
                            ((arm_style==MediaPointArm||point_up)&&!pointing);
                        /* Keep each proximal finger's own natural splay from
                         * the hand mesh. For the pointing gesture, straighten
                         * ONLY the index; forcing all four MCPs onto one axis
                         * stacks the fingers and makes a claw-like silhouette.
                         * Then reset the native knuckle bends and curl the
                         * other digits around the palm on their mirrored local
                         * Y hinges. */
                        if(((pointing||!fist)&&!align(first,segment,axis))||
                            !align(second,position(third)-position(second),position(second)-position(first))||
                            !align(third,position(end)-position(third),position(third)-position(second)))return false;
                        if(fist&&!pointing&&!align(first,segment,XMVector3Normalize(segment*.72f+axis*.28f)))return false;
                        float mcp=fist?(raised_fist||support_fist?72.f:point_up?58.f:48.f):pointing?0.f:6.f;
                        const bool relaxed_arm=arm_style==PortraitArms||arm_style==GestureRestArm;
                        float pip=fist?(raised_fist||support_fist?96.f:point_up?82.f:78.f):pointing?0.f:relaxed_arm?18.f:style->finger_curl;
                        float dip=fist?(raised_fist||support_fist?60.f:point_up?46.f:35.f):pointing?0.f:relaxed_arm?8.f:style->fingertip_curl;
                        auto flex=[&](size_t joint,float degrees) {
                            const auto&m=pose[joint];
                            XMVECTOR hinge=XMVectorSet(m._21,m._22,m._23,0)*(left?-1.f:1.f);
                            return rotate_joint(joint,XMMatrixRotationAxis(hinge,XMConvertToRadians(degrees)));
                        };
                        if(!flex(first,mcp)||!flex(second,pip)||!flex(third,dip))return false;
                        continue;
                    }
                    float curl=photo_crossed?28.f:arm_style==PortraitArms?22.f:style->finger_curl;
                    float tip_curl=photo_crossed?18.f:arm_style==PortraitArms?12.f:style->fingertip_curl;
                    if(arm_style==MediaPointArm&&!strcmp(finger,"Index"))curl=tip_curl=0;
                    if(!align(first,segment,XMVector3Normalize(segment)*.35f+axis*.65f)||
                        !rotate_joint(second,XMMatrixRotationAxis(curl_axis,XMConvertToRadians(curl)))||
                        !rotate_joint(third,XMMatrixRotationAxis(curl_axis,XMConvertToRadians(tip_curl))))return false;
                    if(arm_style==MediaPointArm&&strcmp(finger,"Index")&&!rotate_joint(first,XMMatrixRotationAxis(curl_axis,XMConvertToRadians(26.f))))return false;
                    if(thumbs_up&&!rotate_joint(first,XMMatrixRotationAxis(curl_axis,XMConvertToRadians(26.f))))return false;
                }
                if(style->info.modes&(PoseIndividual|PoseSeatedPlayer)) {
                    const std::string name=prefix+"HandThumb";
                    size_t first=find((name+"1").c_str()),second=find((name+"2").c_str()),third=find((name+"3").c_str()),end=find((name+"End").c_str());
                    if(first==count||second==count||third==count||end==count)return false;
                    XMVECTOR thumb=position(end)-position(first);
                    /* The gesture uses the native thumb, not a separate mesh.
                     * Other portraits gently gather it without making a fist. */
                    XMVECTOR thumb_target=thumbs_up?XMVectorSet(0,1,.03f,0):
                        XMVector3Normalize(thumb)*.8f+axis*.2f;
                    if(raised_fist||support_fist||point_up) {
                        /* Fold the thumb across the palm toward the index
                         * knuckle. A fixed world-space thumb direction makes
                         * it stick out sideways when the wrist is rotated;
                         * derive this vector from the posed hand itself. */
                        XMVECTOR across=position(index)-position(first);
                        XMVECTOR palm_normal=XMVector3Cross(position(index)-position(hand),
                            position(pinky)-position(hand));
                        palm_normal=XMVector3Normalize(palm_normal);
                        const float camera_side=XMVectorGetX(XMVector3Dot(palm_normal,XMVectorSet(0,0,1,0)))<0?-1.f:1.f;
                        thumb_target=XMVector3Normalize(across*.72f-axis*.34f+palm_normal*(camera_side*.08f));
                    }
                    if(!align(first,thumb,thumb_target))return false;
                    const float thumb_base_curl=raised_fist||support_fist?16.f:point_up?18.f:0.f;
                    const float thumb_middle_curl=raised_fist||support_fist?48.f:point_up?52.f:12.f;
                    const float thumb_tip_curl=raised_fist||support_fist?36.f:point_up?38.f:7.f;
                    auto flex_thumb=[&](size_t joint,float degrees) {
                        const auto&m=pose[joint];
                        XMVECTOR hinge=XMVectorSet(m._21,m._22,m._23,0)*(left?-1.f:1.f);
                        return rotate_joint(joint,XMMatrixRotationAxis(hinge,XMConvertToRadians(degrees)));
                    };
                    if(!thumbs_up&&(!flex_thumb(first,thumb_base_curl)||
                        !flex_thumb(second,thumb_middle_curl)||
                        !flex_thumb(third,thumb_tip_curl)))return false;
                    if(raised_fist||point_up) {
                        XMVECTOR forearm_axis=XMVector3Normalize(position(hand)-position(elbow));
                        if(!rotate_joint(hand,XMMatrixRotationAxis(forearm_axis,
                            XMConvertToRadians(point_up?4.f:-3.f))))return false;
                    }
                }
            }
        }
    }
    if(style->info.modes&PoseIndividual) {
        const auto&stance=style->portrait;
        /* Subtle knee relaxation and a three-quarter body/head relationship
         * follow the portrait references. Collective recipes never enter this
         * branch, and their first/second rows keep their original geometry. */
        for(const char*side:{"Left","Right"}) {
            std::string prefix=side;
            const bool left=!strcmp(side,"Left");
            const float knee=stance.knee_bend+(left?stance.left_knee_offset:stance.right_knee_offset);
            const float spread=left?stance.leg_spread:-stance.leg_spread;
            if(!rotate((prefix+"UpLeg").c_str(),-knee*.5f,spread)||
                !rotate((prefix+"Leg").c_str(),knee,0)||
                !rotate((prefix+"Foot").c_str(),-knee*.5f,-spread))return false;
        }
        if(stance.torso_roll!=0&&(!rotate("Spine",0,stance.torso_roll)||
            !rotate("Head",0,-stance.torso_roll*.65f)))return false;
        if(!rotate_joint(find("Reference"),XMMatrixRotationY(XMConvertToRadians(stance.body_yaw)))||
            !rotate_joint(find("Neck"),XMMatrixRotationY(XMConvertToRadians(stance.head_yaw*.4f)))||
            !rotate_joint(find("Head"),XMMatrixRotationY(XMConvertToRadians(stance.head_yaw*.6f))))return false;
        if(stance.head_pitch!=0&&!rotate("Head",stance.head_pitch,0))return false;
    }
    for(size_t i=0;i<count;++i)XMStoreFloat4x4(&delta[i],XMMatrixInverse(nullptr,XMLoadFloat4x4(&rest[i]))*XMLoadFloat4x4(&pose[i]));
    /* Validate every influence before touching a vertex. No partial deformation
     * is published when an RX3 uses an unknown rig or malformed weights. */
    for(const auto&p:model.parts) {
        if(!p.skinned)return false;
        for(const auto&v:p.vertices)for(int j=0;j<8;++j)if(v.weights[j]&&v.joints[j]>=count)return false;
    }
    auto parts=model.parts;
    float feet=std::numeric_limits<float>::max();
    for(auto&p:parts)for(auto&v:p.vertices) {
        XMVECTOR input=XMVectorSet(v.position.x/model.bind_scale,v.position.y/model.bind_scale+model.bind_feet,v.position.z/model.bind_scale,1);
        XMVECTOR output=XMVectorZero(),normal=XMVectorZero();unsigned sum=0;
        XMVECTOR original_normal=XMVectorSet(v.normal.x,v.normal.y,v.normal.z,0);
        for(int j=0;j<8;++j)if(v.weights[j]) {
            output=XMVectorAdd(output,XMVectorScale(XMVector3TransformCoord(input,XMLoadFloat4x4(&delta[v.joints[j]])),float(v.weights[j])));
            if(p.native_normals)normal+=XMVector3TransformNormal(original_normal,XMLoadFloat4x4(&delta[v.joints[j]]))*float(v.weights[j]);
            sum+=v.weights[j];
        }
        if(!sum)return false;output=XMVectorScale(output,model.bind_scale/float(sum));
        v.position={XMVectorGetX(output),XMVectorGetY(output),XMVectorGetZ(output)};
        if(p.native_normals) {
            if(XMVectorGetX(XMVector3LengthSq(normal))<1e-6f)return false;normal=XMVector3Normalize(normal);
            v.normal={XMVectorGetX(normal),XMVectorGetY(normal),XMVectorGetZ(normal)};
            if(!std::isfinite(v.normal.x)||!std::isfinite(v.normal.y)||!std::isfinite(v.normal.z))return false;
        }
        if(!std::isfinite(v.position.x)||!std::isfinite(v.position.y)||!std::isfinite(v.position.z))return false;
        if(p.asset.find("/shoe/")!=p.asset.npos)feet=std::min(feet,v.position.y);
    }
    if(!std::isfinite(feet)||feet==std::numeric_limits<float>::max())return false;
    for(auto&p:parts)for(auto&v:p.vertices)v.position.y-=feet;
    auto landmark=[&](const char*name,Vec3&out)->bool {
        size_t joint=find(name);if(joint==count)return false;const auto&p=pose[joint];
        out={p._41*model.bind_scale,p._42*model.bind_scale-feet,p._43*model.bind_scale};return true;
    };
    Vec3 ls,rs,lh,rh,le,re,lhip,rhip,lknee,rknee,lfingers,rfingers;
    if(!landmark("LeftArm",ls)||!landmark("RightArm",rs)||!landmark("LeftHand",lh)||!landmark("RightHand",rh)||
        !landmark("LeftForeArm",le)||!landmark("RightForeArm",re)||
        !landmark("LeftUpLeg",lhip)||!landmark("RightUpLeg",rhip)||
        !landmark("LeftLeg",lknee)||!landmark("RightLeg",rknee)||
        !landmark("LeftHandMiddleEnd",lfingers)||!landmark("RightHandMiddleEnd",rfingers))return false;
    model.left_shoulder=ls;model.right_shoulder=rs;model.left_hand=lh;model.right_hand=rh;model.pose_floor_cm=feet;
    model.left_elbow=le;model.right_elbow=re;
    model.left_hip=lhip;model.right_hip=rhip;model.left_knee=lknee;model.right_knee=rknee;
    model.left_fingers=lfingers;model.right_fingers=rfingers;
    model.left_support_error_cm=support_error[0];model.right_support_error_cm=support_error[1];
    model.parts=std::move(parts);model.presentation_pose=true;model.presentation_pose_id=pose_id;
    model.diagnostic+="\npose_id="+std::to_string(pose_id)+" "+style->info.name;
    model.diagnostic+=seated_player?"\npresentation_pose=mod_seated_player; native athlete rig":crouching?"\npresentation_pose=mod_crouching; native skeleton, custom joint rotations":"\npresentation_pose=mod_standing; native skeleton, custom joint rotations";
    if(contacts)model.diagnostic+="; neighbour contacts left="+std::to_string(contacts->left)+" right="+std::to_string(contacts->right);
    return true;
}
bool apply_coach_pose(Model&model,unsigned id) {
    const auto*style=recipe(id);const auto&rig=model.skeleton;
    if(!style||!(style->info.modes&PoseCoachAny)||!rig||rig->names.size()!=31||rig->parents.size()!=31||rig->inverse_bind.size()!=31||model.parts.empty())return false;
    if(model.presentation_pose)return model.presentation_pose_id==id;
    std::vector<XMFLOAT4X4>rest(31),pose(31),delta(31);
    for(size_t i=0;i<31;++i){if(rig->parents[i]!=0xffff&&rig->parents[i]>=i)return false;
        XMFLOAT4X4 inverse;memcpy(&inverse,rig->inverse_bind[i].data(),64);XMVECTOR det;
        auto m=XMMatrixInverse(&det,XMLoadFloat4x4(&inverse));if(!std::isfinite(XMVectorGetX(det))||fabsf(XMVectorGetX(det))<.0001f)return false;
        XMStoreFloat4x4(&rest[i],m);pose[i]=rest[i];}
    auto point=[&](int i){return XMVectorSet(pose[i]._41,pose[i]._42,pose[i]._43,0);};
    auto rotate=[&](int joint,FXMMATRIX rotation){const auto&m=pose[joint];
        auto matrix=XMMatrixTranslation(-m._41,-m._42,-m._43)*rotation*XMMatrixTranslation(m._41,m._42,m._43);
        for(int i=joint;i<31;++i){int p=i;while(p!=joint&&rig->parents[p]!=0xffff)p=rig->parents[p];
            if(p==joint)XMStoreFloat4x4(&pose[i],XMLoadFloat4x4(&pose[i])*matrix);}};
    auto align=[&](int joint,FXMVECTOR from,FXMVECTOR to){if(XMVectorGetX(XMVector3LengthSq(from))<.0001f||XMVectorGetX(XMVector3LengthSq(to))<.0001f)return false;
        auto a=XMVector3Normalize(from),b=XMVector3Normalize(to);float dot=std::max(-1.f,std::min(1.f,XMVectorGetX(XMVector3Dot(a,b))));
        if(dot<.99999f){auto axis=XMVector3Cross(a,b);if(dot<-.9999f)axis=XMVector3Cross(a,XMVectorSet(0,0,1,0));rotate(joint,XMMatrixRotationAxis(axis,acosf(dot)));}return true;};
    if(style->info.modes&PoseSeatedCoach){
        /* Lower the pelvis by the actual thigh length, rotate each thigh
         * forward, counter-rotate calves. Feet remain grounded naturally. */
        float shift=(pose[3]._42-pose[4]._42+pose[7]._42-pose[8]._42)*.5f;
        rotate(3,XMMatrixRotationX(-XM_PIDIV2));rotate(4,XMMatrixRotationX(XM_PIDIV2));
        rotate(7,XMMatrixRotationX(-XM_PIDIV2));rotate(8,XMMatrixRotationX(XM_PIDIV2));
        for(auto&p:pose)p._42-=shift;
    }
    if(style->coach_pose==CoachPoseArrival){rotate(3,XMMatrixRotationX(XMConvertToRadians(-9.f)));rotate(4,XMMatrixRotationX(XMConvertToRadians(12.f)));
        rotate(7,XMMatrixRotationX(XMConvertToRadians(7.f)));rotate(8,XMMatrixRotationX(XMConvertToRadians(4.f)));}
    for(bool left:{true,false}) {
        int arm=left?17:22,elbow=left?18:23,hand=left?19:24,end=left?20:25;auto s=point(arm);
        float a=XMVectorGetX(XMVector3Length(point(elbow)-s)),b=XMVectorGetX(XMVector3Length(point(hand)-point(elbow)));
        if(a<5||b<5)return false;
        auto target=s+XMVectorSet(left?4.f:-4.f,-(a+b)*.96f,8,0);
        auto pole=XMVectorSet(left?1.f:-1.f,-.1f,1,0);
        if(style->coach_pose==CoachPoseArrival){target=s+XMVectorSet(left?5.f:-5.f,-(a+b)*.94f,left?-7.f:14.f,0);pole=XMVectorSet(left?1.f:-1.f,-.15f,.25f,0);}
        if(style->coach_pose==CoachPoseCrossed){
            /* Rest each hand on the opposite upper arm, with a small vertical
             * stagger so the wrists stack instead of colliding at the sternum. */
            int opposite=left?22:17;
            target=s+(point(opposite)-s)*.68f+
                XMVectorSet(0,-a*(left?.78f:1.0f),a*(left?.60f:.85f),0);
            pole=XMVectorSet(left?1.f:-1.f,-1,.1f,0);
        }
        if(style->coach_pose==CoachPoseHandsBehind){target=point(2)+XMVectorSet(left?7.f:-7.f,12,-15,0);pole=XMVectorSet(left?1.f:-1.f,0,-1,0);}
        if(style->coach_pose==CoachPoseTactical&&!left){
            /* One forearm directs play diagonally outward; keep the elbow bent
             * and the hand around shoulder height rather than reaching at camera. */
            target=s+XMVectorSet(-a*.84f,-a*.40f,(a+b)*.30f,0);
            pole=XMVectorSet(-.34f,-.84f,-.10f,0);
        }
        if(style->coach_pose==CoachPoseHandsOnHips){target=point(2)+XMVectorSet(left?22.f:-22.f,6.f,-2.f,0);pole=XMVectorSet(left?1.f:-1.f,-.25f,-.15f,0);}
        if(style->coach_pose==CoachPoseCalmDown){
            /* Palms settle in front of the upper abdomen. Elbows stay visibly
             * flexed and slightly outside the wrists: a compact, calming cue. */
            target=point(2)+XMVectorSet(left?14.f:-14.f,30.f,22.f,0);
            pole=XMVectorSet(left?1.f:-1.f,-.38f,.10f,0);
        }
        if(style->coach_pose==CoachPoseExplaining){
            /* Open, conversational gesture: hands closer to the body, with a
             * slight height difference so it reads as speech, not a T-pose. */
            target=point(2)+XMVectorSet(left?15.f:-15.f,left?40.f:34.f,24.f,0);
            pole=XMVectorSet(left?1.f:-1.f,-.66f,.16f,0);
        }
        if(style->info.modes&PoseSeatedCoach){target=XMVectorSet(left?9.f:-9.f,93,45,0);pole=XMVectorSet(left?1.f:-1.f,-1,.15f,0);
            if(style->coach_pose==CoachPoseSeatedGesture&&!left)target=s+XMVectorSet(-a*.50f,3,34,0);}
        auto axis=XMVector3Normalize(target-s);float distance=XMVectorGetX(XMVector3Length(target-s));
        distance=std::max(fabsf(a-b)+.05f,std::min(a+b-.1f,distance));target=s+axis*distance;
        float along=(a*a-b*b+distance*distance)/(2*distance),height=sqrtf(std::max(0.f,a*a-along*along));
        auto plane=XMVector3Normalize(pole-axis*XMVectorGetX(XMVector3Dot(pole,axis)));auto e=s+axis*along+plane*height;
        if(!align(arm,point(elbow)-s,e-s)||!align(elbow,point(hand)-point(elbow),target-point(elbow)))return false;
        auto fingers=XMVector3Normalize(point(hand)-point(elbow));
        if(style->coach_pose==CoachPoseDefault||style->coach_pose==CoachPoseArrival)fingers=XMVectorSet(0,-1,.10f,0);
        if(style->coach_pose==CoachPoseHandsBehind)fingers=XMVectorSet(left?-.55f:.55f,-.8f,0,0);
        if(style->coach_pose==CoachPoseCrossed)fingers=XMVectorSet(left?-.82f:.82f,-.30f,.10f,0);
        if(style->coach_pose==CoachPoseTactical&&!left)fingers=XMVectorSet(-.94f,-.08f,.20f,0);
        if(style->coach_pose==CoachPoseHandsOnHips)fingers=XMVectorSet(left?-.4f:.4f,-.9f,.15f,0);
        if(style->coach_pose==CoachPoseCalmDown)fingers=XMVectorSet(0,-.08f,1,0);
        if(style->coach_pose==CoachPoseExplaining)fingers=XMVectorSet(left?-.12f:.12f,.34f,.92f,0);
        if(style->info.modes&PoseSeatedCoach)fingers=XMVectorSet(left?-.1f:.1f,-.08f,1,0);
        if(!align(hand,point(end)-point(hand),fingers))return false;
    }
    for(size_t i=0;i<31;++i)XMStoreFloat4x4(&delta[i],XMMatrixInverse(nullptr,XMLoadFloat4x4(&rest[i]))*XMLoadFloat4x4(&pose[i]));
    auto parts=model.parts;float floor=FLT_MAX;
    for(auto&p:parts){if(!p.skinned)return false;for(auto&v:p.vertices){XMVECTOR output=XMVectorZero(),normal=XMVectorZero();unsigned sum=0;
        auto input=XMVectorSet(v.position.x,v.position.y+model.bind_feet,v.position.z,1);auto n=XMVectorSet(v.normal.x,v.normal.y,v.normal.z,0);
        for(int j=0;j<8;++j)if(v.weights[j]){if(v.joints[j]>=31)return false;auto matrix=XMLoadFloat4x4(&delta[v.joints[j]]);
            output+=XMVector3TransformCoord(input,matrix)*float(v.weights[j]);normal+=XMVector3TransformNormal(n,matrix)*float(v.weights[j]);sum+=v.weights[j];}
        if(!sum)return false;output/=float(sum);normal=XMVector3Normalize(normal);
        v.position={XMVectorGetX(output),XMVectorGetY(output),XMVectorGetZ(output)};
        if(p.native_normals)v.normal={XMVectorGetX(normal),XMVectorGetY(normal),XMVectorGetZ(normal)};
        if(!std::isfinite(v.position.x)||!std::isfinite(v.position.y)||!std::isfinite(v.position.z)||!std::isfinite(v.normal.x)||!std::isfinite(v.normal.y)||!std::isfinite(v.normal.z))return false;
        floor=std::min(floor,v.position.y);}}
    if(!std::isfinite(floor))return false;for(auto&p:parts)for(auto&v:p.vertices)v.position.y-=floor;
    model.parts=std::move(parts);model.presentation_pose=true;model.presentation_pose_id=id;
    model.diagnostic+="\ncoach_pose="+std::to_string(id)+" "+style->info.name+"; own embedded compact SLC skinning";return true;
}
}
