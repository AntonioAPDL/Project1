import os
import pandas as pd
from openpyxl import load_workbook
from PyPDF2 import PdfReader

# Define your documentation directory
DOC_DIR = "/data/muscat_data/jaguir26/project1_ucsc_phd" 

# List all relevant documentation files
doc_files = [f for f in os.listdir(DOC_DIR) if f.endswith(('.xlsx', '.pdf'))]

print("=== Documentation Files Found ===")
for file in doc_files:
    print(f" - {file}")
print("\n")

# Preview Excel files (show sheet names and first few rows)
for file in doc_files:
    path = os.path.join(DOC_DIR, file)
    if file.endswith('.xlsx'):
        print(f"=== {file} ===")
        try:
            xl = pd.ExcelFile(path)
            print("Sheets:", xl.sheet_names)
            # Preview the first sheet
            df = xl.parse(xl.sheet_names[0])
            print(df.head(5))
        except Exception as e:
            print(f"Error reading {file}: {e}")
        print("\n")

# Preview PDF files (print first page text)
for file in doc_files:
    path = os.path.join(DOC_DIR, file)
    if file.endswith('.pdf'):
        print(f"=== {file} (First Page Preview) ===")
        try:
            reader = PdfReader(path)
            page = reader.pages[0]
            print(page.extract_text()[:1000])  # Print first 1000 characters
        except Exception as e:
            print(f"Error reading {file}: {e}")
        print("\n")
