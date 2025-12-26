@echo off
REM ZIMON Launcher Script
REM This script activates the virtual environment and runs ZIMON

echo Starting ZIMON...
echo.

REM Navigate to parent directory where .venv is located
cd /d "%~dp0\.."

REM Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo Virtual environment activated.
    echo.
    
    REM Navigate back to ZEBB_code directory
    cd ZEBB_code
    
    REM Run the application
    python main.py
) else (
    echo Error: Virtual environment not found at .venv
    echo Please create a virtual environment first.
    pause
    exit /b 1
)

