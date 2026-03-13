import os
import random
from fpdf import FPDF
import pandas as pd
from datetime import datetime

# Create output directory
output_dir = "test_company"
os.makedirs(output_dir, exist_ok=True)

# Helper to create a simple PDF with text
def create_pdf(filename, title, lines):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=title, ln=True, align='C')
    pdf.ln(10)
    for line in lines:
        pdf.multi_cell(0, 10, txt=line)
    pdf.output(os.path.join(output_dir, filename))

# 1. Kbis (company registration)
company_name = "SARL TRANSFORM INDUSTRIE"
siret = "12345678901234"
naf_code = "10.71A"  # Boulangerie industrielle (eligible)
address = "15 Rue de l'Usine, 75001 Paris"
create_pdf("Kbis.pdf", "EXTRAIT K BIS", [
    f"SIRET: {siret}",
    f"Code NAF: {naf_code}",
    f"Dénomination: {company_name}",
    f"Adresse: {address}",
    "Date d'immatriculation: 01/01/2010",
    "Forme juridique: SARL",
    "Capital: 100 000 EUR"
])

# 2. Electricity invoices 2024 (2 invoices)
total_consumption_kwh = 120000  # 120 MWh
total_excise_paid = total_consumption_kwh * 22.5 / 1000  # 22.5 EUR/MWh → 2700 EUR
invoice_data = []
invoice1_kwh = 60000
invoice2_kwh = 60000
invoice1_amount = 7500  # total HT including energy + excise
invoice2_amount = 7500


def create_invoice(filename, period, consumption_kwh, amount_ht):
    lines = [
        f"Facture d'électricité - Période: {period}",
        f"Consommation: {consumption_kwh} kWh",
        f"Total HT: {amount_ht} EUR",  # changed from EUR to EUR
        "Détail des taxes:",
        f"  Accise (TICFE): {consumption_kwh * 22.5 / 1000:.2f} EUR",  # changed
        f"  TVA: {amount_ht * 0.2:.2f} EUR",  # changed
        "Net à payer: {:.2f} EUR".format(amount_ht * 1.2)  # changed
    ]
    create_pdf(filename, "FACTURE D'ÉLECTRICITÉ", lines)


create_invoice("facture_elec_2024_01.pdf", "Janvier-Juin 2024", invoice1_kwh, invoice1_amount)
create_invoice("facture_elec_2024_02.pdf", "Juillet-Décembre 2024", invoice2_kwh, invoice2_amount)

# 3. Liasse fiscale (tax return) 2024
value_added = 1500000  # 1.5 million EUR
create_pdf("liasse_fiscale_2024.pdf", "LIASSE FISCALE 2024 (extrait)", [
    "Formulaire 2050 - Bilan",
    "..." ,
    "Valeur ajoutée (case VA): {:,} EUR".format(value_added).replace(',', ' '),
    "..." ,
    "Résultat fiscal: ..."
])

# 4. Technical description
production_share = 85  # percent
process_desc = (
    "L'entreprise fabrique des produits de boulangerie industrielle. "
    "Le processus comprend le pétrissage, la fermentation, la cuisson et l'emballage. "
    "Les équipements principaux : fours électriques (200 kW), pétrins (50 kW), ligne de conditionnement (80 kW). "
    "Les bureaux et espaces de stockage représentent environ 15% de la consommation totale."
)
create_pdf("description_technique.pdf", "DESCRIPTION DU PROCESS INDUSTRIEL", [
    process_desc,
    "",
    f"Part estimée de la consommation affectée à la production : {production_share} %",
    "Méthode d'estimation : relevés de compteurs divisionnaires.",
    "Plan du site avec zones de production joint."
])

# 5. Proof of production share (Excel)
equipment_data = [
    ["Zone", "Équipement", "Puissance (kW)", "Heures/an", "Consommation (kWh)"],
    ["Production", "Four électrique", 200, 4000, 800000],
    ["Production", "Pétrin", 50, 3000, 150000],
    ["Production", "Ligne conditionnement", 80, 3500, 280000],
    ["Bureaux", "Éclairage, informatique", 30, 2000, 60000],
    ["Stockage", "Éclairage, froid", 25, 3000, 75000]
]
df = pd.DataFrame(equipment_data[1:], columns=equipment_data[0])
df["Consommation (kWh)"] = df["Consommation (kWh)"].astype(int)
# Add totals
total_prod = df[df["Zone"]=="Production"]["Consommation (kWh)"].sum()
total_all = df["Consommation (kWh)"].sum()
ratio = total_prod / total_all * 100
df.loc[len(df)] = ["TOTAL PRODUCTION", "", "", "", total_prod]
df.loc[len(df)] = ["TOTAL TOUS", "", "", "", total_all]
df.loc[len(df)] = ["% PRODUCTION", "", "", "", f"{ratio:.1f}%"]
df.to_excel(os.path.join(output_dir, "repartition_consommations.xlsx"), index=False)

print(f"✅ Test files generated in '{output_dir}' folder.")
print("Files:")
for f in os.listdir(output_dir):
    print(f"  - {f}")