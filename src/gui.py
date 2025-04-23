import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QFileDialog, 
                            QVBoxLayout, QWidget, QLabel, QProgressBar, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from pdf_processor import PDFProcessor

class PDFProcessorThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, input_dir, output_dir):
        super().__init__()
        self.input_dir = input_dir
        self.output_dir = output_dir

    def run(self):
        try:
            processor = PDFProcessor(self.input_dir, self.output_dir)
            results = processor.process_all_pdfs()
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

class PDFProcessorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Processor")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Input directory selection
        self.input_label = QLabel("Input Directory: Not Selected")
        self.input_button = QPushButton("Select Input Directory")
        self.input_button.clicked.connect(self.select_input_dir)
        
        # Output directory selection
        self.output_label = QLabel("Output Directory: Not Selected")
        self.output_button = QPushButton("Select Output Directory")
        self.output_button.clicked.connect(self.select_output_dir)
        
        # Process button
        self.process_button = QPushButton("Process PDFs")
        self.process_button.clicked.connect(self.start_processing)
        self.process_button.setEnabled(False)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        # Status label
        self.status_label = QLabel("")
        
        # Add widgets to layout
        layout.addWidget(self.input_label)
        layout.addWidget(self.input_button)
        layout.addWidget(self.output_label)
        layout.addWidget(self.output_button)
        layout.addWidget(self.process_button)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        
        self.input_dir = None
        self.output_dir = None
        
    def select_input_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Input Directory")
        if dir_path:
            self.input_dir = dir_path
            self.input_label.setText(f"Input Directory: {dir_path}")
            self.check_process_button()
            
    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            self.output_dir = dir_path
            self.output_label.setText(f"Output Directory: {dir_path}")
            self.check_process_button()
            
    def check_process_button(self):
        self.process_button.setEnabled(bool(self.input_dir and self.output_dir))
            
    def start_processing(self):
        if not self.input_dir or not self.output_dir:
            return
            
        self.process_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Processing...")
        
        # Create worker thread
        self.worker = PDFProcessorThread(self.input_dir, self.output_dir)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.processing_finished)
        self.worker.error.connect(self.processing_error)
        self.worker.start()
        
    def update_progress(self, value):
        self.progress_bar.setValue(value)
        
    def processing_finished(self, results):
        self.process_button.setEnabled(True)
        self.progress_bar.setValue(100)
        
        success_count = sum(1 for r in results.values() if r["status"] == "success")
        total_count = len(results)
        
        self.status_label.setText(f"Processing complete. Successfully processed {success_count} out of {total_count} PDFs.")
        
        QMessageBox.information(self, "Processing Complete", 
                              f"Successfully processed {success_count} out of {total_count} PDFs.\n\n"
                              f"Results have been saved to: {self.output_dir}")
        
    def processing_error(self, error_message):
        self.process_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Error occurred during processing.")
        
        QMessageBox.critical(self, "Processing Error", 
                           f"An error occurred during processing:\n\n{error_message}")

def main():
    app = QApplication(sys.argv)
    window = PDFProcessorGUI()
    window.show()
    sys.exit(app.exec_()) 