# Save this as detect_table_continuations.py 
import os
import sys
sys.path.append('src')

import pandas as pd
from pdf_processor import PDFProcessor

def looks_like_data_not_header(row_list):
    """Detect if a 'header' row is actually data"""
    patterns = []
    
    # Check if mostly empty (common for continuation tables)
    empty_count = sum(1 for cell in row_list if str(cell).strip() in ['', 'nan', 'None'])
    if empty_count >= len(row_list) * 0.6:  # 60% or more empty
        patterns.append("mostly_empty")
    
    for cell in row_list:
        cell_str = str(cell).strip()
        
        # Skip empty cells
        if cell_str in ['', 'nan', 'None']:
            continue
        
        # Check for year patterns (like "2007.0", "2015.0")
        if cell_str.replace('.', '').replace('-', '').isdigit() and len(cell_str) >= 4:
            patterns.append("year")
        
        # Check for company names (contains common business words)
        business_words = ['GmbH', 'AG', 'Co', 'KG', 'Ltd', 'Inc', 'Corp']
        if any(word in cell_str for word in business_words):
            patterns.append("company")
        
        # Check for job descriptions (longer text, contains specific terms)
        job_words = ['arbeiten', 'montage', 'technik', 'mechaniker', 'elektriker']
        if any(word.lower() in cell_str.lower() for word in job_words):
            patterns.append("job_desc")
    
    # If we found typical continuation patterns
    return len(patterns) >= 1  # Lowered threshold since empty headers are common

def classify_table_with_continuation(df, previous_classification=None):
    """Enhanced classification that handles table continuations"""
    if df.empty or df.shape[0] < 1:
        return "unknown"
    
    header = df.iloc[0].astype(str).str.strip().tolist()
    
    # First, try normal classification
    processor = PDFProcessor(".", ".")
    normal_classification = processor.classify_table(df)
    
    if normal_classification != "unknown":
        return normal_classification
    
    # If unknown, check if it's a continuation
    if looks_like_data_not_header(header):
        print(f"🔍 Detected data-like header: {header[:2]}...")
        
        # Enhanced logic for work_experience continuations
        if previous_classification == "work_experience":
            # Check for empty headers (common continuation pattern)
            empty_count = sum(1 for cell in header if str(cell).strip() in ['', 'nan', 'None'])
            if empty_count >= len(header) * 0.5:  # 50% or more empty
                print(f"   ✅ Classified as continuation of work_experience (empty headers)")
                return "work_experience"
            
            # Check for work-related content
            work_patterns = any(
                word in ' '.join(header).lower() 
                for word in ['unternehmen', 'firma', 'gmbh', 'ag', 'arbeit', 'montage']
            )
            if work_patterns:
                print(f"   ✅ Classified as continuation of work_experience (work content)")
                return "work_experience"
        
        # Enhanced logic for education continuations  
        if previous_classification == "education":
            edu_patterns = any(
                word in ' '.join(header).lower() 
                for word in ['schule', 'ausbildung', 'studium', 'universität']
            )
            if edu_patterns:
                print(f"   ✅ Classified as continuation of education")
                return "education"
    
    return "unknown"

def list_all_pdfs():
    input_dir = "input"
    pdf_files = [f for f in os.listdir(input_dir) if f.endswith('.pdf')]
    
    print("📁 All PDF files in input/:")
    for pdf in sorted(pdf_files):
        print(f"   {pdf}")
    
    return pdf_files

def test_continuation_detection():
    input_dir = "input"
    
    # First, list all PDFs
    all_pdfs = list_all_pdfs()
    
    # Find PDFs that had continuation issues from your debug output
    problem_names = ["Dziedziel Mariusz", "Eich Oliver"]
    problem_pdfs = [pdf for pdf in all_pdfs 
                   if any(name in pdf for name in problem_names)]
    
    if not problem_pdfs:
        print(f"\n🔍 Testing first 3 PDFs:")
        problem_pdfs = all_pdfs[:3]
    
    for pdf_file in problem_pdfs:
        pdf_path = os.path.join(input_dir, pdf_file)
        if not os.path.exists(pdf_path):
            print(f"❌ PDF not found: {pdf_file}")
            continue
            
        print(f"\n🔍 Testing continuation detection: {pdf_file}")
        print("="*60)
        
        processor = PDFProcessor(".", ".")
        tables = processor.extract_tables_from_pdf(pdf_path)
        
        previous_classification = None
        
        for i, df in enumerate(tables, 1):
            if not df.empty:
                header = df.iloc[0].astype(str).str.strip().tolist()
                
                # Test enhanced classification
                classification = classify_table_with_continuation(df, previous_classification)
                
                print(f"TABLE {i}: {classification}")
                print(f"   Header: {header[:3]}...")
                
                # Show if data-like pattern detected
                if looks_like_data_not_header(header):
                    print(f"   🚨 DETECTED: Data-like header pattern!")
                
                previous_classification = classification

if __name__ == "__main__":
    test_continuation_detection()