@echo off
setlocal
call "%~dp0..\env.cmd" "tests" "test_financial_incorporation"
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /D_CRT_SECURE_NO_WARNINGS /Fe:test_financial_incorporation.exe "%CAREER_ROOT%\tests\providers\test_financial_incorporation.c"
if errorlevel 1 exit /b 1
test_financial_incorporation.exe
if errorlevel 1 exit /b 1
popd
endlocal
