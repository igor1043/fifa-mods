#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include "career_operations.h"
#include "../../features/operations/career_operations_io.h"
#include "../transfers/transfer_center_screen.h"
#include "../../features/retirement/retirement_engine.h"
#include "../../platform/overlay/mod_overlay_screens.h"
#include "../../platform/input/mod_xinput_gate.h"
#include "../../ui/common/screen_visuals.h"
#include "../player/club_player_profile.h"
#include "../player/player_profile_view.h"
#include "../../render/renderer/fifa_player_renderer.h"
#include "../../../third_party/imgui/imgui.h"
#include <algorithm>
#include <mutex>
#include <memory>
#include <vector>
#include <unordered_set>
#include <string>
#include <cctype>
#include <unordered_map>
#include <cmath>
namespace {
std::mutex guard;
std::string root,mod,active_path,snapshot_path,snapshot_message;
CareerLoanSnapshot snapshot={};bool snapshot_valid=false;
unsigned int window_end1=0,window_end2=0;bool window_ends_valid=false;
int live_club=0,live_date=0;
HANDLE refresh_event=nullptr;
volatile LONG roster_requested=0;
std::vector<RetirementUiPlayer>published,visible;
unsigned revision=0,visible_revision=~0U;int roster_club=0,roster_date=0;bool roster_valid=false;
void(*logger)(const char*)=nullptr;
std::unordered_set<std::string>automatic;
std::unordered_set<unsigned>selected;
std::vector<size_t>filtered;
int scope=0,row=0,age=18,plan=0,principal=1000000;
bool reset_age=false,confirm=false,keyboard=false,queued=false,scroll_row=false;
unsigned deferred_profile_id=0;
std::string pending_request;
bool calendar_date(int date){int y=date/10000,m=date/100%100,d=date%100;static const int days[]={0,31,28,31,30,31,30,31,31,30,31,30,31};return y>=2008&&y<=2100&&m>=1&&m<=12&&d>=1&&d<=days[m]+(m==2&&y%4==0&&(y%100||y%400==0));}
std::string money(uint64_t value){std::string s=std::to_string(value);for(int i=(int)s.size()-3;i>0;i-=3)s.insert((size_t)i,".");return s;}
std::string monthly_amount(const CareerLoanSchedule&s){return money(s.installment_base)+(s.extra_unit_installments?" a "+money(s.installment_base+1):"");}
std::string date_text(uint32_t value){char s[24];sprintf_s(s,"%02u/%02u/%04u",value%100,value/100%100,value/10000);return s;}
#ifdef CAREER_OPS_SCREEN_TEST
std::unordered_map<int,ImVec2>row_centers,detail_centers;
ImVec2 loan_centers[6]={};
#endif
int key_index=0;char search[128]={};std::string feedback;
WORD buttons=0;DWORD input_ready=0,next_repeat=0;
const char*keys[]={"A","B","C","D","E","F","G","H","I","J","K","L","M","N","O","P","Q","R","S","T","U","V","W","X","Y","Z","0","1","2","3","4","5","6","7","8","9","Á","É","Í","Ó","Ú","Ã","Õ","Ç","ESPAÇO","APAGAR","OK"};
struct LoanOffer {const char*name,*description;unsigned installments,rate;};
const LoanOffer offers[]={
    {"Crédito econômico","Menor custo total; parcela mais alta.",6,300},
    {"Plano equilibrado","Prazo intermediário e custo moderado.",12,800},
    {"Fôlego no orçamento","Mais tempo, com juros maiores.",18,1200},
    {"Prazo estendido","Menor parcela; dívida por mais tempo.",24,2200},
    {"Curto / custo alto","Mesmo prazo curto, mas custo maior. Compare.",6,1800},
    {"Parcela reduzida","Parcela mais leve; maior custo total.",36,3500}};
constexpr int offer_count=(int)std::size(offers);
bool profile=false,profile_valid=false,profile_received=false;unsigned profile_id=0,profile_requested=0;
ClubPlayerRow profile_row={};std::string profile_team;
player_profile::State profile_state;
float &profile_yaw=profile_state.yaw,&profile_zoom=profile_state.zoom;
unsigned profile_pose=101;
void queue_profile_pose(unsigned id=0);
HANDLE visual_event=nullptr;unsigned visual_serial=0;
std::vector<unsigned>portrait_ids;
std::vector<int>portrait_teams;
struct VisualBatch {unsigned serial=0;std::unordered_map<unsigned,fifa_player::Texture>faces;fifa_player::Texture crest,flag,league_logo;int nationality=0,age=-1,foot=0,league=0;float league_strength=-1;std::string league_name;
    std::vector<fifa_player::CompetitionIdentity>competition_names;std::unordered_map<int,fifa_player::Texture>competitions;
    std::unordered_map<int,fifa_player::Texture>clubs;
    std::shared_ptr<const fifa_player::Model>model;};
std::shared_ptr<const VisualBatch>visual_ready,visual_shown;
ID3D11Device*device=nullptr;std::unordered_map<unsigned,ID3D11ShaderResourceView*>face_views;
std::unordered_map<int,ID3D11ShaderResourceView*>club_views;
std::unordered_map<int,ID3D11ShaderResourceView*>profile_competition_views;
ID3D11ShaderResourceView*profile_crest=nullptr,*profile_flag=nullptr,*profile_league=nullptr;fifa_player::Renderer profile_renderer;
void clear_visuals(){for(auto&v:face_views)screen_visuals::release(v.second);face_views.clear();for(auto&v:club_views)screen_visuals::release(v.second);club_views.clear();for(auto&v:profile_competition_views)screen_visuals::release(v.second);profile_competition_views.clear();screen_visuals::release(profile_crest);screen_visuals::release(profile_flag);screen_visuals::release(profile_league);visual_shown.reset();profile_renderer.clear();}
void request_visuals(const std::vector<unsigned>&ids,const std::vector<int>&teams){std::lock_guard<std::mutex>lock(guard);if(ids==portrait_ids&&teams==portrait_teams)return;
    portrait_ids=ids;portrait_teams=teams;++visual_serial;visual_ready.reset();if(visual_event)SetEvent(visual_event);}
DWORD WINAPI visual_worker(void*){fifa_player::Assets assets(root);
    for(;;){if(WaitForSingleObject(visual_event,INFINITE)!=WAIT_OBJECT_0)return 0;
        auto b=std::make_shared<VisualBatch>();std::vector<unsigned>ids;std::vector<int>teams;ClubPlayerRow player={};bool load=false,cancelled=false;unsigned pose=101;
        {std::lock_guard<std::mutex>lock(guard);b->serial=visual_serial;ids=portrait_ids;teams=portrait_teams;player=profile_row;load=profile&&profile_valid;pose=profile_pose;}
        for(unsigned id:ids){{std::lock_guard<std::mutex>lock(guard);if(b->serial!=visual_serial){cancelled=true;break;}}fifa_player::Texture t;if(assets.portrait((int)id,t))b->faces.emplace(id,std::move(t));}
        if(cancelled){assets.clear_portrait_cache();continue;}
        for(int id:teams)if(id>0&&!b->clubs.count(id)){fifa_player::Texture t;if(assets.crest(id,t))b->clubs.emplace(id,std::move(t));}
        if(load){b->nationality=assets.nationality(player.player_id);assets.nationality_flag(b->nationality,b->flag);b->age=assets.player_age(player.player_id);b->foot=assets.preferred_foot(player.player_id);
            b->league=assets.league(player.team_id,b->league_name);assets.competition_icon(b->league,b->league_logo);b->league_strength=assets.league_strength(player.team_id);
            b->competition_names=assets.profile_competition_names(player.player_id,player.team_id);for(auto&i:b->competition_names){fifa_player::Texture logo;if(assets.competition_icon(i.asset,logo))b->competitions.emplace(i.root,std::move(logo));}}
        if(load&&player.team_id>0){assets.crest(player.team_id,b->crest);auto model=std::make_shared<fifa_player::Model>(assets.load(player));
            auto*p=fifa_player::presentation_pose_find(pose);
            if(p&&!model->parts.empty()&&fifa_player::apply_presentation_pose(*model,false,nullptr,p->id))b->model=model;}
        assets.clear_portrait_cache();
        {std::lock_guard<std::mutex>lock(guard);if(b->serial!=visual_serial)continue;visual_ready=b;}
    }
}
DWORD WINAPI guarded_visual_worker(void*p){try{return visual_worker(p);}catch(...){if(logger)logger("Retirement visual worker failed safely; save remains untouched");return 0;}}
void sync_visuals(){std::shared_ptr<const VisualBatch>b;unsigned current;
    {std::lock_guard<std::mutex>lock(guard);b=visual_ready;current=visual_serial;}
    if(!b||b==visual_shown||b->serial!=current)return;clear_visuals();visual_shown=b;
    for(const auto&i:b->faces)if(auto*v=screen_visuals::upload(device,i.second))face_views.emplace(i.first,v);
    for(const auto&i:b->clubs)if(auto*v=screen_visuals::upload(device,i.second))club_views.emplace(i.first,v);
    for(const auto&i:b->competitions)if(auto*v=screen_visuals::upload(device,i.second))profile_competition_views.emplace(i.first,v);
    profile_crest=screen_visuals::upload(device,b->crest);
    profile_flag=screen_visuals::upload(device,b->flag);
    profile_league=screen_visuals::upload(device,b->league_logo);
}
std::string utf8(const char*s){if(!s)return {};if(MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s,-1,nullptr,0))return s;
    int n=MultiByteToWideChar(CP_ACP,0,s,-1,nullptr,0);if(!n)return {};std::vector<wchar_t>w(n);MultiByteToWideChar(CP_ACP,0,s,-1,w.data(),n);
    int m=WideCharToMultiByte(CP_UTF8,0,w.data(),-1,nullptr,0,nullptr,nullptr);std::string out(m,'\0');WideCharToMultiByte(CP_UTF8,0,w.data(),-1,&out[0],m,nullptr,nullptr);out.pop_back();return out;}
std::string folded(const std::string&s){auto value=utf8(s.c_str());int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,value.data(),(int)value.size(),nullptr,0);if(!n)return {};
    std::vector<wchar_t>wide(n);MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,value.data(),(int)value.size(),wide.data(),n);
    int count=LCMapStringEx(LOCALE_NAME_INVARIANT,LCMAP_LOWERCASE,wide.data(),n,nullptr,0,nullptr,nullptr,0);if(!count)return {};
    std::vector<wchar_t>lower(count);LCMapStringEx(LOCALE_NAME_INVARIANT,LCMAP_LOWERCASE,wide.data(),n,lower.data(),count,nullptr,nullptr,0);
    for(auto&c:lower){if(wcschr(L"àáâãäå",c))c=L'a';else if(wcschr(L"èéêë",c))c=L'e';else if(wcschr(L"ìíîï",c))c=L'i';
        else if(wcschr(L"òóôõö",c))c=L'o';else if(wcschr(L"ùúûü",c))c=L'u';else if(c==L'ç')c=L'c';else if(c==L'ñ')c=L'n';}
    int bytes=WideCharToMultiByte(CP_UTF8,0,lower.data(),count,nullptr,0,nullptr,nullptr);std::string out(bytes,'\0');
    if(bytes)WideCharToMultiByte(CP_UTF8,0,lower.data(),count,&out[0],bytes,nullptr,nullptr);return out;}
bool get_snapshot(CareerLoanSnapshot&s,std::string&p,std::string&m){std::lock_guard<std::mutex>lock(guard);s=snapshot;p=snapshot_path;m=snapshot_message;
    if(!snapshot_valid||p.empty()){m="Ainda não foi possível ler um save válido. Salve a carreira pelo menu do jogo.";return false;}
    if(live_club<=0){m="Nenhum clube da carreira foi identificado. Entre na carreira antes de solicitar.";return false;}
    if(s.club!=(unsigned)live_club){m="O save lido pertence a outro clube. Salve a carreira que está aberta.";return false;}
    if(!calendar_date(live_date)){m="A data da carreira ainda não foi identificada. Salve e reabra a carreira.";return false;}
    if(s.date>(unsigned)live_date){m="A data do save não corresponde à carreira aberta. Reabra o save correto.";return false;}
    return true;}
bool launch(career_ops::Request&r,std::string&message,std::string*registered=nullptr){
#ifdef CAREER_OPS_SCREEN_TEST
    message="QA offline: solicitações e gravações de save desativadas.";return false;
#endif
    std::string operations=mod+"\\runtime\\operations";CreateDirectoryA((mod+"\\runtime").c_str(),nullptr);CreateDirectoryA(operations.c_str(),nullptr);
    std::string exe=mod+"\\career_operations_worker.exe";if(!career_ops::exists(exe)){message="Worker não instalado; nenhuma solicitação registrada.";return false;}
    FILETIME created,exited,kernel,user;ULARGE_INTEGER ft;
    if(!GetProcessTimes(GetCurrentProcess(),&created,&exited,&kernel,&user))return false;
    ft.LowPart=created.dwLowDateTime;ft.HighPart=created.dwHighDateTime;r.parent_created=ft.QuadPart;r.parent=GetCurrentProcessId();
    std::string path=operations+"\\request-"+std::to_string(r.parent)+"-"+std::to_string(GetTickCount64())+"-"+std::to_string(r.kind)+".bin";
    if(!career_ops::write_request(path,r,message))return false;
    std::string command="\""+exe+"\" \""+path+"\" \""+mod+"\"";STARTUPINFOA start={};PROCESS_INFORMATION process={};start.cb=sizeof(start);start.dwFlags=STARTF_USESHOWWINDOW;start.wShowWindow=SW_HIDE;
    if(!CreateProcessA(exe.c_str(),&command[0],nullptr,nullptr,FALSE,CREATE_NO_WINDOW,nullptr,root.c_str(),&start,&process)){message="Worker não iniciou. Solicitação não executada.";return false;}
    CloseHandle(process.hThread);CloseHandle(process.hProcess);if(logger)logger(("CareerOps request="+path).c_str());
    if(registered)*registered=path;message="Pedido registrado. Agora salve a carreira, feche o FIFA completamente e aguarde a aplicação antes de reabrir.";return true;
}
DWORD WINAPI refresh_worker(void*){
    for(;;){WaitForSingleObject(refresh_event,INFINITE);std::string path;int club,date;
        {std::lock_guard<std::mutex>lock(guard);path=active_path;club=live_club;date=live_date;}
        if(path.empty())continue;CareerLoanSnapshot s={};std::vector<unsigned char>data;std::string message;
        bool valid=career_ops::read_save(path,data,s,message);
        unsigned int end1=0,end2=0;bool ends_valid=valid&&retirement_engine_get_transfer_window_ends(path.c_str(),&end1,&end2)!=0;
        {std::lock_guard<std::mutex>lock(guard);if(path!=active_path)continue;snapshot=s;snapshot_path=path;snapshot_valid=valid;snapshot_message=message;
            window_end1=ends_valid?end1:0;window_end2=ends_valid?end2:0;window_ends_valid=ends_valid;}
        if(!valid||club<=0||s.club!=(unsigned)club||s.date>(unsigned)date)continue;
        std::string ledger=career_ops::ledger_path(mod,path,s.setup_date,s.manager);
        if((career_ops::exists(ledger)||career_ops::exists(ledger+".journal"))&&!automatic.count(ledger)){
            career_ops::Ledger contract;
            if(career_ops::exists(ledger+".journal")||(career_ops::read_ledger(ledger,contract,message)&&contract.club==s.club&&contract.credited&&contract.paid<contract.terms.installments)){
                auto r=std::make_unique<career_ops::Request>();r->kind=career_ops::LoanCollect;r->club=s.club;r->manager=s.manager;r->setup=s.setup_date;r->career_date=s.date;
                strcpy_s(r->data,path.c_str());if(launch(*r,message))automatic.insert(ledger);
            }
        }
    }
}
DWORD WINAPI guarded_refresh_worker(void*context){try{return refresh_worker(context);}catch(...){
    {std::lock_guard<std::mutex>lock(guard);snapshot_valid=false;snapshot_message="Serviço indisponível. Nenhuma nova operação será executada.";}
    if(logger)logger("CareerOps: worker stopped safely; UI operations disabled");return 0;}}
void refresh_visible(){std::lock_guard<std::mutex>lock(guard);if(visible_revision!=revision){visible=published;visible_revision=revision;row=0;scroll_row=true;
    std::unordered_set<unsigned>valid;for(const auto&r:visible)if(r.retiring==1)valid.insert(r.id);
    for(auto i=selected.begin();i!=selected.end();)if(!valid.count(*i))i=selected.erase(i);else ++i;
    if(profile&&!valid.count(profile_id)){profile=profile_valid=false;profile_requested=0;++visual_serial;visual_ready.reset();}}}
void filter(){filtered.clear();std::string needle=folded(search);
    for(size_t i=0;i<visible.size();++i){const auto&r=visible[i];if(r.retiring!=1||(scope==0&&!r.in_club))continue;
        if(!needle.empty()&&folded(utf8(r.name)).find(needle)==std::string::npos)continue;filtered.push_back(i);}
    row=std::max(0,std::min(row,(int)filtered.size()-1));}
void type_key(int index){if(index<0||index>=(int)std::size(keys))return;
    if(index==46){keyboard=false;input_ready=GetTickCount()+250;return;}
    if(index==45){size_t n=strlen(search);if(n){do{--n;}while(n&&(search[n]&0xC0)==0x80);search[n]=0;}row=0;return;}
    const char*s=index==44?" ":keys[index];if(strlen(search)+strlen(s)<sizeof(search)-1)strcat_s(search,s);row=0;
}
uint32_t next_month(uint32_t date){unsigned y=date/10000,m=date/100%100,d=date%100;if(++m>12){m=1;++y;}
    static const unsigned days[]={0,31,28,31,30,31,30,31,31,30,31,30,31};unsigned max=days[m]+(m==2&&y%4==0&&(y%100!=0||y%400==0));return y*10000+m*100+std::min(d,max);}
bool offer_terms(int choice,CareerLoanTerms&t,CareerLoanSchedule&s){CareerLoanSnapshot f;std::string p,m;if(choice<0||choice>=offer_count||!get_snapshot(f,p,m))return false;
    int date;{std::lock_guard<std::mutex>lock(guard);date=live_date;}if(!calendar_date(date))return false;
    t={};t.principal=(uint32_t)principal;t.interest_basis_points=offers[choice].rate;t.installments=offers[choice].installments;t.contract_date=(uint32_t)date;t.first_due_date=next_month(t.contract_date);t.interval_months=1;
    return career_loan_schedule(&t,&s)!=0;}
bool terms(CareerLoanTerms&t,CareerLoanSchedule&s){return offer_terms(plan,t,s);}
std::vector<unsigned>target_ids(){std::vector<unsigned>ids;
    for(const auto&r:visible)if(r.retiring==1&&selected.count(r.id))ids.push_back(r.id);
    std::sort(ids.begin(),ids.end());ids.erase(std::unique(ids.begin(),ids.end()),ids.end());return ids;}
void apply(bool loan){CareerLoanSnapshot s;std::string path,message;if(!get_snapshot(s,path,message)){feedback="Save atual ainda não validado: "+message;confirm=false;return;}
    auto r=std::make_unique<career_ops::Request>();r->kind=loan?career_ops::LoanCredit:career_ops::Retirement;r->club=s.club;r->manager=s.manager;r->setup=s.setup_date;
    {std::lock_guard<std::mutex>lock(guard);r->career_date=(unsigned)live_date;}
    r->requested_at=career_ops::file_time_now();strcpy_s(r->data,path.c_str());
    if(loan){CareerLoanSchedule schedule;if(!terms(r->terms,schedule)){feedback="Condições inválidas.";return;}
        std::string ledger=career_ops::ledger_path(mod,path,s.setup_date,s.manager);if(ledger.empty()||career_ops::exists(ledger)||career_ops::exists(ledger+".journal")){feedback="Esta carreira já possui um contrato ou uma aplicação pendente. Novo empréstimo bloqueado.";confirm=false;return;}}
    else {r->reset_age=reset_age?1:0;r->target_age=(unsigned)age;
        int club,date;bool valid;{std::lock_guard<std::mutex>lock(guard);club=roster_club;date=roster_date;valid=roster_valid;}
        if(!valid||club!=(int)s.club||date!=(int)r->career_date){feedback="Lista mudou: reabra a tela antes de aplicar.";confirm=false;return;}
        auto ids=target_ids();if(ids.empty()||ids.size()>std::size(r->ids)){feedback="Nenhum jogador elegível selecionado.";confirm=false;return;}
        r->id_count=(unsigned)ids.size();std::copy(ids.begin(),ids.end(),r->ids);}
    if(queued){feedback="Já existe um pedido registrado nesta sessão. Salve e feche o FIFA para aplicar.";confirm=false;return;}
    queued=launch(*r,message,&pending_request);feedback=message;confirm=false;input_ready=GetTickCount()+350;
    if(logger)logger((std::string("CareerOps: ")+(queued?"request accepted: ":"request rejected: ")+message).c_str());
}
void open(void*){scope=0;row=0;deferred_profile_id=0;selected.clear();search[0]=0;reset_age=false;age=18;confirm=keyboard=false;queued=!pending_request.empty();feedback=queued?"Pedido já registrado. Salve a carreira e feche o FIFA para aplicar.":"";input_ready=GetTickCount()+350;buttons=0;
    {std::lock_guard<std::mutex>lock(guard);profile=profile_valid=false;profile_id=profile_requested=0;portrait_ids.clear();portrait_teams.clear();++visual_serial;visual_ready.reset();}clear_visuals();
    InterlockedExchange(&roster_requested,1);career_operations_request_native_refresh();if(refresh_event)SetEvent(refresh_event);}
void loan_open(void*){plan=0;principal=1000000;confirm=keyboard=false;queued=!pending_request.empty();feedback=queued?"Pedido já solicitado. Salve a carreira e feche o FIFA completamente para aplicar.":"";input_ready=GetTickCount()+350;buttons=0;if(refresh_event)SetEvent(refresh_event);}
void closed(void*){{std::lock_guard<std::mutex>lock(guard);profile=profile_valid=profile_received=false;profile_requested=0;portrait_ids.clear();++visual_serial;visual_ready.reset();}
    keyboard=confirm=false;clear_visuals();}
BOOL back(void*){if(keyboard||confirm){keyboard=confirm=false;input_ready=GetTickCount()+350;return TRUE;}
    if(profile){{std::lock_guard<std::mutex>lock(guard);profile=profile_valid=false;profile_requested=0;portrait_ids.clear();portrait_teams.clear();++visual_serial;visual_ready.reset();}
        clear_visuals();scroll_row=true;input_ready=GetTickCount()+350;return TRUE;}return FALSE;}
void open_profile(){if(filtered.empty())return;unsigned id=visible[filtered[row]].id;
    {std::lock_guard<std::mutex>lock(guard);profile=true;profile_valid=profile_received=false;profile_id=profile_requested=id;profile_row={};profile_team.clear();
        portrait_ids={id};portrait_teams.clear();++visual_serial;visual_ready.reset();
        size_t count=fifa_player::presentation_pose_count(fifa_player::PoseIndividual);auto*p=count?fifa_player::presentation_pose_at(GetTickCount()%count,fifa_player::PoseIndividual):nullptr;
        profile_pose=p?p->id:101;}
    clear_visuals();profile_state=player_profile::State{};input_ready=GetTickCount()+350;
    if(logger){char line[128];sprintf_s(line,"Retirement: exact player profile requested id=%u; native provider queued",id);logger(line);}
    career_operations_request_native_refresh();if(visual_event)SetEvent(visual_event);}
void inputs(bool loan){XINPUT_STATE pad={};for(DWORD i=0;i<4;++i)if(mod_xinput_read_raw(i,&pad)==ERROR_SUCCESS)break;
    WORD now=pad.Gamepad.wButtons,pressed=(WORD)(now&~buttons);buttons=now;DWORD tick=GetTickCount();if(tick<input_ready)return;
    bool left=(now&XINPUT_GAMEPAD_DPAD_LEFT)||pad.Gamepad.sThumbLX<-18000,right=(now&XINPUT_GAMEPAD_DPAD_RIGHT)||pad.Gamepad.sThumbLX>18000;
    bool up=(now&XINPUT_GAMEPAD_DPAD_UP)||pad.Gamepad.sThumbLY>18000,down=(now&XINPUT_GAMEPAD_DPAD_DOWN)||pad.Gamepad.sThumbLY<-18000;
    bool key_up=!ImGui::IsAnyItemActive()&&ImGui::IsKeyPressed(ImGuiKey_UpArrow),key_down=!ImGui::IsAnyItemActive()&&ImGui::IsKeyPressed(ImGuiKey_DownArrow);
    bool accept=!ImGui::IsAnyItemActive()&&(ImGui::IsKeyPressed(ImGuiKey_Enter)||ImGui::IsKeyPressed(ImGuiKey_Space));
    if(!loan&&profile){player_profile::input(profile_state,pad,pressed,true);
        if((pressed&XINPUT_GAMEPAD_Y)||ImGui::IsKeyPressed(ImGuiKey_F))profile_state.portrait=!profile_state.portrait;
        if((pressed&XINPUT_GAMEPAD_X)||ImGui::IsKeyPressed(ImGuiKey_P))queue_profile_pose();return;}
    if(confirm){if((pressed&XINPUT_GAMEPAD_A)||accept)apply(loan);return;}
    if(keyboard){if(tick>=next_repeat&&(left||right||up||down)){int delta=(right?1:0)-(left?1:0)+(down?9:0)-(up?9:0);key_index=std::max(0,std::min(46,key_index+delta));next_repeat=tick+160;}
        if(pressed&XINPUT_GAMEPAD_A)type_key(key_index);return;}
    if(queued)return;
    if(loan){int move=(right?1:0)-(left?1:0)+(down?3:0)-(up?3:0);
        if(tick>=next_repeat&&move){plan=std::clamp(plan+move,0,offer_count-1);next_repeat=tick+200;}
        if(key_up)plan=std::max(0,plan-3);if(key_down)plan=std::min(offer_count-1,plan+3);
        if(!ImGui::IsAnyItemActive()&&ImGui::IsKeyPressed(ImGuiKey_LeftArrow))plan=std::max(0,plan-1);
        if(!ImGui::IsAnyItemActive()&&ImGui::IsKeyPressed(ImGuiKey_RightArrow))plan=std::min(offer_count-1,plan+1);
        if(pressed&XINPUT_GAMEPAD_LEFT_SHOULDER)principal=std::max(100000,principal-100000);
        if(pressed&XINPUT_GAMEPAD_RIGHT_SHOULDER)principal=std::min(100000000,principal+100000);
        if(((pressed&XINPUT_GAMEPAD_A)||accept)&&!queued)confirm=true;
    }else {
        if(pressed&(XINPUT_GAMEPAD_LEFT_SHOULDER|XINPUT_GAMEPAD_RIGHT_SHOULDER)){scope=1-scope;row=0;scroll_row=true;filter();}
        if((pressed&XINPUT_GAMEPAD_A)||accept){if(!filtered.empty()){unsigned id=visible[filtered[row]].id;if(selected.count(id))selected.erase(id);else selected.insert(id);}}
        if((pressed&XINPUT_GAMEPAD_BACK)||(!ImGui::IsAnyItemActive()&&ImGui::IsKeyPressed(ImGuiKey_R)))reset_age=!reset_age;
        if(pressed&XINPUT_GAMEPAD_Y){keyboard=true;key_index=0;}
        if(!ImGui::IsAnyItemActive()&&ImGui::IsKeyPressed(ImGuiKey_F3)){keyboard=true;key_index=0;}
        if(!ImGui::IsAnyItemActive()&&ImGui::IsKeyPressed(ImGuiKey_Tab)){scope=1-scope;row=0;scroll_row=true;filter();}
        if(tick>=next_repeat&&reset_age&&(pad.Gamepad.bLeftTrigger>160||pad.Gamepad.bRightTrigger>160)){age=std::max(12,std::min(50,age+(pad.Gamepad.bRightTrigger>160?1:-1)));next_repeat=tick+180;}
        if((tick>=next_repeat&&(up||down))||key_up||key_down){row=std::max(0,std::min((int)filtered.size()-1,row+((down||key_down)?1:-1)));scroll_row=true;next_repeat=tick+110;}
        if((pressed&XINPUT_GAMEPAD_X)||(!ImGui::IsAnyItemActive()&&ImGui::IsKeyPressed(ImGuiKey_I)))open_profile();
        if(((pressed&XINPUT_GAMEPAD_START)||(!ImGui::IsAnyItemActive()&&ImGui::IsKeyPressed(ImGuiKey_F5)))&&!queued)confirm=true;
    }
}
void header(const char*name,bool title=true,bool full_screen=false){ImVec2 size=ImGui::GetIO().DisplaySize;
    if(full_screen)screen_visuals::begin_fullscreen(name,ImGuiWindowFlags_NoTitleBar|ImGuiWindowFlags_NoCollapse|ImGuiWindowFlags_NoNavInputs);
    else {ImGui::SetNextWindowPos(ImVec2(size.x*.06f,size.y*.06f));ImGui::SetNextWindowSize(ImVec2(size.x*.88f,size.y*.88f));
        ImGui::Begin(name,nullptr,ImGuiWindowFlags_NoTitleBar|ImGuiWindowFlags_NoCollapse|ImGuiWindowFlags_NoResize|ImGuiWindowFlags_NoMove|ImGuiWindowFlags_NoSavedSettings|ImGuiWindowFlags_NoNavInputs);}
    if(title){ImGui::SetWindowFontScale(1.35f);ImGui::TextUnformatted(name);ImGui::SetWindowFontScale(1);ImGui::Separator();}}
void confirmation(bool loan){if(!confirm)return;
    ImVec2 display=ImGui::GetIO().DisplaySize;float width=std::min(680.f,display.x*.84f);ImGui::SetNextWindowPos({(display.x-width)*.5f,display.y*.25f});ImGui::SetNextWindowSize({width,display.y*.48f});
    ImGui::Begin("Revisar pedido",nullptr,ImGuiWindowFlags_NoTitleBar|ImGuiWindowFlags_NoMove|ImGuiWindowFlags_NoResize|ImGuiWindowFlags_NoSavedSettings|ImGuiWindowFlags_NoNavInputs);
    ImGui::SetWindowFontScale(1.25f);ImGui::TextUnformatted(loan?"Confirmar empréstimo":"Confirmar seleção");ImGui::SetWindowFontScale(1);ImGui::Separator();
    if(!loan)ImGui::TextWrapped("Remover a aposentadoria de %zu jogadores MARCADOS. %s. Jogadores não marcados não serão alterados.",target_ids().size(),reset_age?"Também alterar a idade":"Preservar a idade atual");
    else {CareerLoanTerms t;CareerLoanSchedule s;if(terms(t,s)){
        ImGui::TextUnformatted(offers[plan].name);ImGui::Text("Você recebe: %s",money(t.principal).c_str());
        ImGui::Text("Juros de todo o contrato: %.2f%% = %s",t.interest_basis_points/100.f,money(s.total-t.principal).c_str());
        ImGui::Text("%u parcelas mensais de %s",s.count,monthly_amount(s).c_str());
        ImGui::Text("TOTAL A PAGAR: %s | primeira parcela: %s",money(s.total).c_str(),date_text(t.first_due_date).c_str());}}
    ImGui::Spacing();ImGui::TextWrapped("1. Confirme o pedido.  2. Salve a carreira.  3. Feche o FIFA completamente. Só então a alteração é aplicada com backup automático. O dinheiro não entra imediatamente nesta tela.");
    if(ImGui::Button("Confirmar pedido (A)",ImVec2(220,34)))apply(loan);ImGui::SameLine();if(ImGui::Button("Cancelar (B)",ImVec2(180,34))){confirm=false;input_ready=GetTickCount()+350;}ImGui::End();
}
void queue_profile_pose(unsigned id){
    size_t count=fifa_player::presentation_pose_count(fifa_player::PoseIndividual);if(!count)return;
    if(!id){size_t index=0;while(index<count&&fifa_player::presentation_pose_at(index,fifa_player::PoseIndividual)->id!=profile_pose)++index;
        id=fifa_player::presentation_pose_at((index+1)%count,fifa_player::PoseIndividual)->id;}
    auto*p=fifa_player::presentation_pose_find(id);if(!p||!(p->modes&fifa_player::PoseIndividual))return;
    std::lock_guard<std::mutex>lock(guard);profile_pose=id;++visual_serial;visual_ready.reset();if(visual_event)SetEvent(visual_event);
}
void draw_profile(){
    ClubPlayerRow r={};std::string team;bool valid,received;
    {std::lock_guard<std::mutex>lock(guard);r=profile_row;team=profile_team;valid=profile_valid;received=profile_received;}
    if(!valid){ImGui::TextUnformatted("Perfil de jogador");
        ImGui::TextUnformatted(received?"Perfil indisponível.":"Carregando dados do jogador...");return;}
    player_profile::Visuals visuals;auto face=face_views.find((unsigned)r.player_id);if(face!=face_views.end())visuals.face=face->second;
    visuals.crest=profile_crest;visuals.flag=profile_flag;visuals.loading=!visual_shown;
    visuals.competition_icons=profile_competition_views;if(visual_shown)visuals.competitions=visual_shown->competition_names;
    if(visual_shown){visuals.model=visual_shown->model;visuals.nationality=visual_shown->nationality;visuals.age=visual_shown->age;visuals.foot=visual_shown->foot;
        visuals.league=visual_shown->league;visuals.league_name=visual_shown->league_name;visuals.league_logo=profile_league;visuals.league_strength=visual_shown->league_strength;}
    auto action=player_profile::draw(r,team.c_str(),profile_state,visuals,profile_renderer,profile_pose);
    if(action.back)mod_screen_request_back();
    if(action.next_pose)queue_profile_pose();
    if(action.pose)queue_profile_pose(action.pose);
}
void draw_retirement(void*){refresh_visible();filter();if(deferred_profile_id){unsigned id=deferred_profile_id;deferred_profile_id=0;for(size_t i=0;i<filtered.size();++i)if(visible[filtered[i]].id==id){row=(int)i;open_profile();break;}}inputs(false);filter();sync_visuals();screen_visuals::LightTheme theme;header(profile?"Perfil de jogador":"Aposentadoria",!profile);
    if(profile){draw_profile();ImGui::End();return;}
    ImGui::TextUnformatted("Mantenha seus jogadores em atividade. Marque quem não deve se aposentar.");
    ImGui::BeginDisabled(confirm||queued);
    const char*scopes[]={"Meu time","Geral"};for(int i=0;i<2;++i){if(i)ImGui::SameLine();bool active=scope==i;if(active)ImGui::PushStyleColor(ImGuiCol_Button,{.04f,.36f,.65f,1});if(active)ImGui::PushStyleColor(ImGuiCol_Text,{1,1,1,1});
        if(ImGui::Button(scopes[i],{180,34})){scope=i;row=0;scroll_row=true;}if(active)ImGui::PopStyleColor(2);}
    ImGui::SameLine();ImGui::TextDisabled("LB / RB: trocar aba");
    ImGui::SetNextItemWidth(std::min(420.f,ImGui::GetContentRegionAvail().x*.5f));if(ImGui::InputTextWithHint("##Nome","Pesquisar jogador...",search,sizeof(search))){row=0;scroll_row=true;}ImGui::SameLine();if(ImGui::Button("Pesquisar (Y / F3)")){keyboard=!keyboard;key_index=0;}
    ImGui::Checkbox("Alterar idade também (opcional / View / R)",&reset_age);if(reset_age){ImGui::SameLine();ImGui::SetNextItemWidth(180);ImGui::SliderInt("Idade (LT / RT)",&age,12,50);}
    bool valid;{std::lock_guard<std::mutex>lock(guard);valid=roster_valid&&roster_club==live_club&&roster_date==live_date;}
    if(!valid)ImGui::TextWrapped("Aguardando lista da carreira atual. Nada pode ser aplicado enquanto a lista não for validada.");
    if(keyboard){ImGui::BeginChild("Teclado",{0,150},true,ImGuiWindowFlags_NoNavInputs);
        for(int i=0;i<(int)std::size(keys);++i){ImGui::PushID(i);if(i%9)ImGui::SameLine();if(i==key_index)ImGui::PushStyleColor(ImGuiCol_Button,{.05f,.42f,.65f,1});
            bool highlighted=i==key_index;if(ImGui::Button(keys[i],{i>=44?90.f:50.f,30}))type_key(i);if(highlighted)ImGui::PopStyleColor();ImGui::PopID();}ImGui::EndChild();}
    filter();
    if(ImGui::Button("Marcar exibidos")){for(size_t index:filtered)selected.insert(visible[index].id);}ImGui::SameLine();
    if(ImGui::Button("Limpar seleção"))selected.clear();ImGui::SameLine();
    ImGui::Text("%zu se aposentando | %zu marcados",filtered.size(),selected.size());
    if(valid&&filtered.empty())ImGui::TextUnformatted(search[0]?"Nenhum aposentando corresponde à pesquisa.":"Nenhum jogador se aposentando neste escopo.");
    float list_height=std::max(60.f,ImGui::GetContentRegionAvail().y-(confirm?205.f:98.f));
    ImGui::BeginChild("Lista aposentadoria",{0,list_height},true,ImGuiWindowFlags_NoNavInputs);
    constexpr float line=52;
    if(scroll_row&&!filtered.empty())ImGui::SetScrollY(std::max(0.f,row*line-list_height*.45f));
    int first=std::max(0,(int)(ImGui::GetScrollY()/line)-4),last=std::min((int)filtered.size(),first+48);
    std::vector<unsigned>ids;std::vector<int>teams;for(int i=first;i<last;++i){ids.push_back(visible[filtered[i]].id);teams.push_back(visible[filtered[i]].team_id);}request_visuals(ids,teams);
#ifdef CAREER_OPS_SCREEN_TEST
    row_centers.clear();detail_centers.clear();
#endif
    ImGuiListClipper clip;clip.Begin((int)filtered.size(),line);
    while(clip.Step())for(int i=clip.DisplayStart;i<clip.DisplayEnd;++i){const auto&r=visible[filtered[i]];ImGui::PushID((int)r.id);bool checked=selected.count(r.id)!=0;
        ImVec2 at=ImGui::GetCursorScreenPos();
        ImGui::SetCursorScreenPos({at.x,at.y+12});if(ImGui::Checkbox("##sel",&checked)){if(checked)selected.insert(r.id);else selected.erase(r.id);}at.x+=32;
        ImGui::SetCursorScreenPos(at);
        float width=ImGui::GetContentRegionAvail().x;bool clicked=ImGui::Selectable("##Marcar",row==i,0,{std::max(30.f,width-122),48});auto*d=ImGui::GetWindowDrawList();auto p=face_views.find(r.id);
        if(p!=face_views.end())d->AddImage((ImTextureID)(intptr_t)p->second,{at.x+4,at.y+2},{at.x+50,at.y+48});
        else {d->AddCircleFilled({at.x+27,at.y+15},8,IM_COL32(154,164,169,255));d->AddRectFilled({at.x+15,at.y+24},{at.x+39,at.y+45},IM_COL32(154,164,169,255),6);}
        auto club_icon=club_views.find(r.team_id);if(club_icon!=club_views.end())d->AddImage((ImTextureID)(intptr_t)club_icon->second,{at.x+58,at.y+12},{at.x+82,at.y+36});
        auto label=utf8(r.name);d->PushClipRect({at.x+94,at.y},{at.x+std::max(96.f,width-128),at.y+48},true);d->AddText({at.x+94,at.y+4},ImGui::GetColorU32(ImGuiCol_Text),label.c_str());
        auto age_label=(r.age>=0?std::to_string(r.age)+" anos · ":std::string{})+(r.club_name[0]?utf8(r.club_name):r.in_club?std::string("Meu time"):std::string("Clube não informado"));
        d->AddText({at.x+94,at.y+27},ImGui::GetColorU32(ImGuiCol_TextDisabled),age_label.c_str());d->PopClipRect();
        if(clicked){row=i;if(selected.count(r.id))selected.erase(r.id);else selected.insert(r.id);}
        ImGui::SetCursorScreenPos({at.x+width-116,at.y+8});if(ImGui::Button("Detalhes (X)",{110,32})){row=i;deferred_profile_id=r.id;}
#ifdef CAREER_OPS_SCREEN_TEST
        row_centers[i]={at.x+std::min(width*.4f,300.f),at.y+24};detail_centers[i]={at.x+width-61,at.y+24};
#endif
        // Never release SRVs or change the list while ImGui still owns this frame.
        ImGui::SetCursorScreenPos({at.x-32,at.y+line});ImGui::PopID();
    }scroll_row=false;ImGui::EndChild();
    ImGui::EndDisabled();
    ImGui::BeginDisabled(!valid||queued||confirm||target_ids().empty());if(ImGui::Button("Aplicar aos marcados (Menu / F5)",{330,34}))confirm=true;ImGui::EndDisabled();
    confirmation(false);if(!feedback.empty())ImGui::TextWrapped("%s",feedback.c_str());
    ImGui::TextWrapped("Direcional: jogador | A/Enter/clique: marcar | X/I: detalhes | Y/F3: pesquisa | LB/RB/Tab: aba | Menu/F5: aplicar | B/Esc: voltar");ImGui::End();
}
void draw_loans(void*){screen_visuals::LightTheme theme;header("Empréstimos do clube",true,true);CareerLoanSnapshot f;std::string p,m;bool valid=get_snapshot(f,p,m);
    career_ops::Ledger contract;std::string ledger=valid?career_ops::ledger_path(mod,p,f.setup_date,f.manager):"";
    bool existing=!ledger.empty()&&(career_ops::exists(ledger)||career_ops::exists(ledger+".journal"));
    // Validate before handling A, including the second confirmation press.
    if(valid&&!existing)inputs(true);else{confirm=false;buttons=0;}
    ImGui::TextWrapped("O clube recebe um reforço no orçamento e devolve esse valor, mais juros, em parcelas mensais. As parcelas usam as datas da carreira, não o tempo real.");
    if(!valid)ImGui::TextWrapped("Abra sua carreira e salve pelo menu do jogo para identificar o save. Ainda não é possível pedir dinheiro. %s",m.c_str());
    else ImGui::Text("Orçamento de transferências: %s  |  valores na moeda da carreira",money(f.transfer_budget).c_str());
    ImGui::BeginDisabled(confirm||queued||existing||!valid);
    ImGui::SetNextItemWidth(260);ImGui::InputInt("Quanto você quer receber? (LB / RB)",&principal,100000,1000000);principal=std::clamp(principal,100000,100000000);
    ImGui::Text("Você recebe %s. Escolha abaixo como deseja pagar:",money(principal).c_str());
    float width=(ImGui::GetContentRegionAvail().x-24)/3;
    auto origin=ImGui::GetCursorScreenPos();float cell=std::max(120.f,std::min(155.f,(ImGui::GetContentRegionAvail().y-150)*.5f));
    for(int i=0;i<offer_count;++i){ImGui::SetCursorScreenPos({origin.x+(i%3)*(width+12),origin.y+(i/3)*(cell+10)});ImGui::PushID(i);
        auto at=ImGui::GetCursorScreenPos();if(ImGui::InvisibleButton("Escolher oferta",{width,cell}))plan=i;
#ifdef CAREER_OPS_SCREEN_TEST
        loan_centers[i]={at.x+width*.5f,at.y+cell*.5f};
#endif
        auto*d=ImGui::GetWindowDrawList();bool chosen=plan==i;
        d->AddRectFilled(at,{at.x+width,at.y+cell},chosen?IM_COL32(225,239,251,255):IM_COL32(251,253,255,255),7);
        d->AddRect(at,{at.x+width,at.y+cell},chosen?IM_COL32(0,93,163,255):IM_COL32(174,195,210,255),7,0,chosen?3.f:1.f);
        d->PushClipRect(at,{at.x+width,at.y+cell},true);
        d->AddText(nullptr,ImGui::GetFontSize()*1.08f,{at.x+12,at.y+10},IM_COL32(0,76,136,255),offers[i].name,nullptr,width-24);
        CareerLoanTerms t;CareerLoanSchedule s;if(offer_terms(i,t,s)){
            std::string monthly=std::to_string(s.count)+" x "+monthly_amount(s)+" / mês";
            std::string interest="Juros totais: "+money(s.total-t.principal)+" ("+std::to_string(offers[i].rate/100)+"%)";
            std::string total="Total a pagar: "+money(s.total);
            d->AddText({at.x+12,at.y+40},IM_COL32(18,52,76,255),monthly.c_str());d->AddText({at.x+12,at.y+65},IM_COL32(64,83,98,255),interest.c_str());
            d->AddText({at.x+12,at.y+88},IM_COL32(0,76,136,255),total.c_str());
        }else d->AddText({at.x+12,at.y+46},IM_COL32(90,106,117,255),"Salve a carreira para calcular.");
        if(cell>=145)d->AddText(nullptr,ImGui::GetFontSize()*.85f,{at.x+12,at.y+cell-33},IM_COL32(82,101,115,255),offers[i].description,nullptr,width-24);
        d->PopClipRect();ImGui::PopID();
    }ImGui::SetCursorScreenPos({origin.x,origin.y+2*(cell+10)});ImGui::EndDisabled();
    CareerLoanTerms t;CareerLoanSchedule s;bool schedule=terms(t,s);
    if(schedule)ImGui::Text("Primeira parcela: %s | Juros indicados são do contrato inteiro, não mensais.",date_text(t.first_due_date).c_str());
    if(existing){if(career_ops::read_ledger(ledger,contract,m)){CareerLoanSchedule active;if(career_loan_schedule(&contract.terms,&active)){
        uint64_t left=0;for(unsigned i=contract.paid;i<active.count;++i)left+=active.amounts[i];
        ImGui::Text("Contrato da carreira: %u/%u parcelas pagas | falta pagar %s",contract.paid,active.count,money(left).c_str());
    }}else ImGui::TextWrapped("Contrato pendente ou indisponível. %s",m.c_str());}
    ImGui::BeginDisabled(!valid||!schedule||queued||existing||confirm);if(ImGui::Button("Revisar e contratar (A / Enter)",{330,34}))confirm=true;ImGui::EndDisabled();
    ImGui::SameLine();if(ImGui::Button("Voltar (B/Esc)"))mod_screen_request_back();
    if(!feedback.empty())ImGui::TextWrapped("%s",feedback.c_str());else ImGui::TextWrapped("Depois de confirmar: SALVE A CARREIRA e FECHE O FIFA. O crédito entra ao reabrir. As cobranças seguem o mesmo processo; saldo insuficiente mantém parcelas pendentes.");
    ImGui::TextUnformatted("Setas / direcional: ofertas | LB/RB: valor | A/Enter: revisar/confirmar | B/Esc: cancelar/voltar");
    confirmation(true);ImGui::End();
}
}
extern "C" void career_operations_note_access(const char*path,const char*){if(!path)return;std::string value=path;if(value.rfind("\\\\?\\",0)==0)value.erase(0,4);
    if(!career_ops::save_path_valid(value.c_str()))return;{std::lock_guard<std::mutex>lock(guard);if(active_path!=value){snapshot_valid=false;active_path=value;}}
    if(refresh_event)SetEvent(refresh_event);}
extern "C" void career_operations_publish_context(int club,int date){bool changed;{std::lock_guard<std::mutex>lock(guard);changed=club!=live_club||date!=live_date;live_club=club;live_date=date;
    if(changed){roster_valid=false;published.clear();++revision;}}if(changed&&refresh_event)SetEvent(refresh_event);if(changed&&mod_screen_is_active("retirement"))InterlockedExchange(&roster_requested,1);}
extern "C" BOOL career_operations_get_transfer_context(CareerTransferUiContext*out){if(!out)return FALSE;*out={};std::lock_guard<std::mutex>lock(guard);
    out->club=live_club>0?(uint32_t)live_club:0;out->date=live_date>0?(uint32_t)live_date:0;
    bool snapshot_matches=snapshot_valid&&!active_path.empty()&&snapshot_path==active_path&&live_club>0&&live_date>0&&
        snapshot.club==(uint32_t)live_club&&snapshot.date<=(uint32_t)live_date;
    out->save_valid=snapshot_matches?1:0;if(snapshot_matches){out->transfer_budget=snapshot.transfer_budget;out->wage_budget=snapshot.wage_budget;out->currency=snapshot.currency;}
    out->window_ends_valid=snapshot_matches&&window_ends_valid?1:0;
    if(out->window_ends_valid){out->first_window_end_mmdd=window_end1;out->second_window_end_mmdd=window_end2;}
    return out->club&&out->date?TRUE:FALSE;}
extern "C" BOOL retirement_screen_take_refresh(){return InterlockedExchange(&roster_requested,0)!=0;}
extern "C" void retirement_screen_publish(const RetirementUiPlayer*rows,size_t count,int club,int date,int valid){std::lock_guard<std::mutex>lock(guard);
    published.clear();std::unordered_set<unsigned>seen;if(valid&&rows&&count<=60000)for(size_t i=0;i<count;++i)if(rows[i].retiring==1&&rows[i].id>0&&rows[i].id<524288&&seen.insert(rows[i].id).second){published.push_back(rows[i]);published.back().name[127]=0;published.back().club_name[127]=0;if(published.back().team_id<0||published.back().team_id>200000)published.back().team_id=0;}
    roster_club=club;roster_date=date;roster_valid=valid&&count<=60000&&(!count||rows);
    std::sort(published.begin(),published.end(),[](const RetirementUiPlayer&a,const RetirementUiPlayer&b){return utf8(a.name)<utf8(b.name);});++revision;}
extern "C" BOOL retirement_profile_take_request(unsigned*player,int*club,int*date){if(!player||!club||!date)return FALSE;std::lock_guard<std::mutex>lock(guard);
    if(!profile_requested)return FALSE;*player=profile_requested;*club=live_club;*date=live_date;profile_requested=0;return TRUE;}
extern "C" void retirement_profile_publish(const ClubPlayerRow*r,const char*team,int club,int date,int valid){std::lock_guard<std::mutex>lock(guard);
    if(!profile||club!=live_club||date!=live_date||!r||r->player_id!=(int)profile_id)return;
    profile_received=true;profile_valid=valid!=0;profile_row=valid?*r:ClubPlayerRow{};profile_row.name[127]=0;profile_team=team?team:"";++visual_serial;visual_ready.reset();if(visual_event)SetEvent(visual_event);}
bool career_operations_register(const char*game_root,void(*log)(const char*)){root=game_root?game_root:"";mod=root+"\\ModCarrerMode";logger=log;
    if(!visual_event){visual_event=CreateEventA(nullptr,FALSE,FALSE,nullptr);if(!visual_event)return false;
        HANDLE thread=CreateThread(nullptr,0,guarded_visual_worker,nullptr,0,nullptr);if(!thread)return false;CloseHandle(thread);}
    if(!refresh_event){refresh_event=CreateEventA(nullptr,FALSE,FALSE,nullptr);if(!refresh_event)return false;
        HANDLE thread=CreateThread(nullptr,0,guarded_refresh_worker,nullptr,0,nullptr);if(!thread){CloseHandle(refresh_event);refresh_event=nullptr;return false;}CloseHandle(thread);}
    const ModOverlayScreen retirement={"retirement",FIFA_RETIREMENT_ACTION,open,draw_retirement,closed,nullptr,back};
    const ModOverlayScreen loans={"loans",FIFA_LOANS_ACTION,loan_open,draw_loans,closed,nullptr,back};
    return mod_screen_register(&retirement)&&mod_screen_register(&loans)&&transfer_center_screen_register(game_root);
}
#ifdef CAREER_OPS_SCREEN_TEST
CareerOpsScreenTestView career_operations_test_view(){std::lock_guard<std::mutex>lock(guard);return {scope,row,age,selected.size(),keyboard,confirm,queued,snapshot_valid,filtered.size(),face_views.size(),profile,profile_valid,plan,visual_shown&&visual_shown->model!=nullptr,profile_yaw,profile_zoom,profile_state.view_tab,profile_state.page,profile_state.scroll_y,profile_state.competition_scroll_y};}
bool career_operations_test_profile_tab_center(int i,float&x,float&y){if(!profile||i<0||i>2)return false;x=profile_state.tab_centers[i].x;y=profile_state.tab_centers[i].y;return x>0&&y>0;}
size_t career_operations_test_ids(unsigned*out,size_t capacity){auto ids=target_ids();if(out)std::copy_n(ids.begin(),std::min(capacity,ids.size()),out);return ids.size();}
bool career_operations_test_row_center(int i,float&x,float&y,bool details){auto&centers=details?detail_centers:row_centers;auto at=centers.find(i);if(at==centers.end())return false;x=at->second.x;y=at->second.y;return true;}
bool career_operations_test_loan_center(int i,float&x,float&y){if(i<0||i>=6)return false;x=loan_centers[i].x;y=loan_centers[i].y;return x>0&&y>0;}
bool career_operations_test_set_search(const char*s){if(!s||strlen(s)>=sizeof(search))return false;strcpy_s(search,s);row=0;scroll_row=true;return true;}
#endif
void career_operations_device(ID3D11Device*d){transfer_center_screen_device(d);if(device==d)return;clear_visuals();device=d;profile_renderer.device(d);}
