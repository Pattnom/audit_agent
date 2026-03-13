import os
import pdfplumber
import pandas as pd
from PIL import Image
import pytesseract

def parse_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def parse_excel(file_path):
    df = pd.read_excel(file_path, sheet_name=None, header=None)
    text = ""
    for sheet_name, sheet_df in df.items():
        text += f"Sheet: {sheet_name}\n"
        text += sheet_df.to_string(index=False, header=False) + "\n"
    return text

def parse_image(file_path):
    image = Image.open(file_path)
    text = pytesseract.image_to_string(image, lang='fra')
    return text

def parse_uploaded_files(files):
    results = {}
    MAX_LEN = 2000  # characters per file
    for file_path in files:
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == '.pdf':
                text = parse_pdf(file_path)
            elif ext in ['.xls', '.xlsx']:
                text = parse_excel(file_path)
            elif ext in ['.jpg', '.jpeg', '.png', '.tiff']:
                text = parse_image(file_path)
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
        
            print(f"--- {file_path} ---\n{text[:500]}...\n")
        
        except Exception as e:
            text = f"Error reading file {file_path}: {str(e)}"
        if len(text) > MAX_LEN:
            text = text[:MAX_LEN] + "\n...[truncated]"
        results[file_path] = text
    return results