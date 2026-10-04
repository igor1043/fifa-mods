@echo off
setlocal
call "%~dp0..\env.cmd" "tests" "test_press_next_match"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /W3 /EHsc /O2 /MT /D_CRT_SECURE_NO_WARNINGS /DCLUB_PLAYER_SCREEN_TEST /DNEXT_MATCH_SCREEN_TEST /I"%CAREER_ROOT%\third_party\imgui" "%CAREER_ROOT%\tests\screens\test_press_next_match.cpp" "%CAREER_ROOT%\src\screens\club\club_player_screen.cpp" "%CAREER_ROOT%\src\screens\next_match\next_match_screen.cpp" stadium_preview.obj mod_overlay_screens.obj fifa_player_assets.obj fifa_player_pose.obj fifa_club_room.obj fifa_player_renderer.obj miniz_tinfl.obj imgui.obj imgui_draw.obj imgui_tables.obj imgui_widgets.obj imgui_impl_dx11.obj /Fe:test_press_next_match.exe /link user32.lib d3d11.lib d3dcompiler.lib
if errorlevel 1 exit /b 1
test_press_next_match.exe %*
if errorlevel 1 exit /b 1
popd
endlocal
