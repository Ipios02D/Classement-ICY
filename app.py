import streamlit as st
import pandas as pd
import numpy as np

# --- CONFIGURATION (Modifiée selon vos demandes) ---
# L'UE Option est exclue.
# ING05-ICY-DevApp est passé à 6 ECTS.
UES_CONFIG = {
    "ING05-ICY-LSH1": 5,
    "ING05-ICY-Maths": 5,
    "ING05-ICY-Archi": 4,
    "ING05-ICY-Securite": 3,
    "ING05-ICY-Optimisation": 3,
    "ING05-ICY-DevApp": 6, 
    "ING05-ICY-SAE": 3
}

def calculer_moyenne_ponderee(row):
    """Calcule la moyenne en ignorant les cases vides"""
    total_points = 0
    total_coefs = 0
    
    for ue, coef in UES_CONFIG.items():
        # Vérifie si la colonne existe et si la note est valide (pas vide/NaN)
        if ue in row and pd.notna(row[ue]):
            total_points += row[ue] * coef
            total_coefs += coef
            
    if total_coefs == 0:
        return np.nan # Pas de note, pas de moyenne
    return round(total_points / total_coefs, 2)

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Classement ING05", layout="wide")
st.title("🎓 Système de Classement ING05")
st.markdown("Calcul des moyennes et classements en temps réel (Même avec notes partielles).")

# Barre latérale pour la configuration
st.sidebar.header("Configuration des Coefs")
st.sidebar.write("Les coefficients actuels sont :")
st.sidebar.json(UES_CONFIG)

# --- GESTION DES DONNÉES ---
st.subheader("1. Saisie des Notes")
col1, col2 = st.columns([1, 2])

with col1:
    st.info("Vous pouvez modifier le tableau ci-contre ou importer un Excel.")
    uploaded_file = st.file_uploader("Importer un fichier Excel (optionnel)", type=["xlsx", "csv"])

# Données initiales par défaut (Exemple)
default_data = pd.DataFrame(columns=["Nom"] + list(UES_CONFIG.keys()))
if default_data.empty:
    default_data = pd.DataFrame([
        {"Nom": "Etudiant 1", "ING05-ICY-DevApp": 15, "ING05-ICY-Maths": 12},
        {"Nom": "Etudiant 2", "ING05-ICY-DevApp": 10, "ING05-ICY-Maths": 14},
    ])

# Chargement des données
if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_input = pd.read_csv(uploaded_file)
        else:
            df_input = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Erreur de lecture : {e}")
        df_input = default_data
else:
    df_input = default_data

# Assurer que toutes les colonnes UE existent
for ue in UES_CONFIG.keys():
    if ue not in df_input.columns:
        df_input[ue] = np.nan

# Éditeur de données interactif
with col2:
    edited_df = st.data_editor(df_input, num_rows="dynamic", use_container_width=True)

# --- CALCULS ---
if not edited_df.empty:
    # Calcul de la moyenne
    edited_df['Moyenne_Generale'] = edited_df.apply(calculer_moyenne_ponderee, axis=1)
    
    # Calcul du rang général (les moyennes vides sont mises à la fin)
    edited_df['Rang_General'] = edited_df['Moyenne_Generale'].rank(ascending=False, na_option='bottom', method='min')

    # --- AFFICHAGE DES RÉSULTATS ---
    st.divider()
    st.subheader("🏆 Classement Général")
    
    # Mise en forme du tableau final (Trié par rang)
    final_df = edited_df.sort_values("Rang_General")
    
    # Affichage avec mise en valeur du Top 3
    st.dataframe(
        final_df[['Rang_General', 'Nom', 'Moyenne_Generale']],
        use_container_width=True,
        hide_index=True
    )

    # --- STATISTIQUES PAR MATIÈRE ---
    st.divider()
    st.subheader("📊 Classements par Matière")
    
    tabs = st.tabs(list(UES_CONFIG.keys()))
    
    for i, ue in enumerate(UES_CONFIG.keys()):
        with tabs[i]:
            # Filtrer pour ne garder que ceux qui ont une note
            df_ue = edited_df[['Nom', ue]].dropna()
            
            if not df_ue.empty:
                df_ue['Rang'] = df_ue[ue].rank(ascending=False, method='min')
                df_ue = df_ue.sort_values('Rang')
                st.dataframe(df_ue, use_container_width=True, hide_index=True)
            else:
                st.warning(f"Aucune note saisie pour {ue}")

else:
    st.warning("Veuillez entrer des données ou charger un fichier.")