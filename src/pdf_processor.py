import os
import re
import pdfplumber
import pandas as pd
from collections import defaultdict
from typing import List, Dict
from datetime import datetime
import logging

class PDFProcessor:
    TABLE_TYPES = {
        "education": ["Beginn", "Ende", "Ausbildung", "Institution"],
        "work_experience": ["Beginn", "Ende", "Unternehmen", "Bezeichnung", "Allg Beschreibung"],
        "skills": ["Gruppe", "Name", "Einstufung"],
        "traits": ["Persönliche Eigenschaften"]
    }

    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('pdf_processor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def flatten_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        # Convert all columns to string and apply the cleaning function
        for col in df.columns:
            df[col] = df[col].map(lambda x: str(x).replace('\n', ' ').strip() if isinstance(x, str) else x)
        return df

    def safe_filename(self, name: str) -> str:
        replacements = {
            'ä': 'ae', 'ö': 'oe', 'ü': 'ue',
            'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue',
            'ß': 'ss'
        }
        for search, replace in replacements.items():
            name = name.replace(search, replace)
        name = re.sub(r'[^a-zA-Z0-9 _-]', '', name)
        return name

    def extract_tables_from_pdf(self, pdf_path: str) -> List[pd.DataFrame]:
        tables = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_tables = page.extract_tables()
                    for tbl in page_tables:
                        df = pd.DataFrame(tbl)
                        df.dropna(how='all', axis=1, inplace=True)
                        df.dropna(how='all', axis=0, inplace=True)
                        if not df.empty:
                            tables.append(df)
        except Exception as e:
            self.logger.error(f"Error extracting tables from {pdf_path}: {str(e)}")
        return tables

    def classify_table(self, df: pd.DataFrame) -> str:
        if df.empty or df.shape[0] < 1:
            return "unknown"
        header = df.iloc[0].astype(str).str.strip().tolist()
        for table_type, known_header in self.TABLE_TYPES.items():
            if all(h in header for h in known_header):
                return table_type
        return "unknown"

    def extract_logical_tables(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        logical_tables = {}
        headers = df.iloc[0].astype(str).str.strip().fillna("").tolist()
        
        # Map both person types to person_info
        if "Name" in headers and "Geburtsdatum" in headers:
            logical_tables["person_info"] = df
        elif "Erlernter Beruf" in headers or "Barcode" in headers:
            logical_tables["person_info"] = df
        elif "Persönliche Eigenschaften" in headers:
            logical_tables["traits"] = df
        else:
            logical_tables["unknown"] = df
        return logical_tables

    def extract_trait_text_from_pdf(self, pdf_path: str) -> str:
        text_blob = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text and "Persönliche Eigenschaften" in text:
                        lines = text.split("\n")
                        for i, line in enumerate(lines):
                            if "Persönliche Eigenschaften" in line:
                                trait_lines = []
                                for following_line in lines[i+1:]:
                                    if following_line.strip() == "" or following_line.strip().endswith(":"):
                                        break
                                    trait_lines.append(following_line.strip())
                                text_blob = " ".join(trait_lines)
                                return text_blob
        except Exception as e:
            self.logger.error(f"Error extracting trait text from {pdf_path}: {str(e)}")
        return ""

    def process_pdf(self, pdf_name: str) -> Dict[str, str]:
        try:
            pdf_path = os.path.join(self.input_dir, pdf_name)
            person_name = self.safe_filename(os.path.splitext(pdf_name)[0].replace("_", " ").strip())
            person_dir = os.path.join(self.output_dir, person_name)
            os.makedirs(person_dir, exist_ok=True)

            tables = self.extract_tables_from_pdf(pdf_path)
            table_store: Dict[str, List[pd.DataFrame]] = defaultdict(list)
            generated_files = []

            previous_classification = None
            previous_table_type = None

            for df in tables:
                table_type = self.classify_table_enhanced(df, previous_classification)
                
                # Check if this is a continuation table
                is_continuation = (table_type == previous_classification and 
                                 table_type in ["work_experience", "education"] and
                                 self._looks_like_data_not_header(df.iloc[0].astype(str).str.strip().tolist()))
                
                if is_continuation:
                    # For continuation tables, DON'T set first row as headers
                    # Just use the data as-is, but we need to match column structure
                    if table_store[table_type]:
                        # Get column structure from previous table of same type
                        previous_df = table_store[table_type][-1]
                        expected_cols = len(previous_df.columns)
                        
                        # Adjust current table to match column count
                        if len(df.columns) != expected_cols:
                            # Pad or trim columns to match
                            while len(df.columns) < expected_cols:
                                df[f'col_{len(df.columns)}'] = ''
                            df = df.iloc[:, :expected_cols]
                        
                        # Set same column names as previous table
                        df.columns = previous_df.columns
                    else:
                        # Fallback: use generic column names
                        df.columns = [f'col_{i}' for i in range(len(df.columns))]
                else:
                    # Normal processing for regular tables (including first table of each type)
                    df.columns = df.iloc[0]
                    df = df[1:].copy()

                if table_type == "unknown":
                    logical_splits = self.extract_logical_tables(df)
                    for subtype, subdf in logical_splits.items():
                        if not is_continuation:  # Only set headers for non-continuation
                            subdf.columns = subdf.iloc[0]
                            subdf = subdf[1:].copy()
                        table_store[subtype].append(subdf)
                else:
                    table_store[table_type].append(df)
                
                previous_classification = table_type
                if not is_continuation:
                    previous_table_type = table_type

            for table_type, dfs in table_store.items():
                if dfs:
                    combined = pd.concat(dfs, ignore_index=True)
                    combined = self.flatten_dataframe(combined)
                    csv_path = os.path.join(person_dir, f"{table_type}.csv")
                    combined.to_csv(csv_path, index=False, sep=";", encoding="utf-8-sig")
                    generated_files.append(f"{table_type}.csv")

            trait_text = self.extract_trait_text_from_pdf(pdf_path)
            if trait_text:
                trait_df = pd.DataFrame([{"text": trait_text}])
                csv_path = os.path.join(person_dir, "traits.csv")
                trait_df.to_csv(csv_path, index=False, sep=";", encoding="utf-8-sig")
                generated_files.append("traits.csv")

            readme_path = os.path.join(person_dir, "README.txt")
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write("🧾 PDF-Profil-Export\n")
                f.write("----------------------\n")
                f.write(f"Source PDF: {pdf_name}\n")
                f.write(f"Erstellt: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
                f.write("Enthaltene CSV-Dateien:\n")
                for file in generated_files:
                    f.write(f"- {file}\n")

            return {
                "status": "success",
                "message": f"Successfully processed {pdf_name}",
                "files": generated_files
            }

        except Exception as e:
            self.logger.error(f"Error processing {pdf_name}: {str(e)}")
            return {
                "status": "error",
                "message": f"Error processing {pdf_name}: {str(e)}",
                "files": []
            }

    def process_all_pdfs(self) -> Dict[str, Dict[str, str]]:
        results = {}
        for filename in os.listdir(self.input_dir):
            if filename.endswith(".pdf"):
                results[filename] = self.process_pdf(filename)
        return results

    def _looks_like_data_not_header(self, row_list: List[str]) -> bool:
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
        return len(patterns) >= 1

    def classify_table_enhanced(self, df: pd.DataFrame, previous_classification: str = None) -> str:
        """Enhanced classification that handles table continuations"""
        if df.empty or df.shape[0] < 1:
            return "unknown"
        
        header = df.iloc[0].astype(str).str.strip().tolist()
        
        # First, try normal classification
        for table_type, known_header in self.TABLE_TYPES.items():
            if all(h in header for h in known_header):
                return table_type
        
        # If unknown, check if it's a continuation
        if self._looks_like_data_not_header(header):
            # Enhanced logic for work_experience continuations
            if previous_classification == "work_experience":
                # Check for empty headers (common continuation pattern)
                empty_count = sum(1 for cell in header if str(cell).strip() in ['', 'nan', 'None'])
                if empty_count >= len(header) * 0.5:  # 50% or more empty
                    return "work_experience"
                
                # Check for work-related content
                work_patterns = any(
                    word in ' '.join(header).lower() 
                    for word in ['unternehmen', 'firma', 'gmbh', 'ag', 'arbeit', 'montage']
                )
                if work_patterns:
                    return "work_experience"
            
            # Enhanced logic for education continuations  
            if previous_classification == "education":
                edu_patterns = any(
                    word in ' '.join(header).lower() 
                    for word in ['schule', 'ausbildung', 'studium', 'universität']
                )
                if edu_patterns:
                    return "education"
        
        return "unknown" 