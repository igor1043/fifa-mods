@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\Install-ClubEnvironment.ps1" %*
exit /b %errorlevel%
