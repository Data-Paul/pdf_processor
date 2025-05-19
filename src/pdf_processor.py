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
        "work_experience": ["Beginn", "Ende", "Unternehmen", "Bezeichnung"],
        "skills": ["Gruppe", "Name", "Einstufung"],
        "person_info": ["Name", "Familienname", "Geburtsdatum", "Nationalität"]
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
        if "Name" in headers and "Geburtsdatum" in headers:
            logical_tables["person_info"] = df
        elif "Erlernter Beruf" in headers or "Barcode" in headers:
            logical_tables["job_info"] = df
        elif "Persönliche Eigenschaften" in headers:
            logical_tables["traits_table"] = df
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

            for df in tables:
                table_type = self.classify_table(df)
                df.columns = df.iloc[0]
                df = df[1:].copy()

                if table_type == "unknown":
                    logical_splits = self.extract_logical_tables(df)
                    for subtype, subdf in logical_splits.items():
                        subdf.columns = subdf.iloc[0]
                        subdf = subdf[1:].copy()
                        table_store[subtype].append(subdf)
                else:
                    table_store[table_type].append(df)

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