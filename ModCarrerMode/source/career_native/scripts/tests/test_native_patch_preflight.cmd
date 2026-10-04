@echo off
setlocal
call "%~dp0..\env.cmd" "tests" "test_native_patch_preflight"
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W3 /O2 /MT /Fe:test_native_patch_preflight.exe "%CAREER_ROOT%\tests\providers\test_native_patch_preflight.c" fce_contracts.obj fce_model.obj fce_runtime.obj crowd_runtime.obj retirement_engine.obj global_ranking.obj ranking_overlay.obj ranking_card_action.obj ranking_input_gate.obj mod_overlay_screens.obj mod_xinput_gate.obj club_player_screen.obj clubs_browser.obj leagues_browser.obj club_competitions_screen.obj player_search_screen.obj transfer_center_screen.obj trophy_room_screen.obj sponsor_screen.obj coach_profile_screen.obj next_match_screen.obj stadium_preview.obj career_operations.obj career_operations_io.obj career_loan_engine.obj fifa_player_assets.obj fifa_player_pose.obj fifa_club_room.obj fifa_player_renderer.obj miniz_tinfl.obj imgui.obj imgui_draw.obj imgui_tables.obj imgui_widgets.obj imgui_impl_win32.obj imgui_impl_dx11.obj /link kernel32.lib user32.lib gdi32.lib dwmapi.lib d3d11.lib d3dcompiler.lib dxgi.lib psapi.lib bcrypt.lib
if errorlevel 1 exit /b 1
test_native_patch_preflight.exe
if errorlevel 1 exit /b 1
popd
endlocal
