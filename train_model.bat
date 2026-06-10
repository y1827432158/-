@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo Continuous Sign Language Recognition Model Training Launcher
echo ========================================
echo.

set "PYTHON_CMD="

if not defined PYTHON_CMD (
    py -3.13 -c "import sys" >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=py -3.13"
)

if not defined PYTHON_CMD (
    py -3.12 -c "import sys" >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=py -3.12"
)

if not defined PYTHON_CMD (
    py -3.11 -c "import sys" >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=py -3.11"
)

if not defined PYTHON_CMD (
    py -3.10 -c "import sys" >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=py -3.10"
)

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    if exist ".venv\Scripts\python.exe" set "PYTHON_CMD=.venv\Scripts\python.exe"
)

if not defined PYTHON_CMD (
    echo Supported Python was not found.
    echo Please install Python 3.10, 3.11, 3.12, or 3.13 and enable "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

call %PYTHON_CMD% start_training.py %*
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
    echo Training launcher failed. Please review the messages above and try again.
    pause
    exit /b %EXIT_CODE%
)

echo Training launcher finished.
pause
