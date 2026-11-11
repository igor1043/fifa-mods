#include "frame_chain.h"
#include <cassert>
int main(){
 using namespace trophy_chain;
 assert(classify(L"club_browser.dll")==Owner::clubBrowser);
 assert(classify(L"CLUB_BROWSER.DLL")==Owner::clubBrowser);
 assert(classify(L"native_dressing_room.dll")==Owner::dressingRoom);
 assert(classify(L"frontend_stadium_native_v11.dll")==Owner::frontend);
 assert(classify(L"panorama_drone_v5.dll")==Owner::panorama);
 assert(classify(L"other.dll")==Owner::unknown);
 assert(classify(nullptr)==Owner::unknown);
 assert(ready(Owner::clubBrowser,true,true));
 assert(!ready(Owner::dressingRoom,true,true));
 assert(!ready(Owner::frontend,true,true));
 assert(!ready(Owner::unknown,true,true));
 assert(ready(Owner::dressingRoom,true,false));
 assert(!ready(Owner::frontend,true,false));
 assert(ready(Owner::native,false,false));
 assert(ready(Owner::frontend,false,false));
 assert(ready(Owner::panorama,false,false));
 assert(!ready(Owner::unknown,false,false));
}
