@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
pushd "%~dp0build"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /W4 /WX /EHsc /O2 /MT /Fe:test_mod_xinput_gate.exe ..\native\test_mod_xinput_gate.cpp
if errorlevel 1 exit /b 1
test_mod_xinput_gate.exe
if errorlevel 1 exit /b 1
popd
endlocal
