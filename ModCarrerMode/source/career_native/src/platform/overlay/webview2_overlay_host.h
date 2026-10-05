#ifndef FIFA16_WEBVIEW2_OVERLAY_HOST_H
#define FIFA16_WEBVIEW2_OVERLAY_HOST_H

#include <windows.h>
#include <d3d11.h>
#include <dxgi.h>

namespace fifa_webview {

bool configure(const char *game_root, void (*log)(const char *));
void show();
void hide();
int status(); /* 0 starting, 1 ready, -1 unavailable */
bool page_is_home();
bool page_is_scene();
bool page_is_player();
bool visible();
void clear_scene_preview();
void set_career_context(int club_id, const char *club_name,
    int player_count, bool valid_starting_eleven, const char *detail_json=nullptr);
bool publish_scene(ID3D11ShaderResourceView *image);
bool handle_window_message(HWND window, UINT message, WPARAM wparam,
    LPARAM lparam, LRESULT *result);

} // namespace fifa_webview

#endif
