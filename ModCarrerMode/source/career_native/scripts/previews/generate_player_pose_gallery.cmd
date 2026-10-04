@echo off
setlocal
call "%~dp0..\env.cmd" "previews" "generate_player_pose_gallery"
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W3 /O2 /MT /DMINIZ_NO_ZLIB_APIS /DMINIZ_NO_DEFLATE_APIS /DMINIZ_NO_ARCHIVE_APIS /DMINIZ_NO_STDIO /c "%CAREER_ROOT%\third_party\miniz\miniz_tinfl.c"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /EHsc /W3 /O2 /MT /D_CRT_SECURE_NO_WARNINGS "%CAREER_ROOT%\tools\previews\generate_player_pose_gallery.cpp" "%CAREER_ROOT%\src\render\assets\fifa_player_assets.cpp" "%CAREER_ROOT%\src\render\poses\fifa_player_pose.cpp" "%CAREER_ROOT%\src\render\scenes\fifa_club_room.cpp" "%CAREER_ROOT%\src\render\renderer\fifa_player_renderer.cpp" miniz_tinfl.obj /Fe:generate_player_pose_gallery.exe /link d3d11.lib d3dcompiler.lib windowscodecs.lib ole32.lib
if errorlevel 1 exit /b 1
generate_player_pose_gallery.exe "U:\fifa 16" "J:\mods\fifa 16\estudos fifa 16\02_ENGENHARIA_REVERSA\clube_3d_20261001\flamengo_preview.bin" "C:\Users\igorv\OneDrive\Área de Trabalho\poses\catalogo_poses_do_jogo"
if errorlevel 1 exit /b 1
popd
endlocal
