#define NOMINMAX
#include "stadium_scene_screen.h"
#include "stadium_scene_assets.h"
#include "../../render/renderer/fifa_player_renderer.h"
#include "../../platform/overlay/mod_overlay_screens.h"
#include "../../platform/input/mod_xinput_gate.h"
#include "../../ui/common/screen_visuals.h"
#include "../../render/stadium_thumbnails/stadium_preview.h"
#include "../../screens/office/career_news_feed.h"
#include <mutex>
#include <algorithm>
#include <cmath>
namespace {
struct Request {int club=0;std::string name,key;unsigned generation=0;};
struct Result {Request request;stadium_scene::Preview preview;fifa_player::Texture image;std::string image_source;};
std::mutex gate;Request published,request;unsigned generation=0;
std::shared_ptr<const Result>ready,shown;std::string root;
HANDLE event=nullptr;volatile LONG refresh=0;fifa_player::Renderer renderer;
ID3D11Device*device=nullptr;ID3D11ShaderResourceView*image_view=nullptr;
void(*logger)(const char*)=nullptr;float yaw=.45f,zoom=1;bool orbit=true;WORD previous=0;DWORD input_at=0;
bool free_camera=false,free_init=false;fifa_player::StadiumCamera camera;
void toggle_camera(){free_camera=!free_camera;free_init=free_camera;}
float axis(SHORT value){return abs(value)>9000?value/32768.f:0;}
DWORD WINAPI worker(void*){
    for(;;){WaitForSingleObject(event,INFINITE);Request job;{std::lock_guard<std::mutex>g(gate);job=request;}
        auto result=std::make_shared<Result>();result->request=job;
        try{result->preview=stadium_scene::load(root,job.club,job.key);
            if(!job.name.empty())result->preview.name=job.name;
            CareerClubStadiumFacts facts={};if(career_club_stadium_copy(job.club,&facts)){
                if(facts.name[0])result->preview.name=facts.name;
                if(facts.capacity>0)result->preview.capacity=facts.capacity;
                if(facts.location[0])result->preview.location=facts.location;
                if(facts.image_key[0])result->preview.key=facts.image_key;
            }
            if(!result->preview.key.empty())stadium_preview::load(root,result->preview.key,result->image,result->image_source);
        }catch(...){result->preview.error="Não foi possível carregar a prévia deste estádio.";}
        {std::lock_guard<std::mutex>g(gate);if(job.generation==generation)ready=result;}
        if(logger)logger(("Stadium3D club="+std::to_string(job.club)+" source="+result->preview.source+" model="+(result->preview.model?"yes":"no")+" "+result->preview.error).c_str());
    }
}
void queue(){request=published;request.generation=++generation;ready.reset();SetEvent(event);}
void opened(void*){{std::lock_guard<std::mutex>g(gate);queue();}shown.reset();screen_visuals::release(image_view);renderer.clear();yaw=.45f;zoom=1;orbit=true;free_camera=false;free_init=false;previous=0;input_at=GetTickCount()+250;InterlockedExchange(&refresh,1);}
void closed(void*){std::lock_guard<std::mutex>g(gate);++generation;ready.reset();shown.reset();screen_visuals::release(image_view);renderer.clear();}
void draw(void*){
    auto previous_shown=shown;{std::lock_guard<std::mutex>g(gate);if(ready&&ready->request.generation==generation)shown=ready;else shown.reset();}
    if(shown!=previous_shown){screen_visuals::release(image_view);if(shown&&device)image_view=screen_visuals::upload(device,shown->image);}
    XINPUT_STATE pad={};mod_xinput_read_raw(0,&pad);WORD pressed=pad.Gamepad.wButtons&~previous;previous=pad.Gamepad.wButtons;
    bool input=(LONG)(GetTickCount()-input_at)>=0;auto&io=ImGui::GetIO();float dt=std::clamp(io.DeltaTime,0.f,.1f);
    if(input){
        if(pressed&XINPUT_GAMEPAD_X||ImGui::IsKeyPressed(ImGuiKey_C))toggle_camera();
        if(pressed&XINPUT_GAMEPAD_Y||ImGui::IsKeyPressed(ImGuiKey_R)){yaw=.45f;zoom=1;free_init=free_camera;}
        if(!free_camera){
            if(pressed&XINPUT_GAMEPAD_A||ImGui::IsKeyPressed(ImGuiKey_Space))orbit=!orbit;
            zoom=std::clamp(zoom+(pad.Gamepad.bRightTrigger-pad.Gamepad.bLeftTrigger)/255.f*dt*.7f,.65f,2.f);
            yaw+=axis(pad.Gamepad.sThumbRX)*dt;
            if(ImGui::IsKeyDown(ImGuiKey_LeftArrow))yaw-=dt;if(ImGui::IsKeyDown(ImGuiKey_RightArrow))yaw+=dt;
            if(ImGui::IsKeyDown(ImGuiKey_Equal))zoom=std::min(2.f,zoom+dt*.7f);if(ImGui::IsKeyDown(ImGuiKey_Minus))zoom=std::max(.65f,zoom-dt*.7f);
        }
    }
    if(shown&&shown->preview.model&&orbit&&!free_camera)yaw+=dt*.10f;if(!std::isfinite(yaw))yaw=0;yaw=fmodf(yaw,6.2831853f);
    screen_visuals::LightTheme theme;theme.color(ImGuiCol_Text,{.025f,.30f,.52f,1});theme.color(ImGuiCol_WindowBg,{1,1,1,1});
    ImGui::PushStyleVar(ImGuiStyleVar_WindowBorderSize,0);ImGui::PushStyleVar(ImGuiStyleVar_WindowRounding,0);ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding,{18,14});
    ImGui::SetNextWindowPos({0,0});ImGui::SetNextWindowSize(io.DisplaySize);
    ImGui::Begin("Estádio do clube##Stadium3D",nullptr,ImGuiWindowFlags_NoDecoration|ImGuiWindowFlags_NoMove|ImGuiWindowFlags_NoSavedSettings|ImGuiWindowFlags_NoNavInputs);
    ImGui::TextUnformatted("Estádio do clube");ImGui::SameLine();ImGui::TextDisabled("  |  Prévia 3D");
    if(shown){ImGui::TextUnformatted(shown->preview.name.empty()?"Estádio indisponível":shown->preview.name.c_str());
        if(shown->preview.capacity>0){ImGui::SameLine();ImGui::TextDisabled("  •  Capacidade: %d",shown->preview.capacity);}
        if(!shown->preview.location.empty())ImGui::TextDisabled("Local: %s",shown->preview.location.c_str());}
    else ImGui::TextDisabled("Carregando estádio...");
    ImVec2 stage={ImGui::GetContentRegionAvail().x,std::max(1.f,ImGui::GetContentRegionAvail().y-84)},at=ImGui::GetCursorScreenPos();
    bool bound=shown&&shown->preview.model&&renderer.model(shown->preview.model);
    if(bound&&free_init){camera=renderer.stadium_orbit_camera((UINT)stage.x,(UINT)stage.y,yaw,zoom);free_init=false;}
    if(bound&&input&&free_camera){
        camera.yaw+=axis(pad.Gamepad.sThumbRX)*dt*1.5f;camera.pitch=std::clamp(camera.pitch+axis(pad.Gamepad.sThumbRY)*dt*1.2f,-1.55f,1.55f);
        float forward=axis(pad.Gamepad.sThumbLY)+(pad.Gamepad.bRightTrigger-pad.Gamepad.bLeftTrigger)/255.f;
        float side=axis(pad.Gamepad.sThumbLX),up=0;
        if(ImGui::IsKeyDown(ImGuiKey_W))forward+=1;if(ImGui::IsKeyDown(ImGuiKey_S))forward-=1;
        if(ImGui::IsKeyDown(ImGuiKey_D))side+=1;if(ImGui::IsKeyDown(ImGuiKey_A))side-=1;
        if(ImGui::IsKeyDown(ImGuiKey_E)||(pad.Gamepad.wButtons&XINPUT_GAMEPAD_RIGHT_SHOULDER))up+=1;
        if(ImGui::IsKeyDown(ImGuiKey_Q)||(pad.Gamepad.wButtons&XINPUT_GAMEPAD_LEFT_SHOULDER))up-=1;
        float speed=dt*(ImGui::IsKeyDown(ImGuiKey_LeftShift)?800.f:350.f),y=camera.yaw,t=camera.pitch;
        camera.position.x+=speed*(std::clamp(forward,-1.f,1.f)*sinf(y)*cosf(t)+side*cosf(y));
        camera.position.y+=speed*(std::clamp(forward,-1.f,1.f)*sinf(t)+up);
        camera.position.z+=speed*(-std::clamp(forward,-1.f,1.f)*cosf(y)*cosf(t)+side*sinf(y));
        camera.position.x=std::clamp(camera.position.x,-5000.f,5000.f);camera.position.y=std::clamp(camera.position.y,-5000.f,5000.f);camera.position.z=std::clamp(camera.position.z,-5000.f,5000.f);
    }
    bool rendered=bound&&renderer.render_stadium((UINT)stage.x,(UINT)stage.y,yaw,zoom,free_camera?&camera:nullptr);
    if(rendered)ImGui::Image((ImTextureID)(intptr_t)renderer.image(),stage);
    else if(shown&&image_view)ImGui::Image((ImTextureID)(intptr_t)image_view,stage);
    else {ImGui::Dummy(stage);ImGui::GetWindowDrawList()->AddText({at.x+24,at.y+24},IM_COL32(45,91,127,255),shown?shown->preview.error.c_str():"Preparando a visualização 3D...");}
    if(input&&ImGui::IsItemHovered()){
        if(free_camera){
            if(ImGui::IsMouseDragging(0)){camera.yaw+=io.MouseDelta.x*.006f;camera.pitch=std::clamp(camera.pitch-io.MouseDelta.y*.006f,-1.55f,1.55f);}
            camera.position.x+=io.MouseWheel*60*sinf(camera.yaw)*cosf(camera.pitch);camera.position.y+=io.MouseWheel*60*sinf(camera.pitch);camera.position.z-=io.MouseWheel*60*cosf(camera.yaw)*cosf(camera.pitch);
        }else{zoom=std::clamp(zoom+io.MouseWheel*.08f,.65f,2.f);if(ImGui::IsMouseDragging(0))yaw+=io.MouseDelta.x*.006f;}
    }
    if(ImGui::Button(free_camera?"Órbita automática":"Câmera livre")&&input)toggle_camera();ImGui::SameLine();
    if(!free_camera){if(ImGui::Button(orbit?"Pausar órbita":"Retomar órbita")&&input)orbit=!orbit;ImGui::SameLine();}
    if(ImGui::Button("Reenquadrar")&&input){yaw=.45f;zoom=1;free_init=free_camera;}ImGui::SameLine();
    if(ImGui::Button("Voltar")&&input)mod_screen_request_back();
    ImGui::TextDisabled(free_camera?"X/C: órbita  |  Esquerdo / WASD: mover  |  Direito / arrastar: olhar  |  LT/RT: recuar/avançar  |  LB/RB / Q/E: altura  |  Y/R: reiniciar  |  B/Esc: voltar":"X/C: câmera livre  |  A/Espaço: pausar  |  LT/RT / roda: zoom  |  Direito / arrastar: girar  |  Y/R: reenquadrar  |  B/Esc: voltar");
    ImGui::End();ImGui::PopStyleVar(3);
}
}
extern "C" BOOL stadium_scene_take_refresh(){return InterlockedExchange(&refresh,0)!=0;}
extern "C" void stadium_scene_publish(int club,const char*name,const char*key){
    std::lock_guard<std::mutex>g(gate);published={club>0&&club<=200000?club:0,name?std::string(name,strnlen(name,127)):"",key?std::string(key,strnlen(key,255)):"",0};
    if(event&&mod_screen_is_active("stadium-3d"))queue();
}
bool stadium_scene_register(const char*path,void(*log)(const char*)){
    root=path?path:"";logger=log;if(!event){event=CreateEventA(nullptr,FALSE,FALSE,nullptr);if(!event)return false;
        HANDLE thread=CreateThread(nullptr,0,worker,nullptr,0,nullptr);if(!thread){CloseHandle(event);event=nullptr;return false;}CloseHandle(thread);}
    ModOverlayScreen screen={"stadium-3d",FIFA_STADIUM_SCENE_ACTION,opened,draw,closed,nullptr,nullptr};return mod_screen_register(&screen)!=0;
}
void stadium_scene_device(ID3D11Device*next){renderer.device(next);if(device==next)return;screen_visuals::release(image_view);if(device)device->Release();device=next;if(device)device->AddRef();if(shown&&device)image_view=screen_visuals::upload(device,shown->image);}
#ifdef STADIUM_SCENE_TEST
StadiumSceneTestView stadium_scene_test_view(){return {shown!=nullptr,shown&&bool(shown->preview.model),orbit,shown?shown->request.club:0,yaw,zoom,free_camera,camera.position.x,camera.position.y,camera.position.z,camera.pitch};}
#endif
