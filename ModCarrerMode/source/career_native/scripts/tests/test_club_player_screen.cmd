@echo off
setlocal
call "%~dp0..\env.cmd" "tests" "test_club_player_screen"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /EHsc /W3 /O2 /MT /c "%CAREER_ROOT%\src\render\poses\fifa_player_pose.cpp" "%CAREER_ROOT%\src\render\scenes\fifa_club_room.cpp"
if errorlevel 1 exit /b 1
if exist "%CAREER_ROOT%\src\screens\transfers\transfer_center_screen.cpp" (set "TEST_TRANSFER_CENTER_INPUT="%CAREER_ROOT%\src\screens\transfers\transfer_center_screen.cpp"") else (set "TEST_TRANSFER_CENTER_INPUT=transfer_center_screen.obj")
cl /nologo /std:c++17 /utf-8 /EHsc /W3 /O2 /MT /D_CRT_SECURE_NO_WARNINGS /DCLUB_PLAYER_SCREEN_TEST /I"%CAREER_ROOT%\third_party\imgui" "%CAREER_ROOT%\tests\screens\test_club_player_screen.cpp" "%CAREER_ROOT%\src\screens\club\club_player_screen.cpp" "%CAREER_ROOT%\src\screens\coach\coach_profile_screen.cpp" "%CAREER_ROOT%\src\screens\competitions\club_competitions_screen.cpp" %TEST_TRANSFER_CENTER_INPUT% "%CAREER_ROOT%\src\platform\overlay\mod_overlay_screens.cpp" fifa_player_assets.obj fifa_player_pose.obj fifa_club_room.obj fifa_player_renderer.obj miniz_tinfl.obj imgui.obj imgui_draw.obj imgui_tables.obj imgui_widgets.obj imgui_impl_dx11.obj /Fe:test_club_player_screen.exe /link d3d11.lib d3dcompiler.lib windowscodecs.lib ole32.lib
if errorlevel 1 exit /b 1
if "%~1"=="" (
    test_club_player_screen.exe "U:\fifa 16" "club-screen-test.bmp"
) else (
    test_club_player_screen.exe "U:\fifa 16" "club-flamengo-team.bmp" "%~1" %2
)
if errorlevel 1 exit /b 1
popd
endlocal
