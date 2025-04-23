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
        results = processor.process_all_pdfs()
        
        # Print results
        for pdf_name, result in results.items():
            print(f"Processing {pdf_name}: {result['status']}")
            if result['status'] == 'error':
                print(f"Error: {result['message']}")
    else:
        # Run GUI version
        gui_main()

if __name__ == "__main__":
    main() 