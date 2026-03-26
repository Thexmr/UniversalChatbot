@echo off
chcp 65001 > nul

:: UniversalChatbot Quick Start Script (Windows)
:: Starts the backend with virtual environment

setlocal enabledelayedexpansion

cls
echo.
echo   _   _ _   _ ___  ___     _   _      _   _   _ _____ _   _
echo   ^| ^| ^| ^| ^| ^| ^|  \/  ^|    ^| ^| ^| ^|    ^| ^| ^| ^| ^| ^| ^|_   _^| ^| ^| ^|
echo   ^| ^| ^| ^| ^| ^| ^| .  . ^| ___^| ^|_^| ^| ___^| ^|_^| ^| ^| ^| ^| ^| ^| ^|_^| ^|
echo   ^| ^| ^| ^| ^| ^| ^| ^|\/^| ^|/ _ ^| __^| ^|/ _ ^|  _  ^| ^| ^| ^| ^|  _  ^|
echo   ^| ^|_^| ^| ^|_^| ^| ^| ^|  ^| ^|  __/ ^|_^| ^|  __/ ^| ^| ^|_^| ^| ^| ^| ^|
echo    ^\___/ ^\___/ \_^|  ^|_/^\___^|^\__^|_/^\___^|_^| ^|_^\___/  \_/ ^|_^|_
echo.

:: Get script directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: Check if backend exists
if not exist "backend" (
    echo [ERROR] backend directory not found!
    pause
    exit /b 1
)

:: Setup virtual environment
set "VENV_DIR=.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"

if not exist "%VENV_DIR%" (
    echo [1/3] Creating virtual environment...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo     [OK] Virtual environment created
) else (
    echo [1/3] Virtual environment exists
)

:: Activate and install dependencies
echo [2/3] Activating virtual environment...
echo [3/3] Checking dependencies...

cd backend
"%VENV_PIP%" install -q -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo     [OK] Dependencies ready

:: Check for .env file
if not exist ".env" (
    if exist ".env.example" (
        echo.
        echo [Note] .env file missing!
        echo     Copy .env.example to .env and configure your API keys
        echo.
    )
)

echo.
echo =====================================
echo   [OK] UniversalChatbot is starting...
echo =====================================
echo.
echo   Backend: http://localhost:5000
echo   WebSocket: ws://localhost:5000
echo   Backend dir: %cd%
echo.
echo   Press Ctrl+C to stop
echo.

:: Start the backend
"%VENV_PYTHON%" main.py

:: Keep window open on error
if errorlevel 1 pause
