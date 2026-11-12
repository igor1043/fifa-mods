#include <cassert>
#include <fstream>
#include <sstream>
#include <iostream>
#include "room_tour_loader.h"
#include "room_free_camera.h"
std::string fixture(float fov=83){
 std::ostringstream f;f<<"S16TOUR 5 2120 130026 42 0 1 8 1 0 0 1\n-160 0 77 160 87 213\n";
 for(int i=0;i<9;++i)f<<"0 180 750 0 150 0 74\n";
 f<<"150 178 1685 245 130 2260 "<<fov<<"\n";return f.str();
}
int main(int argc,char**argv){
 room_cinema::Tour tour;std::istringstream good(fixture());assert(room_tour_loader::read(good,2120,130026,42,tour));
 assert(tour.extra.size()==1&&tour.extra[0].fov==83&&tour.obstacles.size()==1);
 room_free::Walk walk;assert(!walk.clear({0,165,140},tour));assert(walk.clear({0,165,750},tour));
 for(auto bad:{fixture(91),fixture(39),fixture().substr(0,70),fixture()+"junk"}){std::istringstream f(bad);assert(!room_tour_loader::read(f,2120,130026,42,tour));assert(tour.obstacles.size()==1);}
 for(auto args:{std::array<unsigned,3>{2121,130026,42},{2120,1,42},{2120,130026,43}}){std::istringstream f(fixture());assert(!room_tour_loader::read(f,args[0],args[1],args[2],tour));}
 if(argc==2){std::ifstream file(argv[1]);std::string line;std::getline(file,line);std::istringstream h(line);std::string magic;unsigned version,pid,club,generation;h>>magic>>version>>pid>>club>>generation;file.clear();file.seekg(0);assert(room_tour_loader::read(file,pid,club,generation,tour));assert(tour.obstacles.size()>100);assert(!walk.clear({0,165,140},tour));}
 std::cout<<"PASS complete tour with 83-degree coach camera, collision map, invalid/truncated and stale files\n";
}
