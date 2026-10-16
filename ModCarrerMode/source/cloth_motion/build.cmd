@echo off
setlocal
set VSCMD_SKIP_SENDTELEMETRY=1
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
if not exist build mkdir build
cl /nologo /std:c++17 /EHsc /W4 /WX /O2 /MT test_live_control.cpp /Fobuild\test_live_control.obj /Febuild\test_live_control.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_live_control.exe
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /O2 /MT test_call_patch.cpp /Fobuild\test_call_patch.obj /Febuild\test_call_patch.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_call_patch.exe
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /O2 /MT test_native_frame.cpp /Fobuild\test_native_frame.obj /Febuild\test_native_frame.exe /link /NOLOGO user32.lib
if errorlevel 1 exit /b 1
build\test_native_frame.exe
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /O2 /MT test_particle_assets.cpp /Fobuild\test_particle_assets.obj /Febuild\test_particle_assets.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_particle_assets.exe "J:\mods\fifa 16\estudos fifa 16\71_CLOTH_PARTICLE_SOLVER_20261015\fixtures" "J:\mods\fifa 16\estudos fifa 16\73_CLOTH_BODY_CONTACT_LAUNCHER_20261015\fixtures"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /O2 /MT test_shirt_revision.cpp /Fobuild\test_shirt_revision.obj /Febuild\test_shirt_revision.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_shirt_revision.exe "J:\mods\fifa 16\estudos fifa 16\71_CLOTH_PARTICLE_SOLVER_20261015\fixtures" "J:\mods\fifa 16\estudos fifa 16\73_CLOTH_BODY_CONTACT_LAUNCHER_20261015\fixtures" "J:\mods\fifa 16\estudos fifa 16\75_CLOTH_SHIRT_CHEST_SLEEVES_20261015\fixtures"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /O2 /MT test_hem_revision.cpp /Fobuild\test_hem_revision.obj /Febuild\test_hem_revision.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_hem_revision.exe "J:\mods\fifa 16\estudos fifa 16\71_CLOTH_PARTICLE_SOLVER_20261015\fixtures" "J:\mods\fifa 16\estudos fifa 16\73_CLOTH_BODY_CONTACT_LAUNCHER_20261015\fixtures" "J:\mods\fifa 16\estudos fifa 16\75_CLOTH_SHIRT_CHEST_SLEEVES_20261015\fixtures"
if errorlevel 1 exit /b 1
if /I "%~1"=="--tests-only" goto done
cl /nologo /std:c++17 /EHsc /W4 /WX /O2 /MT /LD cloth_motion.cpp /Fobuild\cloth_motion.obj /Febuild\cloth_motion.dll /link /NOLOGO user32.lib /IMPLIB:build\cloth_motion.lib
if errorlevel 1 exit /b 1
:done
popd
endlocal
