@echo off
setlocal
call "%~dp0..\env.cmd" "tests" "test_career_operations_io"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /W4 /EHsc /O2 /MT /D_CRT_SECURE_NO_WARNINGS /DCAREER_OPS_IO_TEST "%CAREER_ROOT%\tests\core\test_career_operations_io.cpp" "%CAREER_ROOT%\src\features\operations\career_operations_io.cpp" career_loan_engine.obj retirement_engine.obj /Fe:test_career_operations_io.exe /link bcrypt.lib user32.lib gdi32.lib
if errorlevel 1 exit /b 1
test_career_operations_io.exe %*
if errorlevel 1 exit /b 1
popd
endlocal
