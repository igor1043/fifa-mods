#pragma once
#include "../club/club_player_screen.h"
#include <cstdio>
#include <string>

/* Pure read-only presentation helpers shared by the UI and offline tests.
 * FIFA preferred positions and tactical lineup slots must not be confused. */
namespace club_profile {
inline bool valid_date(int ymd){
    int y=ymd/10000,m=ymd/100%100,d=ymd%100;static const int days[]={31,28,31,30,31,30,31,31,30,31,30,31};
    return y>=1900&&y<=2500&&m>=1&&m<=12&&d>=1&&d<=days[m-1]+(m==2&&y%4==0&&(y%100!=0||y%400==0));
}
inline long long civil_days(int y,unsigned m,unsigned d){
    y-=m<=2;int era=(y>=0?y:y-399)/400;unsigned yo=y-era*400,dy=(153*(m+(m>2?-3:9))+2)/5+d-1;
    return (long long)era*146097+yo*365+yo/4-yo/100+dy-719468;
}
/* The same Gregorian epoch as native_cards/retirement_engine. Age is relative
 * to the save's current date, never the PC clock or the next fixture date. */
inline int age_at(int raw,int today){
    if(raw<0||raw>1048575||!valid_date(today))return -1;
    long long z=civil_days(1582,10,14)+raw+719468,era=(z>=0?z:z-146096)/146097;
    unsigned de=(unsigned)(z-era*146097),ye=(de-de/1460+de/36524-de/146096)/365;
    int y=(int)ye+(int)era*400;unsigned dy=de-(365*ye+ye/4-ye/100),mp=(5*dy+2)/153;
    unsigned d=dy-(153*mp+2)/5+1,m=mp+(mp<10?3:-9);y+=m<=2;
    int age=today/10000-y;if(today/100%100<(int)m||(today/100%100==(int)m&&today%100<(int)d))--age;
    return age>=0&&age<=100?age:-1;
}
inline bool raw_date_ymd(int raw,int&year,unsigned&month,unsigned&day){
    if(raw<0||raw>1048575)return false;
    long long z=civil_days(1582,10,14)+raw+719468,era=(z>=0?z:z-146096)/146097;
    unsigned de=(unsigned)(z-era*146097),ye=(de-de/1460+de/36524-de/146096)/365;
    year=(int)ye+(int)era*400;unsigned doy=de-(365*ye+ye/4-ye/100),mp=(5*doy+2)/153;
    day=doy-(153*mp+2)/5+1;month=mp+(mp<10?3:-9);year+=month<=2;
    return year>=1900&&year<=2500&&month>=1&&month<=12&&day>=1&&day<=31;
}
inline std::string raw_date_label(int raw){
    int year=0;unsigned month=0,day=0;if(!raw_date_ymd(raw,year,month,day))return "—";
    char text[32];sprintf_s(text,"%02u/%02u/%04d",day,month,year);return text;
}
inline std::string club_tenure_label(int joined,int today){
    int y=0;unsigned m=0,d=0;if(!raw_date_ymd(joined,y,m,d)||!valid_date(today))return "—";
    int ty=today/10000,tm=today/100%100,td=today%100;
    int months=(ty-y)*12+(tm-(int)m);if(td<(int)d)--months;if(months<0)return "—";
    if(months==0)return "Menos de 1 mês";
    int years=months/12,remaining=months%12;char text[96];
    if(years&&remaining)sprintf_s(text,"%d a %d m",years,remaining);
    else if(years)sprintf_s(text,"%d %s",years,years==1?"ano":"anos");
    else sprintf_s(text,"%d %s",remaining,remaining==1?"mês":"meses");
    return text;
}
struct PitchPoint {float x,y;};
inline unsigned theme_color(const ClubPlayerRow&r) {
    if(!r.club_colors_valid)return 0x055ca3;
    auto chroma=[](unsigned rgb){unsigned a=(rgb>>16)&255,b=(rgb>>8)&255,c=rgb&255;
        unsigned hi=a>b?a:b,lo=a<b?a:b;return (hi>c?hi:c)-(lo<c?lo:c);};
    unsigned result=r.club_colors[0],best=chroma(result);
    /* White/black primary kits may have a real coloured secondary identity. */
    if(best<32)for(unsigned rgb:r.club_colors)if(chroma(rgb)>best){result=rgb;best=chroma(rgb);}
    return result;
}
inline bool valid_position(int p){return p>=0&&p<28;}
inline const char*position(int p){
    static const char*names[]={"GOL","LIB","ALA D","LD","ZAG D","ZAG","ZAG E","LE","ALA E",
        "VOL D","VOL","VOL E","MD","MC D","MC","MC E","ME","MEI D","MEI","MEI E",
        "SA D","SA","SA E","PD","ATA D","ATA","ATA E","PE"};
    return valid_position(p)?names[p]:"—";
}
inline PitchPoint pitch_point(int p) {
    static const PitchPoint points[28]={
        {.5f,.91f},{.5f,.79f},{.90f,.66f},{.84f,.75f},{.67f,.75f},{.5f,.75f},{.33f,.75f},{.16f,.75f},{.10f,.66f},
        {.67f,.61f},{.5f,.61f},{.33f,.61f},{.86f,.48f},{.67f,.48f},{.5f,.48f},{.33f,.48f},{.14f,.48f},
        {.67f,.34f},{.5f,.34f},{.33f,.34f},{.67f,.23f},{.5f,.23f},{.33f,.23f},
        {.86f,.15f},{.67f,.10f},{.5f,.10f},{.33f,.10f},{.14f,.15f}};
    return valid_position(p)?points[p]:PitchPoint{.5f,.5f};
}
inline int positions(const ClubPlayerRow&r,int (&out)[4]) {
    int count=0;
    if(valid_position(r.position))out[count++]=r.position;
    if(r.secondary_positions_valid==1)for(int p:r.secondary_positions) {
        if(!valid_position(p))continue;
        bool duplicate=false;for(int i=0;i<count;++i)if(out[i]==p)duplicate=true;
        if(!duplicate)out[count++]=p;
    }
    return count;
}
inline int summary(const ClubPlayerRow&r,int category) {
    if(category<0||category>=6)return -1;
    if(r.position==0) {
        const int keeper[6]={28,29,30,31,32,3};
        int value=r.attributes[keeper[category]];return value>=0&&value<=99?value:-1;
    }
    static const int groups[6][6]={{0,1,-1,-1,-1,-1},{6,5,7,8,9,23},{10,11,12,13,14,15},
        {2,4,16,17,3,-1},{22,24,25,26,27,-1},{18,19,20,21,-1,-1}};
    int sum=0,count=0;
    for(int i:groups[category])if(i>=0) {
        int value=r.attributes[i];if(value<0||value>99)return -1;
        sum+=value;++count;
    }
    return count?(sum+count/2)/count:-1;
}
}
