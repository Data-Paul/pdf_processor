@echo off
echo Installing PDF Processor...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed. Please install Python 3.12 from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM Install required packages
echo Installing required packages...
pip install PyQt5 pandas PyInstaller

REM Create the executable
echo Creating executable...
python -m PyInstaller --clean pdf_processor.spec

echo.
echo Installation complete!
echo The PDF Processor executable can be found in the dist folder.
pause 