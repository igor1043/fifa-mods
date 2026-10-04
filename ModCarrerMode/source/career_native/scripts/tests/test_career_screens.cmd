@echo off
setlocal
call "%~dp0..\env.cmd" "tests" "test_career_screens"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /W3 /EHsc /O2 /MT /D_CRT_SECURE_NO_WARNINGS /DCAREER_OPS_SCREEN_TEST /I"%CAREER_ROOT%\third_party\imgui" /c "%CAREER_ROOT%\src\screens\trophies\trophy_room_screen.cpp" "%CAREER_ROOT%\src\screens\sponsors\sponsor_screen.cpp" "%CAREER_ROOT%\src\render\assets\fifa_player_assets.cpp" "%CAREER_ROOT%\src\render\renderer\fifa_player_renderer.cpp"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /W3 /EHsc /O2 /MT /D_CRT_SECURE_NO_WARNINGS /DCAREER_OPS_SCREEN_TEST /I"%CAREER_ROOT%\third_party\imgui" "%CAREER_ROOT%\tests\screens\test_career_screens.cpp" "%CAREER_ROOT%\src\screens\operations\career_operations.cpp" "%CAREER_ROOT%\src\features\operations\career_operations_io.cpp" trophy_room_screen.obj sponsor_screen.obj mod_overlay_screens.obj career_loan_engine.obj retirement_engine.obj fifa_player_assets.obj fifa_player_pose.obj fifa_club_room.obj fifa_player_renderer.obj miniz_tinfl.obj imgui.obj imgui_draw.obj imgui_tables.obj imgui_widgets.obj imgui_impl_dx11.obj /Fe:test_career_screens.exe /link user32.lib gdi32.lib bcrypt.lib d3d11.lib d3dcompiler.lib
if errorlevel 1 exit /b 1
test_career_screens.exe %*
if errorlevel 1 exit /b 1
popd
endlocal
