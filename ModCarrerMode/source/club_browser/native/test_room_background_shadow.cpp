#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <cassert>
#include <iostream>
#include "room_prop_shadow.h"
using namespace roomshadow;
static std::vector<unsigned char> pixels(ID3D11Device* d,ID3D11DeviceContext* c,ID3D11Texture2D* source){
 D3D11_TEXTURE2D_DESC desc{};source->GetDesc(&desc);desc.BindFlags=desc.MiscFlags=0;desc.Usage=D3D11_USAGE_STAGING;desc.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
 ComPtr<ID3D11Texture2D> copy;assert(SUCCEEDED(d->CreateTexture2D(&desc,nullptr,&copy)));c->CopyResource(copy.Get(),source);
 D3D11_MAPPED_SUBRESOURCE map{};assert(SUCCEEDED(c->Map(copy.Get(),0,D3D11_MAP_READ,0,&map)));std::vector<unsigned char> result(desc.Width*desc.Height*4);
 for(unsigned y=0;y<desc.Height;++y)memcpy(result.data()+y*desc.Width*4,(char*)map.pData+y*map.RowPitch,desc.Width*4);c->Unmap(copy.Get(),0);return result;
}
int wmain(int argc,wchar_t**argv){
 _set_error_mode(_OUT_TO_STDERR);_set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);assert(argc==2&&loadShaders(argv[1]));
 ComPtr<ID3D11Device> device;ComPtr<ID3D11DeviceContext> context;
 assert(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&device,nullptr,&context)));
 WNDCLASSW wc{};wc.lpfnWndProc=DefWindowProcW;wc.hInstance=GetModuleHandleW(nullptr);wc.lpszClassName=L"RoomBackgroundShadowTest";
 assert(RegisterClassW(&wc));HWND window=CreateWindowW(wc.lpszClassName,L"",WS_POPUP,0,0,128,128,nullptr,nullptr,wc.hInstance,nullptr);assert(window);
 ComPtr<IDXGIDevice> dxgi;ComPtr<IDXGIAdapter> adapter;ComPtr<IDXGIFactory> factory;ComPtr<IDXGISwapChain> swap;
 assert(SUCCEEDED(device.As(&dxgi))&&SUCCEEDED(dxgi->GetAdapter(&adapter))&&SUCCEEDED(adapter->GetParent(IID_PPV_ARGS(&factory))));
 DXGI_SWAP_CHAIN_DESC sd{};sd.BufferCount=1;sd.BufferDesc.Width=sd.BufferDesc.Height=128;sd.BufferDesc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;sd.BufferUsage=DXGI_USAGE_RENDER_TARGET_OUTPUT;sd.OutputWindow=window;sd.SampleDesc.Count=1;sd.Windowed=TRUE;
 assert(SUCCEEDED(factory->CreateSwapChain(device.Get(),&sd,&swap)));
 ComPtr<ID3D11Texture2D> color;ComPtr<ID3D11RenderTargetView> output;assert(SUCCEEDED(swap->GetBuffer(0,IID_PPV_ARGS(&color)))&&SUCCEEDED(device->CreateRenderTargetView(color.Get(),nullptr,&output)));
 D3D11_TEXTURE2D_DESC dd{};color->GetDesc(&dd);dd.Format=DXGI_FORMAT_D32_FLOAT;dd.BindFlags=D3D11_BIND_DEPTH_STENCIL;
 ComPtr<ID3D11Texture2D> depth;ComPtr<ID3D11DepthStencilView> dsv;assert(SUCCEEDED(device->CreateTexture2D(&dd,nullptr,&depth))&&SUCCEEDED(device->CreateDepthStencilView(depth.Get(),nullptr,&dsv)));
 Frame frame;frame.flags=room_shadow_bridge::Background;frame.context=context;frame.depth=dsv;frame.viewport={0,0,128,128,0,1};frame.depthState.DepthEnable=TRUE;frame.depthState.DepthFunc=D3D11_COMPARISON_LESS_EQUAL;
 frame.viewProjection[0]=1/radius;frame.viewProjection[6]=-1/400.f;frame.viewProjection[9]=-1/radius;frame.viewProjection[12]=-origin[0]/radius;frame.viewProjection[13]=origin[2]/radius;frame.viewProjection[14]=(origin[1]+360)/400;frame.viewProjection[15]=1;
 Mesh canopy;canopy.floatPosition=canopy.transformed=true;canopy.stride=24;canopy.count=6;canopy.indexFormat=DXGI_FORMAT_R16_UINT;
 for(unsigned i=0;i<4;++i)canopy.model[i*5]=1;canopy.model[12]=origin[0];canopy.model[13]=origin[1];canopy.model[14]=origin[2];
 struct V{float xyz[3],pad[3];};V vertices[]={{{-1000,200,-1000},{}},{{1000,200,-1000},{}},{{1000,200,1000},{}},{{-1000,200,1000},{}}};uint16_t indices[]={0,1,2,0,2,3};
 D3D11_BUFFER_DESC bd{};bd.ByteWidth=sizeof vertices;bd.BindFlags=D3D11_BIND_VERTEX_BUFFER;D3D11_SUBRESOURCE_DATA data{vertices,0,0};assert(SUCCEEDED(device->CreateBuffer(&bd,&data,&canopy.vertices)));
 bd.ByteWidth=sizeof indices;bd.BindFlags=D3D11_BIND_INDEX_BUFFER;data.pSysMem=indices;assert(SUCCEEDED(device->CreateBuffer(&bd,&data,&canopy.indices)));
 roompropshadow::state(true,1043,1);roompropshadow::cache.instances[{123,0}]={canopy};roompropshadow::cache.meshes=1;roompropshadow::cache.revision=1;
 static const char* ui="struct P{float4 p:SV_POSITION;};P VS(uint id:SV_VertexID){P o;o.p=float4((id&1)?1:-1,(id&2)?-1:1,0,1);return o;}float4 PS(P i):SV_TARGET{clip(12-i.p.y);return float4(1,1,1,1);}";
 ComPtr<ID3DBlob> vb,pb;assert(SUCCEEDED(D3DCompile(ui,strlen(ui),nullptr,nullptr,nullptr,"VS","vs_5_0",0,0,&vb,nullptr))&&SUCCEEDED(D3DCompile(ui,strlen(ui),nullptr,nullptr,nullptr,"PS","ps_5_0",0,0,&pb,nullptr)));
 ComPtr<ID3D11VertexShader> vs;ComPtr<ID3D11PixelShader> ps;assert(SUCCEEDED(device->CreateVertexShader(vb->GetBufferPointer(),vb->GetBufferSize(),nullptr,&vs))&&SUCCEEDED(device->CreatePixelShader(pb->GetBufferPointer(),pb->GetBufferSize(),nullptr,&ps)));
 assert(clubanim::armVertexObserver(context.Get())&&arm(context.Get()));clubanim::drawBindingObserver=&afterNativeVertexBinding;beforeOverlayDraw=&roompropshadow::beforeOverlay;
 const float white[]={1,1,1,1};context->ClearDepthStencilView(dsv.Get(),D3D11_CLEAR_DEPTH,.9f,0);
 auto fresh=[&](){frame.tick=GetTickCount64();++frame.sequence;roompropshadow::cache.latest=std::make_shared<Frame>(frame);room_shadow_bridge::Submission packet;packet.club=roompropshadow::cache.club;packet.generation=roompropshadow::cache.generation;packet.object=123;packet.frame=frame.sequence;packet.reserved=frame.flags;packet.context=context.Get();memcpy(packet.model,canopy.model,64);memcpy(packet.viewProjection,frame.viewProjection,64);roompropshadow::begin(&packet);auto* rt=output.Get();context->OMSetRenderTargets(1,&rt,dsv.Get());context->OMSetDepthStencilState(nullptr,0);context->RSSetViewports(1,&frame.viewport);roompropshadow::end();++painted;context->ClearRenderTargetView(output.Get(),white);};
 auto drawUi=[&](){auto* rt=output.Get();context->OMSetRenderTargets(1,&rt,nullptr);context->RSSetViewports(1,&frame.viewport);context->VSSetShader(vs.Get(),nullptr,0);context->PSSetShader(ps.Get(),nullptr,0);context->OMSetBlendState(nullptr,nullptr,UINT_MAX);context->IASetInputLayout(nullptr);context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP);auto* vb=canopy.vertices.Get();UINT stride=24,offset=0;context->IASetVertexBuffers(0,1,&vb,&stride,&offset);context->Draw(4,0);};
 for(unsigned i=0;i<roomsurface::lights+1;++i){fresh();drawUi();}
 auto image=pixels(device.Get(),context.Get(),color.Get());unsigned shaded=0,top=0,bottom=0;
 for(unsigned y=0;y<128;++y)for(unsigned x=0;x<128;++x){auto value=image[(y*128+x)*4];if(y<12)assert(value==255);else if(value<250){++shaded;if(y<17)++top;if(y>107)++bottom;}}
 std::cerr<<"background shaded="<<shaded<<" top="<<top<<" bottom="<<bottom<<" frames="<<roompropshadow::frames.load()<<"\n";assert(shaded>500&&top>100&&bottom>100);auto count=roompropshadow::frames.load();
 assert(roompropshadow::present(swap.Get()));drawUi();assert(roompropshadow::frames==count&&pixels(device.Get(),context.Get(),color.Get())==image);
 // The dedicated room and its customization overlay use the same pre-UI
 // compositor. Native panels must stay white, without a second Present blend.
 for(unsigned flags:{0u,unsigned(room_shadow_bridge::Overlay),unsigned(room_shadow_bridge::Background|room_shadow_bridge::Overlay)}){
  frame.flags=flags;fresh();drawUi();assert(roompropshadow::frames==++count);
  auto pixelsWithUi=pixels(device.Get(),context.Get(),color.Get());for(unsigned y=0;y<12;++y)for(unsigned x=0;x<128;++x)assert(pixelsWithUi[(y*128+x)*4]==255);
  roompropshadow::present(swap.Get());assert(roompropshadow::frames==count&&pixels(device.Get(),context.Get(),color.Get())==pixelsWithUi);
 }
 frame.flags=room_shadow_bridge::Background;fresh();context->OMSetRenderTargets(1,output.GetAddressOf(),nullptr);context->IASetIndexBuffer(canopy.indices.Get(),DXGI_FORMAT_R16_UINT,0);context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);auto* uiVertex=canopy.vertices.Get();UINT stride=24,offset=0;context->IASetVertexBuffers(0,1,&uiVertex,&stride,&offset);context->DrawIndexed(6,0,0);assert(roompropshadow::frames==++count);
 ComPtr<ID3D11PixelShader> restored;context->PSGetShader(&restored,nullptr,nullptr);assert(restored.Get()==ps.Get());
 auto compiled=roomsurface::renderer.pixel;roompropshadow::state(false,0,0);roompropshadow::present(swap.Get());assert(roomsurface::renderer.pixel.Get()==compiled.Get());
 roompropshadow::state(true,1043,2);roompropshadow::cache.instances[{123,0}]={canopy};roompropshadow::cache.meshes=1;roompropshadow::cache.revision=1;fresh();drawUi();assert(roomsurface::renderer.pixel.Get()==compiled.Get());
 unsigned valid=0;for(auto revision:roomsurface::renderer.revisions)if(revision)++valid;assert(valid==1); // Previous generation's light contents cannot leak.
 // Reproduce entering the room immediately after a native UI draw: no DSV
 // at Begin, then FIFA's prop binds depth and its actual streams before End.
 roompropshadow::state(true,1043,3);frame.flags=0;room_shadow_bridge::Submission packet;
 packet.club=1043;packet.generation=3;packet.object=456;packet.frame=++frame.sequence;packet.context=context.Get();
 memcpy(packet.model,canopy.model,64);memcpy(packet.viewProjection,frame.viewProjection,64);
 context->OMSetRenderTargets(1,output.GetAddressOf(),nullptr);roompropshadow::begin(&packet);assert(capturing);
 context->OMSetRenderTargets(1,output.GetAddressOf(),dsv.Get());context->OMSetDepthStencilState(nullptr,0);context->RSSetViewports(1,&frame.viewport);
 context->VSSetShader(vs.Get(),nullptr,0);context->PSSetShader(ps.Get(),nullptr,0);context->IASetVertexBuffers(0,1,&uiVertex,&stride,&offset);context->IASetIndexBuffer(canopy.indices.Get(),DXGI_FORMAT_R16_UINT,0);context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);context->DrawIndexed(6,0,0);
 roompropshadow::end();assert(!capturing&&roompropshadow::residentMeshes==1&&roompropshadow::cache.latest->depth.Get()==dsv.Get());
 const auto beforeUiFrames=roompropshadow::frames.load();
 context->ClearRenderTargetView(output.Get(),white);context->OMSetRenderTargets(1,output.GetAddressOf(),nullptr);
 // No vertex rebind: the direct Draw interception must still precede UI.
 context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP);context->Draw(4,0);
 assert(roompropshadow::frames==beforeUiFrames+1);
 // Optional GPU audit reconstructs the same real depth without changing it,
 // the visible target, or the native pixel shader and output bindings.
 auto auditBefore=pixels(device.Get(),context.Get(),color.Get());
 std::ostringstream report;assert(roomaudit::auditor.capture(frame,report));
 assert(report.str().find("\"foreground\":9216")!=std::string::npos);
 assert(report.str().find("\"inside_room\":9216")!=std::string::npos);
 assert(pixels(device.Get(),context.Get(),color.Get())==auditBefore);
 ComPtr<ID3D11PixelShader> afterAudit;context->PSGetShader(&afterAudit,nullptr,nullptr);assert(afterAudit.Get()==ps.Get());
 clubanim::drawBindingObserver=nullptr;roompropshadow::stop();stop();clubanim::stop();roomsurface::renderer.clear();swap.Reset();DestroyWindow(window);UnregisterClassW(wc.lpszClassName,wc.hInstance);
 std::cout<<"PASS room shadows: background and dedicated room use pre-UI pass, depth is captured after prop material, direct/indexed UI protected, no Present accumulation\n";
}
