@echo off
setlocal
call "%~dp0..\env.cmd" "tests" "test_fifa_rig_probe"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /EHsc /W3 /O2 /MT /D_CRT_SECURE_NO_WARNINGS "%CAREER_ROOT%\tests\render\test_fifa_rig_probe.cpp" fifa_player_assets.obj fifa_player_pose.obj miniz_tinfl.obj /Fe:test_fifa_rig_probe.exe
if errorlevel 1 exit /b 1
test_fifa_rig_probe.exe "U:\fifa 16" "J:\mods\fifa 16\estudos fifa 16\02_ENGENHARIA_REVERSA\clube_3d_20261001\rig_recovered"
if errorlevel 1 exit /b 1
popd
endlocal
