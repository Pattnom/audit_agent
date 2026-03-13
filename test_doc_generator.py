# tools/document_generator.py
import os
import pandas as pd
from jinja2 import Template
from weasyprint import HTML
import pdfrw
from datetime import datetime

from pypdf import PdfReader, PdfWriter


TEMPLATE_DIR = "templates"
OUTPUT_DIR = "output"



def flatten_pdf(input_path, output_path):
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    # This merges the form values into the visual layer 
    # and removes the interactive widgets.
    writer.update_page_form_field_values(writer.pages[0], {}, flatten=True)
    
    with open(output_path, "wb") as f:
        writer.write(f)




def fill_cerfa(template_path: str, output_path: str):
    """Fill a fillable PDF CERFA form with data."""
    template_pdf = pdfrw.PdfReader(template_path)
    if not template_pdf.Root.AcroForm:
        raise ValueError("No AcroForm in PDF")
    
    # Prepare field values
    # These field names are examples; you must inspect your CERFA PDF to get the exact names.
    # You can use a tool like Adobe Acrobat or `pdfrw` to list fields.
    field_map = {
        # General identification (adjust as needed)
        "a7.value": "company name", #data.get("company_name", ""),
        "a8": "15 Rue de l'Usine, 75001 Paris",  # you may want to extract from data
        "sie.value": "siret",  #data.get("siret", "")[:9],
        "N° de TVA intracommunautaire": "",  # optional
        # Demand fields (A, B, A-B)
        "a13": "Total",  # str(refund.get("total", 0)),
        "a14": "0",  # we are not imputing, so 0
        "Total": "Total",  # str(refund.get("total", 0)),
        # Signature fields
        "a15b": "Le représentant légal",
    }
    
    for page in template_pdf.pages:
        annotations = page.get('/Annots')
        if not annotations:
            continue
        for annotation in annotations:
            if annotation.get('/Subtype') == '/Widget':
                field_name = annotation.get('/T')
                if field_name:
                    # field_name is a PDF string like "(Nom ou dénomination)"
                    clean_name = field_name[1:-1]  # remove parentheses
                    if clean_name in field_map:
                        value = field_map[clean_name]
                        annotation.update(pdfrw.PdfDict(V=value, AS=value))
    
    pdfrw.PdfWriter().write(output_path, template_pdf)
    



def test_cerfa(template_path, output_path):
    # Data to fill in the form
    data_dict = {
        'a7': 'John',
        
        'a8': '123 Rue de Paris',
        # Add more fields based on your identification step
    }

    # Load the PDF
    template_pdf = pdfrw.PdfReader(template_path)

    # Iterate through pages and annotations
    for page in template_pdf.pages:
        annotations = page.get('/Annots')
        if annotations:
            for annotation in annotations:
                # Target the Field ID via the /T key
                field_name = annotation.get('/T')
                if field_name:
                    # Remove brackets if pdfrw returns them (e.g., (a7))
                    clean_name = field_name.to_unicode()
                    
                    if clean_name in data_dict:
                        # Encode and update the value (/V)
                        annotation.update(pdfrw.PdfDict(
                            V=pdfrw.objects.pdfstring.PdfString.encode(data_dict[clean_name])
                        ))

    # Force appearance generation for Adobe/Chrome viewers
    if template_pdf.Root.AcroForm:
        template_pdf.Root.AcroForm.update(pdfrw.PdfDict(NeedsRendering=pdfrw.PdfName('true')))

    # Save the updated PDF
    pdfrw.PdfWriter().write(output_path, template_pdf)

    out = os.path.join(OUTPUT_DIR, "2040-TIC-REMB-SD_filled_flattened.pdf")
    flatten_pdf(output_path, out)  # Flatten the PDF to make it non-editable


def fill_hierarchical_cerfa(input_path, output_path):

    data_dict = {
        'a7': 'John',
        'a8': '123 Rue de Paris',
        # Add more fields based on your identification step
    }

    reader = pdfrw.PdfReader(input_path)
    
    # 1. Force the viewer to render the values we add
    if not reader.Root.AcroForm:
        reader.Root.AcroForm = pdfrw.PdfDict()
    reader.Root.AcroForm.update(pdfrw.PdfDict(NeedAppearances=pdfrw.PdfObject('true')))

    # 2. Get all fields (even nested ones)
    fields = reader.Root.AcroForm.Fields
    
    for field in fields:
        # Get the field name /T
        field_name = field.get('/T')
        if field_name:
            # Clean name (removes brackets)
            clean_name = field_name.to_unicode()
            
            if clean_name in data_dict:
                # Update the Value (/V)
                field.update(pdfrw.PdfDict(
                    V=pdfrw.objects.pdfstring.PdfString.encode(data_dict[clean_name])
                ))
                # Clear the Appearance (/AP) to force a refresh
                if '/AP' in field:
                    del field['/AP']

    pdfrw.PdfWriter().write(output_path, reader)



#def generate_cerfa_forms(data: dict, refund: dict) -> list:
def generate_cerfa_forms() -> list:
    print(TEMPLATE_DIR)
    """Generate all necessary CERFA forms."""
    forms = []
    # Path to your CERFA template
    remb_path = os.path.join(TEMPLATE_DIR, "CERFA_2040-TIC-REMB-SD.pdf")
    print(remb_path)
    p = os.path.exists(remb_path)
    print(p)
    if os.path.exists(remb_path):
        print(remb_path)
        out = os.path.join(OUTPUT_DIR, "2040-TIC-REMB-SD_filled.pdf")
        print(out)
        #fill_cerfa(remb_path, out)
        fill_hierarchical_cerfa(remb_path, out)
        forms.append(out)
    
    
    # Add other CERFA forms if needed (e.g., 2040-TIC-VA-E-SD)

    # remb_path = os.path.join(TEMPLATE_DIR, "CERFA_2040-TIC-VA-E-SD.pdf")
    # if os.path.exists(remb_path):
    #     out = os.path.join(OUTPUT_DIR, "2040-TIC-VA-E-SD_filled.pdf")
    #     fill_cerfa(remb_path, out)
    #     forms.append(out)

    return forms



if __name__ == "__main__": 
    forms = generate_cerfa_forms()
    print(forms)