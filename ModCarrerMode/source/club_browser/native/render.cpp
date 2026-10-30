#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <d3d11.h>
#include <dxgi.h>
#include <psapi.h>
#include <xinput.h>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <array>
#include <cstring>
#include <cstdint>
#include "../../common/custom_ui_theme.h"
#include "model.h"
#include "room_roster_mode.h"
#include "graphics.h"
#include "globe_texture.h"
#include "native_scene.h"
#include "lineup_view.h"
#include "roster_view.h"
#include "coach_view.h"
#include "mascot_view.h"
#include "competitions_model.h"
#include "competitions_layout.h"
#include "ranking_model.h"
#include "../../server16_py/d3d_overlay/third_party/reshade/reshade_events.hpp"
namespace fs=std::filesystem;
namespace {
HMODULE own=nullptr,reshadeModule=nullptr;uintptr_t executable=0;fs::path root,logPath;LONG started=0,stopped=0;std::mutex drawLock;thread_local bool drawing=false;HWND gameWindow=nullptr;
clublineup::View lineup;clubassets::Reader art;clubs::Model model;clubgfx::Renderer renderer;bool entered=false,roomEntry=false;int entryKind=0;ULONGLONG lastFrame=0,enteredAt=0;
#ifdef CLUB_BROWSER_VALIDATION
std::atomic<int> validationClub{-1};std::atomic<bool> validationCapture{false};
#endif
std::atomic<bool>rosterMouseActive{false};std::atomic<int>wheelDelta{0};HWND inputWindow=nullptr;WNDPROC originalWindowProc=nullptr;
LRESULT CALLBACK rosterWindowProc(HWND window,UINT message,WPARAM w,LPARAM l){if(message==WM_MOUSEWHEEL&&rosterMouseActive&&!stopped){wheelDelta.fetch_add((short)HIWORD(w));return 0;}return originalWindowProc?CallWindowProcW(originalWindowProc,window,message,w,l):DefWindowProcW(window,message,w,l);}
void attachInputWindow(HWND window){if(inputWindow==window)return;if(inputWindow&&originalWindowProc&&(WNDPROC)GetWindowLongPtrW(inputWindow,GWLP_WNDPROC)==rosterWindowProc)SetWindowLongPtrW(inputWindow,GWLP_WNDPROC,(LONG_PTR)originalWindowProc);inputWindow=window;originalWindowProc=(WNDPROC)GetWindowLongPtrW(window,GWLP_WNDPROC);SetWindowLongPtrW(window,GWLP_WNDPROC,(LONG_PTR)rosterWindowProc);}
using Present=HRESULT(WINAPI*)(IDXGISwapChain*,UINT,UINT);Present originalPresent=nullptr;void** hookedTable=nullptr;
using ReadPad=DWORD(WINAPI*)(DWORD,XINPUT_STATE*);ReadPad readPad=nullptr;
void log(const char* value){std::ofstream out(logPath,std::ios::app);out<<GetTickCount64()<<" pid="<<GetCurrentProcessId()<<" "<<value<<"\n";}
bool read(uintptr_t at,void* out,size_t count){SIZE_T got=0;return at>=0x10000&&ReadProcessMemory(GetCurrentProcess(),(void*)at,out,count,&got)&&got==count;}
template<class T>T get(uintptr_t at){T result{};read(at,&result,sizeof(result));return result;}
bool readPage(char (&name)[128]){uintptr_t p=get<uintptr_t>(executable+0x3809030);for(unsigned offset:{232u,192u,136u,472u}){if(!p)return false;p=get<uintptr_t>(p+offset);}return read(p,name,127)&&memchr(name,0,128);}
int careerClub();
int pageKind(){char name[128]{};if(!readPage(name))return 0;if(!strcmp(name,"game/screens/career/server16/CareerCompetitions"))return 3;if(!strcmp(name,"game/screens/career/server16/WorldClubRanking"))return 4;if(!strcmp(name,"game/screens/career/server16/WorldNationRanking"))return 5;if(clubs::roomRosterMode.visible(name,careerClub()))return 2;if(!clubs::isDressingRoomPage(name))clubs::roomRosterMode.close();return clubs::isRoomPlayersPage(name)?2:clubs::isPage(name)?1:0;}
bool page(){return pageKind()!=0;}
std::wstring wide(const std::string& value){if(value.empty())return {};int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,value.data(),int(value.size()),nullptr,0);if(!n)return L"—";std::wstring out(size_t(n),L' ');MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,value.data(),int(value.size()),out.data(),n);return out;}
int careerClub(){struct Record{DWORD schema,size,sequence,pid;uintptr_t service,vtable,registry;DWORD epoch,thread;};auto host=GetModuleHandleW(L"dinput8.dll");auto pointer=host?(uintptr_t)GetProcAddress(host,"Fifa16CareerContextRead"):0;Record a{},b{};if(!read(pointer,&a,sizeof(a))||a.schema!=1||a.size!=sizeof(a)||a.sequence&1||a.pid!=GetCurrentProcessId()||get<uintptr_t>(a.service)!=a.vtable)return 0;int selected=get<int>(a.service+0x14);if(selected<0||selected>7)return 0;auto context=get<uintptr_t>(a.service+0x18)+uintptr_t(selected)*0x318;int id=get<int>(context+0x1a4);if(get<int>(context+0x18c)!=1||!read(pointer,&b,sizeof(b))||memcmp(&a,&b,sizeof(a)))return 0;return id;}
bool loadCatalog(){auto generated=art.game/L"ModCarrerMode/runtime/club_browser/catalog";std::ifstream in(fs::is_regular_file(generated/L"catalog.tsv")?generated/L"catalog.tsv":root/L"catalog.tsv");if(!in||!model.load(in)){log("CATALOG_INVALID");return false;}std::ifstream nations(fs::is_regular_file(generated/L"nations.tsv")?generated/L"nations.tsv":root/L"nations.tsv");if(nations&&!model.loadNations(nations))log("NATIONS_CATALOG_INVALID");auto font=art.game/L"data/ui/fonts/eahelveticaneueconbol-mod.ttf";AddFontResourceExW(font.c_str(),FR_PRIVATE,nullptr);log("CATALOG_READY");return true;}
}

bool clubgfx::Renderer::init(ID3D11Device* dev,const std::wstring& path){
 if(device==dev&&vs&&globe)return true;clear();device=dev;device->AddRef();
 const char* source=R"hlsl(
 cbuffer Params:register(b0){float4 p0;float4 p1;float4 p2;float4 p3;};
 Texture2D surface:register(t0);Texture2D atlas:register(t1);SamplerState smoothMap:register(s0);SamplerState nearestMap:register(s1);
 struct VertexIn{float2 pos:POSITION;float2 uv:TEXCOORD;};struct PixelIn{float4 pos:SV_POSITION;float2 uv:TEXCOORD;};
 PixelIn VS(VertexIn v){PixelIn o;o.pos=float4(v.pos,0,1);o.uv=v.uv;return o;}
 float4 PS(PixelIn v):SV_TARGET{return surface.Sample(smoothMap,v.uv)*p0;}
 float countryAt(int2 p){return floor(atlas.Load(int3((p.x+8192)%8192,clamp(p.y,0,4095),0)).r*255+.5);}
 float4 Earth(PixelIn v):SV_TARGET{
  float2 q=float2((v.uv.x*p1.y+p1.z)*2-1,1-(v.uv.y*p1.w+p2.x)*2);float3 eye=float3(0,0,3.8/p0.z);float3 ray=normalize(float3(q.x*p1.x/2.3,q.y/2.3,-1));float b=dot(eye,ray),disc=b*b-dot(eye,eye)+1;if(disc<0)discard;float t=-b-sqrt(disc);float3 n=eye+ray*t;
  float sy=sin(p0.x),cy=cos(p0.x),sx=sin(p0.y),cx=cos(p0.y);float3 unpitched=float3(n.x,cx*n.y+sx*n.z,-sx*n.y+cx*n.z);float3 local=float3(cy*unpitched.x-sy*unpitched.z,unpitched.y,sy*unpitched.x+cy*unpitched.z);float2 uv=float2(atan2(local.x,local.z)/6.283185307+.5,.5-asin(clamp(local.y,-1.,1.))/3.141592654);
  float2 grid=uv*float2(8192,4096)-.5,f=frac(grid);int2 cell=int2(floor(grid));float4 ids=float4(countryAt(cell),countryAt(cell+int2(1,0)),countryAt(cell+int2(0,1)),countryAt(cell+int2(1,1)));
  // Interpolate membership, never IDs (blending numeric IDs invents countries).
  float4 weights=float4((1-f.x)*(1-f.y),f.x*(1-f.y),(1-f.x)*f.y,f.x*f.y);float land=dot(step(.5,ids),weights);float selected=dot(1-step(.4,abs(ids-p0.w)),weights);
  // Country IDs need nearest sampling; the independent distance channel is
  // linear. Its screen-space footprint keeps outlines smooth at close zoom.
  float2 dx=ddx(uv),dy=ddy(uv);dx.x-=round(dx.x);dy.x-=round(dy.x);float footprint=clamp(max(length(dx*float2(8192,4096)),length(dy*float2(8192,4096))),.25,8.);
  float distance=atlas.Sample(smoothMap,uv).g*16;float edge=1-smoothstep(max(0,max(.65,footprint*.65)-max(.4,footprint*.5)),max(.65,footprint*.65)+max(.4,footprint*.5),distance);
  float3 base=pow(surface.SampleGrad(smoothMap,uv,dx,dy).rgb,.78);base=lerp(base,float3(.045,.35,.68),(1-land)*.30);base=lerp(base,float3(.40,.77,.40),selected*.12);base=lerp(base,lerp(float3(.84,.92,.87),float3(.82,1,.76),selected),edge*(.16+.54*selected));
  float incidence=max(0,dot(n,normalize(float3(-.45,.55,1))));float rim=pow(1-max(n.z,0),3);return float4(base*(.83+.27*incidence)+float3(.025,.10,.16)*rim,1);
 })hlsl";
 ID3DBlob *vertex=nullptr,*pixel=nullptr,*earthCode=nullptr,*error=nullptr;
 auto compile=[&](const char* entry,const char* profile,ID3DBlob** out){auto hr=D3DCompile(source,strlen(source),nullptr,nullptr,nullptr,entry,profile,0,0,out,&error);if(FAILED(hr)){if(error)log((const char*)error->GetBufferPointer());clubgfx::release(error);return false;}clubgfx::release(error);return true;};
 if(!compile("VS","vs_4_0",&vertex)||!compile("PS","ps_4_0",&pixel)||!compile("Earth","ps_4_0",&earthCode)){clubgfx::release(vertex);clubgfx::release(pixel);clubgfx::release(earthCode);clear();return false;}
 D3D11_INPUT_ELEMENT_DESC elements[]={{"POSITION",0,DXGI_FORMAT_R32G32_FLOAT,0,0,D3D11_INPUT_PER_VERTEX_DATA,0},{"TEXCOORD",0,DXGI_FORMAT_R32G32_FLOAT,0,8,D3D11_INPUT_PER_VERTEX_DATA,0}};
 bool ok=SUCCEEDED(dev->CreateVertexShader(vertex->GetBufferPointer(),vertex->GetBufferSize(),nullptr,&vs))&&SUCCEEDED(dev->CreatePixelShader(pixel->GetBufferPointer(),pixel->GetBufferSize(),nullptr,&ps))&&SUCCEEDED(dev->CreatePixelShader(earthCode->GetBufferPointer(),earthCode->GetBufferSize(),nullptr,&globe))&&SUCCEEDED(dev->CreateInputLayout(elements,2,vertex->GetBufferPointer(),vertex->GetBufferSize(),&layout));release(vertex);release(pixel);release(earthCode);
 D3D11_BUFFER_DESC bd{};bd.ByteWidth=96*sizeof(Vertex);bd.Usage=D3D11_USAGE_DYNAMIC;bd.BindFlags=D3D11_BIND_VERTEX_BUFFER;bd.CPUAccessFlags=D3D11_CPU_ACCESS_WRITE;ok=ok&&SUCCEEDED(dev->CreateBuffer(&bd,nullptr,&vb));bd={};bd.ByteWidth=64;bd.Usage=D3D11_USAGE_DEFAULT;bd.BindFlags=D3D11_BIND_CONSTANT_BUFFER;ok=ok&&SUCCEEDED(dev->CreateBuffer(&bd,nullptr,&constants));
 D3D11_BLEND_DESC blendDesc{};auto& rt=blendDesc.RenderTarget[0];rt.BlendEnable=TRUE;rt.SrcBlend=D3D11_BLEND_SRC_ALPHA;rt.DestBlend=D3D11_BLEND_INV_SRC_ALPHA;rt.BlendOp=D3D11_BLEND_OP_ADD;rt.SrcBlendAlpha=D3D11_BLEND_ONE;rt.DestBlendAlpha=D3D11_BLEND_INV_SRC_ALPHA;rt.BlendOpAlpha=D3D11_BLEND_OP_ADD;rt.RenderTargetWriteMask=D3D11_COLOR_WRITE_ENABLE_ALL;ok=ok&&SUCCEEDED(dev->CreateBlendState(&blendDesc,&blend));
 D3D11_DEPTH_STENCIL_DESC depth{};depth.DepthEnable=FALSE;depth.DepthWriteMask=D3D11_DEPTH_WRITE_MASK_ZERO;depth.DepthFunc=D3D11_COMPARISON_ALWAYS;ok=ok&&SUCCEEDED(dev->CreateDepthStencilState(&depth,&ds));D3D11_RASTERIZER_DESC rd{};rd.FillMode=D3D11_FILL_SOLID;rd.CullMode=D3D11_CULL_NONE;rd.DepthClipEnable=TRUE;ok=ok&&SUCCEEDED(dev->CreateRasterizerState(&rd,&raster));
 D3D11_SAMPLER_DESC sd{};sd.Filter=D3D11_FILTER_MIN_MAG_MIP_LINEAR;sd.AddressU=D3D11_TEXTURE_ADDRESS_WRAP;sd.AddressV=sd.AddressW=D3D11_TEXTURE_ADDRESS_CLAMP;sd.MaxLOD=D3D11_FLOAT32_MAX;ok=ok&&SUCCEEDED(dev->CreateSamplerState(&sd,&linear));sd.Filter=D3D11_FILTER_MIN_MAG_MIP_POINT;ok=ok&&SUCCEEDED(dev->CreateSamplerState(&sd,&nearest));
 const unsigned whitePixel=0xffffffff;std::vector<unsigned> pixels(64*64);for(int y=0;y<64;++y)for(int x=0;x<64;++x){float d=std::sqrt(float((x-31.5f)*(x-31.5f)+(y-31.5f)*(y-31.5f)))/31.5f;unsigned a=unsigned(std::clamp((1-d)*4,0.f,1.f)*255);pixels[y*64+x]=(a<<24)|0x00e4faff;}
 ok=ok&&upload(dev,dot,pixels.data(),64,64)&&upload(dev,white,&whitePixel,1,1)&&globeSurface(dev,earth,path+L"/assets/globe/earth.dds")&&globeAtlas(dev,atlas,path+L"/assets/globe/atlas-hd.png");if(!ok){log("GRAPHICS_INITIALIZATION_FAILED");clear();return false;}log("GRAPHICS_READY");return true;
}

namespace {
void prepareClub();
#include "roster_ui.inc"
#include "mascot_ui.inc"
#include "competitions_ui.inc"
#include "ranking_ui.inc"
void drawContent(ID3D11DeviceContext* context){auto& r=renderer;const auto& c=model.club();const auto white=RGB(255,255,255),ink=RGB(52,77,90),muted=RGB(118,141,151);int label=0;
 auto text=[&](std::wstring value,float x,float y,int w,int h,int size,COLORREF color,bool centered=false){r.label(context,label++,value,x,y,w,h,size,color,centered);};
 float params[16]={model.yaw,model.pitch,model.zoom,float(c.world),clubs::GlobeView::w/clubs::GlobeView::h,1600.f/clubs::GlobeView::w,-clubs::GlobeView::x/clubs::GlobeView::w,760.f/clubs::GlobeView::h,-clubs::GlobeView::y/clubs::GlobeView::h};context->UpdateSubresource(r.constants,0,nullptr,params,0,0);context->PSSetConstantBuffers(0,1,&r.constants);context->PSSetShader(r.globe,nullptr,0);context->PSSetShaderResources(1,1,&r.atlas.view);r.quad(context,0,0,1600,760,r.earth.view);r.normal(context);
 // Surface points are projected with the same camera/ray model as Earth.
 // The horizon test uses the tangent plane, so back-side cities never float.
 for(auto i:model.choices(2)){const auto& club=model.rows[i];if(club.lat==0&&club.lon==0)continue;auto p=clubs::project(club.lat,club.lon,model.yaw,model.pitch,model.zoom);if(!p.visible||p.x<470||p.x>1570||p.y<245||p.y>754)continue;constexpr float size=7;float glow[16]={.35f,.85f,1,.45f};context->UpdateSubresource(r.constants,0,nullptr,glow,0,0);r.quad(context,p.x-size,p.y-size,size*2,size*2,r.dot.view);r.normal(context);r.quad(context,p.x-2.5f,p.y-2.5f,5,5,r.dot.view);}
 for(int i=0;i<3;++i){float y=i==0?150.f:i==1?258.f:366.f,h=i==2?340.f:96.f;bool selected=model.focus==i;r.normal(context);r.rectangle(context,64,y,400,h,selected?uitheme::accent():0xffeef2f4);if(selected){r.rectangle(context,64,y,400,2,uitheme::focus());r.rectangle(context,64,y+h-2,400,2,uitheme::focus());r.rectangle(context,64,y,2,h,uitheme::focus());r.rectangle(context,462,y,2,h,uitheme::focus());}COLORREF color=selected?uitheme::selectedText():ink;std::wstring name=i==0?wide(c.countryName):i==1?wide(model.national?c.city:c.leagueName):wide(c.name);text(i==0?(model.national?L"CONFEDERAÇÃO":L"PAÍS / REGIÃO"):i==1?(model.national?L"PAÍS":L"LIGA"):(model.national?L"SELEÇÃO":L"CLUBE"),83,y+8,250,25,18,color);
  int optionKind=model.national&&i==1?2:i;auto options=model.choices(optionKind);size_t at=0;for(size_t j=0;j<options.size();++j){const auto& v=model.rows[options[j]];if(optionKind==0?v.country==c.country:optionKind==1?v.league==c.league:v.id==c.id){at=j;break;}}text(std::to_wstring(at+1)+L" / "+std::to_wstring(options.size()),375,y+8,70,25,16,color,true);
  text(L"‹",74,y+(i==2?143:37),25,40,37,color,true);text(L"›",426,y+(i==2?143:37),25,40,37,color,true);
  if(i<2){text(name,177,y+(i==0?34:31),244,36,27,color);if(i==1)text(model.national?L"Seleções nacionais":std::to_wstring(c.level)+L"ª divisão",177,y+65,244,20,16,color);}
 }
 // Reuse a small fixed cache: three selected logos, never the full catalog.
 r.normal(context);gameImage(r.device,r.countryIcon,art,{"data/ui/imgAssets/flags512x512/f_"+std::to_string(c.nation)+".dds","data/ui/artassets/countryflags/f_"+std::to_string(c.nation)+".big"});gameImage(r.device,r.leagueIcon,art,{"data/ui/imgAssets/careerCompetitionIcons/"+std::to_string(c.league)+".png","data/ui/imgAssets/league/light/l"+std::to_string(c.league)+".dds","data/ui/imgAssets/league/dark/l"+std::to_string(c.league)+".dds"});gameImage(r.device,r.clubIcon,art,{"data/ui/imgAssets/crest/light/l"+std::to_string(c.id)+".dds","data/ui/imgAssets/crest/dark/l"+std::to_string(c.id)+".dds"});
 auto contain=[&](const clubgfx::Texture& t,float x,float y,float w,float h){if(t.w<=0||t.h<=0)return;float fit=(std::min)(w/t.w,h/t.h);r.quad(context,x+(w-t.w*fit)/2,y+(h-t.h*fit)/2,t.w*fit,t.h*fit,t.view);};
 contain(r.countryIcon,112,183,58,50);if(model.national)gameImage(r.device,r.leagueIcon,art,{"data/ui/imgAssets/flags512x512/f_"+std::to_string(c.nation)+".dds"});contain(r.leagueIcon,112,286,58,58);contain(r.clubIcon,218,410,92,92);
 const auto teamInk=model.focus==2?uitheme::selectedText():ink;
 if(!r.clubIcon.view)text(wide(c.name.substr(0,2)),209,416,110,70,38,teamInk,true);
 text(wide(c.name),112,513,304,40,34,teamInk,true);text(wide(c.city),112,553,304,28,21,teamInk,true);
 for(int i=0;i<3;++i){int v=i==0?c.attack:i==1?c.midfield:c.defense;text(std::wstring(i==0?L"ATA":i==1?L"MEI":L"DEF"),96+i*111,603,110,25,18,teamInk,true);text(std::to_wstring(v),96+i*111,630,110,36,34,teamInk,true);}
 text(std::to_wstring(model.choices(2).size())+(model.national?L" seleções nesta região":L" clubes nesta liga"),84,675,260,25,18,teamInk);text(L"GER "+std::to_wstring(c.overall),348,674,96,29,21,teamInk,true);
 // Pixel shader intersects and shades the actual rotating 3D sphere. Pixels
 // outside the sphere discard, preserving FIFA's existing stadium framebuffer.
 auto point=clubs::project(c.lat,c.lon,model.yaw,model.pitch,model.zoom);float px=point.x,py=point.y;
 if((c.lat!=0||c.lon!=0)&&point.visible&&px>490&&px<1560&&py>245&&py<754){contain(r.clubIcon,px-29,py-78,58,58);r.rectangle(context,px-1,py-20,2,20,0xffe1f6ff);}
 r.normal(context);r.rectangle(context,515,146,990,92,0x70132330);
 text(L"FUTEBOL PELO MUNDO",535,156,850,25,17,white);text(wide(c.countryName+" · "+c.leagueName),535,188,950,40,31,white);
 r.rectangle(context,515,710,990,34,0x70132330);text(wide(c.city+" · "+c.countryName),535,713,700,28,21,white);r.normal(context);
 // Header is drawn here; the native APT owns only lifecycle/input/footer.
 r.rectangle(context,0,0,1600,138,0x70132330);text(L"TEMPORADA  /  OUTRAS LIGAS",64,37,850,27,18,white);text(model.national?L"VER SELEÇÕES":L"VER CLUBES",64,73,850,57,46,white);
 for(int i=0;i<2;++i){r.rectangle(context,1115+i*190.f,73,180,40,model.national==bool(i)?uitheme::accent():0x903b4c57);text(i?L"SELEÇÕES":L"CLUBES",1115+i*190.f,73,180,40,20,model.national==bool(i)?uitheme::selectedText():white,true);}
}
void drawLineup(ID3D11DeviceContext* context){
 auto& r=renderer;const auto& c=model.club();lineup.poll(r.device);r.normal(context);
 r.rectangle(context,0,0,1600,138,0x90132330);
 gameImage(r.device,r.clubIcon,art,{"data/ui/imgAssets/crest/light/l"+std::to_string(c.id)+".dds","data/ui/imgAssets/crest/dark/l"+std::to_string(c.id)+".dds"});r.normal(context);r.quad(context,64,36,76,76,r.clubIcon.view);
 r.label(context,0,L"ONZE TITULARES",162,33,1300,26,19,RGB(255,255,255));r.label(context,1,wide(c.name),162,68,1300,54,42,RGB(255,255,255));
 bool error=lineup.status=="error"||clubscene::fault!=0;
 if(error||clubscene::readySequence!=lineup.sequence){r.normal(context);r.rectangle(context,260,315,1080,166,0xd0132330);r.label(context,2,error?L"Não foi possível exibir os titulares":L"Preparando os 11 titulares",290,337,1020,44,31,RGB(255,255,255),true);r.label(context,3,error?wide(lineup.message.empty()?"Confira o diagnóstico em runtime/club_browser. Não é necessário salvar a carreira.":lineup.message):L"Carregando os jogadores e os uniformes na cena do estádio...",290,395,1020,56,21,RGB(220,233,240),true);}
 r.label(context,4,L"11 titulares · escalação do save da carreira",162,115,1300,20,16,RGB(220,233,240));
}
void prepareClub(){lineup.career=careerClub();if(lineup.career)lineup.request(model.club().id);else{lineup.status="error";lineup.message="A carreira ainda não está disponível.";}}
void activateClub(){openXI();log("REQUEST_STARTING_XI");}
#ifdef CLUB_BROWSER_VALIDATION
void captureNative(ID3D11Device* dev,ID3D11DeviceContext* context,ID3D11Texture2D* back){
 if(!validationCapture.exchange(false))return;D3D11_TEXTURE2D_DESC desc{};back->GetDesc(&desc);desc.Usage=D3D11_USAGE_STAGING;desc.BindFlags=desc.MiscFlags=0;desc.CPUAccessFlags=D3D11_CPU_ACCESS_READ;ID3D11Texture2D* staging=nullptr;if(FAILED(dev->CreateTexture2D(&desc,nullptr,&staging)))return;context->CopyResource(staging,back);D3D11_MAPPED_SUBRESOURCE pixels{};
 if(SUCCEEDED(context->Map(staging,0,D3D11_MAP_READ,0,&pixels))){auto folder=lineup.folder/L"validation";fs::create_directories(folder);auto name=std::to_wstring(model.club().id)+L"_"+std::to_wstring(lineup.sequence);std::ofstream raw(folder/(name+L".pixels"),std::ios::binary);for(unsigned y=0;y<desc.Height;++y)raw.write((char*)pixels.pData+size_t(y)*pixels.RowPitch,size_t(desc.Width)*4);raw.close();std::ofstream meta(folder/(name+L".json"));meta<<"{\"width\":"<<desc.Width<<",\"height\":"<<desc.Height<<",\"format\":"<<desc.Format<<",\"club\":"<<model.club().id<<",\"sequence\":"<<lineup.sequence<<"}";context->Unmap(staging,0);}clubgfx::release(staging);
}
#endif
void inputs(HWND window,float w,float h,float dt){
 DWORD pid=0;GetWindowThreadProcessId(GetForegroundWindow(),&pid);if(pid!=GetCurrentProcessId()||GetTickCount64()<enteredAt+250)return;
 static std::array<bool,256> previous{};std::array<bool,256> keys{};for(int key:std::initializer_list<int>{VK_LEFT,VK_RIGHT,VK_UP,VK_DOWN,VK_RETURN,VK_ESCAPE,'X','C','E','R','W','I','J','K','L',VK_ADD,VK_SUBTRACT,VK_OEM_PLUS,VK_OEM_MINUS,VK_LBUTTON})keys[key]=(GetAsyncKeyState(key)&0x8000)!=0;
 XINPUT_STATE pad{};if(readPad)for(DWORD i=0;i<4;i++)if(readPad(i,&pad)==ERROR_SUCCESS)break;static WORD previousPad=0;const WORD pressed=pad.Gamepad.wButtons&~previousPad;
 if(model.detailOpen){
  if(actorPage()){
   auto axis=[](SHORT v){return std::abs(int(v))>8000?v/32768.f:0.f;};clubscene::playerAngle=clubscene::playerAngle.load()+axis(pad.Gamepad.sThumbRX)*dt*2.8f;clubscene::playerPan=std::clamp(clubscene::playerPan.load()+axis(pad.Gamepad.sThumbRY)*dt*.6f,-.45f,.65f);
   int wheel=wheelDelta.exchange(0);POINT mouse{};GetCursorPos(&mouse);ScreenToClient(window,&mouse);float mouseFit=(std::min)(w/1600,h/900),mouseX=(mouse.x-(w-1600*mouseFit)/2)/mouseFit,mouseY=(mouse.y-(h-900*mouseFit)/2)/mouseFit;if(clubPage==ClubPage::Roster&&wheel&&mouseX>=68&&mouseX<493&&mouseY>=270&&mouseY<774&&roster.ready){roster.choose(roster.selected+(wheel>0?-1:1));wheel=0;}if(clubPage==ClubPage::Coach&&coach.tab==2&&wheel&&mouseX>=530&&mouseX<972&&mouseY>=270&&mouseY<805){coach.navigate(wheel>0?-1:1);wheel=0;}if(mouseX<1000)wheel=0;
   float input=(pad.Gamepad.bRightTrigger-pad.Gamepad.bLeftTrigger)/255.f+(keys['E']||keys[VK_ADD]||keys[VK_OEM_PLUS]?1:0)-(keys['W']||keys[VK_SUBTRACT]||keys[VK_OEM_MINUS]?1:0);clubscene::playerZoom=std::clamp(clubscene::playerZoom.load()*std::exp(input*dt+wheel*.001f),clubs::rosterMinimumZoom(clubscene::roomView.load()),2.8f);
   POINT pt{};GetCursorPos(&pt);ScreenToClient(window,&pt);float fit=(std::min)(w/1600,h/900),mx=(pt.x-(w-1600*fit)/2)/fit,my=(pt.y-(h-900*fit)/2)/fit;static float lastMouse=0,lastMouseY=0;static bool rotate=false;
   if(keys[VK_LBUTTON]&&!previous[VK_LBUTTON]){if(clubPage==ClubPage::Roster&&mx>=68&&mx<493&&my>=230&&my<262){roster.sortFocus=true;roster.setSort(std::clamp(int((mx-68)/106),0,3));}else if(clubPage==ClubPage::Roster&&mx>=68&&mx<493&&my>=270&&my<774&&roster.ready){roster.sortFocus=false;roster.choose(roster.scroll+int((my-270)/72));}else if(mx>=530&&mx<972&&my>=173&&my<213){int tab=std::clamp(int((mx-530)/147),0,2);if(clubPage==ClubPage::Coach)coach.setTab(clubcoach::tabAt(mx-530));else roster.tab=tab;}else if(mx>1000){rotate=true;lastMouse=mx;lastMouseY=my;}}
   if(rotate&&keys[VK_LBUTTON]){clubscene::playerAngle=clubscene::playerAngle.load()+(mx-lastMouse)*.012f;clubscene::playerPan=std::clamp(clubscene::playerPan.load()+(my-lastMouseY)*.003f,-.45f,.65f);lastMouse=mx;lastMouseY=my;}if(!keys[VK_LBUTTON])rotate=false;
  }
  // Choice focus is owned by APT for mouse, keyboard and pad together.
  // Independently inferring it from a stale mouse coordinate desynchronizes
  // the highlighted native card from the keyboard's activation target.
  previous=keys;previousPad=pad.Gamepad.wButtons;return;
 }
 static int direction=0;static ULONGLONG repeatAt=0;int next=keys[VK_LEFT]||(pad.Gamepad.wButtons&XINPUT_GAMEPAD_DPAD_LEFT)||pad.Gamepad.sThumbLX< -16000?1:keys[VK_RIGHT]||(pad.Gamepad.wButtons&XINPUT_GAMEPAD_DPAD_RIGHT)||pad.Gamepad.sThumbLX>16000?2:keys[VK_UP]||(pad.Gamepad.wButtons&XINPUT_GAMEPAD_DPAD_UP)||pad.Gamepad.sThumbLY>16000?3:keys[VK_DOWN]||(pad.Gamepad.wButtons&XINPUT_GAMEPAD_DPAD_DOWN)||pad.Gamepad.sThumbLY< -16000?4:0;
 auto now=GetTickCount64();if(next&&(next!=direction||now>=repeatAt)){if(next<=2)model.step(model.focus,next==1?-1:1);else model.moveFocus(next==3?-1:1);repeatAt=now+(next!=direction?360:150);}direction=next;
 if((keys['X']&&!previous['X'])||(pressed&XINPUT_GAMEPAD_LEFT_SHOULDER))model.step(1,-1);if((keys['C']&&!previous['C'])||(pressed&XINPUT_GAMEPAD_RIGHT_SHOULDER))model.step(1,1);if((keys['R']&&!previous['R'])||(pressed&XINPUT_GAMEPAD_RIGHT_THUMB))model.recenter();
 auto axis=[](SHORT v){return std::abs(int(v))>8000?v/32768.f:0.f;};model.rotate((axis(pad.Gamepad.sThumbRX)+(keys['L']?1:0)-(keys['J']?1:0))*dt*1.7f,(-axis(pad.Gamepad.sThumbRY)+(keys['K']?1:0)-(keys['I']?1:0))*dt*1.3f);
 model.zoomBy(((pad.Gamepad.bRightTrigger-pad.Gamepad.bLeftTrigger)/255.f+(keys[VK_ADD]||keys[VK_OEM_PLUS]||keys['E']?1:0)-(keys[VK_SUBTRACT]||keys[VK_OEM_MINUS]||keys['W']?1:0))*dt*.5f);
 POINT point{};GetCursorPos(&point);ScreenToClient(window,&point);float scale=(std::min)(w/1600,h/900),mx=(point.x-(w-1600*scale)/2)/scale,my=(point.y-(h-900*scale)/2)/scale;static bool dragging=false;static float lastX=0,lastY=0;
 if(keys[VK_LBUTTON]&&!previous[VK_LBUTTON]){if(mx>=1115&&mx<1495&&my>=73&&my<113){model.setNational(mx>=1305);}else if(mx>=64&&mx<=464&&my>=150&&my<=706){int kind=my<246?0:my<354?1:2;model.focus=kind;++model.revision;if(mx<112)model.step(kind,-1);else if(mx>416)model.step(kind,1);else if(kind==2)enterChoice();}else if(mx>470&&mx<1600&&my>145&&my<745){dragging=true;lastX=mx;lastY=my;}}
 if(dragging&&keys[VK_LBUTTON]){model.rotate((mx-lastX)*.006f,(my-lastY)*.005f);lastX=mx;lastY=my;}if(!keys[VK_LBUTTON])dragging=false;previous=keys;previousPad=pad.Gamepad.wButtons;
}
void render(IDXGISwapChain* swap){
 if(!swap||drawing||stopped)return;auto kind=pageKind();if(!kind){clubscene::mascotCamera=false;clubscene::intent(false,0);entered=false;model.detailOpen=false;clubPage=ClubPage::Map;clubscene::rosterCamera=false;clubscene::roomView=false;rosterMouseActive=false;return;}if(entered&&entryKind!=kind)entered=false;drawing=true;std::lock_guard<std::mutex> guard(drawLock);DXGI_SWAP_CHAIN_DESC sd{};ID3D11Device* dev=nullptr;ID3D11DeviceContext* context=nullptr;ID3D11Texture2D* back=nullptr;ID3D11RenderTargetView* target=nullptr;
 if(SUCCEEDED(swap->GetDesc(&sd))&&SUCCEEDED(swap->GetDevice(IID_PPV_ARGS(&dev)))&&SUCCEEDED(swap->GetBuffer(0,IID_PPV_ARGS(&back)))){DWORD pid=0;GetWindowThreadProcessId(sd.OutputWindow,&pid);D3D11_TEXTURE2D_DESC desc{};back->GetDesc(&desc);
  if(pid==GetCurrentProcessId()&&desc.Width>=320&&desc.Height>=180){gameWindow=sd.OutputWindow;attachInputWindow(sd.OutputWindow);dev->GetImmediateContext(&context);if(context&&SUCCEEDED(dev->GetDeviceRemovedReason())&&SUCCEEDED(dev->CreateRenderTargetView(back,nullptr,&target))){
   static thread_local bool comInitialized=false;if(!comInitialized){CoInitializeEx(nullptr,COINIT_MULTITHREADED);comInitialized=true;}if(!model.rows.empty()||loadCatalog()){
    auto now=GetTickCount64();float dt=lastFrame?(std::min)(.06f,float(now-lastFrame)*.001f):0.f;lastFrame=now;if(!entered){entryKind=kind;roomEntry=kind==2;clubPage=roomEntry?ClubPage::Roster:ClubPage::Map;roster.clear();coach.clear();{std::lock_guard<std::mutex> q(commandMutex);commands.clear();}model.detailOpen=roomEntry;hubFocus=1;lineup.club=0;lineup.sequence=0;model.zoom=model.targetZoom=1.3f;int club=careerClub();model.setNational(false);if(club)model.choose(club);enteredAt=now;entered=true;if(kind==3)competitions.enter(club);if(kind==4||kind==5)rankings.enter(club,kind==5);log(kind==3?"ENTER_CAREER_COMPETITIONS":"ENTER_CLUB_BROWSER");}
    #ifdef CLUB_BROWSER_VALIDATION
    auto command=validationClub.exchange(-1);if(command==0)model.closeDetail();else if(command>0&&model.choose(command))activateClub();
    #endif
    if(kind==4||kind==5){
     clubscene::intent(false,0);clubscene::mascotCamera=false;clubscene::rosterCamera=false;clubscene::roomView=false;rosterMouseActive=true;
     {std::vector<std::string>pending;{std::lock_guard<std::mutex>q(commandMutex);pending.swap(commands);}for(auto&s:pending)rankings.command(s);}
     rankings.controls(sd.OutputWindow,float(desc.Width),float(desc.Height));
     if(renderer.init(dev,root.wstring())){rankings.poll();clubgfx::UiPass saved(context,renderer.uiPipeline);renderer.begin(context,target,float(desc.Width),float(desc.Height));rankings.draw(context);saved.restore();}
    }else if(kind==3){
     clubscene::intent(false,0);clubscene::mascotCamera=false;clubscene::rosterCamera=false;clubscene::roomView=false;rosterMouseActive=true;
     {std::vector<std::string>pending;{std::lock_guard<std::mutex>q(commandMutex);pending.swap(commands);}for(auto&s:pending)competitions.command(s);}
     competitions.controls(sd.OutputWindow,float(desc.Width),float(desc.Height));
     if(renderer.init(dev,root.wstring())){competitions.poll();clubgfx::UiPass saved(context,renderer.uiPipeline);renderer.begin(context,target,float(desc.Width),float(desc.Height));competitions.draw(context);saved.restore();}
    }else{
    if(clubPage==ClubPage::Map){static uint64_t catalogCheck=0;static fs::file_time_type catalogStamp{};if(now>=catalogCheck){catalogCheck=now+2000;std::error_code ec;auto stamp=fs::last_write_time(art.game/L"ModCarrerMode/runtime/club_browser/catalog/ready.json",ec);if(!ec&&stamp!=catalogStamp){int id=model.club().id;bool national=model.national;if(loadCatalog()){model.setNational(national);model.choose(id);catalogStamp=stamp;}}}}
    clubscene::roomView=roomEntry&&clubs::roomRosterMode.club.load()>0;if(roomEntry)syncRoomRoster(careerClub());drainClubCommands();bool mascotOpen=clubPage==ClubPage::Mascot;clubscene::mascotCamera=mascotOpen;rosterMouseActive=actorPage()||mascotOpen;clubscene::rosterCamera=actorPage()||mascotOpen;
    if(mascotOpen){int current=careerClub();if(current!=mascot.career)enterMascot(model.club().id,current);mascotControls(sd.OutputWindow,float(desc.Width),float(desc.Height),dt);mascot.poll(lineup,dev);}else inputs(sd.OutputWindow,float(desc.Width),float(desc.Height),dt);
    // Model preparation is requested only by Ver titulares / Atualizar.
    auto submitted=mascotOpen?mascot.submitted:clubPage==ClubPage::Coach?coach.submitted:roster.submitted;clubscene::intent(clubPage==ClubPage::XI||((actorPage()||mascotOpen)&&submitted&&submitted==lineup.sequence),lineup.sequence);model.tick(dt);if(renderer.init(dev,root.wstring())){clubgfx::UiPass saved(context,renderer.uiPipeline);renderer.begin(context,target,float(desc.Width),float(desc.Height));if(mascotOpen)drawMascot(context);else if(clubPage==ClubPage::XI)drawLineup(context);else if(clubPage==ClubPage::Choice)drawChoice(context);else if(clubPage==ClubPage::Coach)drawCoach(context);else if(actorPage())drawRoster(context);else drawContent(context);saved.restore();

     #ifdef CLUB_BROWSER_VALIDATION
     captureNative(dev,context,back);
     #endif
    }
    }
   }
  }}
 }
 clubgfx::release(target);clubgfx::release(back);clubgfx::release(context);clubgfx::release(dev);drawing=false;
}
HRESULT WINAPI present(IDXGISwapChain* swap,UINT interval,UINT flags){if(!(flags&DXGI_PRESENT_TEST)){try{render(swap);}catch(...){drawing=false;log("DRAW_EXCEPTION");}}return originalPresent(swap,interval,flags);}
void onReShade(reshade::api::effect_runtime* runtime){if(runtime&&runtime->get_device()->get_api()==reshade::api::device_api::d3d11){try{render(reinterpret_cast<IDXGISwapChain*>(runtime->get_native()));}catch(...){drawing=false;log("DRAW_EXCEPTION");}}}
DWORD initializeImpl(){
 auto game=root.parent_path().parent_path().parent_path();clubscene::start(game,executable,careerClub);art.initialize(game);lineup.configure(game);log("LINEUP_WORKER_ON_DEMAND");log("GAME_ART_INDEX_READY");Sleep(500);HMODULE modules[1024]{};DWORD bytes=0;if(EnumProcessModules(GetCurrentProcess(),modules,sizeof(modules),&bytes))for(DWORD i=0;i<(std::min)(DWORD(1024),bytes/DWORD(sizeof(HMODULE)));++i){
  auto registerAddon=reinterpret_cast<bool(*)(HMODULE,uint32_t)>(GetProcAddress(modules[i],"ReShadeRegisterAddon"));auto registerEvent=reinterpret_cast<void(*)(HMODULE,reshade::addon_event,void*)>(GetProcAddress(modules[i],"ReShadeRegisterEventForAddon"));if(registerAddon&&registerEvent){if(registerAddon(own,17)){registerEvent(own,reshade::addon_event::reshade_present,reinterpret_cast<void*>(onReShade));reshadeModule=modules[i];log("RESHADE_RENDER_CALLBACK_READY");}else log("RESHADE_REGISTRATION_REJECTED");return 0;}}
 // Same COM Present-vtable technique as the installed stadium selector. Chain
 // the previous pointer and never overwrite FIFA executable instructions.
 WNDCLASSEXW wc{};wc.cbSize=sizeof(wc);wc.lpfnWndProc=DefWindowProcW;wc.hInstance=own;wc.lpszClassName=L"Server16ClubGlobeProbe";RegisterClassExW(&wc);HWND probe=CreateWindowExW(0,wc.lpszClassName,L"",WS_POPUP,0,0,1,1,nullptr,nullptr,own,nullptr);DXGI_SWAP_CHAIN_DESC sd{};sd.BufferCount=1;sd.BufferDesc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;sd.BufferUsage=DXGI_USAGE_RENDER_TARGET_OUTPUT;sd.OutputWindow=probe;sd.SampleDesc.Count=1;sd.Windowed=TRUE;ID3D11Device* dev=nullptr;IDXGISwapChain* swap=nullptr;auto hr=D3D11CreateDeviceAndSwapChain(nullptr,D3D_DRIVER_TYPE_HARDWARE,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&sd,&swap,&dev,nullptr,nullptr);
 if(SUCCEEDED(hr)&&swap){auto table=*reinterpret_cast<void***>(swap);DWORD old=0;originalPresent=reinterpret_cast<Present>(table[8]);if(VirtualProtect(table+8,sizeof(void*),PAGE_READWRITE,&old)){auto previous=InterlockedCompareExchangePointer((PVOID volatile*)(table+8),(void*)present,(void*)originalPresent);if(previous==(void*)originalPresent){hookedTable=table;log("PRESENT_CHAIN_READY");}else log("PRESENT_CHAIN_CHANGED_NOT_INSTALLED");DWORD ignored=0;VirtualProtect(table+8,sizeof(void*),old,&ignored);}else log("PRESENT_CHAIN_UNAVAILABLE");}else log("GRAPHICS_PROBE_FAILED");clubgfx::release(swap);clubgfx::release(dev);DestroyWindow(probe);UnregisterClassW(wc.lpszClassName,own);return 0;
}
DWORD WINAPI initialize(void*){try{return initializeImpl();}catch(...){log("INITIALIZATION_EXCEPTION");return 0;}}
}
inline bool copyClubCommand(const char*wire,char*command){__try{for(unsigned i=0;i<31;++i){command[i]=wire[i];if(!wire[i])break;}return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16ClubBrowserCommand(const char* wire){
 if(!wire||stopped)return FALSE;char command[32]{};if(!copyClubCommand(wire,command))return FALSE;if(!memchr(command,0,sizeof(command))||std::string(command).find_first_not_of("abcdefghijklmnopqrstuvwxyz_")!=std::string::npos)return FALSE;
 if(!strcmp(command,"room_roster")||!strcmp(command,"room_close")){char name[128]{};if(!readPage(name)||!clubs::isDressingRoomPage(name))return FALSE;if(!strcmp(command,"room_roster"))return clubs::roomRosterMode.open(name,careerClub())?TRUE:FALSE;clubs::roomRosterMode.close();clubscene::intent(false,0);return TRUE;}
 if(!page())return FALSE;
 static const char*allowed[]={"mascot","focus_mascot","mascot_center","open","xi","roster","coach","focus_xi","focus_roster","focus_coach","detail","back","left","right","prev","next","refresh","sort","tab_prev","tab_next","comp_prev","comp_next","comp_stat_prev","comp_stat_next","comp_mode","comp_refresh","comp_bracket","comp_close","comp_center","rank_mode","rank_prev","rank_next","rank_top","rank_mine","rank_filter","rank_refresh","globe_mode"};bool valid=false;for(auto*a:allowed)if(!strcmp(command,a))valid=true;if(!valid)return FALSE;std::lock_guard<std::mutex>lock(commandMutex);if(commands.size()>=32)return FALSE;commands.emplace_back(command);return TRUE;
}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16ClubBrowserRoomRosterActive(){char name[128]{};return !stopped&&readPage(name)&&clubs::roomRosterMode.visible(name,careerClub());}
extern "C" __declspec(dllexport) unsigned WINAPI Fifa16ModGetApiVersion(){return 1;}
#ifdef CLUB_BROWSER_VALIDATION
// Test build only: queue work for Present/the verified FIFA frame callback.
// These functions never invoke FIFA on the diagnostic caller's thread.
extern "C" __declspec(dllexport) DWORD WINAPI Fifa16ClubBrowserValidate(void* club){auto id=(uintptr_t)club;if(id>=500000)return 0;validationClub=int(id);return 1;}
extern "C" __declspec(dllexport) DWORD WINAPI Fifa16ClubBrowserCapture(void*){validationCapture=true;return 1;}
#endif
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char*){
 if(InterlockedCompareExchange(&started,1,0))return TRUE;executable=(uintptr_t)GetModuleHandleW(nullptr);if(get<uint16_t>(executable)!=0x5a4d||get<unsigned>(executable+get<int>(executable+0x3c)+8)!=0x577de45c){started=0;return FALSE;}wchar_t path[1024]{};GetModuleFileNameW(nullptr,path,1024);root=fs::path(path).parent_path()/L"ModCarrerMode/data/club_browser";uitheme::load(fs::path(path).parent_path()/L"ModCarrerMode/data/custom_ui_theme.json");logPath=fs::path(path).parent_path()/L"ModCarrerMode/logs/club_browser.log";if(!fs::is_regular_file(root/L"catalog.tsv")){log("MISSING_CATALOG");started=0;return FALSE;}HMODULE pin=nullptr;GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCWSTR)&started,&pin);HMODULE xi=LoadLibraryW(L"xinput1_4.dll");if(!xi)xi=LoadLibraryW(L"xinput9_1_0.dll");readPad=xi?reinterpret_cast<ReadPad>(GetProcAddress(xi,"XInputGetState")):nullptr;HANDLE thread=CreateThread(nullptr,0,initialize,nullptr,0,nullptr);if(!thread){started=0;return FALSE;}CloseHandle(thread);log("START");return TRUE;
}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16ModStop(){InterlockedExchange(&stopped,1);rosterMouseActive=false;if(inputWindow&&originalWindowProc&&(WNDPROC)GetWindowLongPtrW(inputWindow,GWLP_WNDPROC)==rosterWindowProc)SetWindowLongPtrW(inputWindow,GWLP_WNDPROC,(LONG_PTR)originalWindowProc);clubscene::stop();clubanim::stop();lineup.stop();return TRUE;}
BOOL WINAPI DllMain(HINSTANCE module,DWORD reason,LPVOID){if(reason==DLL_PROCESS_ATTACH){own=module;DisableThreadLibraryCalls(module);}return TRUE;}
