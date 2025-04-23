@echo off
echo Building PDF Processor executable...
pyinstaller --clean pdf_processor.spec
echo Build complete!
echo The executable can be found in the dist folder.
pause 