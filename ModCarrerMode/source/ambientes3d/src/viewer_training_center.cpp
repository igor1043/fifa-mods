#include "viewer_training_center.h"
#include "viewer_room_geometry.h"
#include <algorithm>
#include <cmath>
#include <map>
#include <sstream>

namespace studio {
using namespace fifa_player;
using namespace room_geometry;
namespace {
const Vec3 steel={.24f,.28f,.31f},rubber={.055f,.07f,.075f};
Texture floor_texture(bool grass){
    Texture t;t.width=t.height=512;t.format=3;t.bytes.resize(512*512*4);
    for(unsigned y=0;y<512;++y)for(unsigned x=0;x<512;++x){unsigned h=x*1973+y*9277+89173;h=(h^(h>>13))*1274126177;float noise=(h&255)/255.f-.5f;
        float grain=.017f*sinf(y*.37f+1.7f*sinf(x*.018f))+.006f*sinf(y*1.13f+x*.004f);Vec3 c=grass?Vec3{.19f+noise*.025f,.48f+noise*.045f,.20f+noise*.022f}:Vec3{.68f+grain,.54f+grain*.8f,.38f+grain*.5f};
        if(!grass){c=add(c,{noise*.016f,noise*.012f,noise*.008f});if(y%128==0)c=mul(c,.74f);}
        for(int k=0;k<3;++k)t.bytes[(y*512+x)*4+k]=uint8_t(std::clamp((&c.x)[k],0.f,1.f)*255);t.bytes[(y*512+x)*4+3]=255;
    }return t;
}
void horizontal(Builder&b,const std::string&name,Vec3 center,float width,float depth,Vec3 color,int texture=-1,float u=1,float v=1){
    b.face(name,add(center,{-width/2,0,-depth/2}),add(center,{width/2,0,-depth/2}),add(center,{width/2,0,depth/2}),add(center,{-width/2,0,depth/2}),{0,1,0},color,texture,false,u,v);
}
void sign(Builder&b,const std::string&name,Vec3 p,const wchar_t*text,float width,Vec3 accent){b.rounded_box(name,p,{width,28,3},1,accent);b.panel(name,add(p,{0,0,2}),width-6,20,b.texture(text_label(text,accent,white,80)));}
void rail(Builder&b,const std::string&name,Vec3 a,Vec3 B){auto d=sub(B,a);float length=sqrtf(d.x*d.x+d.y*d.y+d.z*d.z);int n=std::max(1,int(length/110));for(int i=0;i<=n;++i){auto p=add(a,mul(d,float(i)/n));b.tube(name,p,add(p,{0,108,0}),2.3f,steel,12);}for(float y:{42.f,74.f,108.f})b.tube(name,add(a,{0,y,0}),add(B,{0,y,0}),2,steel,12);}
void wheel(Builder&b,const std::string&name,Vec3 p){b.tube(name,add(p,{-2,0,0}),add(p,{2,0,0}),6,rubber,16);b.tube(name,add(p,{0,6,0}),add(p,{0,13,0}),1.5f,steel,12);}
void pad(Builder&b,const std::string&name,Vec3 p,Vec3 size,Vec3 color){b.rounded_box(name,add(p,{0,-4,0}),add(size,{3,4,3}),2,steel);b.rounded_box(name,p,size,3.5f,color);}
void sphere(Builder&b,const std::string&name,Vec3 p,float radius,Vec3 color){for(int y=0;y<12;++y)for(int x=0;x<24;++x){float a=x*2*pi/24,A=(x+1)*2*pi/24,t=-pi/2+y*pi/12,T=-pi/2+(y+1)*pi/12;auto q=[&](float u,float v){return Vec3{radius*cosf(v)*cosf(u),radius*sinf(v),radius*cosf(v)*sinf(u)};};b.face(name,add(p,q(a,t)),add(p,q(A,t)),add(p,q(A,T)),add(p,q(a,T)),normalized(q((a+A)/2,(t+T)/2)),color);}}
void plate(Builder&b,const std::string&name,Vec3 p,float radius,Vec3 c){b.tube(name,add(p,{-2,0,0}),add(p,{2,0,0}),radius,c,20);b.tube(name,add(p,{2.1f,0,0}),add(p,{2.8f,0,0}),radius*.32f,steel,16);}
void barbell(Builder&b,const std::string&name,Vec3 p,float length=185){b.tube(name,add(p,{-length/2,0,0}),add(p,{length/2,0,0}),1.6f,metal,16);for(float s:{-1.f,1.f}){plate(b,name,add(p,{s*(length/2-17),0,0}),20,rubber);plate(b,name,add(p,{s*(length/2-23),0,0}),17,rubber);}}
void rack(Builder&b,Vec3 p,Vec3 accent,int index){
    b.frame(p);std::string n="Academia / rack de força "+std::to_string(index);
    for(float x:{-69.f,69.f})for(float z:{-47.f,47.f}){b.rounded_box(n,{x,128,z},{7,250,7},1.2f,steel);b.box(n,{x,4,z},{28,5,32},rubber);for(float y=45;y<230;y+=12)b.box(n,{x, y,z+4},{1.5f,1.5f,.25f},metal);}
    for(float z:{-47.f,47.f})b.tube(n,{-69,250,z},{69,250,z},3,metal,12);for(float x:{-69.f,69.f})b.tube(n,{x,248,-47},{x,248,47},3,metal,12);
    for(float x:{-60.f,60.f}){b.box(n,{x,119,12},{20,5,23},accent);b.tube(n,{x,120,15},{x,126,15},2,metal,12);}
    barbell(b,n,{0,129,17});pad(b,n,{0,49,0},{34,10,95},accent);for(float z:{-34.f,34.f})b.tube(n,{0,6,z},{0,42,z},3,steel,12);b.tube(n,{-36,7,-34},{36,7,-34},3,steel,12);b.tube(n,{-36,7,34},{36,7,34},3,steel,12);
    b.crest(n,{0,218,-43},20);b.frame();
}
void cable_machine(Builder&b,Vec3 p,Vec3 accent,int index){
    b.frame(p);std::string n="Academia / estação de cabos "+std::to_string(index);
    for(float x:{-72.f,72.f}){b.rounded_box(n,{x,118,0},{26,230,48},3,steel);for(int i=0;i<14;++i)b.rounded_box(n,{x,26.f+i*4,5},{22,3.4f,29},1,rubber);b.tube(n,{x,19,24},{x,223,24},1.1f,metal,12);b.tube(n,{x,224,24},{x,110,75},.4f,rubber,8);b.tube(n,{x-9,110,75},{x+9,110,75},1.5f,metal,12);}
    b.rounded_box(n,{0,224,0},{164,12,48},3,steel);pad(b,n,{0,60,26},{48,10,46},accent);pad(b,n,{0,113,-4},{48,82,12},accent);b.box(n,{0,30,0},{7,51,70},steel);b.tube(n,{-62,5,-8},{62,5,-8},3,steel,12);b.frame();
}
void treadmill(Builder&b,Vec3 p,Vec3 accent,int index){
    b.frame(p);std::string n="Academia / esteira "+std::to_string(index);b.rounded_box(n,{0,16,0},{82,22,184},7,steel);b.rounded_box(n,{0,28,9},{63,2,152},.8f,rubber);
    for(int i=0;i<16;++i)b.box(n,{0,29,-60.f+i*9},{58,.3f,.4f},{.14f,.17f,.18f});for(float x:{-35.f,35.f}){b.tube(n,{x,18,-64},{x,112,-64},3,steel,12);b.tube(n,{x,109,-64},{x,100,-7},2.5f,steel,12);}
    b.rounded_box(n,{0,116,-65},{76,20,14},3,steel);b.panel(n,{0,116,-57},26,12,b.texture(text_label(L"08:30  12.0",{.08f,.15f,.18f},{.45f,.86f,.78f})));b.box(n,{0,111,-55},{6,3,2},accent);b.frame();
}
void bike(Builder&b,Vec3 p,Vec3 accent,int index){
    b.frame(p);std::string n="Academia / bicicleta "+std::to_string(index);b.tube(n,{-5,29,28},{5,29,28},24,rubber,28);b.tube(n,{0,30,28},{0,79,-24},4,steel,12);b.tube(n,{0,35,28},{0,62,50},4,steel,12);b.tube(n,{0,42,37},{0,82,44},2.5f,metal,12);pad(b,n,{0,85,44},{28,6,18},accent);
    for(float z:{-27.f,58.f})b.tube(n,{-29,7,z},{29,7,z},3,steel,12);b.tube(n,{0,77,-24},{0,98,-33},2,metal,12);b.tube(n,{-24,99,-33},{24,99,-33},2.2f,rubber,12);b.rounded_box(n,{0,102,-34},{20,14,3},1.2f,steel);b.tube(n,{-19,34,28},{19,34,28},1.5f,metal,12);for(float x:{-20.f,20.f})b.rounded_box(n,{x,32,28},{9,4,15},1,rubber);b.frame();
}
void dumbbells(Builder&b,Vec3 p,Vec3 accent){
    b.frame(p);const std::string n="Academia / halteres";for(float x:{-162.f,162.f})b.rounded_box(n,{x,50,0},{6,95,76},2,steel);
    for(float y:{34.f,72.f}){b.rounded_box(n,{0,y,0},{340,4,72},1.5f,steel);for(int i=0;i<11;++i)for(float z:{-20.f,20.f}){Vec3 q={-144.f+i*29,y+9,z};b.tube(n,add(q,{-9,0,0}),add(q,{9,0,0}),1.8f,metal,12);plate(b,n,add(q,{-10,0,0}),6+(i%3),rubber);plate(b,n,add(q,{10,0,0}),6+(i%3),rubber);}}
    b.panel(n,{0,90,38},105,10,b.texture(text_label(L"PESOS LIVRES",accent,white)));b.frame();
}
void gym(Builder&b,Vec3 accent,int wood){
    const std::string n="Academia / ";b.frame();b.box(n+"piso",{0,-9,-900},{2740,18,1840},steel);horizontal(b,n+"piso de madeira",{0,.05f,-900},2700,1800,white,wood,6,4);
    b.box(n+"parede de fundo",{0,360,-1810},{2740,720,20},white);for(float x:{-1360.f,1360.f})b.box(n+"paredes laterais",{x,360,-900},{20,720,1840},white);
    b.box(n+"teto",{0,729,-900},{2740,18,1840},white);for(float z=-1700;z<0;z+=400)b.box(n+"vigas",{0,695,z},{2720,25,12},steel);
    b.box(n+"mural",{600,350,-1796},{1000,650,3},accent);b.crest(n+"escudo mural",{600,377,-1792},420);
    sign(b,n+"força",{-680,277,-1793},L"FORÇA E PREPARAÇÃO",540,accent);
    // Upper gallery leaves the central training floor open to both storeys.
    b.box(n+"mezanino",{0,349,-1450},{2700,22,700},{.72f,.74f,.75f});horizontal(b,n+"mezanino piso",{0,360.1f,-1450},2700,700,white,wood,6,2);
    b.box(n+"galeria lateral",{1140,349,-550},{420,22,1100},{.72f,.74f,.75f});horizontal(b,n+"galeria piso",{1140,360.1f,-550},420,1100,white,wood,2,3);
    rail(b,n+"guarda-corpo",{-970,361,-1100},{920,361,-1100});rail(b,n+"guarda-corpo",{930,361,-1090},{930,361,-10});
    for(float x:{-910.f,0.f,910.f})b.box(n+"pilares",{x,175,-1120},{18,350,18},steel);
    for(int i=0;i<20;++i){float h=(i+1)*18,z=-870.f-i*40;b.box(n+"escada",{-1170,h/2,z},{210,h,41},{.71f,.72f,.73f});b.box(n+"escada antiderrapante",{-1170,h+.3f,z},{204,.6f,36},rubber);}
    rail(b,n+"corrimão escada",{-1277,18,-850},{-1277,360,-1650});rail(b,n+"corrimão escada",{-1063,18,-850},{-1063,360,-1650});
    // A transparent curtain wall, not a photograph of an outdoor scene.
    Texture glass;glass.width=glass.height=1;glass.format=3;glass.bytes={142,197,211,18};int pane=b.texture(std::move(glass));
    for(int i=0;i<6;++i){float x=-1125.f+i*450;b.face(n+"vidraça",{x-221,692,-5},{x+221,692,-5},{x+221,10,-5},{x-221,10,-5},{0,0,-1},white,pane,true);}
    for(float x=-1350;x<=1350;x+=450)b.box(n+"caixilhos",{x,350,-5},{8,700,12},steel);for(float y:{10.f,350.f,695.f})b.box(n+"caixilhos",{0,y,-5},{2700,8,12},steel);
    for(int i=0;i<4;++i)rack(b,{-770.f+i*495,0,-1470},accent,i+1);
    for(int i=0;i<3;++i)cable_machine(b,{1160,0,-870.f+i*270},accent,i+1);
    dumbbells(b,{-620,0,-920},accent);dumbbells(b,{90,0,-920},accent);
    for(int i=0;i<6;++i){float x=-790.f+(i%3)*235,z=-500.f+(i/3)*250;horizontal(b,n+"tapete de mobilidade "+std::to_string(i+1),{x,.8f,z},170,210,rubber);b.tube(n+"rolos de mobilidade",{x-53,11,z+65},{x-16,11,z+65},10,{.17f,.20f,.21f},20);}
    for(int i=0;i<4;++i)treadmill(b,{-800.f+i*370,361,-1490},accent,i+1);
    for(int i=0;i<4;++i)bike(b,{130.f+i*205,361,-1260},accent,i+1);
    b.frame();sign(b,n+"cardio",{0,634,-1793},L"CARDIO  /  CONDICIONAMENTO",580,accent);
    for(float x:{-800.f,0.f,800.f})for(float z:{-1450.f,-650.f}){b.box(n+"luminárias",{x,700,z},{145,8,65},steel);b.box(n+"luminárias",{x,694,z},{139,1,59},{1.23f,1.23f,1.18f});}
    for(int i=0;i<3;++i){float x=-620.f+i*550;b.box(n+"luminárias térreo",{x,330,-1460},{120,3,40},{1.22f,1.21f,1.17f});}
    // Balls, kettlebells, gym accessories and a hydration counter.
    b.box(n+"bola medicine rack",{620,36,-700},{250,6,80},steel);for(int i=0;i<10;++i){float x=515.f+(i%5)*52,z=-720.f+(i/5)*43;sphere(b,n+"medicine balls",{x,52,z},13,i%2?accent:rubber);}
    for(int i=0;i<8;++i){float x=340.f+(i%4)*40,z=-470.f+(i/4)*40;sphere(b,n+"kettlebells",{x,10,z},9,rubber);b.tube(n+"kettlebells",{x-6,13,z},{x-6,24,z},1.7f,steel,12);b.tube(n+"kettlebells",{x+6,13,z},{x+6,24,z},1.7f,steel,12);b.tube(n+"kettlebells",{x-6,24,z},{x+6,24,z},1.7f,steel,12);}
    b.rounded_box(n+"hidratação",{1240,52,-1480},{130,100,60},4,white);b.rounded_box(n+"hidratação",{1240,105,-1480},{136,6,64},2,accent);for(int i=0;i<4;++i)sports_bottle(b,n+"hidratação",{1202.f+i*22,108,-1480},accent,i);b.crest(n+"hidratação",{1240,66,-1448},36);
    b.frame();
}
void goal(Builder&b,float z,bool far_end){
    std::string n=far_end?"CT / gol norte":"CT / gol sul";float depth=far_end?180.f:-180.f;
    for(float x:{-366.f,366.f})b.tube(n,{x,2,z},{x,246,z},6,white,20);b.tube(n,{-366,246,z},{366,246,z},6,white,20);
    for(float x:{-366.f,366.f}){b.tube(n,{x,2,z+depth},{x,240,z+depth},2.5f,steel,12);b.tube(n,{x,245,z},{x,240,z+depth},2.5f,steel,12);}
    auto net=n+" / rede";Vec3 c={.84f,.88f,.85f};for(float x=-360;x<=360;x+=20)b.tube(net,{x,3,z+depth},{x,240,z+depth},.45f,c,6);for(float y=10;y<=240;y+=20)b.tube(net,{-366,y,z+depth},{366,y,z+depth},.45f,c,6);
    for(float x:{-366.f,366.f}){for(float y=10;y<=240;y+=20)b.tube(net,{x,y,z},{x,y,z+depth},.45f,c,6);for(float d=0;d<=180;d+=20)b.tube(net,{x,4,z+copysignf(d,depth)},{x,240,z+copysignf(d,depth)},.45f,c,6);}
    for(float d=0;d<=180;d+=20)b.tube(net,{-366,244,z+copysignf(d,depth)},{366,244,z+copysignf(d,depth)},.45f,c,6);
}
void fence(Builder&b,Vec3 a,Vec3 B){const std::string n="CT / cercamento";auto d=sub(B,a);float length=sqrtf(d.x*d.x+d.z*d.z);int posts=std::max(1,int(length/250));for(int i=0;i<=posts;++i){auto p=add(a,mul(d,float(i)/posts));b.tube(n,p,add(p,{0,340,0}),4,steel,10);}for(float y:{15.f,170.f,340.f})b.tube(n,add(a,{0,y,0}),add(B,{0,y,0}),2,steel,8);
    int wires=std::max(1,int(length/45));for(int i=0;i<=wires;++i){auto p=add(a,mul(d,float(i)/wires));b.tube(n+" / grade",add(p,{0,8,0}),add(p,{0,330,0}),.65f,{.39f,.43f,.42f},6);}for(float y=40;y<340;y+=45)b.tube(n+" / grade",add(a,{0,y,0}),add(B,{0,y,0}),.65f,{.39f,.43f,.42f},6);
}
void cone(Builder&b,Vec3 p,int i){std::string n="CT / cones "+std::to_string(i);b.rounded_box(n,add(p,{0,2,0}),{33,4,33},1.5f,{.96f,.36f,.045f});b.frustum(n,add(p,{0,4,0}),13,3,34,{.96f,.36f,.045f},16);b.frustum(n,add(p,{0,19,0}),8.5f,7,6,white,16);}
void dummy(Builder&b,Vec3 p,Vec3 accent,int i){std::string n="CT / barreira "+std::to_string(i);b.box(n,add(p,{0,4,0}),{55,8,50},rubber);for(float x:{-15.f,15.f})b.tube(n,add(p,{x,6,0}),add(p,{x,111,0}),2.2f,steel,10);
    b.rounded_box(n,add(p,{0,112,0}),{46,96,8},3,accent);b.tube(n,add(p,{0,181,-3}),add(p,{0,181,3}),18,accent,24);b.tube(n,add(p,{-30,93,0}),add(p,{-22,147,0}),4,accent,12);b.tube(n,add(p,{30,93,0}),add(p,{22,147,0}),4,accent,12);b.crest(n,add(p,{0,129,4.3f}),21);
}
void coach_board(Builder&b,Vec3 p,Vec3 accent){b.frame(p);const std::string n="CT / lousa do treinador";b.rounded_box(n,{0,167,0},{173,117,6},2,steel);b.box(n,{0,167,3.4f},{164,108,.5f},white);
    auto line=[&](float x,float y,float X,float Y){b.tube(n,{x,y,4},{X,Y,4},.35f,steel,8);};line(-72,121,72,121);line(72,121,72,211);line(72,211,-72,211);line(-72,211,-72,121);line(0,121,0,211);
    for(int i=0;i<48;++i){float a=i*2*pi/48,A=(i+1)*2*pi/48;line(12*cosf(a),166+12*sinf(a),12*cosf(A),166+12*sinf(A));}
    for(int i=0;i<11;++i)b.tube(n,{-58.f+(i%4)*31,136.f+(i/4)*28,4},{-58.f+(i%4)*31,136.f+(i/4)*28,6},3,accent,12);
    for(float x:{-69.f,69.f}){b.tube(n,{x,16,0},{x,111,0},2,steel,12);b.tube(n,{x,14,-36},{x,14,36},2,steel,12);for(float z:{-32.f,32.f})wheel(b,n,{x,6,z});}b.frame();
}
void training_field(Builder&b,Vec3 accent,int grass,const TrainingResources&r){
    b.frame();horizontal(b,"CT / terreno externo",{0,-7,5200},34000,34000,{.89f,.95f,.86f},grass,45,45);horizontal(b,"CT / entorno",{0,-1,5550},10500,14500,{.37f,.46f,.34f});horizontal(b,"CT / circulação",{0,.04f,400},3000,800,{.58f,.60f,.59f});
    for(int i=0;i<14;++i)horizontal(b,"CT / gramado",{0,.1f,1475.f+i*750},6800,750,i%2?Vec3{.83f,.92f,.84f}:white,grass,20,3);
    auto line=[&](float x,float z,float X,float Z){Vec3 mid={(x+X)/2,2.2f,(z+Z)/2};horizontal(b,"CT / marcações",mid,std::max(12.f,fabsf(X-x)),std::max(12.f,fabsf(Z-z)),white);};
    line(-3400,1100,3400,1100);line(3400,1100,3400,11600);line(3400,11600,-3400,11600);line(-3400,11600,-3400,1100);line(-3400,6350,3400,6350);
    auto arc=[&](float x,float z,float radius,float a,float A){for(int i=0;i<128;++i){float t=a+(A-a)*i/128,T=a+(A-a)*(i+1)/128;auto P=Vec3{x+radius*cosf(t),2.2f,z+radius*sinf(t)},Q=Vec3{x+radius*cosf(T),2.2f,z+radius*sinf(T)};auto d=normalized(sub(Q,P));Vec3 side={-d.z*6,0,d.x*6};b.face("CT / marcações",add(P,side),add(Q,side),sub(Q,side),sub(P,side),{0,1,0},white);}};
    arc(0,6350,915,0,2*pi);b.disc("CT / marcações",{0,2.25f,6350},10,white,16);
    for(bool far_end:{false,true}){float z=far_end?11600.f:1100.f,s=far_end?-1.f:1.f;for(auto box:std::array<Vec3,2>{{{2016,1650,0},{916,550,0}}}){line(-box.x,z,-box.x,z+s*box.y);line(-box.x,z+s*box.y,box.x,z+s*box.y);line(box.x,z+s*box.y,box.x,z);}b.disc("CT / marcações",{0,2.25f,z+s*1100},10,white,16);float angle=asinf(550.f/915);arc(0,z+s*1100,915,far_end?pi+angle:angle,far_end?2*pi-angle:pi-angle);goal(b,z,far_end);for(float x:{-3400.f,3400.f}){arc(x,z,100,x<0?(far_end?-pi/2:0):(far_end?pi:pi/2),x<0?(far_end?0:pi/2):(far_end?3*pi/2:pi));b.tube("CT / bandeirinhas",{x,0,z},{x,150,z},1.4f,white,10);b.box("CT / bandeirinhas",{x+16,135,z},{31,28,.5f},accent);}}
    fence(b,{-3800,0,750},{-3800,0,12000});fence(b,{3800,0,750},{3800,0,12000});fence(b,{-3800,0,12000},{3800,0,12000});fence(b,{-3800,0,750},{-1550,0,750});fence(b,{1550,0,750},{3800,0,750});
    for(int i=0;i<6;++i)dummy(b,{-150.f+i*60,0,2930},accent,i+1);for(int i=0;i<24;++i)cone(b,{-1350.f+(i%6)*220,0,3600.f+(i/6)*230},i+1);
    for(int i=0;i<10;++i){float x=1900.f+(i%5)*140,z=3520.f+(i/5)*340;b.tube("CT / mini barreiras",{x-38,2,z},{x-38,45,z},2,accent,10);b.tube("CT / mini barreiras",{x-38,45,z},{x+38,45,z},2,accent,10);b.tube("CT / mini barreiras",{x+38,45,z},{x+38,2,z},2,accent,10);}
    for(int i=0;i<14;++i){float z=4600.f+i*60;b.box("CT / escada de agilidade",{2000,.8f,z},{80,.8f,5},{.94f,.79f,.13f});}for(float x:{1960.f,2040.f})b.box("CT / escada de agilidade",{x,.5f,4990},{3,.8f,800},rubber);
    coach_board(b,{-3520,0,2150},accent);b.frame({-3490,0,2450});const std::string cart="CT / carrinho do treinador";for(float x:{-55.f,55.f})for(float z:{-36.f,36.f}){wheel(b,cart,{x,6,z});b.tube(cart,{x,17,z},{x,94,z},1.7f,steel,10);}for(float y:{28.f,85.f})b.rounded_box(cart,{0,y,0},{120,4,86},1.5f,white);for(int i=0;i<4;++i)sports_bottle(b,cart,{-41.f+i*25,88,-13},accent,i);b.rounded_box(cart,{25,91,21},{39,7,25},2,accent);b.frame();
    b.frame({-3300,0,1850});const std::string balls="CT / carrinho de bolas";for(float x:{-53.f,53.f})for(float z:{-40.f,40.f}){wheel(b,balls,{x,6,z});b.tube(balls,{x,17,z},{x,100,z},2,steel,10);}for(float y:{26.f,60.f,100.f})b.rim(balls,{0,y,0},110,85,5,1.5f,steel);for(float x=-42;x<53;x+=15)for(float z:{-40.f,40.f})b.tube(balls,{x,28,z},{x,100,z},.7f,steel,8);for(float z=-28;z<40;z+=15)for(float x:{-53.f,53.f})b.tube(balls,{x,28,z},{x,100,z},.7f,steel,8);b.rounded_box(balls,{0,25,0},{115,3,86},1,steel);
    std::map<int,int>textures;for(int i=0;i<12;++i)game_ball(b,r.ball,"CT / bola "+std::to_string(i+1),{-36.f+(i%3)*30,40.f+(i/6)*23,-24.f+((i/3)%2)*38},i*.63f,textures);b.frame();for(int i=0;i<7;++i)game_ball(b,r.ball,"CT / bola "+std::to_string(i+13),{-780.f+i*220,11,1800},i*.6f,textures);
    // Small training-ground stand, dugouts and perimeter floodlights.
    for(int step=0;step<4;++step){float x=4120.f+step*85;b.box("CT / arquibancada",{x,20.f+step*23,6350},{90,40.f+step*46,2250},{.64f,.66f,.65f});for(int i=0;i<35;++i)pad(b,"CT / assentos",{x,47.f+step*46,5265.f+i*63},{44,7,47},i%3?accent:white);}
    for(float z:{5400.f,7300.f}){b.box("CT / banco de reservas",{-3530,44,z},{50,8,460},steel);for(int i=0;i<7;++i)pad(b,"CT / banco de reservas",{-3530,51,z-185.f+i*62},{47,7,48},accent);b.box("CT / cobertura do banco",{-3530,225,z},{130,5,500},{.62f,.69f,.72f});for(float Z:{z-240,z+240})b.tube("CT / cobertura do banco",{-3580,0,Z},{-3580,225,Z},3,steel,10);}
    for(float x:{-4100.f,4100.f})for(float z:{1400.f,6200.f,11200.f}){b.tube("CT / iluminação",{x,0,z},{x,1000,z},8,steel,12);b.box("CT / refletores",{x,995,z},{100,28,35},steel);b.box("CT / refletores",{x,991,z+19},{91,16,1},white);}
    b.frame({4200,0,4950},-pi/2);sign(b,"CT / identidade",{0,280,0},L"CENTRO DE TREINAMENTO",700,accent);b.crest("CT / identidade",{0,423,3},150);b.frame();
    // A geometric daytime sky and distant planting; no flat stadium photograph.
    Texture sky;sky.width=8;sky.height=256;sky.format=3;sky.bytes.resize(8*256*4);for(int y=0;y<256;++y)for(int x=0;x<8;++x){float t=y/255.f;Vec3 c={.38f+.43f*t,.66f+.22f*t,.85f+.09f*t};auto k=(y*8+x)*4;sky.bytes[k]=uint8_t(c.x*255);sky.bytes[k+1]=uint8_t(c.y*255);sky.bytes[k+2]=uint8_t(c.z*255);sky.bytes[k+3]=255;}int tex=b.texture(std::move(sky));
    Texture cap;cap.width=cap.height=1;cap.format=3;cap.bytes={97,168,217,255};int top=b.texture(std::move(cap));
    for(int i=0;i<32;++i){float a=i*2*pi/32,A=(i+1)*2*pi/32;Vec3 P={cosf(a)*15000,0,5200+sinf(a)*15000},Q={cosf(A)*15000,0,5200+sinf(A)*15000};b.face("CT / céu",add(P,{0,11000,0}),add(Q,{0,11000,0}),Q,P,{0,0,1},{1.1f,1.1f,1.1f},tex);b.face("CT / céu superior",{0,11000,5200},add(Q,{0,11000,0}),add(P,{0,11000,0}),{0,11000,5200},{0,-1,0},{1.1f,1.1f,1.1f},top);}
    for(int i=0;i<26;++i){Vec3 p={-4700.f+(i%2)*9400,0,1200.f+(i/2)*850};b.tube("CT / árvores",p,add(p,{0,310,0}),13,{.27f,.22f,.16f},8);b.frustum("CT / árvores",add(p,{0,190,0}),155,25,350,{.20f,.38f,.22f},12);}
}
}
TrainingResources load_training_resources(Assets&assets,const fs::path&game,int club){auto prints=load_dressing_prints(assets,game,club);return {std::move(prints.ball),std::move(prints.ball_asset)};}
Model build_training_center(const Model&club,const TrainingResources&r,bool exterior){
    Builder b;b.room.team_id=club.team_id;b.room.club_colors_valid=club.club_colors_valid;b.room.room=exterior?RoomTraining:RoomGym;b.room.player_count=0;std::copy(std::begin(club.club_colors),std::end(club.club_colors),std::begin(b.room.club_colors));
    if(club.crest_texture>=0&&size_t(club.crest_texture)<club.textures.size()){b.room.crest_texture=0;b.room.textures.push_back(club.textures[club.crest_texture]);}Vec3 accent=club.club_colors[0];int wood=b.texture(floor_texture(false)),grass=b.texture(floor_texture(true));
    gym(b,accent,wood);training_field(b,accent,grass,r);b.batch();b.room.diagnostic="Academia de dois andares e CT integrado: mezanino, vidraça, força/cardio/mobilidade, campo 105 x 68 m, gols com redes, cercamento, barreiras, cones, bolas FIFA, apoio do treinador e arquibancada. Ambiente genérico personalizado pelo clube; não é o CT real.";return std::move(b.room);
}
void training_camera_view(Camera&c,int environment,int view){
    c.orbit=false;c.speed=environment==6?250:800;c.fov=72;c.position={-950,235,-260};c.target={270,180,-1250};
    if(environment==6){if(view==1){c.position={-930,539,-1190};c.target={400,280,-620};c.fov=74;}else if(view==2){c.position={-280,210,-240};c.target={0,175,4600};c.fov=73;}else if(view==3){c.position={-150,192,-1130};c.target={410,140,-1470};c.fov=62;}else if(view==4){c.position={160,525,-1140};c.target={-20,438,-1490};c.fov=68;}}
    else {c.position={-6500,4800,900};c.target={0,30,6350};c.fov=70;if(view==1){c.position={900,240,1630};c.target={0,140,2950};c.fov=64;}else if(view==2){c.position={-2960,227,2370};c.target={-3390,115,2110};c.fov=66;}else if(view==3){c.position={4400,1290,6400};c.target={0,30,6400};c.fov=74;}else if(view==4){c.position={0,390,1300};c.target={0,370,-750};c.fov=72;}}
    auto d=sub(c.target,c.position);c.distance=sqrtf(d.x*d.x+d.y*d.y+d.z*d.z);c.pitch=std::clamp(asinf(d.y/c.distance),-1.5f,1.5f);c.yaw=atan2f(d.x,-d.z);
}
void open_training_center(Model&m){for(auto&p:m.parts)if(p.name=="Academia / teto"||p.name=="Academia / paredes laterais"){p.vertices.clear();p.indices.clear();}}
}
