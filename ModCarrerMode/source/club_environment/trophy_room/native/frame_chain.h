#pragma once
#include <cwchar>

namespace trophy_chain {
enum class Owner { unknown, native, dressingRoom, clubBrowser, frontend, panorama };
inline Owner classify(const wchar_t* leaf) {
 if(!leaf)return Owner::unknown;
 if(!_wcsicmp(leaf,L"native_dressing_room.dll"))return Owner::dressingRoom;
 if(!_wcsicmp(leaf,L"club_browser.dll"))return Owner::clubBrowser;
 if(!_wcsnicmp(leaf,L"frontend_stadium",16))return Owner::frontend;
 if(!_wcsnicmp(leaf,L"panorama_drone",14))return Owner::panorama;
 return Owner::unknown;
}
inline bool ready(Owner owner,bool dressingLoaded,bool browserLoaded) {
 // Ver clubes wraps the dressing-room callback. Wait for the outside of the
 // existing chain so neither module mistakes this gallery for a foreign hook.
 if(browserLoaded)return owner==Owner::clubBrowser;
 if(dressingLoaded)return owner==Owner::dressingRoom;
 return owner==Owner::native||owner==Owner::frontend||owner==Owner::panorama;
}
}
