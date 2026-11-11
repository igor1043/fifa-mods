#define NOMINMAX
#include <cassert>
#include <cmath>
#include <iostream>
#include "room_fps_mouse.h"
struct MouseMock {
 inline static HWND window=reinterpret_cast<HWND>(1);
 inline static POINT point{300,240};
 inline static RECT client{100,100,900,700},restriction{0,0,1920,1080};
 inline static unsigned moves=0;
 static bool position(POINT& p){p=point;return true;}
 static bool bounds(HWND,RECT& r){r=client;return true;}
 static bool clip(RECT& r){r=restriction;return true;}
 static bool constrain(const RECT& r){restriction=r;return true;}
 static void move(POINT p){point=p;++moves;}
 static HWND foreground(){return window;}
 static void hide(){}
};
int main(){
 using Look=room_fps::MouseLook<MouseMock>;Look mouse;auto game=MouseMock::window;
 auto first=mouse.sample(game);assert(first.yaw==0&&first.pitch==0&&mouse.captured);
 assert(MouseMock::point.x==500&&MouseMock::point.y==400);
 // Mouse look is button-free, keeps working at any screen edge and has no
 // frame-time scaling: one mouse pixel always has the same angular effect.
 for(int i=0;i<100;++i){MouseMock::point={520,390};auto delta=mouse.sample(game);assert(std::abs(delta.yaw-.06f)<.00001f&&std::abs(delta.pitch-.03f)<.00001f);assert(MouseMock::point.x==500&&MouseMock::point.y==400);}
 auto stopped=mouse.sample(game);assert(stopped.yaw==0&&stopped.pitch==0);
 mouse.reset();assert(!mouse.captured&&MouseMock::point.x==300&&MouseMock::point.y==240);assert(MouseMock::restriction.right==1920);
 // Alt-Tab releases confinement without moving the pointer in another app.
 mouse.sample(game);MouseMock::window=reinterpret_cast<HWND>(2);MouseMock::point={700,650};auto moves=MouseMock::moves;
 mouse.sample(game);assert(!mouse.captured&&MouseMock::moves==moves&&MouseMock::restriction.right==1920);
 MouseMock::window=game;auto back=mouse.sample(game);assert(back.yaw==0&&back.pitch==0);
 // A resolution/window change starts at a new center without a look jump.
 MouseMock::client={0,0,2560,1080};auto resized=mouse.sample(game);assert(resized.yaw==0&&resized.pitch==0&&MouseMock::point.x==1280);
 // Never overwrite capture acquired by another overlay after this camera.
 MouseMock::restriction={10,10,30,30};moves=MouseMock::moves;mouse.reset();assert(MouseMock::restriction.right==30&&MouseMock::moves==moves);
 room_fps::DragLook<MouseMock> drag;MouseMock::client={100,100,900,700};MouseMock::point={300,240};moves=MouseMock::moves;
 assert(drag.sample(game,false).yaw==0&&!drag.dragging);
 assert(drag.sample(game,true).yaw==0&&drag.dragging);
 MouseMock::point={320,230};const auto delta=drag.sample(game,true);assert(std::abs(delta.yaw-.06f)<.00001f&&std::abs(delta.pitch-.03f)<.00001f);
 assert(MouseMock::moves==moves);drag.sample(game,false);assert(!drag.dragging);
 MouseMock::point={500,690};drag.sample(game,true);assert(!drag.dragging); // Footer click.
 MouseMock::point={500,110};drag.sample(game,true);assert(!drag.dragging); // Header click.
 MouseMock::point={500,400};drag.sample(game,true);assert(drag.dragging);
 MouseMock::window=reinterpret_cast<HWND>(2);drag.sample(game,true);assert(!drag.dragging&&MouseMock::moves==moves);
 std::cout<<"PASS mouse look: left-button scene drag, release/focus safety, header/footer excluded, cursor never moved or confined\n";
}
