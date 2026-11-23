@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Alloy Addition Calculator — Sakthi Hackathon 2.0

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

"%PY_CMD%" run.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Server exited with code %errorlevel%.
    pause
)
