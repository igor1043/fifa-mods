@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /D_CRT_SECURE_NO_WARNINGS /I native native\retirement_engine.c retirement_engine_test.c /Fe:retirement_engine_test.exe user32.lib
if errorlevel 1 exit /b 1
endlocal
