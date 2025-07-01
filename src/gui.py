import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, 
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
            results = processor.process_single_pdf()
            if results:
                self.finished.emit(results)
            else:
                self.error.emit("Keine PDF-Datei im Profil_PDF Ordner gefunden!")
        except Exception as e:
            self.error.emit(str(e))

class PDFProcessorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Processor")
        self.setGeometry(100, 100, 400, 200)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Fixed folder paths (placeholders/platzhalter)
        self.input_dir = r"C:\Users\paulh\Desktop\Codersbay\pdf_pro\pdf_processor\dist\Profil_PDF"  # Fixed folder name
        self.output_dir = r"C:\Users\paulh\Desktop\Codersbay\pdf_pro\pdf_processor\dist\Profil_CSV"  # Fixed folder name
        
        # Status labels
        self.input_label = QLabel(f"Input Directory: {self.input_dir}")
        self.output_label = QLabel(f"Output Directory: {self.output_dir}")
        
        # Process button
        self.process_button = QPushButton("PDF verarbeiten")
        self.process_button.clicked.connect(self.start_processing)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        # Status label
        self.status_label = QLabel("Bereit zur Verarbeitung")
        
        # Add widgets to layout
        layout.addWidget(self.process_button)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        
    def start_processing(self):
        # Create directories if they don't exist
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Check if there's a PDF file in the input directory
        pdf_files = [f for f in os.listdir(self.input_dir) if f.lower().endswith('.pdf')]
        if not pdf_files:
            QMessageBox.warning(self, "Keine PDF-Datei", 
                              f"Keine PDF-Datei im Ordner '{self.input_dir}' gefunden!")
            return
            
        self.process_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Verarbeite PDF...")
        
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
        
        if results["status"] == "success":
            # Get the PDF filename for the confirmation message
            pdf_files = [f for f in os.listdir(self.input_dir) if f.lower().endswith('.pdf')]
            if pdf_files:
                pdf_name = os.path.splitext(pdf_files[0])[0]
                QMessageBox.information(self, "Verarbeitung erfolgreich", 
                                      f"Profil Daten {pdf_name} erfolgreich verarbeitet!")
            
            self.status_label.setText("Verarbeitung abgeschlossen")
        else:
            self.status_label.setText("Fehler bei der Verarbeitung")
            QMessageBox.critical(self, "Verarbeitungsfehler", 
                               f"Fehler: {results['message']}")
        
    def processing_error(self, error_message):
        self.process_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Fehler aufgetreten")
        
        QMessageBox.critical(self, "Verarbeitungsfehler", 
                           f"Ein Fehler ist aufgetreten:\n\n{error_message}")

def main():
    app = QApplication(sys.argv)
    window = PDFProcessorGUI()
    window.show()
    sys.exit(app.exec_()) 