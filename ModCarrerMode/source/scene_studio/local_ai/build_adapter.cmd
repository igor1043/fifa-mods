@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
cl /nologo /O2 /MT adapters.cpp /Fe:adapters.exe /link dxgi.lib >adapter-build.log 2>&1
if errorlevel 1 exit /b 1
adapters.exe > device.json
popd
