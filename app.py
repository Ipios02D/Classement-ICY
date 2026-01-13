import streamlit as st
import pandas as pd
import numpy as np
from streamlit_gsheets import GSheetsConnection

# ==============================================================================
# --- 1. CONFIGURATION DU PROGRAMME (À MODIFIER ICI) ---
# ==============================================================================
# C'est ici que vous définissez la structure de votre année.
# Structure : "NOM_UE": { "coef_ue": X, "matieres": { "Nom_Matiere": Y, ... } }
# ==============================================================================

PROGRAMME_EDUCATIF = {
    "LSH1": {
        "coef_ue": 5.0,  # Coefficient de l'UE LSH1 dans la moyenne générale
        "matieres": {
            "Anglais": 3.0,          # Coef de la matière DANS l'UE
            "RSE": 1.0,
            "Org. Entreprises": 1.0,
            "Comptabilité": 3.0,
            "Gestion Projet": 1.0,
            "FAPSA (Sport)": 2.0
        }
    },
    "Maths": {
        "coef_ue": 5.0,  # Coefficient de l'UE Maths
        "matieres": {
            "Analyse Appliquée": 1.5,
            "Proba & Stats": 1.75,
            "Analyse Numérique": 1.75
        }
    },
    "Archi": {
        "coef_ue": 4.0,
        "matieres": {
            "Archi Système": 1.0,
            "Prog Système": 1.0
        }
    },
    "Securite": {
        "coef_ue": 3.0,
        "matieres": {
            "BDD Système": 2.0,
            "RGPD": 1.0
        }
    },
    "Optimisation": {
        "coef_ue": 3.0,
        "matieres": {
            "Prog Linéaire": 1.0,
            "Complexité": 1.0
        }
    },
    "DevApp": {
        "coef_ue": 6.0,
        "matieres": {
            "Langage C (Niv 2)": 1.0,
            "POO Java": 1.0,
            "Dev Web 1": 1.0
        }
    },
    "SAE": {
        "coef_ue": 3.0,
        "matieres": {
            "Projet Web": 1.0
        }
    }
}

# --- INITIALISATION DES VARIABLES GLOBALES (NE PAS TOUCHER) ---
# Ces listes sont générées automatiquement à partir de la configuration ci-dessus.

COLONNES_SHEET = []       # Liste des noms de colonnes pour le Google Sheet
LISTE_UES = list(PROGRAMME_EDUCATIF.keys()) # Liste des noms des UEs
LISTE_CHOIX_MATIERES = [] # Liste pour le menu déroulant (Format: "UE | Matière")

for ue, details in PROGRAMME_EDUCATIF.items():
    for matiere in details["matieres"].keys():
        # On crée un nom unique pour chaque colonne : "Maths | Analyse"
        nom_colonne = f"{ue} | {matiere}"
        COLONNES_SHEET.append(nom_colonne)
        LISTE_CHOIX_MATIERES.append(nom_colonne)

# ==============================================================================
# --- 2. FONCTIONS DE CALCUL ---
# ==============================================================================

def calculer_moyennes(row):
    """
    Cette fonction prend une ligne (un étudiant) et calcule :
    1. La moyenne de chaque UE (basée sur les coefs des matières).
    2. La moyenne générale (basée sur les moyennes d'UE et les coefs d'UE).
    """
    resultats = {}
    
    # Variables pour la moyenne générale
    total_points_general = 0
    total_coefs_general = 0
    
    # On parcourt chaque UE définie dans la config
    for ue_nom, ue_details in PROGRAMME_EDUCATIF.items():
        ue_coef_global = ue_details["coef_ue"]
        matieres_dict = ue_details["matieres"]
        
        points_ue = 0
        coefs_ue_cumules = 0
        
        # On parcourt les matières de cette UE
        for mat_nom, mat_coef in matieres_dict.items():
            nom_colonne = f"{ue_nom} | {mat_nom}"
            valeur_note = row.get(nom_colonne)
            
            # Vérification : la note existe-t-elle et est-elle un nombre ?
            if pd.notna(valeur_note) and valeur_note != "":
                try:
                    f_val = float(valeur_note)
                    points_ue += f_val * mat_coef
                    coefs_ue_cumules += mat_coef
                except:
                    pass # Ignore si la valeur n'est pas convertible en nombre
        
        # --- Calcul de la Moyenne de l'UE ---
        if coefs_ue_cumules > 0:
            moyenne_ue = points_ue / coefs_ue_cumules
            resultats[ue_nom] = moyenne_ue
            
            # Si l'UE a une moyenne, elle compte pour la générale
            total_points_general += moyenne_ue * ue_coef_global
            total_coefs_general += ue_coef_global
        else:
            # Pas de notes dans cette UE -> NaN (Pas de note)
            resultats[ue_nom] = np.nan

    # --- Calcul de la Moyenne Générale ---
    if total_coefs_general > 0:
        resultats["Moyenne_Generale"] = total_points_general / total_coefs_general
    else:
        resultats["Moyenne_Generale"] = np.nan
        
    return pd.Series(resultats)

# ==============================================================================
# --- 3. INTERFACE STREAMLIT ---
# ==============================================================================

st.set_page_config(page_title="Classement ING05", layout="wide")
st.title("🎓 Système de Notes (ING05)")

# --- CONNEXION GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Lecture des données (ttl=0 pour ne pas utiliser le cache et voir les maj direct)
    df_input = conn.read(ttl=0)
    
    # Si le sheet est vide, on crée la structure de base
    if df_input.empty:
        df_input = pd.DataFrame(columns=["Nom"] + COLONNES_SHEET)
    elif "Nom" not in df_input.columns:
        st.error("⚠️ Colonne 'Nom' manquante dans le Google Sheet. Ajoutez-la manuellement.")
        st.stop()
    
    # On s'assure que toutes les colonnes matières existent (si on a ajouté une matière dans la config)
    for col in COLONNES_SHEET:
        if col not in df_input.columns:
            df_input[col] = np.nan

except Exception as e:
    st.error("Erreur de connexion au Google Sheet. Vérifiez votre fichier `.streamlit/secrets.toml`.")
    st.expander("Détails de l'erreur").write(e)
    st.stop()

# ==============================================================================
# --- 4. BARRE LATÉRALE (SIDEBAR) - SAISIE ---
# ==============================================================================

# --- A. CRÉATION D'ÉTUDIANT ---
st.sidebar.header("➕ Nouvel Étudiant")
with st.sidebar.form("form_creation"):
    nouveau_nom = st.text_input("Nom Prénom")
    btn_creer = st.form_submit_button("Créer l'étudiant")

    if btn_creer:
        if nouveau_nom:
            # Vérifie si le nom existe déjà
            if not df_input.empty and nouveau_nom in df_input["Nom"].values:
                st.warning("Cet étudiant existe déjà.")
            else:
                try:
                    # Création d'une ligne vide avec les bonnes colonnes
                    new_row = {col: np.nan for col in df_input.columns}
                    new_row["Nom"] = nouveau_nom
                    
                    # Ajout au dataframe et sauvegarde
                    df_update = pd.concat([df_input, pd.DataFrame([new_row])], ignore_index=True)
                    conn.update(data=df_update)
                    
                    st.toast(f"Étudiant {nouveau_nom} ajouté !", icon="✅")
                    st.rerun() # Recharge la page
                except Exception as e:
                    st.error(f"Erreur lors de l'ajout : {e}")
        else:
            st.error("Veuillez entrer un nom.")

st.sidebar.divider()

# --- B. SAISIE DE NOTE SIMPLIFIÉE ---
st.sidebar.header("📝 Saisir une note")

# Récupération de la liste des étudiants
liste_etudiants = sorted(df_input["Nom"].dropna().astype(str).unique().tolist())

if not liste_etudiants:
    st.sidebar.info("La liste d'étudiants est vide.")
else:
    with st.sidebar.form("form_note"):
        # 1. Choisir l'étudiant
        nom_sel = st.selectbox("Étudiant", liste_etudiants)
        
        # 2. Choisir la matière (Liste unique "UE | Matière")
        # Cela permet de sélectionner directement sans passer par l'UE
        matiere_cible = st.selectbox("Matière", LISTE_CHOIX_MATIERES)
        
        # 3. Saisir la note
        valeur_note = st.number_input("Note (/20)", 0.0, 20.0, step=0.5)
        
        if st.form_submit_button("Enregistrer la note"):
            try:
                # On copie le dataframe pour modifier
                df_update = df_input.copy()
                
                # On trouve l'index de l'étudiant
                idx = df_update.index[df_update["Nom"] == nom_sel][0]
                
                # On met à jour la colonne spécifique (qui correspond exactement au string du selectbox)
                df_update.at[idx, matiere_cible] = valeur_note
                
                # Sauvegarde GSheets
                conn.update(data=df_update)
                st.toast("Note enregistrée !", icon="💾")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur de sauvegarde : {e}")

# ==============================================================================
# --- 5. CALCULS ET AFFICHAGE PRINCIPAL ---
# ==============================================================================
st.divider()

if not df_input.empty:
    # 1. Conversion des notes en numérique (au cas où il y ait du texte dans le sheet)
    cols_notes = [c for c in df_input.columns if c != "Nom"]
    for c in cols_notes:
        df_input[c] = pd.to_numeric(df_input[c], errors='coerce')

    # 2. Application de la fonction de calcul
    df_calc = df_input.apply(calculer_moyennes, axis=1)
    
    # 3. Fusion des infos brutes (notes) et calculées (moyennes)
    df_final = pd.concat([df_input.reset_index(drop=True), df_calc.reset_index(drop=True)], axis=1)
    
    # Nettoyage doublons colonnes au cas où
    df_final = df_final.loc[:, ~df_final.columns.duplicated()]

    # 4. Gestion du classement (Rang)
    if "Moyenne_Generale" in df_final.columns:
        # Création du rang basé sur la Moyenne Générale
        df_final['Rang'] = df_final['Moyenne_Generale'].rank(ascending=False, na_option='bottom', method='min')
        # Tri : D'abord le rang, puis le Nom alphabétique pour les égalités
        df_final = df_final.sort_values(['Rang', 'Nom'], na_position='last')

        # --- TABS D'AFFICHAGE ---
        tab_gen, tab_det = st.tabs(["🏆 Classement Général", "📊 Détails par UE"])

        # --- A. CLASSEMENT GÉNÉRAL ---
        with tab_gen:
            # Colonnes à afficher : Rang, Nom, Moyenne Générale, puis les Moyennes des UE
            cols_a_afficher = ["Rang", "Nom", "Moyenne_Generale"] + LISTE_UES
            
            # Filtre pour ne garder que les colonnes qui existent vraiment
            cols_finales = [c for c in cols_a_afficher if c in df_final.columns]
            
            st.dataframe(
                df_final[cols_finales].style.format("{:.2f}", subset=[c for c in cols_finales if c not in ["Rang", "Nom"]]),
                use_container_width=True, 
                hide_index=True
            )

        # --- B. DÉTAILS PAR UE ---
        with tab_det:
            # On crée un sous-onglet pour chaque UE
            subtabs = st.tabs(LISTE_UES)
            
            for i, ue in enumerate(LISTE_UES):
                with subtabs[i]:
                    # On cherche les colonnes qui appartiennent à cette UE
                    cols_ue_specifiques = [c for c in COLONNES_SHEET if c.startswith(ue + " |")]
                    
                    # Colonnes cibles : Nom, Moyenne de l'UE, Notes des matières
                    target_cols = ["Nom", ue] + cols_ue_specifiques
                    valid_cols = [c for c in target_cols if c in df_final.columns]
                    
                    if ue in df_final.columns:
                        # Création d'un mini dataframe local
                        df_ue = df_final[valid_cols].copy()
                        
                        # Classement spécifique à cette UE
                        df_ue['Rang_UE'] = df_ue[ue].rank(ascending=False, na_option='bottom', method='min')
                        df_ue = df_ue.sort_values(['Rang_UE', 'Nom'])
                        
                        # Réorganisation des colonnes pour avoir le rang en premier
                        cols_display = ['Rang_UE'] + valid_cols
                        
                        st.write(f"### Détails pour l'UE : {ue} (Coef: {PROGRAMME_EDUCATIF[ue]['coef_ue']})")
                        st.dataframe(
                            df_ue[cols_display].style.format("{:.2f}", subset=[c for c in valid_cols if c != "Nom"]),
                            use_container_width=True, 
                            hide_index=True
                        )
else:
    st.info("La base de données est vide. Ajoutez un étudiant via le menu de gauche pour commencer.")