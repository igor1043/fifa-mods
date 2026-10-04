@echo off
setlocal
if not "%~1"=="" (
    if not exist "%~dp0scripts\tests\%~1.cmd" exit /b 2
    call "%~dp0scripts\tests\%~1.cmd" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b
)
for %%T in (test_mod_paths test_career_leaders test_career_operations build_retirement_engine_test test_player_competitions test_retirement_profile_provider test_mod_overlay_screens test_mod_xinput_gate test_ranking_input_gate test_ranking_card_action test_native_patch_preflight test_ranking_controller_capture) do (
    call "%~dp0scripts\tests\%%T.cmd"
    if errorlevel 1 exit /b 1
)
echo Testes de regressao concluidos.
endlocal
