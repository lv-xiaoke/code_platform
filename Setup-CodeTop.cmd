@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup.ps1" %*
if errorlevel 1 (
    echo.
    echo Setup failed. Read the message above and docs\deployment.md.
    pause
    exit /b 1
)
echo.
echo Ready. Double-click Start-CodeTop.cmd to open CodeTop.
pause
