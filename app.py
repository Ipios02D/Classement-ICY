import streamlit as st
import pandas as pd
import numpy as np
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURATION (Identique) ---
STRUCTURE_COURS = {
    "ING05-ICY-LSH1": {"Anglais": 2.0, "RSE": 0.5, "Org. Entreprises": 0.5, "Comptabilité": 0.5, "Gestion Projet": 1.0, "APSA (Sport)": 0.5},
    "ING05-ICY-Maths": {"Analyse Appliquée": 1.5, "Proba & Stats": 2.0, "Analyse Numérique": 1.5},
    "ING05-ICY-Archi": {"Archi Système": 2.0, "Prog Système": 2.0},
    "ING05-ICY-Securite": {"BDD Système": 2.0, "RGPD": 1.0},
    "ING05-ICY-Optimisation": {"Prog Linéaire": 1.5, "Complexité": 1.5},
    "ING05-ICY-DevApp": {"Langage C (Niv 2)": 2.0, "POO Java": 2.0, "Dev Web 1": 2.0},
    "ING05-ICY-SAE": {"Projet Web": 3.0}
}

COLONNES_MATIERES = []
for ue, matieres in STRUCTURE_COURS.items():
    for matiere in matieres.keys():
        COLONNES_MATIERES.append(f"{ue} | {matiere}")

def calculer_moyennes(row):
    """Fonction de calcul inchangée"""
    resultats = {}
    total_general_points = 0
    total_general_coefs = 0
    
    for ue, matieres in STRUCTURE_COURS.items():
        ue_points = 0
        ue_coefs = 0
        for matiere, coef in matieres.items():
            col_name = f"{ue} | {matiere}"
            valeur = row.get(col_name)
            if pd.notna(valeur):
                ue_points += valeur * coef
                ue_coefs += coef
        
        if ue_coefs > 0:
            moyenne_ue = ue_points / ue_coefs
            resultats[ue] = moyenne_ue
            total_general_points += moyenne_ue * ue_coefs 
            total_general_coefs += ue_coefs
        else:
            resultats[ue] = np.nan

    if total_general_coefs > 0:
        resultats["Moyenne_Generale"] = total_general_points / total_general_coefs
    else:
        resultats["Moyenne_Generale"] = np.nan
        
    return pd.Series(resultats)

# --- INTERFACE ---
st.set_page_config(page_title="Classement ING05 (Live)", layout="wide")
st.title("🎓 Classement ING05 - Données en Temps Réel")

# Bouton de rafraîchissement manuel
if st.button("🔄 Actualiser les données depuis Google Sheets"):
    st.cache_data.clear()

# --- CONNEXION BASE DE DONNÉES ---
# Crée une connexion au Google Sheet
conn = st.connection("gsheets", type=GSheetsConnection)
url_sheet = "https://docs.google.com/spreadsheets/d/1wgSA92nA7YnQ5_bSfiiPv8DqtOXOb34u3uT6OdiVSzs/edit?usp=sharing"

try:
    # Lire les données (ttl=0 signifie pas de cache long, pour voir les modifs vite)
    df_input = conn.read(spreadsheet=url_sheet, ttl=10)
    
    # Vérification que la colonne Nom existe
    if "Nom" not in df_input.columns:
        st.error("Le Google Sheet doit contenir une colonne 'Nom'.")
        st.stop()
        
except Exception as e:
    st.error(f"Erreur de connexion au Google Sheet : {e}")
    st.stop()

# --- CALCULS ---
if not df_input.empty:
    with st.spinner('Calcul des classements en cours...'):
        # On force les colonnes de notes en numérique au cas où il y ait du texte
        cols_notes = [c for c in df_input.columns if c != "Nom"]
        for c in cols_notes:
            df_input[c] = pd.to_numeric(df_input[c], errors='coerce')

        # Calcul
        df_calc = df_input.apply(calculer_moyennes, axis=1)
        df_final = pd.concat([df_input[["Nom"]], df_calc], axis=1)
        
        # Rang
        df_final['Rang'] = df_final['Moyenne_Generale'].rank(ascending=False, na_option='bottom', method='min')
        df_final = df_final.sort_values('Rang')

        # --- AFFICHAGE GENERAL ---
        st.success("Données synchronisées !")
        
        st.subheader("🏆 Classement Général (Top Promo)")
        # Mise en forme
        style_cols = list(STRUCTURE_COURS.keys()) + ["Moyenne_Generale"]
        st.dataframe(
            df_final.style.format("{:.2f}", subset=style_cols),
            use_container_width=True,
            height=400
        )

        # --- AFFICHAGE PAR UE ---
        st.divider()
        st.subheader("📦 Détails par UE")
        tabs = st.tabs(list(STRUCTURE_COURS.keys()))
        
        for i, ue in enumerate(STRUCTURE_COURS.keys()):
            with tabs[i]:
                cols_ue = [c for c in COLONNES_MATIERES if c.startswith(ue)]
                # Vérifier si ces colonnes existent dans le sheet
                cols_presentes = [c for c in cols_ue if c in df_input.columns]
                
                if cols_presentes:
                    df_view = df_final[["Nom", ue] + cols_presentes].copy()
                    df_view = df_view.dropna(subset=[ue])
                    
                    if not df_view.empty:
                        df_view['Rang_UE'] = df_view[ue].rank(ascending=False, method='min')
                        df_view = df_view.sort_values('Rang_UE')
                        
                        st.dataframe(
                            df_view.style.format("{:.2f}", subset=[ue] + cols_presentes),
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info("Pas encore de moyenne calculable pour cette UE.")
                else:
                    st.warning(f"Colonnes manquantes dans le Google Sheet pour {ue}")

else:
    st.warning("Le Google Sheet est vide.")