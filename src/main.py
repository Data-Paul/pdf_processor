import os
import sys
from gui import main as gui_main
from pdf_processor import PDFProcessor

def main():
    # Check if running in Docker
    if os.getenv('DOCKER_ENV'):
        input_dir = os.getenv('INPUT_DIR', '/data/input')
        output_dir = os.getenv('OUTPUT_DIR', '/data/output')
        
        processor = PDFProcessor(input_dir, output_dir)
        results = processor.process_single_pdf()
        
        # Print results
        if results:
            print(f"Processing result: {results['status']}")
            if results['status'] == 'error':
                print(f"Error: {results['message']}")
        else:
            print("No PDF file found to process")
    else:
        # Run GUI version
        gui_main()

if __name__ == "__main__":
    main() 