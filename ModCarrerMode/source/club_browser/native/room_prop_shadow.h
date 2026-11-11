#pragma once
#include <unordered_map>
#include "../../common/room_shadow_bridge.h"
#include "native_animation.h"
#include "roster_native_shadow.h"
#include "room_surface_shadow.h"
#include "room_shadow_depth_audit.h"
#include "indoor_scene_profile.h"
#include "gallery_reflection.h"

namespace roompropshadow {
using namespace roomshadow;
inline constexpr unsigned maxInstances=2048,maxMeshes=4096;
struct InstanceKey {
 uint64_t object;unsigned instance;
 bool operator==(const InstanceKey& other)const{return object==other.object&&instance==other.instance;}
};
struct KeyHash {size_t operator()(const InstanceKey& key)const{return size_t(key.object^(uint64_t(key.instance)<<32));}};
struct Cache {
 bool visible=false;unsigned club=0,generation=0;uint64_t revision=0;
 std::unordered_map<InstanceKey,std::vector<Mesh>,KeyHash> instances;
 std::shared_ptr<Frame> latest;size_t meshes=0;
 std::shared_ptr<const std::vector<Mesh>> flattened;uint64_t flatRevision=0;
};
inline std::mutex mutex;inline Cache cache;
inline indoor_profile::Ownership ownership;
inline std::mutex ownershipMutex;inline std::atomic<unsigned> ownerProfile{0};
inline std::atomic<bool> backgroundPending{false};
inline void beforeOverlay(ID3D11DeviceContext* context);
inline std::atomic<unsigned> residentMeshes{0},residentInstances{0},maskBuilds{0},frames{0};
inline std::atomic<unsigned> repeatedPresents{0};
inline std::atomic<unsigned> preUiFrames{0},dedicatedFrames{0},surfaceRejected{0};
inline std::atomic<uint64_t> lifecycle{1};
struct Capture {
 std::shared_ptr<Frame> frame;InstanceKey key{};unsigned club=0,generation=0;
 bool previousStatic=false,ownsCapture=false,previousFilter=false;
 ID3D11DeviceContext* previousPaint=nullptr;
};
inline thread_local std::unique_ptr<Capture> capture;
inline void state(bool visible,unsigned club,unsigned generation){
 std::lock_guard<std::mutex> lock(mutex);
 if(cache.club!=club||cache.generation!=generation||(!visible&&cache.visible)){
  cache={};backgroundPending=false;beforeOverlayDraw=nullptr;residentMeshes=0;residentInstances=0;++lifecycle;
 }
 cache.visible=visible;cache.club=club;cache.generation=generation;
}
inline void scopedState(unsigned owner,bool visible,unsigned club,unsigned generation){
 std::lock_guard<std::mutex> guard(ownershipMutex);
 const auto previous=ownership.owner;if(!ownership.accept(owner,visible))return;
 ownerProfile=ownership.owner;
 if(previous!=ownership.owner)state(false,0,0);
 state(visible,club,generation);
}
inline bool source(Frame& frame,ID3D11DeviceContext* context,const room_shadow_bridge::Submission& packet){
 if(!context||context->GetType()!=D3D11_DEVICE_CONTEXT_IMMEDIATE)return false;
 for(unsigned i=0;i<16;++i)if(!std::isfinite(packet.model[i])||!std::isfinite(packet.viewProjection[i]))return false;
 if(std::abs(packet.model[12]-indoor_profile::originX(packet.reserved))>5000||std::abs(packet.model[13])>2000||std::abs(packet.model[14])>5000)return false;
 frame.flags=packet.reserved;frame.sequence=packet.frame;frame.tick=GetTickCount64();frame.context=context;frame.scenery=true;
 memcpy(frame.model,packet.model,64);memcpy(frame.viewProjection,packet.viewProjection,64);
 return true;
}
inline bool surface(Frame& frame){
 auto* context=frame.context.Get();if(!context)return false;frame.depth.Reset();
 context->OMGetRenderTargets(0,nullptr,frame.depth.GetAddressOf());
 ComPtr<ID3D11DepthStencilState> depth;UINT stencil=0;context->OMGetDepthStencilState(&depth,&stencil);
 if(!frame.depth)return false;
 if(depth)depth->GetDesc(&frame.depthState);
 else {frame.depthState.DepthEnable=TRUE;frame.depthState.DepthFunc=D3D11_COMPARISON_LESS;}
 UINT count=1;context->RSGetViewports(&count,&frame.viewport);
 return count==1&&frame.depthState.DepthEnable&&frame.viewport.Width>0&&frame.viewport.Height>0;
}
inline bool snapshot(Frame& frame,ID3D11DeviceContext* context,const room_shadow_bridge::Submission& packet){return source(frame,context,packet)&&surface(frame);}
inline void begin(const room_shadow_bridge::Submission* packet){
 if(capture||capturing||!packet||packet->size!=sizeof(*packet)||packet->version!=3||!packet->club||
    !packet->generation||!packet->object||packet->instance>=64||!std::atomic_load(&shaderCode))return;
 const unsigned owner=indoor_profile::gallery(packet->reserved)?room_shadow_bridge::TrophyGallery:room_shadow_bridge::DressingRoom;
 if(ownerProfile&&ownerProfile!=owner)return;
 auto* context=static_cast<ID3D11DeviceContext*>(packet->context);
 auto item=std::make_unique<Capture>();item->key={packet->object,packet->instance};item->club=packet->club;item->generation=packet->generation;
 item->frame=std::make_shared<Frame>();if(!source(*item->frame,context,*packet))return;
 bool missing=false;
 {
  std::lock_guard<std::mutex> lock(mutex);
  if(!cache.visible||cache.club!=item->club||cache.generation!=item->generation)return;
  missing=!(packet->reserved&room_shadow_bridge::TextureOnly)&&cache.instances.find(item->key)==cache.instances.end()&&cache.instances.size()<maxInstances&&cache.meshes<maxMeshes;
 }
 if(!clubanim::armVertexObserver(context)||!arm(context))return;
 beforeOverlayDraw=&beforeOverlay;backgroundPending=true;
 item->previousPaint=paintContext;paintContext=context;
 item->previousStatic=clubanim::staticSceneDraw;clubanim::staticSceneDraw=true;
 item->previousFilter=roomfilter::enabled;roomfilter::enabled=true;
 // FIFA binds the prop's depth target with its material, after Begin. The
 // previous draw may be a depth-free APT panel. Capture vertices now, but read
 // the scene target in End, once the native prop has actually been drawn.
 if(missing){capturing=item->frame.get();item->ownsCapture=true;}
 capture=std::move(item);
}
inline void end(bool publish=true){
 if(!capture)return;auto item=std::move(capture);
 if(item->ownsCapture&&capturing==item->frame.get())capturing=nullptr;
 paintContext=item->previousPaint;
 clubanim::staticSceneDraw=item->previousStatic;
 roomfilter::enabled=item->previousFilter;
 if(!publish||!item->frame)return;
 if(!surface(*item->frame)){++surfaceRejected;return;}
 roomaudit::capture(*item->frame,false);
 std::lock_guard<std::mutex> lock(mutex);
 if(!cache.visible||cache.club!=item->club||cache.generation!=item->generation)return;
 cache.latest=item->frame;
 if(item->frame->meshes.empty()||cache.instances.size()>=maxInstances||
    cache.meshes+item->frame->meshes.size()>maxMeshes)return;
 const auto count=item->frame->meshes.size();
 if(cache.instances.emplace(item->key,std::move(item->frame->meshes)).second){
  cache.meshes+=count;++cache.revision;residentMeshes=unsigned(cache.meshes);residentInstances=unsigned(cache.instances.size());
 }
}
inline constexpr unsigned lightCount=unsigned(ceilingSources);
inline std::array<Renderer,lightCount> renderers;
inline uint64_t renderedRevision[lightCount]{},renderedLifecycle=0;
inline uint64_t appliedPaint=0;
inline unsigned nextTile=0;
inline void renderLife(uint64_t life){
 if(renderedLifecycle==life)return;
 // Keep one bounded GPU program/target pool on this device. Renderer::draw
 // invalidates all light contents by lifecycle; recompiling the identical
 // shaders at each hub/card transition only stalls entry into the room.
 for(auto& renderer:renderers)renderer.clear();for(auto& value:renderedRevision)value=0;
 renderedLifecycle=life;nextTile=0;appliedPaint=0;
}
inline Area area(unsigned index){
 const auto& source=room_spotlight_r79::kSources[index];Area result;
 result.center[0]=origin[0]+source.x;result.center[2]=source.z;
 result.halfWidth=result.halfLength=540;result.light[0]=result.light[2]=0;result.light[1]=source.y;
 result.spot=int(index);result.opacity=.48f;result.lift=.8f;return result;
}
// Both career backgrounds and the dedicated room have native APT panels.
// Finish room shadows at the 3D -> UI boundary, before a depth-free draw.
// Never paint over native menus from Present and never change their geometry.
inline void beforeOverlay(ID3D11DeviceContext* context){
 if(!backgroundPending.load()||clubanim::staticSceneDraw)return;
 const auto paint=painted.load();if(paint==appliedPaint)return;
 ComPtr<ID3D11RenderTargetView> target;ComPtr<ID3D11DepthStencilView> depth;context->OMGetRenderTargets(1,&target,&depth);if(!target)return;
 ComPtr<ID3D11DepthStencilState> state;UINT reference=0;context->OMGetDepthStencilState(&state,&reference);
 D3D11_DEPTH_STENCIL_DESC ds{};if(state)state->GetDesc(&ds);
 if(depth&&(!state||ds.DepthEnable))return;
 Frame frame;uint64_t revision=0;
 {std::lock_guard<std::mutex> lock(mutex);
  if(!cache.visible||!cache.latest||cache.instances.empty()||cache.latest->context.Get()!=context||
     GetTickCount64()-cache.latest->tick>250)return;
  frame=*cache.latest;revision=cache.revision;
  if(!cache.flattened||cache.flatRevision!=revision){auto merged=std::make_shared<std::vector<Mesh>>();for(const auto& entry:cache.instances)merged->insert(merged->end(),entry.second.begin(),entry.second.end());cache.flattened=merged;cache.flatRevision=revision;}
  frame.staticMeshes=cache.flattened;
 }
 ComPtr<ID3D11Resource> resource;target->GetResource(&resource);ComPtr<ID3D11Texture2D> texture;if(FAILED(resource.As(&texture)))return;
 D3D11_TEXTURE2D_DESC desc{};texture->GetDesc(&desc);
 if(desc.SampleDesc.Count!=1||desc.Width<unsigned(frame.viewport.TopLeftX+frame.viewport.Width)||desc.Height<unsigned(frame.viewport.TopLeftY+frame.viewport.Height))return;
 const auto life=lifecycle.load();
 renderLife(life);
 roomaudit::capture(frame,true);
 if(roomsurface::renderer.draw(frame,nullptr,target.Get(),desc,revision,life,false)){
  if(indoor_profile::gallery(frame.flags)&&!gallery_reflection::renderer.draw(frame,target.Get(),desc))++gallery_reflection::failures;
  roomaudit::maps(frame,desc);
  appliedPaint=paint;++frames;++preUiFrames;if(!(frame.flags&room_shadow_bridge::Background))++dedicatedFrames;
  backgroundPending=false;beforeOverlayDraw=nullptr;
 }
}
inline bool present(IDXGISwapChain* swap){
 const auto life=lifecycle.load();
 renderLife(life);
 const auto paint=painted.load();Frame frame;uint64_t revision=0;
 {
  std::lock_guard<std::mutex> lock(mutex);
  if(!cache.visible||!cache.latest||cache.instances.empty())return false;
  // A retained image stays already shaded even after the scene becomes idle.
  if(paint==appliedPaint){++repeatedPresents;return true;}
  if(GetTickCount64()-cache.latest->tick>250)return false;
  frame=*cache.latest;revision=cache.revision;
  // Flatten references once per geometry revision, not once per display frame.
  if(!cache.flattened||cache.flatRevision!=revision){
   auto merged=std::make_shared<std::vector<Mesh>>();merged->reserve(cache.meshes);
   for(const auto& entry:cache.instances)merged->insert(merged->end(),entry.second.begin(),entry.second.end());
   cache.flattened=merged;cache.flatRevision=revision;
  }
  frame.staticMeshes=cache.flattened;
 }
 // Present can run again while FIFA keeps the previous 3D image. Blending the
 // shadow twice darkens it cumulatively. Fresh native draws always pass this
 // guard, even if their UI frame number and Windows timestamp are identical.
 ComPtr<ID3D11Texture2D> color;ComPtr<ID3D11Device> device;ComPtr<ID3D11RenderTargetView> target;
 if(FAILED(swap->GetBuffer(0,IID_PPV_ARGS(&color)))||FAILED(swap->GetDevice(IID_PPV_ARGS(&device)))||
    FAILED(device->CreateRenderTargetView(color.Get(),nullptr,&target)))return false;
 D3D11_TEXTURE2D_DESC desc{};color->GetDesc(&desc);
 if(frame.flags&(room_shadow_bridge::Background|room_shadow_bridge::Overlay))return true;
 if(!(frame.flags&room_shadow_bridge::FloorOnly)){
  std::shared_ptr<roomshadow::Frame> actor;if(!indoor_profile::gallery(frame.flags)){std::lock_guard<std::mutex> lock(roomshadow::frameMutex);actor=roomshadow::pending;}
  // The browser draws its UI after this pass. Masking fixed screen bands here
  // cuts real 3D receivers (feet, furniture and ceiling) behind that UI.
  if(roomsurface::renderer.draw(frame,actor.get(),target.Get(),desc,revision,life,false)){
   if(actor){std::lock_guard<std::mutex> lock(roomshadow::frameMutex);if(roomshadow::pending==actor)roomshadow::pending.reset();}
   appliedPaint=paint;++frames;return true;
  }
  ++roomsurface::shadowFailures;
 }

 auto& first=renderers[0];if(!first.initialize(device.Get())||!first.prepareDepth(frame,desc))return false;
 // One real ceiling focus per cached mask. Rebuild at most one per frame;
 // presentation itself must run on EVERY newly painted frame. GetTickCount64 has a coarse
 // clock on Windows, so timestamp dedup previously dropped shadows at high FPS.
 struct StaticBinding {bool previous=clubanim::staticSceneDraw;StaticBinding(){clubanim::staticSceneDraw=true;}~StaticBinding(){clubanim::staticSceneDraw=previous;}} staticBinding;
 bool built=false,depthCopied=false;
 for(unsigned step=0;step<lightCount;++step){
  unsigned index=(nextTile+step)%lightCount;auto& renderer=renderers[index];
  if(!renderer.initialize(device.Get(),&first))continue;
  if(index){renderer.depthCopy=first.depthCopy;renderer.depthView=first.depthView;renderer.sampledDepth=first.sampledDepth;renderer.copyDepth=first.copyDepth;}
  const bool dirty=renderedRevision[index]!=revision;
  if(dirty&&built&&renderedRevision[index]==0)continue;
  const bool rebuild=dirty&&!built;
  if(renderer.draw(frame,target.Get(),desc,area(index),rebuild,!depthCopied)){
   depthCopied=true;if(rebuild){renderedRevision[index]=revision;++maskBuilds;built=true;}
  }
 }
 if(depthCopied){appliedPaint=paint;++frames;}
 nextTile=(nextTile+1)%lightCount;return false;
}
inline void stop(){beforeOverlayDraw=nullptr;backgroundPending=false;end(false);state(false,0,0);ownerProfile=0;ownership={};roomsurface::renderer.clear();gallery_reflection::renderer.clear();}
}
