@echo off
setlocal
call "%~dp0..\env.cmd" "tests" "test_retirement_profile_provider"
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W3 /O2 /MT /Fe:test_retirement_profile_provider.exe "%CAREER_ROOT%\tests\providers\test_retirement_profile_provider.c"
if errorlevel 1 exit /b 1
test_retirement_profile_provider.exe
if errorlevel 1 exit /b 1
popd
endlocal
