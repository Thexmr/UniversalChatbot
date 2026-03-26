@echo off
chcp 65001 > nul
echo ===========================================
echo  UniversalChatbot Native Host Installer
echo ===========================================
echo.

:: Check Python
echo [1/4] Checking Python installation...
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.11+ from https://python.org
    pause
    exit /b 1
)
python --version
echo.

:: Get script directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: Install Python dependencies
echo [2/4] Installing Python dependencies...
cd backend
if exist "requirements.txt" (
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
) else (
    echo [WARNING] requirements.txt not found, skipping pip install
)
echo.

:: Register Native Messaging Host
echo [3/4] Registering Native Messaging Host...
cd "%SCRIPT_DIR%"
python setup_windows.py
if errorlevel 1 (
    echo [ERROR] Failed to register Native Messaging Host
    pause
    exit /b 1
)
echo.

:: Create desktop shortcut
echo [4/4] Creating desktop shortcut...
set "SHORTCUT_NAME=UniversalChatbot.lnk"
set "TARGET=%SCRIPT_DIR%backend\main.py"
set "ICON=%SCRIPT_DIR%icons\icon48.png"
set "WORKING_DIR=%SCRIPT_DIR%backend"

powershell -Command "$WSHShell = New-Object -ComObject WScript.Shell; $Shortcut = $WSHShell.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\%SHORTCUT_NAME%'); $Shortcut.TargetPath = 'python'; $Shortcut.Arguments = '"""%TARGET%"""'; $Shortcut.WorkingDirectory = '%WORKING_DIR%'; $Shortcut.IconLocation = '%ICON%'; $Shortcut.Save()" 2>nul

echo.
echo ===========================================
echo  Installation Complete!
echo ===========================================
echo.
echo Native Host registered: com.universalchatbot.bridge
echo Manifest location: %USERPROFILE%\.universalchatbot-host.json
echo Shortcut created on Desktop
echo.
echo Run verify_setup.py to test the installation:
echo   python verify_setup.py
echo.
pause
