@echo off
setlocal
call "%~dp0..\env.cmd" "tests" "test_stadium_3d"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /W3 /EHsc /O2 /MT /D_CRT_SECURE_NO_WARNINGS /DSTADIUM_DECODER_DIAGNOSTICS /c "%CAREER_ROOT%\src\render\assets\fifa_player_assets.cpp" /Fo:stadium_test_assets.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /W3 /EHsc /O2 /MT /D_CRT_SECURE_NO_WARNINGS /c "%CAREER_ROOT%\src\render\renderer\fifa_player_renderer.cpp" /Fo:stadium_test_renderer.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /W3 /EHsc /O2 /MT /D_CRT_SECURE_NO_WARNINGS /c "%CAREER_ROOT%\src\render\poses\fifa_player_pose.cpp" /Fo:stadium_test_pose.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /W3 /EHsc /O2 /MT /D_CRT_SECURE_NO_WARNINGS /c "%CAREER_ROOT%\src\render\scenes\fifa_club_room.cpp" /Fo:stadium_test_room.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /W3 /EHsc /O2 /MT /D_CRT_SECURE_NO_WARNINGS /DSTADIUM_SCENE_TEST /I"%CAREER_ROOT%\third_party\imgui" "%CAREER_ROOT%\tests\render\test_stadium_3d.cpp" "%CAREER_ROOT%\src\experimental\stadium_3d\stadium_scene_assets.cpp" "%CAREER_ROOT%\src\experimental\stadium_3d\stadium_scene_screen.cpp" stadium_test_assets.obj stadium_test_renderer.obj mod_overlay_screens.obj stadium_test_pose.obj stadium_test_room.obj miniz_tinfl.obj imgui.obj imgui_draw.obj imgui_tables.obj imgui_widgets.obj imgui_impl_dx11.obj /Fe:test_stadium_3d.exe /link user32.lib gdi32.lib d3d11.lib d3dcompiler.lib
if errorlevel 1 exit /b 1
test_stadium_3d.exe %*
if errorlevel 1 exit /b 1
popd
endlocal
