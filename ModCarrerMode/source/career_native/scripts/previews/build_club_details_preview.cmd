@echo off
setlocal
call "%~dp0..\env.cmd" "previews" "generate_club_details_preview"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /W3 /EHsc /O2 /Gy /MT /D_CRT_SECURE_NO_WARNINGS /I"%CAREER_ROOT%\src\render\renderer" /I"%CAREER_ROOT%\..\ambientes3d\third_party\ufbx" /c "%CAREER_ROOT%\src\render\scenes\new_experience_rooms.cpp" "%CAREER_ROOT%\..\ambientes3d\src\viewer_press_room.cpp" "%CAREER_ROOT%\..\ambientes3d\src\viewer_dressing_room.cpp" "%CAREER_ROOT%\..\ambientes3d\src\viewer_training_center.cpp" "%CAREER_ROOT%\..\ambientes3d\src\viewer_core.cpp" "%CAREER_ROOT%\..\ambientes3d\src\viewer_team.cpp" "%CAREER_ROOT%\..\ambientes3d\src\viewer_pose_hooks.cpp" "%CAREER_ROOT%\..\ambientes3d\src\viewer_animation.cpp" "%CAREER_ROOT%\..\ambientes3d\src\viewer_cinematics.cpp"
if errorlevel 1 exit /b 1
cl /nologo /O2 /Gy /MT /c "%CAREER_ROOT%\..\ambientes3d\third_party\ufbx\ufbx.c"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /W3 /EHsc /O2 /MT /D_CRT_SECURE_NO_WARNINGS "%CAREER_ROOT%\tools\previews\generate_club_details_preview.cpp" fifa_player_assets.obj fifa_player_pose.obj fifa_club_room.obj fifa_player_renderer.obj new_experience_rooms.obj viewer_press_room.obj viewer_dressing_room.obj viewer_training_center.obj viewer_core.obj viewer_team.obj viewer_pose_hooks.obj viewer_animation.obj viewer_cinematics.obj ufbx.obj miniz_tinfl.obj /Fe:generate_club_details_preview.exe /link /OPT:REF shlwapi.lib xmllite.lib gdi32.lib user32.lib d3d11.lib d3dcompiler.lib dxgi.lib windowscodecs.lib ole32.lib
if errorlevel 1 exit /b 1
popd
endlocal
