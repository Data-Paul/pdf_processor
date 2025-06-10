import os
import sys
sys.path.append('src')

import pdfplumber
import pandas as pd
from pdf_processor import PDFProcessor

def debug_pdf_structure(pdf_path):
    print(f"🔍 Debugging PDF: {pdf_path}")
    print("="*60)
    
    # Extract tables
    tables = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"\n📄 PAGE {page_num}:")
                page_tables = page.extract_tables()
                
                for table_num, tbl in enumerate(page_tables, 1):
                    if tbl:
                        df = pd.DataFrame(tbl)
                        df.dropna(how='all', axis=1, inplace=True)
                        df.dropna(how='all', axis=0, inplace=True)
                        
                        if not df.empty:
                            print(f"\n  📊 TABLE {table_num}:")
                            print(f"     Size: {df.shape[0]} rows x {df.shape[1]} columns")
                            
                            # Show first few rows
                            print(f"     First 3 rows:")
                            for i in range(min(3, len(df))):
                                row_data = df.iloc[i].astype(str).str.strip().tolist()
                                print(f"       Row {i}: {row_data}")
                            
                            # Check if any row contains our target fields
                            for i, row in df.iterrows():
                                row_str = ' '.join(row.astype(str).str.strip().tolist())
                                if any(term in row_str for term in ["Erlernte", "Beruf", "Barcode"]):
                                    print(f"     🎯 Found target data in row {i}: {row_str}")
                            
                            tables.append(df)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return []
    
    return tables

def test_classification(tables):
    print(f"\n🧠 TESTING CLASSIFICATION:")
    print("="*60)
    
    processor = PDFProcessor(".", ".")
    
    for i, df in enumerate(tables, 1):
        print(f"\n📊 TABLE {i}:")
        
        # Show what classify_table sees
        if not df.empty:
            header = df.iloc[0].astype(str).str.strip().tolist()
            print(f"   Header row: {header}")
            
            classification = processor.classify_table(df)
            print(f"   Classification: {classification}")
            
            if classification == "unknown":
                print(f"   🔍 Checking logical tables...")
                logical_tables = processor.extract_logical_tables(df)
                for subtype, subdf in logical_tables.items():
                    print(f"      → {subtype}: {subdf.shape}")

def main():
    input_dir = "input"
    
    # Find PDF files
    pdf_files = [f for f in os.listdir(input_dir) if f.endswith('.pdf')]
    
    if not pdf_files:
        print("❌ No PDF files found in input/ directory")
        return
    
    # Debug each PDF
    for pdf_file in pdf_files:
        pdf_path = os.path.join(input_dir, pdf_file)
        tables = debug_pdf_structure(pdf_path)
        test_classification(tables)
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
