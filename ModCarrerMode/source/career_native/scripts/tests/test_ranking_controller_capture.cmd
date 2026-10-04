@echo off
setlocal
call "%~dp0..\env.cmd" "tests" "test_ranking_controller_capture"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /W3 /EHsc /O2 /MT /D_CRT_SECURE_NO_WARNINGS /I"%CAREER_ROOT%\third_party\imgui" /Fe:test_ranking_controller_capture.exe "%CAREER_ROOT%\tests\core\test_ranking_controller_capture.cpp" ranking_card_action.obj ranking_input_gate.obj mod_overlay_screens.obj mod_xinput_gate.obj club_player_screen.obj clubs_browser.obj leagues_browser.obj club_competitions_screen.obj player_search_screen.obj transfer_center_screen.obj trophy_room_screen.obj sponsor_screen.obj coach_profile_screen.obj next_match_screen.obj stadium_preview.obj career_operations.obj career_operations_io.obj career_loan_engine.obj retirement_engine.obj fifa_player_assets.obj fifa_player_pose.obj fifa_club_room.obj fifa_player_renderer.obj miniz_tinfl.obj imgui.obj imgui_draw.obj imgui_tables.obj imgui_widgets.obj imgui_impl_win32.obj imgui_impl_dx11.obj /link user32.lib gdi32.lib dwmapi.lib d3d11.lib d3dcompiler.lib dxgi.lib psapi.lib bcrypt.lib
if errorlevel 1 exit /b 1
test_ranking_controller_capture.exe
if errorlevel 1 exit /b 1
popd
endlocal
