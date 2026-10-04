#define NOMINMAX
#define CLUB_PLAYER_SCREEN_QA
#include "test_club_player_3d.cpp"
#include "../../src/render/assets/fifa_player_assets.h"
#include "../../src/experimental/stadium_3d/stadium_scene_assets.h"
#include "../../src/experimental/stadium_3d/stadium_scene_screen.h"
#include "../../src/platform/overlay/mod_overlay_screens.h"
#include "../../src/platform/input/mod_xinput_gate.h"
#include "../../third_party/imgui/backends/imgui_impl_dx11.h"
#include <cstdio>
#include <cstring>
using namespace fifa_player;
static unsigned word(const std::vector<uint8_t>&b,size_t p){return p+4<=b.size()?b[p]|unsigned(b[p+1])<<8|unsigned(b[p+2])<<16|unsigned(b[p+3])<<24:0;}
static XINPUT_STATE pad={};
extern "C" DWORD WINAPI mod_xinput_read_raw(DWORD index,XINPUT_STATE*out){if(index)return ERROR_DEVICE_NOT_CONNECTED;*out=pad;return ERROR_SUCCESS;}
static void log_line(const char*s){puts(s);}
static void frame(ID3D11DeviceContext*c,ID3D11RenderTargetView*target){mod_screen_sync_lifecycle();ImGui_ImplDX11_NewFrame();ImGui::NewFrame();mod_screen_draw();ImGui::Render();float bg[4]={1,1,1,1};c->OMSetRenderTargets(1,&target,nullptr);c->ClearRenderTargetView(target,bg);ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData());Sleep(15);}
int main(int argc,char**argv){
    if(argc>2&&!strcmp(argv[2],"--screen")){
        ID3D11Device*d=nullptr;ID3D11DeviceContext*c=nullptr;D3D_FEATURE_LEVEL level;
        require(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&d,&level,&c)),"WARP device");
        IMGUI_CHECKVERSION();ImGui::CreateContext();auto&io=ImGui::GetIO();io.DisplaySize={1280,720};io.DeltaTime=1.f/60;io.IniFilename=nullptr;require(ImGui_ImplDX11_Init(d,c),"ImGui DX11 host");
        D3D11_TEXTURE2D_DESC desc={};desc.Width=1280;desc.Height=720;desc.MipLevels=desc.ArraySize=1;desc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;desc.SampleDesc.Count=1;desc.BindFlags=D3D11_BIND_RENDER_TARGET|D3D11_BIND_SHADER_RESOURCE;
        ID3D11Texture2D*t=nullptr;ID3D11RenderTargetView*target=nullptr;ID3D11ShaderResourceView*srv=nullptr;
        require(SUCCEEDED(d->CreateTexture2D(&desc,nullptr,&t))&&SUCCEEDED(d->CreateRenderTargetView(t,nullptr,&target))&&SUCCEEDED(d->CreateShaderResourceView(t,nullptr,&srv)),"owned QA target");t->Release();
        require(stadium_scene_register(argv[1],log_line),"own stadium NAV action registered");stadium_scene_device(d);stadium_scene_publish(1043,"Flamengo","");
        require(mod_screen_open_action(FIFA_STADIUM_SCENE_ACTION),"stadium card opens own screen");frame(c,target);require(stadium_scene_take_refresh(),"fresh provider request on open");
        for(int i=0;i<800&&!stadium_scene_test_view().ready;++i)frame(c,target);
        auto state=stadium_scene_test_view();require(state.ready&&state.model&&state.club==1043&&state.orbit,"own exact-club archive loaded off render thread");
        frame(c,target);image(d,c,srv,"stadium-screen-orbit.bmp");float first=stadium_scene_test_view().yaw;frame(c,target);require(stadium_scene_test_view().yaw>first,"automatic orbit advances by frame time");
        pad.Gamepad.wButtons=XINPUT_GAMEPAD_A;frame(c,target);pad={};frame(c,target);state=stadium_scene_test_view();require(!state.orbit,"controller A pauses orbit");first=state.yaw;frame(c,target);require(stadium_scene_test_view().yaw==first,"paused camera remains fixed");
        pad.Gamepad.wButtons=XINPUT_GAMEPAD_X;frame(c,target);pad={};frame(c,target);state=stadium_scene_test_view();require(state.free_camera,"controller X enters free camera");
        pad.Gamepad.bRightTrigger=255;pad.Gamepad.sThumbLX=22000;pad.Gamepad.sThumbRY=12000;pad.Gamepad.wButtons=XINPUT_GAMEPAD_RIGHT_SHOULDER;for(int i=0;i<3;++i)frame(c,target);pad={};frame(c,target);
        auto moved=stadium_scene_test_view();require(moved.z!=state.z&&moved.x!=state.x&&moved.y!=state.y&&moved.pitch!=state.pitch,"triggers + analogs + shoulder buttons move and look in 3D");
        io.AddKeyEvent(ImGuiKey_W,true);io.AddKeyEvent(ImGuiKey_E,true);frame(c,target);io.AddKeyEvent(ImGuiKey_W,false);io.AddKeyEvent(ImGuiKey_E,false);frame(c,target);state=stadium_scene_test_view();require(state.z!=moved.z&&state.y!=moved.y,"WASD and Q/E also move the free camera");
        io.AddMousePosEvent(640,350);frame(c,target);io.AddMouseWheelEvent(0,2);frame(c,target);require(stadium_scene_test_view().z!=state.z,"wheel advances free camera beyond orbit zoom clamp");
        image(d,c,srv,"stadium-screen-free.bmp");
        stadium_scene_device(nullptr);stadium_scene_device(d);frame(c,target);require(stadium_scene_test_view().model,"device reset preserves owned CPU mesh, restores GPU scene");
        io.AddKeyEvent(ImGuiKey_C,true);frame(c,target);io.AddKeyEvent(ImGuiKey_C,false);frame(c,target);require(!stadium_scene_test_view().free_camera,"keyboard C returns to orbit");
        require(mod_screen_request_back(),"Back accepted");frame(c,target);Sleep(270);require(!mod_screen_captures_input(),"Back releases input after shared cooldown");
        require(mod_screen_open_action(FIFA_STADIUM_SCENE_ACTION),"reopen");frame(c,target);stadium_scene_publish(0,"","");for(int i=0;i<200&&!stadium_scene_test_view().ready;++i)frame(c,target);state=stadium_scene_test_view();require(state.ready&&!state.model&&state.club==0,"missing club does not retain old stadium");
        mod_screen_close();frame(c,target);stadium_scene_device(nullptr);ImGui_ImplDX11_Shutdown();ImGui::DestroyContext();srv->Release();target->Release();c->Release();d->Release();
        puts("PASS: exact-club RAR preview, automatic orbit, free camera Xbox/keyboard/wheel, device reset, Back and missing club; offline only.");return 0;
    }
    if(argc>2&&!strcmp(argv[2],"--render")){
        ID3D11Device*d=nullptr;ID3D11DeviceContext*c=nullptr;D3D_FEATURE_LEVEL level;
        require(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&d,&level,&c)),"WARP device");
        Renderer render;render.device(d);auto original=stadium_scene::original(argv[1],2);printf("Original error=%s\n",original.error.c_str());require(original.model!=nullptr,"native original stadium model");
        for(int i=0;i<3;++i){require(render.model(original.model)&&render.render(1280,720,i*1.6f,1),"whole-stadium multi-angle render");std::string path="stadium-original-"+std::to_string(i)+".bmp";image(d,c,render.image(),path.c_str());}
        auto custom=stadium_scene::load(argv[1],1043);printf("CUSTOM model=%d source=%s error=%s\n",bool(custom.model),custom.source.c_str(),custom.error.c_str());
        require(custom.model!=nullptr,"RAR exact-club stadium with own material names");
        require(render.model(custom.model)&&render.render_stadium(1280,720,.45f,1),"custom exact club stadium render");image(d,c,render.image(),"stadium-maracana.bmp");
        StadiumCamera inside={{0,-custom.model->stadium_focus_radius*.12f,0},.3f,0};
        require(render.render_stadium(1280,720,0,1,&inside),"free camera inside stadium without orbit distance clamp");image(d,c,render.image(),"stadium-inside.bmp");
        inside.position.z=300;inside.pitch=-.1f;require(render.render_stadium(1280,720,0,1,&inside),"free camera travels through geometry");
        inside.pitch=2;require(!render.render_stadium(1280,720,0,1,&inside),"unsafe singular camera pitch rejected");
        require(!stadium_scene::load(argv[1],1043,"../outside").model,"archive path traversal rejected");
        printf("PASS: bounded original RX3 with own material groups and 3 orbit viewpoints.\n");render.device(nullptr);c->Release();d->Release();return 0;
    }
    if(argc>2&&!strcmp(argv[2],"--load")){
        auto result=stadium_scene::load(argv[1],1043);printf("CUSTOM name=%s source=%s model=%d error=%s\n",result.name.c_str(),result.source.c_str(),bool(result.model),result.error.c_str());
        auto native=stadium_scene::original(argv[1],2);printf("ORIGINAL source=%s model=%d error=%s\n",native.source.c_str(),bool(native.model),native.error.c_str());return result.model&&native.model?0:1;
    }
    Assets assets(argc>1?argv[1]:"U:/fifa 16");std::vector<uint8_t>b;
    const char*path=argc>2?argv[2]:"data/sceneassets/stadium/stadium_2.rx3";
    if(!(argc>2&&!strcmp(argv[2],"--packaged")?assets.read_packaged("data/sceneassets/stadium/stadium_2.rx3",b):assets.read(path,b))){printf("MISSING %s\n",path);return 1;}
    printf("RX3 %s decoded=%zu header=%.4s sections=%u\n",path,b.size(),b.data(),word(b,12));
    for(unsigned i=0;i<word(b,12)&&i<2048;i++){
        size_t at=16+i*16,off=word(b,at+4),size=word(b,at+8);unsigned type=word(b,at);
        if(i<3||(type!=0xc28193f0&&type!=0x00587aa1&&type!=0x005878f4)){
            printf("section %u type=%08x offset=%zu size=%zu n=%u stride=%u\n",i,type,off,size,word(b,off+4),word(b,off+8));
            if(type==0xc28193f0&&off+16+word(b,off+4)<=b.size())printf("descriptor %.*s\n",(int)word(b,off+4),b.data()+off+16);
            if(type==0x7e2480ec){for(size_t j=0;j<160&&j<size;j++)printf("%02x%s",b[off+j],j%16==15?"\n":" ");puts("");}
        }
    }
    auto names=texture_names(b);for(size_t i=580;i<names.size()&&i<605;i++)printf("name %zu %s\n",i,names[i].c_str());
    std::vector<uint8_t>textures;if(assets.read("data/sceneassets/stadium/stadium_2_1_textures.rx3",textures)){auto tn=texture_names(textures);printf("TEXCOUNT %zu\n",tn.size());for(size_t i=0;i<tn.size()&&i<25;i++)printf("texname %zu %s\n",i,tn[i].c_str());}
    std::vector<Part>parts;printf("mesh=%d\n",read_mesh(b,parts));
    return 0;
}
