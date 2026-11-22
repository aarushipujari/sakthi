@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title VULCAN // SAKTHI MELT-OS (Coreless Induction Decision Support)
echo =========================================================================
echo   VULCAN // SAKTHI MELT-OS - METALLURGICAL DECISION SUPPORT SYSTEM
echo   Automated Corrective Alloy Addition Engine from Spectrometer Readings
echo =========================================================================
echo.

set "PY_CMD="

if exist "C:\Users\aarus\AppData\Local\Programs\Python\Python310\python.exe" (
    set "PY_CMD=C:\Users\aarus\AppData\Local\Programs\Python\Python310\python.exe"
) else (
    where python >nul 2>nul
    if !errorlevel! equ 0 (
        set "PY_CMD=python"
    ) else (
        where py >nul 2>nul
        if !errorlevel! equ 0 (
            set "PY_CMD=py"
        )
    )
)

if "%PY_CMD%"=="" (
    echo [ERROR] Python 3.10+ was not found in PATH or standard directories.
    echo Please install Python 3.10+ and add it to your system PATH.
    pause
    exit /b 1
)

echo Initializing VULCAN Melt-OS on http://127.0.0.1:8000 ...
echo Press Ctrl+C in this terminal to halt the server.
echo.
"%PY_CMD%" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
pause
