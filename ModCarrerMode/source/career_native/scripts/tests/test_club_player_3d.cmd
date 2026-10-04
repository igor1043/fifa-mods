@echo off
setlocal
call "%~dp0..\env.cmd" "tests" "test_club_player_3d"
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W3 /O2 /MT /DMINIZ_NO_ZLIB_APIS /DMINIZ_NO_DEFLATE_APIS /DMINIZ_NO_ARCHIVE_APIS /DMINIZ_NO_STDIO /c "%CAREER_ROOT%\third_party\miniz\miniz_tinfl.c"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /EHsc /W3 /O2 /MT /D_CRT_SECURE_NO_WARNINGS "%CAREER_ROOT%\tests\render\test_club_player_3d.cpp" "%CAREER_ROOT%\src\render\assets\fifa_player_assets.cpp" "%CAREER_ROOT%\src\render\poses\fifa_player_pose.cpp" "%CAREER_ROOT%\src\render\scenes\fifa_club_room.cpp" "%CAREER_ROOT%\src\render\renderer\fifa_player_renderer.cpp" miniz_tinfl.obj /Fe:test_club_player_3d.exe /link d3d11.lib d3dcompiler.lib
if errorlevel 1 exit /b 1
test_club_player_3d.exe "U:\fifa 16" "club-player-test.bmp"
if errorlevel 1 exit /b 1
popd
endlocal
