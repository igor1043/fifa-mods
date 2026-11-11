@echo off
setlocal
call "%~dp0..\env.cmd" "tests" "test_scoreboard_options_wire"
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /D_CRT_SECURE_NO_WARNINGS "%CAREER_ROOT%\tests\providers\test_scoreboard_options_wire.c" /Fe:test_scoreboard_options_wire.exe
if errorlevel 1 exit /b 1
test_scoreboard_options_wire.exe
if errorlevel 1 exit /b 1
popd
endlocal
