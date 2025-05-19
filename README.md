# PDF Processor

A Python application that processes PDF files to extract and organize information into structured CSV files.

## Prerequisites

Before running the installation script, please ensure you have:

1. Python 3.13 or later installed
   - Download from [Python's official website](https://www.python.org/downloads/)
   - **Important**: During installation, check "Add Python to PATH"
   - Verify installation by opening a command prompt and typing `python --version`

2. Windows 10 or later operating system

## Installation

The application comes with two batch files for easy installation and building:

### 1. First-time Installation (install.bat)

This script will:
- Check if Python is installed
- Install all required Python packages:
  - PyQt5 (v5.15.10) - For the graphical user interface
  - pandas (v2.2.1) - For data manipulation
  - pdfplumber (v0.10.3) - For PDF processing
  - Flask (v3.0.2) - For web interface
  - python-dotenv (v1.0.1) - For environment variable management
  - PyInstaller - For creating the executable
- Create the executable in the `dist` folder

To install:
1. Double-click `install.bat`
2. Wait for the installation to complete
3. The executable will be created in the `dist` folder

### 2. Rebuilding the Application (build.bat)

Use this script when you:
- Have already installed all dependencies
- Want to rebuild the executable after code changes
- Need to recreate the executable

The script will:
- Clean previous build files
- Create a new executable in the `dist` folder

## Running the Application

1. Navigate to the `dist` folder
2. Double-click `pdf_processor.exe`
3. Use the GUI to:
   - Select input directory containing PDF files
   - Select output directory for processed files
   - Process PDFs and view results

## Output

The application will create:
- A separate folder for each processed PDF
- CSV files containing extracted information
- A README.txt file with processing details

## Troubleshooting

If you encounter any issues:

1. Make sure Python is properly installed and added to PATH
2. Try running `install.bat` again
3. Check the `pdf_processor.log` file for error messages
4. Ensure you have write permissions in the output directory

## Development

If you want to modify the code:
1. Make your changes to the Python files in the `src` directory
2. Run `build.bat` to create a new executable
3. Test the new executable from the `dist` folder

## License

[Your License Information Here]
