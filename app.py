import streamlit as st
import pandas as pd
import numpy as np
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURATION DES MATIÈRES ET COEFS ---
STRUCTURE_COURS = {
    "ING05-ICY-LSH1": {"Anglais": 2.0, "RSE": 0.5, "Org. Entreprises": 0.5, "Comptabilité": 0.5, "Gestion Projet": 1.0, "APSA (Sport)": 0.5},
    "ING05-ICY-Maths": {"Analyse Appliquée": 1.5, "Proba & Stats": 2.0, "Analyse Numérique": 1.5},
    "ING05-ICY-Archi": {"Archi Système": 2.0, "Prog Système": 2.0},
    "ING05-ICY-Securite": {"BDD Système": 2.0, "RGPD": 1.0},
    "ING05-ICY-Optimisation": {"Prog Linéaire": 1.5, "Complexité": 1.5},
    "ING05-ICY-DevApp": {"Langage C (Niv 2)": 2.0, "POO Java": 2.0, "Dev Web 1": 2.0},
    "ING05-ICY-SAE": {"Projet Web": 3.0}
}

# Création de la liste des colonnes aplatie (ex: "ING05-ICY-Maths | Proba & Stats")
COLONNES_MATIERES = []
OPTIONS_UE = list(STRUCTURE_COURS.keys())
MAP_UE_MATIERES = {} # Pour le menu déroulant

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
            # On récupère la note, si elle existe
            valeur = row.get(col_name)
            if pd.notna(valeur) and valeur != "":
                try:
                    valeur = float(valeur)
                    ue_points += valeur * coef
                    ue_coefs += coef
                except:
                    pass # Ignore si pas un nombre
        
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
st.title("🎓 Système de Notes Collaboratif (ING05)")

# Connexion Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
url_sheet = "https://docs.google.com/spreadsheets/d/1wgSA92nA7YnQ5_bSfiiPv8DqtOXOb34u3uT6OdiVSzs/edit?usp=sharing"
# --- CHARGEMENT DES DONNÉES ---
try:
    # On lit le sheet actuel
    df_input = conn.read(spreadsheet=url_sheet, ttl=0)
    
    # Sécurités : si vide ou pas de colonne Nom
    if df_input.empty:
        df_input = pd.DataFrame(columns=["Nom"] + COLONNES_MATIERES)
    if "Nom" not in df_input.columns:
        st.error("ERREUR : La colonne 'Nom' est introuvable dans le Google Sheet.")
        st.stop()
        
    # On s'assure que toutes les colonnes matières existent (sinon on les crée vides)
    for col in COLONNES_MATIERES:
        if col not in df_input.columns:
            df_input[col] = np.nan

except Exception as e:
    st.error(f"Erreur de connexion : {e}")
    st.stop()

# --- 3. BARRE LATÉRALE : AJOUT DE NOTES ---
st.sidebar.header("📝 Saisir une note")
st.sidebar.info("Sélectionnez votre nom et ajoutez votre note.")

with st.sidebar.form("form_ajout_note"):
    # 1. Choisir l'étudiant (ou Nouveau)
    liste_noms = df_input["Nom"].dropna().unique().tolist()
    liste_noms.sort()
    nouveau_nom = "➕ Ajouter un nouvel étudiant"
    choix_nom = st.selectbox("Étudiant", [nouveau_nom] + liste_noms, index=1 if liste_noms else 0)
    
    nom_saisi = ""
    if choix_nom == nouveau_nom:
        nom_saisi = st.text_input("Entrez votre Nom Prénom")
    else:
        nom_saisi = choix_nom

    # 2. Choisir la matière
    ue_selectionnee = st.selectbox("Choisir l'UE", OPTIONS_UE)
    matiere_selectionnee = st.selectbox("Choisir la Matière", MAP_UE_MATIERES[ue_selectionnee])
    
    # 3. La note
    valeur_note = st.number_input("Note (/20)", min_value=0.0, max_value=20.0, step=0.5, format="%.2f")
    
    bouton_envoyer = st.form_submit_button("Enregistrer la note")

    if bouton_envoyer:
        if not nom_saisi:
            st.error("Il faut un nom !")
        else:
            try:
                # Copie de travail
                df_update = df_input.copy()
                
                # Est-ce que l'étudiant existe déjà ?
                if nom_saisi in df_update["Nom"].values:
                    # On met à jour la ligne existante
                    idx = df_update.index[df_update["Nom"] == nom_saisi][0]
                    df_update.at[idx, matiere_selectionnee] = valeur_note
                else:
                    # On crée une nouvelle ligne
                    new_row = {col: np.nan for col in df_update.columns}
                    new_row["Nom"] = nom_saisi
                    new_row[matiere_selectionnee] = valeur_note
                    # Ajout propre via concat
                    df_new_row = pd.DataFrame([new_row])
                    df_update = pd.concat([df_update, df_new_row], ignore_index=True)

                # SAUVEGARDE DANS GOOGLE SHEETS
                conn.update(data=df_update)
                st.success(f"Note enregistrée pour {nom_saisi} ! Rechargez la page si nécessaire.")
                st.rerun() # Rafraîchit la page immédiatement
                
            except Exception as e:
                st.error(f"Erreur lors de la sauvegarde : {e}")


# --- 4. CALCULS ET AFFICHAGE ---
st.divider()

if not df_input.empty:
    # Nettoyage des données (convertir en nombres)
    cols_notes = [c for c in df_input.columns if c != "Nom"]
    for c in cols_notes:
        df_input[c] = pd.to_numeric(df_input[c], errors='coerce')

    # Calcul des moyennes
    df_moyennes = df_input.apply(calculer_moyennes, axis=1)
    
    # FUSION CORRECTE (C'est ici que l'erreur précédente était corrigée)
    # On garde df_input (notes brutes) ET on ajoute les colonnes calculées
    # On drop les index pour éviter les soucis d'alignement
    df_final = pd.concat([df_input.reset_index(drop=True), df_moyennes.reset_index(drop=True)], axis=1)
    
    # Suppression des colonnes dupliquées s'il y en a
    df_final = df_final.loc[:, ~df_final.columns.duplicated()]

    # Calcul du Rang Général
    if "Moyenne_Generale" in df_final.columns:
        df_final['Rang'] = df_final['Moyenne_Generale'].rank(ascending=False, na_option='bottom', method='min')
        df_final = df_final.sort_values('Rang')

        # --- TABS D'AFFICHAGE ---
        tab_general, tab_details = st.tabs(["🏆 Classement Général", "📊 Détails par Matière"])

        with tab_general:
            cols_to_show = ["Rang", "Nom", "Moyenne_Generale"] + list(STRUCTURE_COURS.keys())
            # On filtre pour n'afficher que les colonnes qui existent vraiment
            cols_existantes = [c for c in cols_to_show if c in df_final.columns]
            
            st.dataframe(
                df_final[cols_existantes].style.format("{:.2f}", subset=[c for c in cols_existantes if c not in ["Rang", "Nom"]]),
                use_container_width=True,
                hide_index=True
            )

        with tab_details:
            st.write("Classements spécifiques par Unité d'Enseignement")
            # Sous-onglets pour chaque UE
            subtabs = st.tabs(list(STRUCTURE_COURS.keys()))
            
            for i, ue in enumerate(STRUCTURE_COURS.keys()):
                with subtabs[i]:
                    # Quelles sont les matières de cette UE ?
                    cols_matieres_ue = MAP_UE_MATIERES[ue]
                    
                    # On prépare les colonnes à afficher : Nom + Moyenne UE + Notes Matières
                    target_cols = ["Nom", ue] + cols_matieres_ue
                    
                    # Vérification de sécurité : est-ce que ces colonnes existent dans df_final ?
                    valid_cols = [c for c in target_cols if c in df_final.columns]
                    
                    if ue in df_final.columns:
                        # On prend le dataframe, on ne garde que les lignes où l'UE a une moyenne
                        df_ue = df_final[valid_cols].dropna(subset=[ue]).copy()
                        
                        if not df_ue.empty:
                            df_ue['Rang_UE'] = df_ue[ue].rank(ascending=False, method='min')
                            df_ue = df_ue.sort_values('Rang_UE')
                            
                            # On met le rang en premier
                            final_cols = ['Rang_UE'] + valid_cols
                            
                            st.dataframe(
                                df_ue[final_cols].style.format("{:.2f}", subset=[c for c in valid_cols if c != "Nom"]),
                                use_container_width=True,
                                hide_index=True
                            )
                        else:
                            st.info(f"Pas encore de notes suffisantes pour calculer la moyenne de {ue}.")
                    else:
                        st.warning(f"L'UE {ue} n'a pas encore été calculée.")

    else:
        st.info("Ajoutez des notes pour voir apparaître le classement.")
else:
    st.warning("Le tableau est vide.")