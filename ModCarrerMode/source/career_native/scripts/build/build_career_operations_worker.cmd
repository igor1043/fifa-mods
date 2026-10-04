@echo off
setlocal
call "%~dp0..\env.cmd" "build" "build_career_operations_worker"
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /D_CRT_SECURE_NO_WARNINGS /c "%CAREER_ROOT%\src\features\finance\career_loan_engine.c" "%CAREER_ROOT%\src\features\retirement\retirement_engine.c"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /W4 /EHsc /O2 /MT /D_CRT_SECURE_NO_WARNINGS "%CAREER_ROOT%\workers\career_operations_worker.cpp" "%CAREER_ROOT%\src\features\operations\career_operations_io.cpp" career_loan_engine.obj retirement_engine.obj /Fe:career_operations_worker.exe /link bcrypt.lib user32.lib gdi32.lib
if errorlevel 1 exit /b 1
copy /Y career_operations_worker.exe "%MOD_ROOT%\career_operations_worker.exe" >nul
if errorlevel 1 exit /b 1
popd
endlocal
