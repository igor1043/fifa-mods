@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\maintenance\Install-Game.ps1" %*
exit /b %errorlevel%
