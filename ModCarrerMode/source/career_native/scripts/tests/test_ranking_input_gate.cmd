@echo off
setlocal
call "%~dp0..\env.cmd" "tests" "test_ranking_input_gate"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /W4 /WX /EHsc /O2 /MT /D_CRT_SECURE_NO_WARNINGS /Fe:test_ranking_input_gate.exe "%CAREER_ROOT%\tests\core\test_ranking_input_gate.cpp" /link user32.lib
if errorlevel 1 exit /b 1
test_ranking_input_gate.exe
if errorlevel 1 exit /b 1
popd
endlocal
