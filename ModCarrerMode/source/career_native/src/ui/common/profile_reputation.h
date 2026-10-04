#pragma once
#include <algorithm>
#include <cmath>
namespace profile_reputation {
// Presentation only. League strength outweighs short-term form or overall.
inline double league(int level,double international){
    if(level<1||level>7||!std::isfinite(international)||international<0||international>20)return -1;
    return 100*(.60*(1-.70*(level-1)/6.)+.40*international/20.);
}
inline int stars(double score){return score<0||!std::isfinite(score)?-1:(int)std::floor(std::clamp(score,0.,5.)+.5);}
inline double player(double strength,int overall){
    if(!std::isfinite(strength)||strength<0||strength>100||overall<0||overall>99)return -1;
    return 5*(.70*strength/100.+.30*std::clamp((overall-40)/59.,0.,1.));
}
}
