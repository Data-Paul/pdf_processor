import os
import re
import pdfplumber
import pandas as pd
from collections import defaultdict
from typing import List, Dict
from datetime import datetime
import logging
import shutil

class PDFProcessor:
    TABLE_TYPES = {
        "education": ["Beginn", "Ende", "Ausbildung", "Institution"],
        "work_experience": ["Beginn", "Ende", "Unternehmen", "Bezeichnung", "Allg Beschreibung"],
        "skills": ["Gruppe", "Name", "Einstufung"],
        "traits": ["Name", "Familienname", "Geburstag", "Natinalität","Persönliche Eigenschaften","Erlernter Beruf", "Barcode"]
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

    def clean_output_directory(self):
        """Clean the output directory before processing"""
        if os.path.exists(self.output_dir):
            for file in os.listdir(self.output_dir):
                file_path = os.path.join(self.output_dir, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    self.logger.error(f"Error deleting {file_path}: {e}")

    def get_single_pdf_file(self) -> str:
        """Get the first PDF file from the input directory"""
        pdf_files = [f for f in os.listdir(self.input_dir) if f.lower().endswith('.pdf')]
        if pdf_files:
            return pdf_files[0]
        return None

    def flatten_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        # Convert all columns to string and apply the cleaning function
        for col in df.columns:
            self.logger.info(f"Flattening column: {col}")
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

    def is_personal_info_table(self, df: pd.DataFrame) -> bool:
        """Check if table contains personal information headers"""
        if df.empty or df.shape[0] < 1:
            return False
        header = df.iloc[0].astype(str).str.strip().tolist()
        
        # Check for personal info headers
        personal_headers = ["Name", "Familienname", "Geburstag", "Natinalität"]
        return all(h in header for h in personal_headers)

    def is_occupation_table(self, df: pd.DataFrame) -> bool:
        """Check if table contains occupation information"""
        if df.empty or df.shape[0] < 1:
            return False
        header = df.iloc[0].astype(str).str.strip().tolist()
        
        # Check for occupation headers
        occupation_headers = ["Erlernter Beruf", "Barcode"]
        return any(h in header for h in occupation_headers)

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

    def process_single_pdf(self) -> Dict[str, str]:
        """Process a single PDF file from the input directory"""
        # Clean output directory first
        self.clean_output_directory()
        
        # Get the PDF file
        pdf_name = self.get_single_pdf_file()
        if not pdf_name:
            return None
            
        try:
            pdf_path = os.path.join(self.input_dir, pdf_name)
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

                # Special handling for personal info and occupation tables
                if table_type == "unknown":
                    if self.is_personal_info_table(df):
                        table_store["traits"].append(df)
                    elif self.is_occupation_table(df):
                        table_store["traits"].append(df)
                    else:
                        # Only add to unknown if it's not personal info or occupation
                        table_store["unknown"].append(df)
                else:
                    table_store[table_type].append(df)
                
                previous_classification = table_type
                if not is_continuation:
                    previous_table_type = table_type

            # Save CSV files directly to output directory (no subfolders)
            for table_type, dfs in table_store.items():
                if dfs:
                    combined = pd.concat(dfs, ignore_index=True)
                    combined = self.flatten_dataframe(combined)
                    csv_path = os.path.join(self.output_dir, f"{table_type}.csv")
                    combined.to_csv(csv_path, index=False, sep=";", encoding="utf-8-sig")
                    generated_files.append(f"{table_type}.csv")

            # Handle traits text and add it to traits.csv
            trait_text = self.extract_trait_text_from_pdf(pdf_path)
            if trait_text:
                # If traits.csv already exists, add the text as a new column
                traits_csv_path = os.path.join(self.output_dir, "traits.csv")
                if os.path.exists(traits_csv_path):
                    # Read existing traits.csv and add the text column
                    existing_traits = pd.read_csv(traits_csv_path, sep=";", encoding="utf-8-sig")
                    existing_traits["Persönliche Eigenschaften"] = trait_text
                    existing_traits.to_csv(traits_csv_path, index=False, sep=";", encoding="utf-8-sig")
                else:
                    # Create new traits.csv with just the text
                    trait_df = pd.DataFrame([{"Persönliche Eigenschaften": trait_text}])
                    trait_df.to_csv(traits_csv_path, index=False, sep=";", encoding="utf-8-sig")
                    generated_files.append("traits.csv")

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