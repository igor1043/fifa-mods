@echo off
setlocal
call "%~dp0..\env.cmd" "build" "build_active_chain_crashfix"
if errorlevel 1 exit /b 1
rc /nologo /I"%CAREER_ROOT%\resources" /fo dinput8_active_chain_resource.res "%CAREER_ROOT%\resources\dinput8_active_chain_resource.rc"
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /D_CRT_SECURE_NO_WARNINGS /c "%CAREER_ROOT%\src\core\fce_contracts.c" "%CAREER_ROOT%\src\core\fce_model.c" "%CAREER_ROOT%\src\core\fce_runtime.c" "%CAREER_ROOT%\src\features\crowd\crowd_runtime.c" "%CAREER_ROOT%\src\features\retirement\retirement_engine.c" "%CAREER_ROOT%\src\features\ranking\global_ranking.c" "%CAREER_ROOT%\src\features\finance\career_loan_engine.c"
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W3 /O2 /MT /D_CRT_SECURE_NO_WARNINGS /c "%CAREER_ROOT%\src\host\dinput8_wrapper.c"
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W3 /O2 /MT /DMINIZ_NO_ZLIB_APIS /DMINIZ_NO_DEFLATE_APIS /DMINIZ_NO_ARCHIVE_APIS /DMINIZ_NO_STDIO /c "%CAREER_ROOT%\third_party\miniz\miniz_tinfl.c"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /W3 /EHsc /O2 /MT /D_CRT_SECURE_NO_WARNINGS /DIMGUI_IMPL_WIN32_DISABLE_GAMEPAD /I"%CAREER_ROOT%\third_party\imgui" /c "%CAREER_ROOT%\src\screens\ranking\ranking_overlay.cpp" "%CAREER_ROOT%\src\platform\input\ranking_card_action.cpp" "%CAREER_ROOT%\src\platform\input\ranking_input_gate.cpp" "%CAREER_ROOT%\src\platform\overlay\mod_overlay_screens.cpp" "%CAREER_ROOT%\src\platform\input\mod_xinput_gate.cpp" "%CAREER_ROOT%\src\screens\club\club_player_screen.cpp" "%CAREER_ROOT%\src\screens\player\player_search_screen.cpp" "%CAREER_ROOT%\src\screens\clubs\clubs_browser.cpp" "%CAREER_ROOT%\src\screens\leagues\leagues_browser.cpp" "%CAREER_ROOT%\src\screens\competitions\club_competitions_screen.cpp" "%CAREER_ROOT%\src\screens\trophies\trophy_room_screen.cpp" "%CAREER_ROOT%\src\screens\sponsors\sponsor_screen.cpp" "%CAREER_ROOT%\src\screens\coach\coach_profile_screen.cpp" "%CAREER_ROOT%\src\screens\next_match\next_match_screen.cpp" "%CAREER_ROOT%\src\render\stadium_thumbnails\stadium_preview.cpp" "%CAREER_ROOT%\src\screens\operations\career_operations.cpp" "%CAREER_ROOT%\src\features\operations\career_operations_io.cpp" "%CAREER_ROOT%\src\screens\transfers\transfer_center_screen.cpp" "%CAREER_ROOT%\src\render\assets\fifa_player_assets.cpp" "%CAREER_ROOT%\src\render\poses\fifa_player_pose.cpp" "%CAREER_ROOT%\src\render\scenes\fifa_club_room.cpp" "%CAREER_ROOT%\src\render\renderer\fifa_player_renderer.cpp" "%CAREER_ROOT%\third_party\imgui\imgui.cpp" "%CAREER_ROOT%\third_party\imgui\imgui_draw.cpp" "%CAREER_ROOT%\third_party\imgui\imgui_tables.cpp" "%CAREER_ROOT%\third_party\imgui\imgui_widgets.cpp" "%CAREER_ROOT%\third_party\imgui\backends\imgui_impl_win32.cpp" "%CAREER_ROOT%\third_party\imgui\backends\imgui_impl_dx11.cpp"
if errorlevel 1 exit /b 1
link /nologo /DLL /MAP:dinput8.map /MAPINFO:EXPORTS /OUT:dinput8.dll /DEF:"%CAREER_ROOT%\src\host\dinput8_wrapper.def" dinput8_wrapper.obj fce_contracts.obj fce_model.obj fce_runtime.obj crowd_runtime.obj retirement_engine.obj global_ranking.obj ranking_overlay.obj ranking_card_action.obj ranking_input_gate.obj mod_overlay_screens.obj mod_xinput_gate.obj club_player_screen.obj player_search_screen.obj clubs_browser.obj leagues_browser.obj club_competitions_screen.obj trophy_room_screen.obj sponsor_screen.obj coach_profile_screen.obj next_match_screen.obj stadium_preview.obj career_operations.obj career_operations_io.obj transfer_center_screen.obj career_loan_engine.obj fifa_player_assets.obj fifa_player_pose.obj fifa_club_room.obj fifa_player_renderer.obj miniz_tinfl.obj imgui.obj imgui_draw.obj imgui_tables.obj imgui_widgets.obj imgui_impl_win32.obj imgui_impl_dx11.obj dinput8_active_chain_resource.res kernel32.lib user32.lib gdi32.lib dwmapi.lib d3d11.lib d3dcompiler.lib dxgi.lib psapi.lib bcrypt.lib
if errorlevel 1 exit /b 1
copy /Y dinput8.dll "%REPO_ROOT%\dinput8.dll" >nul
if errorlevel 1 exit /b 1
popd
endlocal
