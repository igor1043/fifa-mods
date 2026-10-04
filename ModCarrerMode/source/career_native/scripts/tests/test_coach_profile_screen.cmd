@echo off
setlocal
call "%~dp0..\env.cmd" "tests" "test_coach_profile_screen"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /W3 /EHsc /O2 /MT /D_CRT_SECURE_NO_WARNINGS /DCOACH_PROFILE_TEST /I"%CAREER_ROOT%\third_party\imgui" "%CAREER_ROOT%\tests\screens\test_coach_profile_screen.cpp" "%CAREER_ROOT%\src\screens\coach\coach_profile_screen.cpp" mod_overlay_screens.obj fifa_player_assets.obj fifa_player_pose.obj fifa_club_room.obj fifa_player_renderer.obj miniz_tinfl.obj imgui.obj imgui_draw.obj imgui_tables.obj imgui_widgets.obj imgui_impl_dx11.obj /Fe:test_coach_profile_screen.exe /link user32.lib d3d11.lib d3dcompiler.lib windowscodecs.lib ole32.lib
if errorlevel 1 exit /b 1
test_coach_profile_screen.exe %*
if errorlevel 1 exit /b 1
popd
endlocal
