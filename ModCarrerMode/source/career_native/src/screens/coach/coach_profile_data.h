#pragma once
#include "coach_profile_screen.h"
#include <vector>
#include <unordered_map>
#include <algorithm>
#include <cstring>
#include <string>
#include <cmath>
#include "../../ui/common/profile_reputation.h"
namespace coach_profile {
inline double reputation_score(const CoachProfileContext&c){
    if(!c.league_strength_valid||!std::isfinite(c.league_strength)||c.league_strength<0||c.league_strength>100)return -1;
    double league=c.league_strength/100.,form=league,native=league;
    if(c.recent_valid&&c.recent_games>0&&c.recent_games<=5&&c.recent_points>=0&&c.recent_points<=c.recent_games*3)
        form=c.recent_points/(c.recent_games*3.);
    if(c.reputation>=0&&c.reputation<=1501)native=c.reputation/1501.;
    return std::clamp(5*(.70*league+.20*form+.10*native),0.,5.);
}
inline int reputation_stars(const CoachProfileContext&c){return profile_reputation::stars(reputation_score(c));}
inline void recent_form(CoachProfileContext&c,const FceFixture*f,size_t count,int today){
    c.recent_valid=c.recent_games=c.recent_points=0;
    if(!f||count>65536||c.club<=0||today<20080101||today>20601231)return;
    std::unordered_map<int,FceFixture>seen;
    for(size_t i=0;i<count;++i){const auto&m=f[i];if((m.home!=c.club&&m.away!=c.club)||!m.played_raw||m.date_raw>today)continue;
        if(m.id<=0||m.home==m.away||m.date_raw<20080101||m.home_score<0||m.home_score>255||m.away_score<0||m.away_score>255)return;
        auto old=seen.find(m.id);if(old!=seen.end()){if(memcmp(&old->second,&m,sizeof(m)))return;}else seen.emplace(m.id,m);}
    std::vector<FceFixture>games;for(const auto&m:seen)games.push_back(m.second);
    std::sort(games.begin(),games.end(),[](const auto&a,const auto&b){return a.date_raw>b.date_raw||(a.date_raw==b.date_raw&&a.id>b.id);});
    for(size_t i=0;i<std::min<size_t>(5,games.size());++i){const auto&m=games[i];int gf=m.home==c.club?m.home_score:m.away_score,ga=m.home==c.club?m.away_score:m.home_score;
        ++c.recent_games;c.recent_points+=gf>ga?3:gf==ga?1:0;}
    c.recent_valid=c.recent_games>0;
}
inline bool valid(const CoachMatchStats&s){return s.games>=0&&s.games<=100000&&s.wins>=0&&s.wins<=100000&&s.draws>=0&&s.draws<=100000&&s.losses>=0&&s.losses<=100000&&
    s.wins+s.draws+s.losses==s.games&&s.goals_for>=0&&s.goals_for<=1000000&&s.goals_against>=0&&s.goals_against<=1000000;}
inline void add(CoachMatchStats&a,const CoachMatchStats&b){a.games+=b.games;a.wins+=b.wins;a.draws+=b.draws;a.losses+=b.losses;a.goals_for+=b.goals_for;a.goals_against+=b.goals_against;}
inline bool same(const CoachMatchStats&a,const CoachMatchStats&b){return a.games==b.games&&a.wins==b.wins&&a.draws==b.draws&&a.losses==b.losses&&a.goals_for==b.goals_for&&a.goals_against==b.goals_against;}
inline double efficiency(const CoachMatchStats&s){return s.games>0?(s.wins*3.+s.draws)*100/(s.games*3.):-1;}
inline double win_rate(const CoachMatchStats&s){return s.games>0?s.wins*100./s.games:-1;}
inline bool row_valid(const CoachCareerRow&r){
    if(r.key<0||r.team<=0||r.team>200000||r.team_kind<0||r.team_kind>1||r.season<0||r.season>200||r.league<0||r.league>65535||r.season_valid<0||r.season_valid>1||!valid(r.total))return false;
    if(r.league_titles<0||r.league_titles>1000||r.domestic_titles<0||r.domestic_titles>1000||r.continental_titles<0||r.continental_titles>1000)return false;
    if(r.splits_valid){auto combined=r.home;if(!valid(r.home)||!valid(r.away))return false;add(combined,r.away);if(!same(combined,r.total))return false;}
    return true;
}
inline bool copy(const CoachProfileContext*c,const CoachCareerRow*rows,size_t n,CoachProfileContext&out,std::vector<CoachCareerRow>&data){
    if(!c||!c->valid||c->kind<1||c->kind>3||c->id<0||c->id>200000||c->club<0||c->club>200000||c->national_team<0||c->national_team>200000||
        n>COACH_PROFILE_CAPACITY||(n&&!rows)||(!c->history_valid&&n)||c->stats_scope<COACH_STATS_NONE||c->stats_scope>COACH_STATS_CURRENT_CLUB||
        (n&&c->stats_scope==COACH_STATS_NONE))return false;
    if((c->kind==COACH_CAREER_USER&&c->id>63)||(c->kind==COACH_CLUB_MANAGER&&(c->id<=0||c->club!=c->id))||
        (c->kind==COACH_NATIONAL_MANAGER&&(c->id<=0||c->national_team!=c->id)))return false;
    out=*c;out.name[127]=out.club_name[127]=out.national_name[127]=0;
    if(!std::isfinite(out.league_strength)||out.league_strength<0||out.league_strength>100)out.league_strength_valid=0;
    if(out.recent_games<1||out.recent_games>5||out.recent_points<0||out.recent_points>out.recent_games*3)out.recent_valid=0;
    data.clear();for(size_t i=0;i<n;++i){auto r=rows[i];r.team_name[127]=0;if(!row_valid(r))return false;
        auto found=std::find_if(data.begin(),data.end(),[&](const auto&old){return old.key==r.key;});
        if(found!=data.end()){if(memcmp(&*found,&r,sizeof(r)))return false;continue;}data.push_back(r);}
    std::sort(data.begin(),data.end(),[](const auto&a,const auto&b){return a.season<b.season||(a.season==b.season&&a.key<b.key);});return true;
}
struct Passage {int team,kind,first,last,league,titles=0;std::string name;CoachMatchStats total={},home={},away={};bool splits=true,season_valid=true;};
inline std::vector<Passage> passages(const std::vector<CoachCareerRow>&rows,int kind=-1){
    std::vector<Passage>out;for(const auto&r:rows){if(kind>=0&&r.team_kind!=kind)continue;
        /* Keep separate spells when a coach returns after another assignment;
         * do not silently merge two non-consecutive spells into one. */
        auto found=out.end();if(!out.empty()&&out.back().team==r.team&&out.back().kind==r.team_kind&&r.season<=out.back().last+1)found=out.end()-1;
        if(found==out.end()){out.push_back({r.team,r.team_kind,r.season,r.season,r.league,0,r.team_name});found=out.end()-1;found->season_valid=r.season_valid!=0;}
        else found->season_valid=found->season_valid&&r.season_valid;
        found->last=std::max(found->last,r.season);add(found->total,r.total);found->titles+=r.league_titles+r.domestic_titles+r.continental_titles;
        found->splits=found->splits&&r.splits_valid;if(r.splits_valid){add(found->home,r.home);add(found->away,r.away);}}
    return out;
}
inline bool fixtures(const FceFixture*f,size_t n,int club,int today,CoachMatchStats&home,CoachMatchStats&away){
    home={};away={};if(!f||n>65536||club<=0||today<20080101||today>20601231)return false;
    std::unordered_map<int,FceFixture>seen;
    for(size_t i=0;i<n;++i){auto&m=f[i];if((m.home!=club&&m.away!=club)||!m.played_raw||m.date_raw>today)continue;
        if(m.id<=0||m.home==m.away||m.date_raw<20080101||m.home_score<0||m.home_score>255||m.away_score<0||m.away_score>255)return false;
        auto at=seen.find(m.id);if(at!=seen.end()){if(memcmp(&at->second,&m,sizeof(m)))return false;continue;}seen[m.id]=m;
        bool is_home=m.home==club;auto&s=is_home?home:away;int gf=is_home?m.home_score:m.away_score,ga=is_home?m.away_score:m.home_score;
        ++s.games;s.goals_for+=gf;s.goals_against+=ga;if(gf>ga)++s.wins;else if(gf==ga)++s.draws;else ++s.losses;
    }return true;
}
inline bool current_club_row(const FceFixture*f,size_t n,int club,int today,const char*name,CoachCareerRow&row){
    CoachMatchStats home={},away={};if(!fixtures(f,n,club,today,home,away))return false;
    row={};row.key=0;row.team=club;row.team_kind=COACH_TEAM_CLUB;row.season=0;row.league=0;
    if(name)strncpy_s(row.team_name,name,_TRUNCATE);row.home=home;row.away=away;row.total=home;add(row.total,away);row.splits_valid=1;row.season_valid=0;
    return row_valid(row);
}
inline void bind_splits(CoachCareerRow*rows,size_t n,const FceFixture*f,size_t count,int today,int club,int season){
    if(!rows||n>COACH_PROFILE_CAPACITY)return;CoachMatchStats home={},away={};
    if(!fixtures(f,count,club,today,home,away))return;auto total=home;add(total,away);if(!total.games)return;
    size_t match=n;for(size_t i=0;i<n;++i)if(rows[i].team==club&&rows[i].season==season&&same(rows[i].total,total)){
        if(match!=n)return;match=i;}
    if(match<n){rows[match].home=home;rows[match].away=away;rows[match].splits_valid=1;}
}
}
