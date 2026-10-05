@echo off
setlocal
call "%~dp0..\env.cmd" "build" "build_active_chain_crashfix"
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W3 /O2 /MT /D_CRT_SECURE_NO_WARNINGS /c "%CAREER_ROOT%\src\host\dinput8_wrapper.c"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /W3 /EHsc /O2 /MT /D_CRT_SECURE_NO_WARNINGS /DIMGUI_IMPL_WIN32_DISABLE_GAMEPAD /I"%CAREER_ROOT%\third_party\imgui" /c "%CAREER_ROOT%\src\platform\overlay\webview2_overlay_host.cpp" "%CAREER_ROOT%\src\screens\club\club_player_screen.cpp" "%CAREER_ROOT%\src\screens\competitions\club_competitions_screen.cpp"
if errorlevel 1 exit /b 1
link /nologo /OPT:REF /DLL /MAP:dinput8.map /MAPINFO:EXPORTS /OUT:dinput8.dll /DEF:"%CAREER_ROOT%\src\host\dinput8_wrapper.def" dinput8_wrapper.obj fce_contracts.obj fce_model.obj fce_runtime.obj crowd_runtime.obj retirement_engine.obj global_ranking.obj ranking_overlay.obj ranking_card_action.obj ranking_input_gate.obj mod_overlay_screens.obj webview2_overlay_host.obj mod_xinput_gate.obj club_player_screen.obj player_search_screen.obj clubs_browser.obj leagues_browser.obj club_competitions_screen.obj trophy_room_screen.obj sponsor_screen.obj coach_profile_screen.obj next_match_screen.obj stadium_preview.obj career_operations.obj career_operations_io.obj transfer_center_screen.obj career_loan_engine.obj fifa_player_assets.obj fifa_player_pose.obj fifa_club_room.obj fifa_player_renderer.obj new_experience_rooms.obj viewer_press_room.obj viewer_dressing_room.obj viewer_training_center.obj viewer_core.obj viewer_team.obj viewer_pose_hooks.obj viewer_animation.obj viewer_cinematics.obj ufbx.obj miniz_tinfl.obj imgui.obj imgui_draw.obj imgui_tables.obj imgui_widgets.obj imgui_impl_win32.obj imgui_impl_dx11.obj dinput8_active_chain_resource.res kernel32.lib user32.lib gdi32.lib dwmapi.lib ole32.lib windowscodecs.lib crypt32.lib shlwapi.lib xmllite.lib d3d11.lib d3dcompiler.lib dxgi.lib psapi.lib bcrypt.lib
if errorlevel 1 exit /b 1
copy /Y dinput8.dll "%REPO_ROOT%\dinput8.dll" >nul
popd
