@echo off
echo Installing PDF Processor...
echo.

REM Check if Python is installed and show which one
echo Checking Python installation...
python --version
where python
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
python -m pip install --upgrade pip
python -m pip install PyQt5==5.15.10 pandas==2.2.1 PyInstaller pdfplumber==0.10.3 Flask==3.0.2 python-dotenv==1.0.1

REM Verify installation
echo.
echo Verifying package installation...
python -c "import pdfplumber; print('pdfplumber version:', pdfplumber.__version__)"
python -c "import PyQt5; print('PyQt5 version:', PyQt5.QtCore.QT_VERSION_STR)"
echo.

REM Create the executable
echo Creating executable...
python -m PyInstaller --clean pdf_processor.spec

echo.
echo Installation complete!
echo The PDF Processor executable can be found in the dist folder.
pause 