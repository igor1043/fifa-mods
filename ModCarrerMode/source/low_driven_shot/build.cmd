@echo off
setlocal
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
for /f "usebackq delims=" %%i in (`"%VSWHERE%" -latest -products * -property installationPath`) do set "VSINSTALL=%%i"
if not defined VSINSTALL exit /b 1
call "%VSINSTALL%\VC\Auxiliary\Build\vcvarsall.bat" x64 >nul 2>&1
if errorlevel 1 exit /b 1
pushd "%~dp0"
if not exist build mkdir build
cl /nologo /O2 /MT /W4 /LD /EHsc /std:c++17 low_driven_shot.cpp /Fo:build\ /Fe:build\low_driven_shot.dll /link /INCREMENTAL:NO
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%
