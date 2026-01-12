import streamlit as st
import pandas as pd
import numpy as np
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURATION (Noms simplifiés) ---
# J'ai retiré "ING05-ICY-" des clés pour alléger l'affichage
STRUCTURE_COURS = {
    "LSH1": {"Anglais": 2.0, "RSE": 0.5, "Org. Entreprises": 0.5, "Comptabilité": 0.5, "Gestion Projet": 1.0, "APSA (Sport)": 0.5},
    "Maths": {"Analyse Appliquée": 1.5, "Proba & Stats": 2.0, "Analyse Numérique": 1.5},
    "Archi": {"Archi Système": 2.0, "Prog Système": 2.0},
    "Securite": {"BDD Système": 2.0, "RGPD": 1.0},
    "Optimisation": {"Prog Linéaire": 1.5, "Complexité": 1.5},
    "DevApp": {"Langage C (Niv 2)": 2.0, "POO Java": 2.0, "Dev Web 1": 2.0},
    "SAE": {"Projet Web": 3.0}
}

# Génération des noms de colonnes (ex: "Maths | Proba & Stats")
COLONNES_MATIERES = []
OPTIONS_UE = list(STRUCTURE_COURS.keys())
MAP_UE_MATIERES = {}

for ue, matieres in STRUCTURE_COURS.items():
    liste_mats = []
    for matiere in matieres.keys():
        col_name = f"{ue} | {matiere}"
        COLONNES_MATIERES.append(col_name)
        liste_mats.append(col_name)
    MAP_UE_MATIERES[ue] = liste_mats

def calculer_moyennes(row):
    """Calcule les moyennes par UE et la moyenne générale"""
    resultats = {}
    total_general_points = 0
    total_general_coefs = 0
    
    for ue, matieres in STRUCTURE_COURS.items():
        ue_points = 0
        ue_coefs = 0
        
        for matiere, coef in matieres.items():
            col_name = f"{ue} | {matiere}"
            valeur = row.get(col_name)
            # Conversion sécurisée en float
            if pd.notna(valeur) and valeur != "":
                try:
                    f_val = float(valeur)
                    ue_points += f_val * coef
                    ue_coefs += coef
                except:
                    pass
        
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

# --- 2. INTERFACE STREAMLIT ---
st.set_page_config(page_title="Classement ING05", layout="wide")
st.title("🎓 Système de Notes (ING05)")

# Connexion via secrets.toml (INDISPENSABLE pour écrire)
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CHARGEMENT ---
try:
    df_input = conn.read(ttl=0)
    
    # Si le sheet est vide ou nouveau, on initialise les colonnes
    if df_input.empty:
        df_input = pd.DataFrame(columns=["Nom"] + COLONNES_MATIERES)
    elif "Nom" not in df_input.columns:
        st.error("Le Google Sheet doit avoir une colonne 'Nom'.")
        st.stop()
        
    # Création des colonnes manquantes (si vous avez changé les noms dans le code)
    for col in COLONNES_MATIERES:
        if col not in df_input.columns:
            df_input[col] = np.nan

except Exception as e:
    st.error(f"Erreur connexion : {e}")
    st.info("Vérifiez votre fichier secrets.toml et le partage du Sheet avec le Service Account.")
    st.stop()

# --- 3. BARRE LATÉRALE (SAISIE) ---
st.sidebar.header("📝 Saisir une note")

with st.sidebar.form("form_ajout_note"):
    # Liste des étudiants
    liste_noms = sorted(df_input["Nom"].dropna().astype(str).unique().tolist())
    nouveau_nom = "➕ Nouvel étudiant"
    
    choix_nom = st.selectbox("Étudiant", [nouveau_nom] + liste_noms, index=1 if liste_noms else 0)
    
    nom_saisi = ""
    if choix_nom == nouveau_nom:
        nom_saisi = st.text_input("Nom Prénom")
    else:
        nom_saisi = choix_nom

    # Sélecteurs dynamiques (Noms courts)
    col_ue, col_mat = st.columns(2)
    with col_ue:
        ue_sel = st.selectbox("UE", OPTIONS_UE)
    with col_mat:
        mat_sel = st.selectbox("Matière", MAP_UE_MATIERES[ue_sel]) # Affiche "UE | Matiere"
    
    valeur_note = st.number_input("Note (/20)", 0.0, 20.0, step=0.5)
    
    if st.form_submit_button("Enregistrer"):
        if not nom_saisi:
            st.error("Nom manquant.")
        else:
            try:
                df_update = df_input.copy()
                
                # Gestion ou Création de la ligne étudiant
                if nom_saisi in df_update["Nom"].values:
                    idx = df_update.index[df_update["Nom"] == nom_saisi][0]
                    df_update.at[idx, mat_sel] = valeur_note
                else:
                    new_row = {col: np.nan for col in df_update.columns}
                    new_row["Nom"] = nom_saisi
                    new_row[mat_sel] = valeur_note
                    df_update = pd.concat([df_update, pd.DataFrame([new_row])], ignore_index=True)

                # ÉCRITURE DANS GOOGLE SHEETS
                conn.update(data=df_update)
                st.toast(f"Note enregistrée pour {nom_saisi} !", icon="✅")
                st.rerun()
                
            except Exception as e:
                st.error(f"Erreur sauvegarde : {e}")

# --- 4. AFFICHAGE ET CLASSEMENTS ---
st.divider()

if not df_input.empty:
    # Nettoyage types numériques
    cols_notes = [c for c in df_input.columns if c != "Nom"]
    for c in cols_notes:
        df_input[c] = pd.to_numeric(df_input[c], errors='coerce')

    # Calculs
    df_calc = df_input.apply(calculer_moyennes, axis=1)
    
    # Fusion propre
    df_final = pd.concat([df_input.reset_index(drop=True), df_calc.reset_index(drop=True)], axis=1)
    df_final = df_final.loc[:, ~df_final.columns.duplicated()]

    # Calcul Rang
    if "Moyenne_Generale" in df_final.columns:
        df_final['Rang'] = df_final['Moyenne_Generale'].rank(ascending=False, na_option='bottom', method='min')
        df_final = df_final.sort_values('Rang')

        # Onglets
        tab_gen, tab_det = st.tabs(["🏆 Classement Général", "📊 Détails par Matière"])

        with tab_gen:
            cols_ok = [c for c in (["Rang", "Nom", "Moyenne_Generale"] + OPTIONS_UE) if c in df_final.columns]
            st.dataframe(
                df_final[cols_ok].style.format("{:.2f}", subset=[c for c in cols_ok if c not in ["Rang", "Nom"]]),
                use_container_width=True, 
                hide_index=True
            )

        with tab_det:
            # Sous-onglets par UE
            subtabs = st.tabs(OPTIONS_UE)
            
            for i, ue in enumerate(OPTIONS_UE):
                with subtabs[i]:
                    cols_matieres = MAP_UE_MATIERES[ue]
                    target = ["Nom", ue] + cols_matieres
                    valid = [c for c in target if c in df_final.columns]
                    
                    if ue in df_final.columns:
                        df_ue = df_final[valid].dropna(subset=[ue]).copy()
                        if not df_ue.empty:
                            df_ue['R'] = df_ue[ue].rank(ascending=False, method='min')
                            df_ue = df_ue.sort_values('R')
                            
                            st.dataframe(
                                df_ue[['R'] + valid].style.format("{:.2f}", subset=[c for c in valid if c != "Nom"]),
                                use_container_width=True, 
                                hide_index=True
                            )
                        else:
                            st.info("Pas encore de moyenne calculée.")
                    else:
                        st.warning("Données manquantes.")