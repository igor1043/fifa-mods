@echo off
setlocal
call "%~dp0..\env.cmd" "previews" "generate_club_details_preview"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /W3 /EHsc /O2 /MT /D_CRT_SECURE_NO_WARNINGS "%CAREER_ROOT%\tools\previews\generate_club_details_preview.cpp" fifa_player_assets.obj fifa_player_pose.obj fifa_club_room.obj fifa_player_renderer.obj new_experience_rooms.obj viewer_press_room.obj viewer_dressing_room.obj viewer_training_center.obj viewer_core.obj viewer_team.obj viewer_pose_hooks.obj viewer_animation.obj viewer_cinematics.obj ufbx.obj miniz_tinfl.obj /Fe:generate_club_details_preview.exe /link /OPT:REF shlwapi.lib xmllite.lib gdi32.lib user32.lib d3d11.lib d3dcompiler.lib dxgi.lib windowscodecs.lib ole32.lib
if errorlevel 1 exit /b 1
popd
endlocal
