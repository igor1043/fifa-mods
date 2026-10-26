#pragma once
#include <stddef.h>
/* Owned, resolved career snapshot. A player==0 row seeds a club competition;
 * it is NOT evidence of that player's participation or a clean sheet. */
typedef struct PlayerCompetitionInput {
    int player,club,root,phase,asset,games,goals,assists,clean_sheets,rating_sum;
    unsigned valid;
} PlayerCompetitionInput;
typedef struct PlayerCompetitionRow {
    int root,asset,games,goals,assists,clean_sheets,rating_sum;
    unsigned valid;
} PlayerCompetitionRow;
#ifdef __cplusplus
extern "C" {
#endif
void player_profile_publish_competitions(const PlayerCompetitionInput*,size_t,int career_club,int career_date,unsigned long generation);
#ifdef __cplusplus
}
#include <vector>
#include <algorithm>
#include <cstdint>
namespace player_competitions {
struct Stats {std::vector<PlayerCompetitionRow>rows;bool available=false;};
inline bool valid(const PlayerCompetitionInput&r){return r.root>0&&r.club>0&&r.phase>0&&r.games>=0&&r.goals>=0&&r.assists>=0;}
inline Stats aggregate(const std::vector<PlayerCompetitionInput>&source,int player,int club){
    Stats out;out.available=true;if(player<=0||club<=0)return out;
    std::vector<PlayerCompetitionInput>raw;
    for(auto&r:source)if(r.club==club&&valid(r)){
        auto i=std::find_if(out.rows.begin(),out.rows.end(),[&](auto&v){return v.root==r.root;});
        if(i==out.rows.end())out.rows.push_back({r.root,r.asset,0,0,0,0,0,1});
        if(r.player==player)raw.push_back(r);
    }
    std::sort(raw.begin(),raw.end(),[](auto&a,auto&b){return a.root!=b.root?a.root<b.root:a.phase<b.phase;});
    for(size_t i=0;i<raw.size();){size_t end=i;int root=raw[i].root;PlayerCompetitionRow sum={root,raw[i].asset,0,0,0,0,0,3},total={};bool has_root=false,conflict=false;
        while(end<raw.size()&&raw[end].root==root){auto r=raw[end++];
            while(end<raw.size()&&raw[end].root==root&&raw[end].phase==r.phase){auto&d=raw[end++];
                if(d.games!=r.games||d.goals!=r.goals||d.assists!=r.assists||d.valid!=r.valid||((r.valid&1)&&d.clean_sheets!=r.clean_sheets)||((r.valid&2)&&d.rating_sum!=r.rating_sum))conflict=true;}
            if(r.phase==root){total={root,r.asset,r.games,r.goals,r.assists,r.clean_sheets,r.rating_sum,r.valid};has_root=true;}
            else {auto add=[&](int&a,int b){if(b<0||(int64_t)a+b>INT32_MAX)conflict=true;else a+=b;};
                add(sum.games,r.games);add(sum.goals,r.goals);add(sum.assists,r.assists);add(sum.clean_sheets,r.clean_sheets);add(sum.rating_sum,r.rating_sum);
                sum.valid&=r.valid|(r.games==0?2:0);}
        }
        if(conflict){out.available=false;out.rows.clear();return out;}
        auto at=std::find_if(out.rows.begin(),out.rows.end(),[&](auto&r){return r.root==root;});*at=has_root?total:sum;
        i=end;
    }
    std::sort(out.rows.begin(),out.rows.end(),[](auto&a,auto&b){return a.root<b.root;});return out;
}
inline PlayerCompetitionRow total(const Stats&s){PlayerCompetitionRow out={};out.valid=3;bool overflow=false;
    auto add=[&](int&a,int b){if(b<0||(int64_t)a+b>INT32_MAX)overflow=true;else a+=b;};
    for(auto&r:s.rows){add(out.games,r.games);add(out.goals,r.goals);add(out.assists,r.assists);add(out.clean_sheets,r.clean_sheets);add(out.rating_sum,r.rating_sum);out.valid&=r.valid|(r.games==0?2:0);}
    if(overflow){out={};out.games=out.goals=out.assists=out.clean_sheets=-1;return out;}
    if(!s.available||s.rows.empty())out.valid=0;return out;
}
inline double average(const PlayerCompetitionRow&r){return (r.valid&2)&&r.games>0&&r.rating_sum>0?(double)r.rating_sum/(10.0*r.games):-1;}
}
#endif
