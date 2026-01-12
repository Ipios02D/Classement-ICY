import streamlit as st
import pandas as pd
import numpy as np
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURATION ---
STRUCTURE_COURS = {
    "LSH1": {"Anglais": 2.0, "RSE": 0.5, "Org. Entreprises": 0.5, "Comptabilité": 0.5, "Gestion Projet": 1.0, "APSA (Sport)": 0.5},
    "Maths": {"Analyse Appliquée": 1.5, "Proba & Stats": 2.0, "Analyse Numérique": 1.5},
    "Archi": {"Archi Système": 2.0, "Prog Système": 2.0},
    "Securite": {"BDD Système": 2.0, "RGPD": 1.0},
    "Optimisation": {"Prog Linéaire": 1.5, "Complexité": 1.5},
    "DevApp": {"Langage C (Niv 2)": 2.0, "POO Java": 2.0, "Dev Web 1": 2.0},
    "SAE": {"Projet Web": 3.0}
}

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
    resultats = {}
    total_general_points = 0
    total_general_coefs = 0
    
    for ue, matieres in STRUCTURE_COURS.items():
        ue_points = 0
        ue_coefs = 0
        for matiere, coef in matieres.items():
            col_name = f"{ue} | {matiere}"
            valeur = row.get(col_name)
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

# Connexion
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_input = conn.read(ttl=0)
    if df_input.empty:
        df_input = pd.DataFrame(columns=["Nom"] + COLONNES_MATIERES)
    elif "Nom" not in df_input.columns:
        st.error("Colonne 'Nom' manquante dans le Google Sheet.")
        st.stop()
    
    # Init colonnes
    for col in COLONNES_MATIERES:
        if col not in df_input.columns:
            df_input[col] = np.nan

except Exception as e:
    st.error("Erreur de connexion. Vérifiez secrets.toml.")
    st.stop()

# --- 3. BARRE LATÉRALE ---

# --- SECTION A : CRÉER UN ÉTUDIANT ---
st.sidebar.header("➕ Nouvel Étudiant")
with st.sidebar.form("form_creation"):
    nouveau_nom = st.text_input("Nom Prénom")
    btn_creer = st.form_submit_button("Créer l'étudiant")

    if btn_creer:
        if nouveau_nom:
            if nouveau_nom in df_input["Nom"].values:
                st.warning("Cet étudiant existe déjà.")
            else:
                try:
                    # Création ligne vide
                    new_row = {col: np.nan for col in df_input.columns}
                    new_row["Nom"] = nouveau_nom
                    df_update = pd.concat([df_input, pd.DataFrame([new_row])], ignore_index=True)
                    
                    conn.update(data=df_update)
                    st.toast(f"Étudiant {nouveau_nom} ajouté !", icon="✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")
        else:
            st.error("Veuillez entrer un nom.")

st.sidebar.divider()

# --- SECTION B : SAISIR UNE NOTE ---
st.sidebar.header("📝 Saisir une note")

# Liste des étudiants existants uniquement
liste_etudiants = sorted(df_input["Nom"].dropna().astype(str).unique().tolist())

if not liste_etudiants:
    st.sidebar.info("Commencez par créer un étudiant ci-dessus.")
else:
    with st.sidebar.form("form_note"):
        # Sélection étudiant existant
        nom_sel = st.selectbox("Étudiant", liste_etudiants)
        
        # Sélection Matière
        col_ue, col_mat = st.columns(2)
        with col_ue:
            ue_sel = st.selectbox("UE", OPTIONS_UE)
        with col_mat:
            mat_sel = st.selectbox("Matière", MAP_UE_MATIERES[ue_sel])
        
        valeur_note = st.number_input("Note (/20)", 0.0, 20.0, step=0.5)
        
        if st.form_submit_button("Enregistrer la note"):
            try:
                df_update = df_input.copy()
                idx = df_update.index[df_update["Nom"] == nom_sel][0]
                df_update.at[idx, mat_sel] = valeur_note
                
                conn.update(data=df_update)
                st.toast("Note enregistrée !", icon="💾")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

# --- 4. AFFICHAGE ---
st.divider()

if not df_input.empty:
    cols_notes = [c for c in df_input.columns if c != "Nom"]
    for c in cols_notes:
        df_input[c] = pd.to_numeric(df_input[c], errors='coerce')

    df_calc = df_input.apply(calculer_moyennes, axis=1)
    df_final = pd.concat([df_input.reset_index(drop=True), df_calc.reset_index(drop=True)], axis=1)
    df_final = df_final.loc[:, ~df_final.columns.duplicated()]

    if "Moyenne_Generale" in df_final.columns:
        df_final['Rang'] = df_final['Moyenne_Generale'].rank(ascending=False, na_option='bottom', method='min')
        df_final = df_final.sort_values(['Rang', 'Nom'], na_position='last')

        tab_gen, tab_det = st.tabs(["🏆 Classement", "📊 Détails"])

        with tab_gen:
            # Affichage propre
            cols_ok = [c for c in (["Rang", "Nom", "Moyenne_Generale"] + OPTIONS_UE) if c in df_final.columns]
            st.dataframe(
                df_final[cols_ok].style.format("{:.2f}", subset=[c for c in cols_ok if c not in ["Rang", "Nom"]]),
                use_container_width=True, hide_index=True
            )

        with tab_det:
            subtabs = st.tabs(OPTIONS_UE)
            for i, ue in enumerate(OPTIONS_UE):
                with subtabs[i]:
                    cols_matieres = MAP_UE_MATIERES[ue]
                    target = ["Nom", ue] + cols_matieres
                    valid = [c for c in target if c in df_final.columns]
                    
                    if ue in df_final.columns:
                        # On affiche tout le monde, même ceux sans note, mais on classe ceux qui en ont
                        df_ue = df_final[valid].copy()
                        df_ue['R'] = df_ue[ue].rank(ascending=False, na_option='bottom', method='min')
                        df_ue = df_ue.sort_values(['R', 'Nom'])
                        
                        st.dataframe(
                            df_ue[['R'] + valid].style.format("{:.2f}", subset=[c for c in valid if c != "Nom"]),
                            use_container_width=True, hide_index=True
                        )
else:
    st.info("La base de données est vide. Ajoutez un étudiant à gauche.")