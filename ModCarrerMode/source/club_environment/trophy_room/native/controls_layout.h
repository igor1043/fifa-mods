// Generated from trophy_room/controls.py.

#pragma once
namespace trophy_controls {
constexpr float left=60,top=838,column=370,row=29,width=350,height=26;
struct Item {const wchar_t* key;const wchar_t* label;int action;};
constexpr Item mode0[]={{L"A / Enter",L"Ver taça em 3D",4},{L"B / Esc",L"Voltar",-1},{L"LS / Setas",L"Navegar",-2},{L"LB / RB",L"Clube / treinador",5},{L"LT / G",L"Galeria",6},{L"RT / H",L"Sala 3D",7},{L"Y / PgDn",L"Próxima página",0}};
constexpr Item mode1[]={{L"A / Enter",L"Detalhes da taça",4},{L"B / Esc",L"Galeria",-1},{L"LB / RB",L"Próxima / anterior",-2},{L"Y / F1",L"Próxima taça",0},{L"X / F2",L"Câmera livre",1},{L"LT / G",L"Galeria",6}};
constexpr Item mode2[]={{L"B / Esc",L"Voltar",-1},{L"LB / RB",L"Próxima / anterior",-2},{L"RS / Mouse",L"Rotacionar",-2},{L"LT / RT",L"Zoom",-2},{L"LS / Setas",L"Histórico",-2},{L"X / F2",L"Câmera livre",1}};
constexpr Item mode3[]={{L"B / Esc",L"Galeria",-1},{L"LS / WASD",L"Andar",-2},{L"RS / Mouse",L"Olhar",-2},{L"LB / RB",L"Descer / subir",-2},{L"X / F2",L"Ver taça",1},{L"LT / G",L"Galeria",6}};
constexpr Item mode4[]={{L"B / Esc",L"Voltar",-1},{L"LT / G",L"Galeria",6},{L"RT / H",L"Sala 3D",7}};
inline const Item* items(unsigned mode,unsigned&count){
switch(mode){
case 0:count=7;return mode0;
case 1:count=6;return mode1;
case 2:count=6;return mode2;
case 3:count=6;return mode3;
case 4:count=3;return mode4;
default:count=0;return nullptr;}}
}
