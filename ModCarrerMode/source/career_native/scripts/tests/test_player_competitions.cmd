@echo off
setlocal
call "%~dp0..\env.cmd" "tests" "test_player_competitions"
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /c "%CAREER_ROOT%\src\core\fce_contracts.c" "%CAREER_ROOT%\src\core\fce_model.c"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /W4 /WX /O2 /MT /EHsc "%CAREER_ROOT%\tests\core\test_player_competitions.cpp" fce_contracts.obj fce_model.obj /Fe:test_player_competitions.exe
if errorlevel 1 exit /b 1
test_player_competitions.exe
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT "%CAREER_ROOT%\tests\providers\test_player_competition_provider.c" fce_contracts.obj fce_model.obj /Fe:test_player_competition_provider.exe
if errorlevel 1 exit /b 1
test_player_competition_provider.exe
if errorlevel 1 exit /b 1
popd
endlocal
