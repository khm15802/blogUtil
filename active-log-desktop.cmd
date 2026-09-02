@echo off
cd /d "%~dp0"
if exist ".python\pythonw.exe" (
    start "Active Log" ".python\pythonw.exe" -m active_log.desktop
    exit /b 0
)
if exist ".venv\Scripts\pythonw.exe" (
    start "Active Log" ".venv\Scripts\pythonw.exe" -m active_log.desktop
    exit /b 0
)
echo Active Log is not installed. Run install-windows.ps1 first.
pause
exit /b 1
