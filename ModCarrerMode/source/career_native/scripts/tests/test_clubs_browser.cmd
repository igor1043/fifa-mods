@echo off
setlocal
call "%~dp0..\env.cmd" "tests" "test_clubs_browser"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /EHsc /W3 /O2 /MT /D_CRT_SECURE_NO_WARNINGS /DCLUBS_BROWSER_TEST /DCLUB_PLAYER_SCREEN_TEST /I"%CAREER_ROOT%\third_party\imgui" "%CAREER_ROOT%\tests\screens\test_clubs_browser.cpp" "%CAREER_ROOT%\src\screens\clubs\clubs_browser.cpp" "%CAREER_ROOT%\src\screens\club\club_player_screen.cpp" "%CAREER_ROOT%\src\screens\coach\coach_profile_screen.cpp" "%CAREER_ROOT%\src\platform\overlay\mod_overlay_screens.cpp" fifa_player_assets.obj fifa_player_pose.obj fifa_club_room.obj fifa_player_renderer.obj miniz_tinfl.obj imgui.obj imgui_draw.obj imgui_tables.obj imgui_widgets.obj imgui_impl_dx11.obj /Fe:test_clubs_browser.exe /link d3d11.lib d3dcompiler.lib windowscodecs.lib ole32.lib
if errorlevel 1 exit /b 1
test_clubs_browser.exe "U:\fifa 16" "J:\mods\fifa 16\estudos fifa 16\02_ENGENHARIA_REVERSA\clube_3d_20261001\flamengo_preview.bin" "%~1"
if errorlevel 1 exit /b 1
popd
endlocal
