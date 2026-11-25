@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Installation failed.
    pause
    exit /b %errorlevel%
)
echo.
pause
