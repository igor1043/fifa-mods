@echo off
setlocal
call "%~dp0..\env.cmd" "tests" "test_native_patch_preflight"
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W3 /O2 /MT /Fe:test_native_patch_preflight.exe "%CAREER_ROOT%\tests\providers\test_native_patch_preflight.c" fce_contracts.obj fce_model.obj fce_runtime.obj crowd_runtime.obj retirement_engine.obj /link kernel32.lib user32.lib gdi32.lib psapi.lib bcrypt.lib
if errorlevel 1 exit /b 1
test_native_patch_preflight.exe
if errorlevel 1 exit /b 1
popd
endlocal
