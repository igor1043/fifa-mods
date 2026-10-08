@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
if not exist build mkdir build
cl /nologo /std:c11 /W4 /WX /O2 /MT /D_CRT_SECURE_NO_WARNINGS test_bench_native12.c /Fobuild\test_bench_native12.obj /Febuild\test_bench_native12.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_bench_native12.exe
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /D_CRT_SECURE_NO_WARNINGS test_bench_import_adapter.c bench_import_adapter.c /Fobuild\ /Febuild\test_bench_import_adapter.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_bench_import_adapter.exe
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fobuild\test_native_role_bridge.obj test_native_role_bridge.asm
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /D_CRT_SECURE_NO_WARNINGS test_native_role_limit.c build\test_native_role_bridge.obj /Fobuild\test_native_role_limit.obj /Febuild\test_native_role_limit.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_native_role_limit.exe
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fobuild\test_bench_render_bridge.obj test_bench_render_bridge.asm
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /D_CRT_SECURE_NO_WARNINGS /DBENCH_RENDER_TEST test_bench_render_adapter.c bench_render_adapter.c bench_import_adapter.c build\test_bench_render_bridge.obj /Fobuild\ /Febuild\test_bench_render_adapter.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_bench_render_adapter.exe
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fobuild\bench_job_template.obj bench_job_adapter.asm
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fobuild\test_bench_job_bridge.obj test_bench_job_bridge.asm
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /D_CRT_SECURE_NO_WARNINGS test_bench_job_adapter.c bench_job_adapter.c bench_import_adapter.c build\bench_job_template.obj build\test_bench_job_bridge.obj /Fobuild\ /Febuild\test_bench_job_adapter.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_bench_job_adapter.exe
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /LD /D_CRT_SECURE_NO_WARNINGS bench_native12.c bench_render_adapter.c bench_import_adapter.c bench_job_adapter.c build\bench_job_template.obj /Fobuild\ /Febuild\bench_native12.dll /link /NOLOGO /IMPLIB:build\bench_native12.lib
if errorlevel 1 exit /b 1
popd
endlocal
