// Shared, crisp native HUD. Loading uses the real component progress; no
// animated cards, texture repaints or synthetic countdowns are involved.
using Microsoft::WRL::ComPtr;
void indoorProgress(ID3D11DeviceContext*c,const scene_loading::Status&s,float x,float y,float width,int&label){
 const float progress=scene_loading::progress(s);renderer.rectangle(c,x,y,width,9,0xffece7dc);
 if(progress>=0)renderer.rectangle(c,x,y,width*progress,9,uitheme::accent());
 else {const float segment=width*.2f,offset=float(GetTickCount64()%1800)/1800*(width-segment);renderer.rectangle(c,x+offset,y,segment,9,uitheme::accent());}
 std::wstring text=s.error?L"Volte e entre novamente":s.ready?L"Pronto":progress<0?L"Preparando os dados do clube…":s.loaded>=s.total?L"Finalizando a cena…":std::to_wstring(s.loaded)+L" de "+std::to_wstring(s.total)+L" recursos carregados · "+std::to_wstring(int(progress*100))+L"%";
 renderer.label(c,label++,text,x,y+20,int(width),32,21,RGB(126,105,67),true);
}
void drawIndoorLoading(ID3D11DeviceContext* context,const scene_loading::Status&status,const std::wstring&name,bool trophy){
  // The existing native background remains behind this compact status card.
  // Never paint a full-screen white surface over the room or FIFA's footer.
  const float x=515,y=332,w=570;int label=0;
  renderer.rectangle(context,x,y,w,208,0xfffafbfc);
  renderer.rectangle(context,x,y,w,4,uitheme::accent());
  containImage(context,renderer.clubIcon,x+26,y+28,62,72);
  renderer.label(context,label++,name,x+108,y+26,432,36,27,RGB(51,75,86));
  renderer.label(context,label++,status.error?L"Não foi possível preparar o ambiente":trophy?L"Preparando a sala de troféus…":L"Preparando o vestiário…",x+108,y+66,432,30,21,RGB(105,121,129));
  const float progress=scene_loading::progress(status);
  const unsigned percent=progress<0?0:unsigned(progress*100);
  renderer.label(context,label++,std::to_wstring(percent)+L"%",x+26,y+112,518,34,25,RGB(126,105,67),true);
  renderer.rectangle(context,x+26,y+154,w-52,8,0xffece7dc);
  if(progress>=0)renderer.rectangle(context,x+26,y+154,(w-52)*progress,8,uitheme::accent());
  renderer.label(context,label++,status.error?L"Volte e tente novamente":!status.total?L"Aguarde, preparando os dados do clube…":status.loaded>=status.total?L"Finalizando a cena…":std::to_wstring(status.loaded)+L" de "+std::to_wstring(status.total)+L" recursos carregados",x+26,y+171,518,25,18,RGB(105,121,129),true);
}
void drawRoomBackgroundLoading(ID3D11DeviceContext* context,const scene_loading::Status&status){
 // Keep this above the hub, while its native image provider covers the scene.
 // A solid surface and separate rows keep the activity bar visible even
 // before the Python worker has published the first resource count.
 int label=0;renderer.rectangle(context,1110,22,430,130,0xffffffff);
 renderer.label(context,label++,L"Preparando o vestiário…",1128,31,394,30,22,RGB(57,73,82),true);
 indoorProgress(context,status,1130,77,390,label);
}
std::wstring indoorClubName(unsigned club,bool trophy){
 static unsigned selected=0;static uint64_t next=0;static std::wstring name;
 const auto now=GetTickCount64();if(selected==club&&now<next)return name;selected=club;next=now+500;name=L"Clube";
 for(const auto& row:model.rows)if(row.id==int(club)){name=wide(row.name);return name;}
 for(auto file:{art.game/L"ModCarrerMode/runtime/club_environment/room/runtime/room_context_r46.json",art.game/L"ModCarrerMode/runtime/trophy_room/loading_identity.json"}){
  std::ifstream in(file);char bytes[4096]{};in.read(bytes,sizeof bytes-1);std::string body(bytes,size_t(in.gcount()));
  auto number=[&](const char*key){const auto at=body.find(key);if(at==body.npos)return 0u;const auto colon=body.find(':',at);return colon==body.npos?0u:unsigned(strtoul(body.c_str()+colon+1,nullptr,10));};
  if(number("\"pid\"")!=GetCurrentProcessId()||number("\"club\"")!=club)continue;
  auto at=body.find("\"club_name\"");if(at==body.npos)continue;at=body.find(':',at);std::istringstream value(body.substr(at+1));std::string text;if(value>>std::quoted(text)){name=wide(text);break;}
 }
 return name;
}
#include "trophy_shelf_ui.inc"
bool indoorSceneUi(IDXGISwapChain* swap){
 char pageName[128]{};if(!readPage(pageName))return false;
 const bool trophy=!strcmp(pageName,"game/screens/career/server16/TrophyRoom"),room=!strcmp(pageName,"game/screens/career/server16/DressingRoom");
 const bool background=!trophy&&!room;
 if(background&&strcmp(pageName,"game/screens/fluxHub/FluxHub")&&strcmp(pageName,"game/screens/misc/StadiumPan"))return false;
 const auto module=GetModuleHandleW(trophy?L"trophy_room.dll":L"native_dressing_room.dll");
 using Query=BOOL(WINAPI*)(scene_loading::Status*);const auto query=module?reinterpret_cast<Query>(GetProcAddress(module,trophy?"Fifa16TrophyRoomLoadingStatus":"Fifa16RoomLoadingStatus")):nullptr;
 scene_loading::Status status;if(!query||!query(&status)||status.version!=1||status.size!=sizeof status)return false;
 if(background&&(!(status.variant&4)||!status.visible||status.ready))return false;
 const bool shelf=trophy&&(status.variant&2);
 const bool loading=!status.ready;if(!loading&&!trophy)return false;
 // This can be the first mod screen in a new session, before the globe has
 // initialized WIC on the render thread.
 static thread_local bool comReady=false;if(!comReady){CoInitializeEx(nullptr,COINIT_MULTITHREADED);comReady=true;}
 static bool fontLoaded=false;if(!fontLoaded){auto font=art.game/L"data/ui/fonts/eahelveticaneueconbol-mod.ttf";fontLoaded=AddFontResourceExW(font.c_str(),FR_PRIVATE,nullptr)!=0;}
 if(!status.club)status.club=unsigned(std::max(0,careerClub()));
 ComPtr<ID3D11Device>device;ComPtr<ID3D11DeviceContext>context;ComPtr<ID3D11Texture2D>back;ComPtr<ID3D11RenderTargetView>target;
 if(FAILED(swap->GetDevice(IID_PPV_ARGS(&device)))||FAILED(swap->GetBuffer(0,IID_PPV_ARGS(&back))))return true;
 device->GetImmediateContext(&context);D3D11_TEXTURE2D_DESC desc{};back->GetDesc(&desc);
 if(!context||FAILED(device->CreateRenderTargetView(back.Get(),nullptr,&target))||!renderer.init(device.Get(),root.wstring()))return true;
 clubgfx::UiPass saved(context.Get(),renderer.uiPipeline);renderer.begin(context.Get(),target.Get(),float(desc.Width),float(desc.Height));renderer.normal(context.Get());
 gameImage(renderer.device,renderer.clubIcon,art,{"data/ui/imgAssets/crest/light/l"+std::to_string(status.club)+".dds","data/ui/imgAssets/crest/dark/l"+std::to_string(status.club)+".dds"});
 const auto name=indoorClubName(status.club,trophy);int label=0;
 if(background){
  // The native BOOTFLOW image hides partial geometry BEHIND the hub cards.
  // Only this compact progress hint is drawn above, outside their area.
  drawRoomBackgroundLoading(context.Get(),status);saved.restore();return false;
 }
 if(shelf){DXGI_SWAP_CHAIN_DESC description{};if(SUCCEEDED(swap->GetDesc(&description))){attachInputWindow(description.OutputWindow);rosterMouseActive=true;}drawTrophyShelf(context.Get(),module,status,name);saved.restore();return true;}
 if(loading){
  drawIndoorLoading(context.Get(),status,name,trophy);
 }else{
  const bool details=drawTrophyHistory(context.Get(),module);
  if(!details)shelfViewTabs(context.Get(),label,false);
  containImage(context.Get(),renderer.clubIcon,60,50,62,72);
  renderer.label(context.Get(),label++,L"SALA DE TROFÉUS",146,51,900,45,35,RGB(255,255,255));
  renderer.label(context.Get(),label++,name+((status.variant&1)?L" · Carreira do treinador":L" · Conquistas do clube"),148,101,900,31,20,RGB(224,231,235));
  if(details){DXGI_SWAP_CHAIN_DESC description{};if(SUCCEEDED(swap->GetDesc(&description))){attachInputWindow(description.OutputWindow);rosterMouseActive=true;}saved.restore();return true;}
 }
 saved.restore();return loading;
}
