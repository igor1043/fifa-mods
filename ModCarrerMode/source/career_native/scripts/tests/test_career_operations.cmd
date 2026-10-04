@echo off
setlocal
call "%~dp0..\env.cmd" "tests" "test_career_operations"
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /D_CRT_SECURE_NO_WARNINGS "%CAREER_ROOT%\tests\core\test_career_operations.c" "%CAREER_ROOT%\src\features\finance\career_loan_engine.c" "%CAREER_ROOT%\src\features\retirement\retirement_engine.c" /Fe:test_career_operations.exe /link user32.lib gdi32.lib
if errorlevel 1 exit /b 1
test_career_operations.exe %*
if errorlevel 1 exit /b 1
popd
endlocal
