#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <DirectXPackedVector.h>
#include <cassert>
#include <iostream>
#include "roster_native_shadow.h"
#include "room_prop_shadow.h"
using Microsoft::WRL::ComPtr;
using namespace roomshadow;
static std::vector<unsigned char> pixels(ID3D11Device* device,ID3D11DeviceContext* context,ID3D11Texture2D* texture){
 D3D11_TEXTURE2D_DESC desc{};texture->GetDesc(&desc);desc.BindFlags=desc.MiscFlags=0;desc.Usage=D3D11_USAGE_STAGING;desc.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
 ComPtr<ID3D11Texture2D> copy;assert(SUCCEEDED(device->CreateTexture2D(&desc,nullptr,&copy)));context->CopyResource(copy.Get(),texture);
 D3D11_MAPPED_SUBRESOURCE mapped{};assert(SUCCEEDED(context->Map(copy.Get(),0,D3D11_MAP_READ,0,&mapped)));
 std::vector<unsigned char> result(size_t(desc.Width)*desc.Height*4);
 for(unsigned y=0;y<desc.Height;++y)memcpy(result.data()+size_t(y)*desc.Width*4,static_cast<unsigned char*>(mapped.pData)+size_t(y)*mapped.RowPitch,desc.Width*4);
 context->Unmap(copy.Get(),0);return result;
}
int wmain(int argc,wchar_t** argv){
 _set_error_mode(_OUT_TO_STDERR);
 assert(argc==2);assert(loadShaders(argv[1]));assert(std::atomic_load(&shaderCode));
 ComPtr<ID3D11Device> device;ComPtr<ID3D11DeviceContext> context;
 assert(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&device,nullptr,&context)));
 D3D11_TEXTURE2D_DESC desc{};desc.Width=desc.Height=256;desc.MipLevels=desc.ArraySize=desc.SampleDesc.Count=1;desc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;desc.BindFlags=D3D11_BIND_RENDER_TARGET;
 ComPtr<ID3D11Texture2D> color,depth;assert(SUCCEEDED(device->CreateTexture2D(&desc,nullptr,&color)));
 ComPtr<ID3D11RenderTargetView> target;assert(SUCCEEDED(device->CreateRenderTargetView(color.Get(),nullptr,&target)));
 auto depthDesc=desc;depthDesc.Format=DXGI_FORMAT_D32_FLOAT;depthDesc.BindFlags=D3D11_BIND_DEPTH_STENCIL;
 assert(SUCCEEDED(device->CreateTexture2D(&depthDesc,nullptr,&depth)));
 ComPtr<ID3D11DepthStencilView> depthView;assert(SUCCEEDED(device->CreateDepthStencilView(depth.Get(),nullptr,&depthView)));
 Frame frame;frame.sequence=1;frame.tick=GetTickCount64();frame.context=context;frame.depth=depthView;
 frame.viewport={0,0,256,256,0,1};frame.depthState.DepthEnable=TRUE;frame.depthState.DepthFunc=D3D11_COMPARISON_LESS_EQUAL;
 for(unsigned i=0;i<4;++i)frame.model[i*5]=1;for(unsigned i=0;i<3;++i)frame.model[12+i]=origin[i];
 frame.viewProjection[0]=1/radius;frame.viewProjection[9]=-1/radius;frame.viewProjection[12]=-origin[0]/radius;
 frame.viewProjection[13]=origin[2]/radius;frame.viewProjection[14]=.5f;frame.viewProjection[15]=1;
 struct Vertex {uint16_t position[4];unsigned char other[12];};
 Vertex vertices[3]{};
 auto updateVertices=[&](float shift){
  const float positions[3][3]={{-30+shift,1,0},{30+shift,1,0},{shift,145,0}};
  for(unsigned i=0;i<3;++i){for(unsigned axis=0;axis<3;++axis)vertices[i].position[axis]=DirectX::PackedVector::XMConvertFloatToHalf(positions[i][axis]);vertices[i].position[3]=DirectX::PackedVector::XMConvertFloatToHalf(1.f);}
 };
 updateVertices(0);uint16_t indices[3]={0,1,2};Mesh mesh;mesh.stride=sizeof(Vertex);mesh.count=3;mesh.indexFormat=DXGI_FORMAT_R16_UINT;
 D3D11_BUFFER_DESC buffer{};buffer.ByteWidth=sizeof vertices;buffer.BindFlags=D3D11_BIND_VERTEX_BUFFER;D3D11_SUBRESOURCE_DATA data{vertices,0,0};
 assert(SUCCEEDED(device->CreateBuffer(&buffer,&data,&mesh.vertices)));buffer.ByteWidth=sizeof indices;buffer.BindFlags=D3D11_BIND_INDEX_BUFFER;data.pSysMem=indices;
 assert(SUCCEEDED(device->CreateBuffer(&buffer,&data,&mesh.indices)));frame.meshes.push_back(mesh);
 Renderer renderer;if(!renderer.initialize(device.Get())){
  std::cerr<<"init "<<bool(renderer.caster)<<bool(renderer.maskPixel)<<bool(renderer.position)<<bool(renderer.receiver)<<bool(renderer.receiverPixel)<<bool(renderer.nativeConstants)<<bool(renderer.mapTarget)<<bool(renderer.maxBlend)<<bool(renderer.alphaBlend)<<bool(renderer.raster)<<bool(renderer.sampler)<<bool(renderer.noDepth)<<"\n";
  for(const char* entry:{"VS","PS"}){ComPtr<ID3DBlob> code,error;const auto hr=D3DCompile(receiverShader,strlen(receiverShader),nullptr,nullptr,nullptr,entry,entry[0]=='V'?"vs_5_0":"ps_5_0",0,0,&code,&error);std::cerr<<entry<<" "<<std::hex<<hr<<" ";if(error)std::cerr<<static_cast<const char*>(error->GetBufferPointer());std::cerr<<"\n";}return 1;
 }
 const float white[4]={1,1,1,1};context->ClearRenderTargetView(target.Get(),white);context->ClearDepthStencilView(depthView.Get(),D3D11_CLEAR_DEPTH,1,0);
 ID3D11RenderTargetView* originalTarget=target.Get();context->OMSetRenderTargets(1,&originalTarget,depthView.Get());context->RSSetViewports(1,&frame.viewport);
 assert(renderer.draw(frame,target.Get(),desc));
 auto first=pixels(device.Get(),context.Get(),color.Get());unsigned dark=0;double center=0;
 for(unsigned i=0;i<first.size()/4;++i)if(first[i*4]<250){++dark;center+=i%256;}
 if(!dark){std::cerr<<"No native silhouette reached the receiver\n";return 1;}
 assert(dark>100&&dark<15000);center/=dark;
 ComPtr<ID3D11RenderTargetView> restored;ComPtr<ID3D11DepthStencilView> restoredDepth;
 context->OMGetRenderTargets(1,&restored,&restoredDepth);assert(restored.Get()==target.Get()&&restoredDepth.Get()==depthView.Get());
 updateVertices(60);context->UpdateSubresource(mesh.vertices.Get(),0,nullptr,vertices,0,0);context->ClearRenderTargetView(target.Get(),white);
 assert(renderer.draw(frame,target.Get(),desc));auto second=pixels(device.Get(),context.Get(),color.Get());unsigned moved=0;double nextCenter=0;
 for(unsigned i=0;i<second.size()/4;++i)if(second[i*4]<250){++moved;nextCenter+=i%256;}
 assert(moved>100&&nextCenter/moved>center+25);assert(first!=second);
 context->ClearRenderTargetView(target.Get(),white);context->ClearDepthStencilView(depthView.Get(),D3D11_CLEAR_DEPTH,.2f,0);
 assert(renderer.draw(frame,target.Get(),desc));auto hidden=pixels(device.Get(),context.Get(),color.Get());
 for(unsigned i=0;i<hidden.size()/4;++i)assert(hidden[i*4]==255);
 auto originalCapture=captures.load();assert(arm(context.Get()));
 ComPtr<ID3D11DepthStencilState> readDepth;auto state=frame.depthState;assert(SUCCEEDED(device->CreateDepthStencilState(&state,&readDepth)));
 context->OMSetDepthStencilState(readDepth.Get(),0);context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
 auto* vertex=mesh.vertices.Get();context->IASetVertexBuffers(0,1,&vertex,&mesh.stride,&mesh.offset);context->IASetIndexBuffer(mesh.indices.Get(),mesh.indexFormat,0);
 context->IASetInputLayout(renderer.position.Get());context->VSSetShader(renderer.caster.Get(),nullptr,0);context->PSSetShader(renderer.maskPixel.Get(),nullptr,0);
 ID3D11Buffer* nativeInputs[]={renderer.nativeConstants.Get(),renderer.tileConstants.Get(),renderer.projection.Get()};context->VSSetConstantBuffers(0,3,nativeInputs);
 {
  CaptureScope scope(context.Get(),5,frame.model,frame.viewProjection);assert(capturing);
  context->DrawIndexed(3,0,0);
  afterNativeVertexBinding(context.Get());
  context->DrawIndexedInstanced(3,1,0,0,0);
  capture(context.Get(),3000000,0,0); // Reject an out-of-range native draw.
 }
 if(captures!=originalCapture+2){std::cerr<<"capture count "<<captures-originalCapture<<"\n";return 1;}
 assert(pending&&pending->sequence==5&&pending->meshes.size()==2);discard();assert(!pending&&!capturing);
 float outside[16];memcpy(outside,frame.model,sizeof outside);outside[12]=0;
 {CaptureScope scope(context.Get(),6,outside,frame.viewProjection);assert(!capturing);}
 for(auto format:{DXGI_FORMAT_D32_FLOAT,DXGI_FORMAT_D24_UNORM_S8_UINT})for(unsigned samples:{1u,2u,4u,8u}){
  UINT quality=0;assert(SUCCEEDED(device->CheckMultisampleQualityLevels(format,samples,&quality)));if(!quality)continue;
  ComPtr<ID3D11Texture2D> sampled;ComPtr<ID3D11DepthStencilView> sampledView;
  auto sampledDesc=depthDesc;sampledDesc.Format=format;sampledDesc.SampleDesc.Count=samples;
  assert(SUCCEEDED(device->CreateTexture2D(&sampledDesc,nullptr,&sampled)));assert(SUCCEEDED(device->CreateDepthStencilView(sampled.Get(),nullptr,&sampledView)));
  frame.depth=sampledView;context->OMSetRenderTargets(1,&originalTarget,nullptr);
  for(bool reversed:{false,true}){
   frame.depthState.DepthFunc=reversed?D3D11_COMPARISON_GREATER_EQUAL:D3D11_COMPARISON_LESS_EQUAL;
   context->ClearDepthStencilView(sampledView.Get(),D3D11_CLEAR_DEPTH,reversed?0.f:1.f,0);context->ClearRenderTargetView(target.Get(),white);
   assert(renderer.draw(frame,target.Get(),desc));auto visible=pixels(device.Get(),context.Get(),color.Get());unsigned affected=0;
   for(unsigned i=0;i<visible.size()/4;++i)affected+=visible[i*4]<250;assert(affected>100);
   assert(depthSamples==samples);
   context->ClearDepthStencilView(sampledView.Get(),D3D11_CLEAR_DEPTH,reversed?.8f:.2f,0);context->ClearRenderTargetView(target.Get(),white);
   assert(renderer.draw(frame,target.Get(),desc));auto occluded=pixels(device.Get(),context.Get(),color.Get());
   for(unsigned i=0;i<occluded.size()/4;++i)assert(occluded[i*4]==255);
  }
 }

 // Furniture uses float-position streams and independent object transforms.
 assert(room_shadow_bridge::caster("medical_padding",false));
 assert(room_shadow_bridge::caster("v3_bay_wood",false));
 assert(!room_shadow_bridge::caster("role_floor_2",false));
 assert(room_shadow_bridge::caster("role_neutral_19",false)); // Native display support/frame.
 assert(room_shadow_bridge::caster("role_board_23",false));
 assert(room_shadow_bridge::caster("v3_static_room_part_1",false));
 assert(room_shadow_bridge::caster("v3_table_wood",false));
 assert(!room_shadow_bridge::caster("v3_bay_light",false));
 assert(!room_shadow_bridge::caster("interior_hydration_wall",false));
 assert(!room_shadow_bridge::caster("cooler_glass",true));
 frame.depth=depthView;frame.depthState.DepthFunc=D3D11_COMPARISON_LESS_EQUAL;
 context->OMSetRenderTargets(1,&originalTarget,depthView.Get());context->OMSetDepthStencilState(readDepth.Get(),0);
 context->RSSetViewports(1,&frame.viewport);context->ClearDepthStencilView(depthView.Get(),D3D11_CLEAR_DEPTH,1,0);
 clubanim::drawBindingObserver=&afterNativeVertexBinding;
 struct FloatVertex {float p[3];unsigned char other[12];};
 FloatVertex propVertices[3]={{{-30,1,0},{}},{{30,1,0},{}},{{0,145,0},{}}};
 Mesh prop=mesh;prop.stride=sizeof(FloatVertex);prop.floatPosition=true;prop.vertices.Reset();
 buffer.ByteWidth=sizeof propVertices;buffer.BindFlags=D3D11_BIND_VERTEX_BUFFER;data.pSysMem=propVertices;
 assert(SUCCEEDED(device->CreateBuffer(&buffer,&data,&prop.vertices)));
 room_shadow_bridge::Submission packet;packet.reserved=room_shadow_bridge::FloorOnly;packet.club=1043;packet.generation=1;packet.object=100;packet.context=context.Get();
 memcpy(packet.model,frame.model,64);memcpy(packet.viewProjection,frame.viewProjection,64);
 roompropshadow::state(true,1043,1);
 auto submit=[&](){
  ++packet.frame;roompropshadow::begin(&packet);assert(capturing);
  auto* vb=prop.vertices.Get();context->IASetVertexBuffers(0,1,&vb,&prop.stride,&prop.offset);
  context->IASetInputLayout(renderer.floatPosition.Get());context->IASetIndexBuffer(prop.indices.Get(),prop.indexFormat,0);
  context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);context->DrawIndexed(3,0,0);
  roompropshadow::end();assert(!capturing&&!clubanim::staticSceneDraw);
 };
 packet.model[12]-=80;submit();assert(roompropshadow::residentInstances==1);
 const auto revision=roompropshadow::cache.revision;
 roompropshadow::begin(&packet);assert(!capturing&&clubanim::staticSceneDraw);roompropshadow::end();
 assert(roompropshadow::cache.revision==revision&&roompropshadow::residentMeshes==1);
 // A new FIFA frame refreshes the camera even with the same wall-clock tick.
 ++packet.frame;packet.viewProjection[12]+=.125f;roompropshadow::begin(&packet);roompropshadow::end();
 assert(roompropshadow::cache.latest->sequence==packet.frame&&roompropshadow::cache.latest->viewProjection[12]==packet.viewProjection[12]);
 packet.viewProjection[12]-=.125f;
 packet.object=200;packet.model[12]+=160;submit();assert(roompropshadow::residentInstances==2);
 Frame furniture=*roompropshadow::cache.latest;
 for(const auto& instance:roompropshadow::cache.instances)for(const auto& captured:instance.second){
  assert(captured.transformed&&captured.floatPosition&&captured.stride==24);furniture.meshes.push_back(captured);
 }
 Area propArea;propArea.light[0]=-3000;propArea.light[1]=10000;propArea.light[2]=-5000;
 context->ClearRenderTargetView(target.Get(),white);assert(renderer.draw(furniture,target.Get(),desc,propArea));
 const auto props=pixels(device.Get(),context.Get(),color.Get());unsigned left=0,right=0;
 for(unsigned i=0;i<props.size()/4;++i)if(props[i*4]<250){if(i%256<128)++left;else ++right;}
 assert(left>40&&right>40); // Both world-space silhouettes, not one shared origin.
 for(auto& v:propVertices)v.p[0]+=70;
 context->UpdateSubresource(prop.vertices.Get(),0,nullptr,propVertices,0,0);
 context->ClearRenderTargetView(target.Get(),white);assert(renderer.draw(furniture,target.Get(),desc,propArea,false));
 assert(pixels(device.Get(),context.Get(),color.Get())==props); // Stable cached mask during camera-only frames.
 context->ClearRenderTargetView(target.Get(),white);assert(renderer.draw(furniture,target.Get(),desc,propArea,true));
 assert(pixels(device.Get(),context.Get(),color.Get())!=props);


 // The same geometry must respond to two distinct ceiling focuses.
 context->ClearRenderTargetView(target.Get(),white);assert(renderer.draw(furniture,target.Get(),desc,roompropshadow::area(5)));
 const auto fromFront=pixels(device.Get(),context.Get(),color.Get());
 context->ClearRenderTargetView(target.Get(),white);assert(renderer.draw(furniture,target.Get(),desc,roompropshadow::area(6)));
 const auto fromBack=pixels(device.Get(),context.Get(),color.Get());assert(fromFront!=fromBack);
 // Native room conversion can expand float3 streams from stride 24 to 32.
 // These models keep floor height inside their vertices, not their transform.
 struct ExpandedFloatVertex {float p[3];unsigned char other[20];};
 ExpandedFloatVertex expandedVertices[3]{};
 for(unsigned i=0;i<3;++i){memcpy(expandedVertices[i].p,propVertices[i].p,12);expandedVertices[i].p[1]+=1000;}
 prop.vertices.Reset();prop.stride=sizeof(ExpandedFloatVertex);buffer.ByteWidth=sizeof expandedVertices;data.pSysMem=expandedVertices;
 assert(SUCCEEDED(device->CreateBuffer(&buffer,&data,&prop.vertices)));
 packet.instance=1;packet.model[13]=0;submit();assert(roompropshadow::residentMeshes==3);
 assert(roompropshadow::cache.instances.at({packet.object,packet.instance})[0].stride==32);
 auto paintCached=[&](){
  const auto before=painted.load();roompropshadow::begin(&packet);
  assert(!capturing&&paintContext==context.Get());
  auto* vb=prop.vertices.Get();context->IASetVertexBuffers(0,1,&vb,&prop.stride,&prop.offset);
  context->IASetInputLayout(renderer.floatPosition.Get());context->IASetIndexBuffer(prop.indices.Get(),prop.indexFormat,0);
  context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);context->DrawIndexed(3,0,0);
  roompropshadow::end();assert(painted==before+1&&!paintContext&&!clubanim::staticSceneDraw);
 };
 // Exercise the complete room compositor, including amortized tile builds and
 // one shared native depth copy. The test window stays hidden.
 WNDCLASSW windowClass{};windowClass.lpfnWndProc=DefWindowProcW;windowClass.hInstance=GetModuleHandleW(nullptr);windowClass.lpszClassName=L"RoomPropShadowTest";
 assert(RegisterClassW(&windowClass));HWND window=CreateWindowW(windowClass.lpszClassName,L"",WS_POPUP,0,0,256,256,nullptr,nullptr,windowClass.hInstance,nullptr);assert(window);
 ComPtr<IDXGIDevice> dxgiDevice;ComPtr<IDXGIAdapter> adapter;ComPtr<IDXGIFactory> factory;ComPtr<IDXGISwapChain> swap;
 assert(SUCCEEDED(device.As(&dxgiDevice)));assert(SUCCEEDED(dxgiDevice->GetAdapter(&adapter)));assert(SUCCEEDED(adapter->GetParent(IID_PPV_ARGS(&factory))));
 DXGI_SWAP_CHAIN_DESC swapDesc{};swapDesc.BufferCount=1;swapDesc.BufferDesc.Width=swapDesc.BufferDesc.Height=256;swapDesc.BufferDesc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;
 swapDesc.BufferUsage=DXGI_USAGE_RENDER_TARGET_OUTPUT;swapDesc.OutputWindow=window;swapDesc.SampleDesc.Count=1;swapDesc.Windowed=TRUE;
 assert(SUCCEEDED(factory->CreateSwapChain(device.Get(),&swapDesc,&swap)));
 ComPtr<ID3D11Texture2D> back;ComPtr<ID3D11RenderTargetView> backTarget;
 assert(SUCCEEDED(swap->GetBuffer(0,IID_PPV_ARGS(&back))));assert(SUCCEEDED(device->CreateRenderTargetView(back.Get(),nullptr,&backTarget)));
 const auto builds=roompropshadow::maskBuilds.load();
 for(unsigned i=0;i<roompropshadow::lightCount+3;++i){
  ++packet.frame;paintCached();
  context->ClearRenderTargetView(backTarget.Get(),white);
  const auto before=roompropshadow::maskBuilds.load();roompropshadow::present(swap.Get());
  assert(roompropshadow::maskBuilds-before<=1);
 }
 assert(roompropshadow::maskBuilds-builds==roompropshadow::lightCount);
 const auto scenePixels=pixels(device.Get(),context.Get(),back.Get());unsigned sceneShade=0;
 for(unsigned i=0;i<scenePixels.size()/4;++i)sceneShade+=scenePixels[i*4]<250;
 assert(sceneShade>100);
 for(unsigned i=1;i<roompropshadow::lightCount;++i){
  assert(roompropshadow::renderers[i].depthCopy.Get()==roompropshadow::renderers[0].depthCopy.Get());
  assert(roompropshadow::renderers[i].receiverPixel.Get()==roompropshadow::renderers[0].receiverPixel.Get());
  assert(roompropshadow::renderers[i].map.Get()!=roompropshadow::renderers[0].map.Get());
 }
 assert(roompropshadow::cache.flattened&&roompropshadow::cache.flattened->size()==3);

 // Room MSAA 4x depth is copied only once and shared by all spotlight receivers.
 ComPtr<ID3D11Texture2D> roomMsaa;ComPtr<ID3D11DepthStencilView> roomMsaaView;
 auto roomMsaaDesc=depthDesc;roomMsaaDesc.SampleDesc.Count=4;
 assert(SUCCEEDED(device->CreateTexture2D(&roomMsaaDesc,nullptr,&roomMsaa)));
 assert(SUCCEEDED(device->CreateDepthStencilView(roomMsaa.Get(),nullptr,&roomMsaaView)));
 context->ClearDepthStencilView(roomMsaaView.Get(),D3D11_CLEAR_DEPTH,1,0);
 context->OMSetRenderTargets(0,nullptr,roomMsaaView.Get());++packet.frame;
 // Repeated native timestamps represent distinct backbuffer images. They must
 // receive a shadow every time, even when Windows' 15.6ms clock has not ticked.
 roompropshadow::begin(&packet);roompropshadow::end();
 const auto repeatedTick=GetTickCount64();
 const auto beforeFrames=roompropshadow::frames.load(),beforeBuilds=roompropshadow::maskBuilds.load();
 for(unsigned i=0;i<3;++i){
  paintCached(); // Same UI sequence/timestamp, but a genuinely new native draw.
  context->ClearRenderTargetView(backTarget.Get(),white);roompropshadow::cache.latest->tick=repeatedTick;
  roompropshadow::present(swap.Get());auto image=pixels(device.Get(),context.Get(),back.Get());
  unsigned affected=0;for(unsigned j=0;j<image.size()/4;++j)affected+=image[j*4]<250;
  assert(affected>100);
 }
 assert(roompropshadow::frames==beforeFrames+3&&roompropshadow::maskBuilds==beforeBuilds);
 assert(depthSamples==4);
 const auto stablePixels=pixels(device.Get(),context.Get(),back.Get());
 const auto stableFrames=roompropshadow::frames.load(),skippedPresents=roompropshadow::repeatedPresents.load();
 for(unsigned i=0;i<50;++i)assert(roompropshadow::present(swap.Get()));
 assert(pixels(device.Get(),context.Get(),back.Get())==stablePixels);
 assert(roompropshadow::frames==stableFrames&&roompropshadow::repeatedPresents==skippedPresents+50);
 // The all-surface branch has the same no-accumulation protection.
 packet.reserved=0;packet.viewProjection[6]=.0001f;++packet.frame;paintCached();context->ClearRenderTargetView(backTarget.Get(),white);
 assert(roompropshadow::present(swap.Get()));const auto surfacePixels=pixels(device.Get(),context.Get(),back.Get());
 const auto surfaceFrames=roomsurface::shadowFrames.load();
 for(unsigned i=0;i<50;++i)assert(roompropshadow::present(swap.Get()));
 assert(pixels(device.Get(),context.Get(),back.Get())==surfacePixels&&roomsurface::shadowFrames==surfaceFrames);
 for(unsigned i=1;i<roompropshadow::lightCount;++i)assert(roompropshadow::renderers[i].depthCopy.Get()==roompropshadow::renderers[0].depthCopy.Get());
 // Validate real ceiling placement and finite spot falloff instead of distant
 // directional projections. Independent focuses must have distinct matrices.
 for(unsigned i=0;i<roompropshadow::lightCount;++i){
  auto focus=roompropshadow::area(i);const auto& source=room_spotlight_r79::kSources[i];
  assert(focus.light[1]==source.y&&focus.light[0]==0&&focus.light[2]==0&&focus.spot==int(i));
  assert(focus.center[0]==origin[0]+source.x&&focus.center[2]==source.z);
 }
 roompropshadow::state(false,0,0);roompropshadow::present(swap.Get());
 assert(!roompropshadow::renderers[0].map&&!roompropshadow::cache.flattened);
 swap.Reset();DestroyWindow(window);UnregisterClassW(windowClass.lpszClassName,windowClass.hInstance);
 roompropshadow::state(true,1629,2);assert(!roompropshadow::cache.latest&&roompropshadow::residentMeshes==0);
 packet.club=1629;packet.generation=2;packet.object=300;submit();assert(roompropshadow::residentInstances==1);
 packet.object=400;roompropshadow::begin(&packet);assert(capturing);
 capture(context.Get(),3,0,0);roompropshadow::state(true,1043,3);roompropshadow::end();
 assert(!capturing&&roompropshadow::residentInstances==0);
 roompropshadow::state(false,0,0);assert(!roompropshadow::cache.visible&&!roompropshadow::cache.latest);
 clubanim::drawBindingObserver=nullptr;clubanim::stop();roompropshadow::stop();
 stop();renderer.clear();
 std::cout<<"PASS FIFA native floor shadow: animated actor, independent float-position furniture, cached ceiling-spot compositor, no frame drops with repeated Windows timestamps, club/exit invalidation, state restoration, D32/D24 1x/2x/4x/8x depth on single-sample output, regular and reversed depth occlusion\n";
}
