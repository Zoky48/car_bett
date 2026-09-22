@echo off
setlocal
cd /d "%~dp0"
title Traffic Bet Arena - Setup and Start

echo ========================================
echo   Traffic Bet Arena - Setup and Start
echo ========================================
echo.

where py >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON=py"
) else (
    where python >nul 2>nul
    if %errorlevel% neq 0 (
        echo Python was not found. Install Python 3.10+ and enable Add Python to PATH.
        pause
        exit /b 1
    )
    set "PYTHON=python"
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PYTHON% -m venv .venv
    if errorlevel 1 goto :error
)

echo Installing dependencies...
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto :error
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :error

if not exist "videos" mkdir videos

echo.
echo Setup complete. Starting the video selector...
echo.
.venv\Scripts\python.exe start.py
if errorlevel 1 goto :error
endlocal
exit /b 0

:error
echo.
echo Setup or startup failed.
pause
endlocal
exit /b 1
