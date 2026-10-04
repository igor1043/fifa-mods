@echo off
setlocal
call "%~dp0..\env.cmd" "tests" "test_mod_overlay_screens"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /W4 /WX /EHsc /O2 /MT /Fe:test_mod_overlay_screens.exe "%CAREER_ROOT%\tests\screens\test_mod_overlay_screens.cpp"
if errorlevel 1 exit /b 1
test_mod_overlay_screens.exe
if errorlevel 1 exit /b 1
popd
endlocal
