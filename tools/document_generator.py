# tools/document_generator.py
import os
import pandas as pd
from jinja2 import Template
from weasyprint import HTML
import pdfrw
from datetime import datetime

TEMPLATE_DIR = "templates"
OUTPUT_DIR = "output"

def generate_claim_letter(data: dict, refund: dict) -> str:
    """Generate PDF claim letter using HTML template."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Compute derived fields if not present
    consumption = data.get("electricity_consumption_mwh", 0)
    electricity_cost = data.get("electricity_cost_euro", 0)
    value_added = data.get("value_added_euro", 0)
    production_share = data.get("production_share_percent", 0)
    
    # Calculate ratio if missing
    if value_added and value_added > 0:
        ratio = (electricity_cost / value_added) * 100
    else:
        ratio = 0
    
    # Calculate accise paid (normal rate 22.5 €/MWh)
    accise_paid = consumption * 22.5
    
    # Reduced rate (0.5 €/MWh for eligible companies)
    reduced_accise = consumption * 0.5
    refund_amount = refund.get("total", consumption * 22)  # fallback to consumption*22
    
    # Prepare template variables
    template_vars = {
        "company_name": data.get("company_name", ""),
        "siret": data.get("siret", ""),
        "naf": data.get("naf_code", ""),
        "date": datetime.now().strftime("%d/%m/%Y"),
        "year": data.get("year", ""),
        "value_added": f"{value_added:,.0f}".replace(",", " "),
        "electricity_cost": f"{electricity_cost:,.0f}".replace(",", " "),
        "ratio": f"{ratio:.2f}",
        "production_share": f"{production_share:.1f}",
        "consumption": f"{consumption:.0f}",
        "accise_paid": f"{accise_paid:,.0f}".replace(",", " "),
        "reduced_accise": f"{reduced_accise:,.0f}".replace(",", " "),
        "refund_amount": f"{refund_amount:,.0f}".replace(",", " "),
    }
    
    with open(os.path.join(TEMPLATE_DIR, "claim_letter_template.html"), "r", encoding="utf-8") as f:
        template_str = f.read()
    template = Template(template_str)
    html = template.render(**template_vars)
    
    out_path = os.path.join(OUTPUT_DIR, "lettre_reclamation.pdf")
    HTML(string=html).write_pdf(out_path)
    return out_path

def generate_summary_table(data: dict, refund: dict) -> str:
    """Generate an Excel table summarizing invoices and refund."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    consumption = data.get("electricity_consumption_mwh", 0)
    normal_rate = 22.5
    reduced_rate = 0.5
    gain_per_mwh = normal_rate - reduced_rate
    total_gain = consumption * gain_per_mwh
    
    rows = [{
        "Période": data.get("year", ""),
        "Consommation (MWh)": consumption,
        "Accise payée (€)": consumption * normal_rate,
        "Taux normal (€/MWh)": normal_rate,
        "Taux réduit (€/MWh)": reduced_rate,
        "Gain (€)": total_gain
    }]
    df = pd.DataFrame(rows)
    out_path = os.path.join(OUTPUT_DIR, "tableau_recap.xlsx")
    df.to_excel(out_path, index=False)
    return out_path

def fill_cerfa(template_path: str, data: dict, refund: dict, output_path: str):

    """Fill a fillable PDF CERFA form with data."""
    # Prepare field values
    # These field names are examples; you must inspect your CERFA PDF to get the exact names.
    # You can use a tool like Adobe Acrobat or `pdfrw` to list fields.
    field_map = {
        # General identification (adjust as needed)
        "a7": data.get("company_name", ""),
        "a8": data.get("company_address", ""),  # you may want to extract from data
        "sie": data.get("siret", "")[:9],
        #"N° de TVA intracommunautaire": "",  # optional
        # Demand fields (A, B, A-B)
        "a13": str(refund.get("total", 0)),
        "a14": "0",  # we are not imputing, so 0
        "Total": str(refund.get("total", 0)),
        # Signature fields
        "a15b": "Le représentant légal",
    }
    
    template_pdf = pdfrw.PdfReader(template_path)
    
    # 1. Force the viewer to render the values we add
    if not template_pdf.Root.AcroForm:
        template_pdf.Root.AcroForm = pdfrw.PdfDict()
    template_pdf.Root.AcroForm.update(pdfrw.PdfDict(NeedAppearances=pdfrw.PdfObject('true')))

    # 2. Get all fields (even nested ones)
    fields = template_pdf.Root.AcroForm.Fields
    
    for field in fields:
        # Get the field name /T
        field_name = field.get('/T')
        if field_name:
            # Clean name (removes brackets)
            clean_name = field_name.to_unicode()
            
            if clean_name in field_map:
                # Update the Value (/V)
                field.update(pdfrw.PdfDict(
                    V=pdfrw.objects.pdfstring.PdfString.encode(field_map[clean_name])
                ))
                # Clear the Appearance (/AP) to force a refresh
                if '/AP' in field:
                    del field['/AP']

    pdfrw.PdfWriter().write(output_path, template_pdf)
    
    



def generate_cerfa_forms(data: dict, refund: dict) -> list:
    
    """Generate all necessary CERFA forms."""
    forms = []
    # Path to your CERFA template
    remb_path = os.path.join(TEMPLATE_DIR, "CERFA_2040-TIC-REMB-SD.pdf")
    
    if os.path.exists(remb_path):
       
        out = os.path.join(OUTPUT_DIR, "2040-TIC-REMB-SD_filled.pdf")
        
        fill_cerfa(remb_path, data, refund, out)
        
        forms.append(out)
    
    
    # Add other CERFA forms if needed (e.g., 2040-TIC-VA-E-SD)

    # remb_path = os.path.join(TEMPLATE_DIR, "CERFA_2040-TIC-VA-E-SD.pdf")
    # if os.path.exists(remb_path):
    #     out = os.path.join(OUTPUT_DIR, "2040-TIC-VA-E-SD_filled.pdf")
    #     fill_cerfa(remb_path, data, refund, out)
    #     forms.append(out)

    return forms

def generate_all_documents(data: dict, refund: dict) -> dict:
    """Generate all documents and return paths."""
    docs = {}
    docs["claim_letter"] = generate_claim_letter(data, refund)
    docs["summary_table"] = generate_summary_table(data, refund)
    docs["cerfa_forms"] = generate_cerfa_forms(data, refund)
    return docs

