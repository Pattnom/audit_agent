import streamlit as st
import asyncio
import tempfile
import os
import zipfile
from pathlib import Path

# Importer les fonctions de l'agent (adapter les chemins si nécessaire)
from tools.file_parser import parse_uploaded_files
from tools.data_extractor import extract_company_data
from tools.classifier import classify_naf
from tools.eligibility import check_electricity_eligibility, check_gas_eligibility
from tools.calculator import calculate_refund
from tools.document_generator import generate_all_documents

# Configuration de la page
st.set_page_config(page_title="Audit Accise Électricité/Gaz", layout="wide")
st.title("⚡ Assistant de réclamation d'accise (électricité & gaz)")

# Initialisation de l'historique de chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Déposez les fichiers nécessaires (Kbis, factures, liasses fiscales, justificatifs techniques…). Je les analyserai et générerai les documents de réclamation."}
    ]

# Affichage des messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Widget de téléchargement de fichiers
uploaded_files = st.file_uploader(
    "Choisissez les fichiers",
    type=["pdf", "xlsx", "jpg", "jpeg", "png"],
    accept_multiple_files=True,
    key="uploader"
)

# Bouton pour lancer l'analyse
if st.button("Lancer l'analyse") and uploaded_files:
    with st.chat_message("user"):
        st.markdown(f"Fichiers déposés : {', '.join([f.name for f in uploaded_files])}")
    st.session_state.messages.append({"role": "user", "content": f"Fichiers déposés : {', '.join([f.name for f in uploaded_files])}"})

    # Créer un dossier temporaire pour stocker les fichiers
    with tempfile.TemporaryDirectory() as tmpdir:
        file_paths = []
        for uploaded_file in uploaded_files:
            # Sauvegarder chaque fichier dans le dossier temporaire
            file_path = Path(tmpdir) / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            file_paths.append(str(file_path))

        # Afficher un message de progression
        with st.chat_message("assistant"):
            with st.spinner("Analyse en cours..."):
                # Étape 1 : parser les fichiers
                parsed_texts = parse_uploaded_files(file_paths)

                # Étape 2 : extraire les données structurées (appel Gemini)
                data = extract_company_data(parsed_texts)

                # Étape 3 : classifier le code NAF
                profile = classify_naf(data.get("naf_code", ""))
                if profile == "ineligible":
                    st.error("L'entreprise n'est pas éligible (code NAF hors scope).")
                    st.stop()

                # Étape 4 : vérifier l'éligibilité
                eligibility = {}
                if profile in ["industrie", "artisan"]:
                    eligibility["electricity"] = check_electricity_eligibility(data)
                if data.get("gas_consumption_mwh"):
                    eligibility["gas"] = check_gas_eligibility(data)

                # Vérifier si au moins une énergie est éligible
                if not any(elig.get("eligible", False) for elig in eligibility.values()):
                    st.error("L'entreprise ne remplit pas les critères d'éligibilité.")
                    st.stop()

                # Étape 5 : calculer le remboursement
                refund = calculate_refund(profile, data, eligibility)

                # Étape 6 : générer les documents
                docs = generate_all_documents(data, refund)

            # Afficher le résultat
            st.success(f"Analyse terminée. Montant du remboursement estimé : {refund.get('total', 0):,.0f} €".replace(",", " "))
            st.session_state.messages.append({"role": "assistant", "content": f"Remboursement estimé : {refund.get('total', 0):,.0f} €".replace(",", " ")})

            # Proposer les fichiers en téléchargement
            st.markdown("### 📄 Documents générés")
            col1, col2, col3 = st.columns(3)

            # Lettre de réclamation
            if "claim_letter" in docs:
                with open(docs["claim_letter"], "rb") as f:
                    col1.download_button(
                        label="📥 Lettre de réclamation (PDF)",
                        data=f,
                        file_name=os.path.basename(docs["claim_letter"]),
                        mime="application/pdf"
                    )

            # Tableau récapitulatif
            if "summary_table" in docs:
                with open(docs["summary_table"], "rb") as f:
                    col2.download_button(
                        label="📥 Tableau récapitulatif (Excel)",
                        data=f,
                        file_name=os.path.basename(docs["summary_table"]),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            # CERFA (premier formulaire, s'il existe)
            if docs.get("cerfa_forms") and len(docs["cerfa_forms"]) > 0:
                cerfa_path = docs["cerfa_forms"][0]
                with open(cerfa_path, "rb") as f:
                    col3.download_button(
                        label="📥 CERFA pré‑rempli (PDF)",
                        data=f,
                        file_name=os.path.basename(cerfa_path),
                        mime="application/pdf"
                    )

            # Option : créer une archive ZIP de tous les documents
            zip_path = os.path.join(tmpdir, "documents.zip")
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for key, path in docs.items():
                    if key == "cerfa_forms":
                        for p in path:
                            zipf.write(p, arcname=os.path.basename(p))
                    elif isinstance(path, str) and os.path.exists(path):
                        zipf.write(path, arcname=os.path.basename(path))
            with open(zip_path, "rb") as f:
                st.download_button(
                    label="📦 Tout télécharger (ZIP)",
                    data=f,
                    file_name="documents_reclamation.zip",
                    mime="application/zip"
                )