@echo off
chcp 65001 > nul

:: UniversalChatbot Update Script (Windows)
:: Pulls latest changes and updates dependencies

setlocal enabledelayedexpansion

cls
echo.
echo   _   _ _   _ ___  ___ ___________ _   _
echo   ^| ^| ^| ^| ^| ^| ^|  \/  ^| ^|  _  ^| ___ ^\ ^| ^| ^|
echo   ^| ^| ^| ^| ^| ^| ^| .  . ^| ^| ^| ^| ^| ^|_/ / ^| ^| ^|
echo   ^| ^| ^| ^| ^| ^| ^| ^|\/^| ^| ^| ^| ^| ^|    /^| ^| ^| ^|
echo   ^| ^|_^| ^| ^|_^| ^| ^| ^|  ^| ^|\ \_/ /^| ^|\ ^\ ^|_^|_^|
echo    ^\___/ ^\___/ \_^|  ^|_/ ^\___/ ^\_^| ^\_^|_____^|
echo.

:: Get script directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: Check if it's a git repository
if not exist ".git" (
    echo [ERROR] Not a git repository!
    pause
    exit /b 1
)

echo [1/5] Checking git status...
for /f "tokens=*" %%a in ('git branch --show-current') do set BRANCH=%%a
for /f "tokens=*" %%a in ('git config --get remote.origin.url') do set REMOTE=%%a
echo     Branch: %BRANCH%
echo     Remote: %REMOTE%
echo.

echo [2/5] Stashing local changes (if any)...
git diff-index --quiet HEAD --
if errorlevel 1 (
    git stash push -m "Auto-stash before update"
    echo     Changes stashed
) else (
    echo     No local changes
)
echo.

echo [3/5] Fetching updates...
git fetch origin
if errorlevel 1 (
    echo     Fetch failed!
    pause
    exit /b 1
) else (
    echo     Fetch successful
)
echo.

echo [4/5] Checking for updates...
for /f "tokens=*" %%a in ('git rev-parse HEAD') do set LOCAL=%%a
for /f "tokens=*" %%a in ('git rev-parse origin/%BRANCH%') do set REMOTE=%%a

if "%LOCAL%" == "%REMOTE%" (
    echo     Already up to date!
) else (
    echo     Updates available!
    git log --oneline HEAD..origin/%BRANCH% -- 2>nul
    echo.
    
    echo Merging updates...
    git merge origin/%BRANCH%
    if errorlevel 1 (
        echo     Merge failed!
        pause
        exit /b 1
    )
    echo     Merge successful
)
echo.

echo [5/5] Updating Python dependencies...
if exist ".venv\Scripts\pip.exe" (
    cd backend
    call ..\.venv\Scripts\pip.exe install -r requirements.txt --upgrade --quiet
    echo     Dependencies updated
) else (
    echo     No venv found. Run install.bat first.
)
echo.

echo =====================================
echo   [OK] Update complete!
echo =====================================
echo.
echo   Restart UniversalChatbot:
echo     start.bat
echo.

pause
