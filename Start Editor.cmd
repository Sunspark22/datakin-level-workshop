@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 server.py --open
    goto done
)
where python >nul 2>nul
if not errorlevel 1 (
    python server.py --open
    goto done
)
echo Install Python 3.10 or newer from python.org, then run this file again.
pause
exit /b 1
:done
if errorlevel 1 pause
