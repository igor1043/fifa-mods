#include <cassert>
#include <iostream>
#define CLUBGFX_VALIDATION_UPLOADS
#include "render.cpp"
int wmain(int argc,wchar_t**argv){
 if(argc!=4)return 2;root=argv[1];art.initialize(argv[2]);fs::path out=argv[3];fs::create_directories(out);logPath=out/L"competition-scroll.log";
 CoInitializeEx(nullptr,COINIT_MULTITHREADED);AddFontResourceExW((art.game/L"data/ui/fonts/eahelveticaneueconbol-mod.ttf").c_str(),FR_PRIVATE,nullptr);
 ID3D11Device*device=nullptr;ID3D11DeviceContext*ctx=nullptr;
 assert(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,D3D11_CREATE_DEVICE_BGRA_SUPPORT,nullptr,0,D3D11_SDK_VERSION,&device,nullptr,&ctx)));assert(renderer.init(device,root.wstring()));
 D3D11_TEXTURE2D_DESC d{};d.Width=1600;d.Height=900;d.MipLevels=d.ArraySize=d.SampleDesc.Count=1;d.Format=DXGI_FORMAT_B8G8R8A8_UNORM;d.Usage=D3D11_USAGE_DEFAULT;d.BindFlags=D3D11_BIND_RENDER_TARGET;
 ID3D11Texture2D*buffer=nullptr,*staging=nullptr;ID3D11RenderTargetView*target=nullptr;assert(SUCCEEDED(device->CreateTexture2D(&d,nullptr,&buffer)));assert(SUCCEEDED(device->CreateRenderTargetView(buffer,nullptr,&target)));
 d.Usage=D3D11_USAGE_STAGING;d.BindFlags=0;d.CPUAccessFlags=D3D11_CPU_ACCESS_READ;assert(SUCCEEDED(device->CreateTexture2D(&d,nullptr,&staging)));
 auto&view=competitions;clubcomp::Competition league;league.root=1;league.name="Liga de teste";league.format="league";league.groups.push_back({});league.groups[0].name="Classificação";
 for(int i=0;i<24;++i){clubcomp::Team t;t.id=567+i;t.rank=i+1;t.name="Clube de teste "+std::to_string(i+1);t.games=20;t.wins=12;t.draws=5;t.losses=3;t.gf=35;t.ga=20;t.points=41-i;t.form="VEVVD";league.groups[0].rows.push_back(t);}
 clubcomp::Competition mixed=league;mixed.root=2;mixed.name="Copa de teste";mixed.format="cup";mixed.groups.clear();
 for(int g=0;g<6;++g){mixed.groups.push_back({});mixed.groups.back().name="Grupo "+std::to_string(g+1);for(int i=0;i<4;++i)mixed.groups.back().rows.push_back(league.groups[0].rows[g*4+i]);}
 view.data.club=567;view.data.date=20261113;view.data.clubName="Clube de teste";view.data.competitions={league,mixed};view.currentClub=567;view.ready=true;view.resetSelection();
 auto paint=[&](const wchar_t*name){
  for(int i=0;i<40;++i)view.tickScrolls(1.f/60);
  D3D11_VIEWPORT before{17,22,800,450,.1f,.9f};D3D11_RECT clip{4,6,8,10};ctx->RSSetViewports(1,&before);ctx->RSSetScissorRects(1,&clip);ctx->OMSetRenderTargets(1,&target,nullptr);const float clear[]{.1f,.1f,.1f,1};ctx->ClearRenderTargetView(target,clear);
  {clubgfx::UiPass pass(ctx,renderer.uiPipeline);renderer.begin(ctx,target,1600,900);view.draw(ctx);pass.restore();}
  D3D11_VIEWPORT after{};UINT count=1;ctx->RSGetViewports(&count,&after);assert(!memcmp(&before,&after,sizeof before));D3D11_RECT afterClip{};count=1;ctx->RSGetScissorRects(&count,&afterClip);assert(!memcmp(&clip,&afterClip,sizeof clip));
  ctx->CopyResource(staging,buffer);D3D11_MAPPED_SUBRESOURCE mapped{};assert(SUCCEEDED(ctx->Map(staging,0,D3D11_MAP_READ,0,&mapped)));std::ofstream file(out/name,std::ios::binary);for(int y=0;y<900;++y)file.write((char*)mapped.pData+size_t(y)*mapped.RowPitch,1600*4);ctx->Unmap(staging,0);
 };
 view.scrollAtPointer(300,400,-120,view.data.competitions[0]);assert(view.nav.focus==0&&view.scroll>0&&view.nav.detail==0);view.tickScrolls(1.f/60);assert(view.tableMotion.position>0&&view.tableMotion.position<view.tableMotion.target);
 view.scrollAtPointer(900,400,-120,view.data.competitions[0]);assert(view.nav.detail>0);view.resetSelection();
 assert(view.beginScrollDrag(736,715,view.data.competitions[0]));view.updateScrollDrag(1000,view.data.competitions[0]);assert(view.scroll==4&&view.nav.detail==0);view.scrollDrag=-1;paint(L"table-bottom.bgra");
 view.resetSelection();assert(view.beginScrollDrag(300,500,view.data.competitions[0]));view.updateScrollDrag(440,view.data.competitions[0]);assert(view.scroll>0&&!view.nav.detail);view.scrollDrag=-1;
 view.data.competitions[0].groups[0].rows.resize(20);view.resetSelection();view.scrollFocused(80,view.data.competitions[0]);assert(!view.scroll&&view.nav.detail==80);paint(L"dashboard-scroll.bgra");
 view.selected=1;view.resetSelection();auto&cup=view.data.competitions[1];assert(view.classificationScroll(cup)==1);
 view.scrollAtPointer(300,400,-120,cup);assert(view.mixedScroll==72&&!view.nav.detail);view.tickScrolls(1.f/60);assert(view.mixedMotion.position>0&&view.mixedMotion.position<72);
 for(int i=0;i<60;++i){view.scrollFocused(520.f/60,cup);view.tickScrolls(1.f/60);}assert(view.mixedScroll==592&&!view.nav.detail);paint(L"mixed-scroll.bgra");
 view.resetSelection();assert(view.beginScrollDrag(736,650,cup));view.updateScrollDrag(1000,cup);assert(view.mixedScroll==view.mixedMaximum(cup));view.scrollDrag=-1;paint(L"mixed-bottom.bgra");
 view.resetSelection();assert(view.beginScrollDrag(300,500,cup));view.updateScrollDrag(300,cup);assert(view.mixedScroll==200&&!view.nav.detail);view.scrollDrag=-1;
 view.nav.focus=3;view.scrollFocused(80,cup);assert(view.nav.detail==80&&view.mixedScroll==200);
 // Shrinking data and selection changes cannot leave blank content or carry
 // a previous card's drag. Pure cup tie scrolling remains independent.
 view.resetSelection();assert(!view.mixedScroll&&!view.mixedMotion.position&&view.scrollDrag==-1);
 cup.groups.clear();cup.rounds.resize(1);cup.rounds[0].ties.resize(6);view.scroll=2;view.tickScrolls(1.f/60);assert(view.scroll==2);
 view.clearTextures();renderer.clear();ctx->ClearState();clubgfx::release(target);clubgfx::release(buffer);clubgfx::release(staging);clubgfx::release(ctx);clubgfx::release(device);CoUninitialize();
 std::cout<<"PASS competition scrolling: mouse focus/wheel, content and scrollbar drag, continuous right stick routing, short-table fallback, mixed groups, selection reset and WARP clipping/state restoration\n";
}
