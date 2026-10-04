@echo off
setlocal
call "%~dp0..\env.cmd" "tests" "test_mod_xinput_gate"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /W4 /WX /EHsc /O2 /MT /Fe:test_mod_xinput_gate.exe "%CAREER_ROOT%\tests\core\test_mod_xinput_gate.cpp"
if errorlevel 1 exit /b 1
test_mod_xinput_gate.exe
if errorlevel 1 exit /b 1
popd
endlocal
