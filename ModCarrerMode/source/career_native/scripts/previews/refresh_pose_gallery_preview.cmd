@echo off
setlocal
call "%~dp0..\env.cmd" "previews" "refresh_pose_gallery_preview"
if errorlevel 1 exit /b 1
if "%~1"=="" exit /b 2
cl /nologo /std:c++17 /utf-8 /EHsc /W3 /O2 /MT /D_CRT_SECURE_NO_WARNINGS /c "%CAREER_ROOT%\src\render\poses\fifa_player_pose.cpp" /Fo:fifa_player_pose.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /EHsc /W3 /O2 /MT /D_CRT_SECURE_NO_WARNINGS "%CAREER_ROOT%\tools\previews\generate_player_pose_gallery.cpp" fifa_player_assets.obj fifa_player_pose.obj fifa_club_room.obj fifa_player_renderer.obj miniz_tinfl.obj /Fe:generate_player_pose_gallery.exe /link d3d11.lib d3dcompiler.lib windowscodecs.lib ole32.lib
if errorlevel 1 exit /b 1
generate_player_pose_gallery.exe "U:\fifa 16" "J:\mods\fifa 16\estudos fifa 16\02_ENGENHARIA_REVERSA\clube_3d_20261001\flamengo_preview.bin" "%~1"
if errorlevel 1 exit /b 1
popd
endlocal
