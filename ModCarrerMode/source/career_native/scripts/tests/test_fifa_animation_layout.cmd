@echo off
setlocal
call "%~dp0..\env.cmd" "tests" "test_fifa_animation_layout"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /EHsc /W3 /O2 /MT /D_CRT_SECURE_NO_WARNINGS "%CAREER_ROOT%\tests\render\test_fifa_animation_layout.cpp" /Fe:test_fifa_animation_layout.exe
if errorlevel 1 exit /b 1
test_fifa_animation_layout.exe "J:\mods\fifa 16\estudos fifa 16\02_ENGENHARIA_REVERSA\clube_3d_20261001\animation_recovered"
if errorlevel 1 exit /b 1
popd
endlocal
