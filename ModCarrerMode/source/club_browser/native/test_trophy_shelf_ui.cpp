// Render the actual native cabinet without launching or controlling FIFA.
#include "render.cpp"
#include <cassert>
#include <iostream>
trophy_shelf::Status shelfFixture;
extern "C" __declspec(dllexport) unsigned WINAPI Fifa16TrophyRoomUiMode(){return shelfFixture.list?0u:shelfFixture.detail?2u:1u;}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16TrophyShelfStatus(trophy_shelf::Status*out){*out=shelfFixture;return TRUE;}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16TrophyRoomCommand(const char*){return TRUE;}
int wmain(int argc,wchar_t**argv){
 assert(argc==3);CoInitializeEx(nullptr,COINIT_MULTITHREADED);art.initialize(argv[1]);root=art.game/L"ModCarrerMode/data/club_browser";logPath=fs::path(argv[2])/L"shelf-test.log";
 AddFontResourceExW((art.game/L"data/ui/fonts/eahelveticaneueconbol-mod.ttf").c_str(),FR_PRIVATE,nullptr);
 ComPtr<ID3D11Device>dev;ComPtr<ID3D11DeviceContext>context;assert(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&dev,nullptr,&context)));
 assert(renderer.init(dev.Get(),root.wstring()));gameImage(dev.Get(),renderer.clubIcon,art,{"data/ui/imgAssets/crest/light/l1043.dds"});assert(renderer.clubIcon.view);
 shelfFixture.pid=GetCurrentProcessId();shelfFixture.club=1043;shelfFixture.epoch=1;shelfFixture.generation=1;shelfFixture.total=18;shelfFixture.ready=1;
 const auto previewGame=fs::path(argv[2])/L"preview-game";if(fs::is_directory(previewGame))art.game=previewGame;
 shelfPublication.state=shelfFixture;shelfPublication.next=GetTickCount64()+60000;
 const unsigned ids[]={1003,7,229,9,1009,23};const char*names[]={"CONMEBOL Libertadores","Brasileirão Betano","Copa Betano do Brasil","Supercopa Rei","CONMEBOL Recopa","Campeonato estadual"};
 for(unsigned i=0;i<18;++i){ShelfRow row;row.trophy=row.competition=ids[i%6];row.club=1043;row.year=2026-i/6;row.date=row.year*10000+101;row.name=names[i%6];row.clubName="Flamengo";row.origin="preview";
  for(const auto&file:fs::directory_iterator(previewGame/L"data/sceneassets/server16_trophy_room/thumbnails"))if(file.path().filename().wstring().rfind(L"t"+std::to_wstring(row.trophy)+L"_",0)==0)row.thumbnail=fs::relative(file.path(),previewGame).generic_string();
  row.titles=i==0?12:1;for(unsigned j=0;j<row.titles;++j)row.wins.push_back({2026-j,1043,(2026-j)*10000+101,"Flamengo"});shelfPublication.rows.push_back(row);}
 D3D11_TEXTURE2D_DESC d{};d.Width=1600;d.Height=900;d.MipLevels=d.ArraySize=d.SampleDesc.Count=1;d.Format=DXGI_FORMAT_R8G8B8A8_UNORM;d.BindFlags=D3D11_BIND_RENDER_TARGET;
 ComPtr<ID3D11Texture2D>color,copy;ComPtr<ID3D11RenderTargetView>target;assert(SUCCEEDED(dev->CreateTexture2D(&d,nullptr,&color))&&SUCCEEDED(dev->CreateRenderTargetView(color.Get(),nullptr,&target)));
 d.BindFlags=0;d.Usage=D3D11_USAGE_STAGING;d.CPUAccessFlags=D3D11_CPU_ACCESS_READ;assert(SUCCEEDED(dev->CreateTexture2D(&d,nullptr,&copy)));
 const float gray[]={.1f,.1f,.1f,1};context->ClearRenderTargetView(target.Get(),gray);
 {clubgfx::UiPass saved(context.Get(),renderer.uiPipeline);renderer.begin(context.Get(),target.Get(),1600,900);renderer.normal(context.Get());scene_loading::Status status;drawTrophyShelf(context.Get(),GetModuleHandleW(nullptr),status,L"Flamengo");}
 context->CopyResource(copy.Get(),color.Get());D3D11_MAPPED_SUBRESOURCE m{};assert(SUCCEEDED(context->Map(copy.Get(),0,D3D11_MAP_READ,0,&m)));
 std::ofstream out(fs::path(argv[2])/L"native-preview.rgba",std::ios::binary);unsigned gold=0;
 for(unsigned y=0;y<900;++y){auto*row=static_cast<unsigned char*>(m.pData)+y*m.RowPitch;out.write((const char*)row,1600*4);for(unsigned x=0;x<1600;++x){const auto*p=row+x*4;if(y>840)assert(p[0]<30&&p[1]<30&&p[2]<30);if(abs(int(p[0])-185)<3&&abs(int(p[1])-162)<3&&abs(int(p[2])-116)<3)++gold;}}
 context->Unmap(copy.Get(),0);assert(gold>100);unsigned icons=0;for(auto&t:shelfCups)if(t.view)++icons;assert(icons==18);
 out.close();for(auto&t:shelfCups)assert(t.w==256&&t.h==256);
 // Render the real, unlit white detail panel with a scrollable multi-win history.
 shelfFixture.list=0;shelfFixture.detail=1;shelfFixture.detailScroll=2;
 detailPublication.state=shelfFixture;detailPublication.next=GetTickCount64()+60000;detailPublication.rows=shelfPublication.rows;
 context->ClearRenderTargetView(target.Get(),gray);
 {clubgfx::UiPass saved(context.Get(),renderer.uiPipeline);renderer.begin(context.Get(),target.Get(),1600,900);renderer.normal(context.Get());assert(drawTrophyHistory(context.Get(),GetModuleHandleW(nullptr)));}
 context->CopyResource(copy.Get(),color.Get());assert(SUCCEEDED(context->Map(copy.Get(),0,D3D11_MAP_READ,0,&m)));std::ofstream history(fs::path(argv[2])/L"history-preview.rgba",std::ios::binary);
 for(unsigned y=0;y<900;++y){auto*row=static_cast<unsigned char*>(m.pData)+y*m.RowPitch;history.write((const char*)row,1600*4);if(y>840)for(unsigned x=0;x<1600;++x)assert(row[x*4]<30&&row[x*4+1]<30&&row[x*4+2]<30);}
 context->Unmap(copy.Get(),0);
 // A single conquest has a compact card, its exact date and one winning
 // club. It must leave the unused lower viewport available to the camera.
 shelfFixture.selected=0;shelfFixture.total=4;shelfFixture.detailScroll=0;detailPublication.state=shelfFixture;detailPublication.next=GetTickCount64()+60000;
 detailPublication.rows[0]=shelfPublication.rows[2];detailPublication.rows[0].year=2027;detailPublication.rows[0].date=20271205;
 context->ClearRenderTargetView(target.Get(),gray);
 {clubgfx::UiPass saved(context.Get(),renderer.uiPipeline);renderer.begin(context.Get(),target.Get(),1600,900);renderer.normal(context.Get());assert(drawTrophyHistory(context.Get(),GetModuleHandleW(nullptr)));}
 context->CopyResource(copy.Get(),color.Get());assert(SUCCEEDED(context->Map(copy.Get(),0,D3D11_MAP_READ,0,&m)));std::ofstream single(fs::path(argv[2])/L"single-history-preview.rgba",std::ios::binary);
 for(unsigned y=0;y<900;++y){auto*row=static_cast<unsigned char*>(m.pData)+y*m.RowPitch;single.write((const char*)row,1600*4);if(y>=660)for(unsigned x=1070;x<1544;++x)assert(row[x*4]<30&&row[x*4+1]<30&&row[x*4+2]<30);}
 context->Unmap(copy.Get(),0);single.close();shelfFixture.selected=0;shelfFixture.total=18;
 // Render the same native gallery over FIFA's existing BOOTFLOW artwork.
 // This is a visual preview only; the running game supplies this image through
 // its own background provider, behind the UI and its original help footer.
 auto previewReader=art.game;art.game=fs::path(argv[1]);clubgfx::Texture wallpaper;
 assert(gameImage(dev.Get(),wallpaper,art,{"data/ui/imgAssets/backgroundstadiums/st_bootflow.DDS"}));art.game=previewReader;
 shelfFixture.list=1;shelfFixture.detail=0;shelfFixture.detailScroll=0;
 {clubgfx::UiPass saved(context.Get(),renderer.uiPipeline);renderer.begin(context.Get(),target.Get(),1600,900);renderer.normal(context.Get());renderer.quad(context.Get(),0,0,1600,900,wallpaper.view);scene_loading::Status loading;drawTrophyShelf(context.Get(),GetModuleHandleW(nullptr),loading,L"Flamengo");}
 context->CopyResource(copy.Get(),color.Get());assert(SUCCEEDED(context->Map(copy.Get(),0,D3D11_MAP_READ,0,&m)));std::ofstream gallery(fs::path(argv[2])/L"gallery-preview.rgba",std::ios::binary);
 unsigned footerInk=0;
 for(unsigned y=0;y<900;++y){const auto*row=static_cast<unsigned char*>(m.pData)+y*m.RowPitch;gallery.write((const char*)row,1600*4);
  if(y>=838&&y<893)for(unsigned x=60;x<1540;++x){const auto*p=row+x*4;if(p[0]>180&&p[1]>180&&p[2]>180)++footerInk;}}
 context->Unmap(copy.Get(),0);gallery.close();wallpaper.clear();
 // During loading only a small centred card may cover the photograph. The
 // actual FIFA HelpManager is rendered by the engine, never this HUD.
 for(bool trophy:{true,false}){
 context->ClearRenderTargetView(target.Get(),gray);
 {clubgfx::UiPass saved(context.Get(),renderer.uiPipeline);renderer.begin(context.Get(),target.Get(),1600,900);renderer.normal(context.Get());scene_loading::Status loading;loading.loaded=25;loading.total=50;drawIndoorLoading(context.Get(),loading,L"Flamengo",trophy);}
 context->CopyResource(copy.Get(),color.Get());assert(SUCCEEDED(context->Map(copy.Get(),0,D3D11_MAP_READ,0,&m)));std::ofstream loading(fs::path(argv[2])/(trophy?L"loading-preview.rgba":L"room-loading-preview.rgba"),std::ios::binary);
 unsigned panel=0;for(unsigned y=0;y<900;++y){const auto*row=static_cast<unsigned char*>(m.pData)+y*m.RowPitch;loading.write((const char*)row,1600*4);for(unsigned x=0;x<1600;++x){const auto*p=row+x*4;if(y<330||y>=542||x<514||x>=1086)assert(p[0]<30&&p[1]<30&&p[2]<30);if(p[0]>200&&p[1]>200&&p[2]>200)++panel;}}
 context->Unmap(copy.Get(),0);assert(panel>50000&&panel<125000);
 }
 renderer.clear();std::cout<<"PASS native cabinet: centred cups, multi-win history, compact real-progress loading, untouched native-footer area, restored GPU state\n";
}
