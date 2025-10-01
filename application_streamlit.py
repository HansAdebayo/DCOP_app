# application_streamlit.py (Version avec choix de Modélisation 1 ou 2)
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
import random

# Importation des fonctions traduites (Assurez-vous que constructeur_dcop.py est présent)
from constructeur_dcop import (
    generer_positions_aleatoires, 
    construire_json_a_partir_positions, 
    json_vers_xml, 
    afficher_json_joli
)

# Configuration de la page
st.set_page_config(page_title="DCOP – Générateur d'Instance & Analyse", page_icon="🚗", layout="wide")
st.title("🚗 Constructeur d'Instance DCOP & Analyse de Benchmark (FRODO)")

# --- FONCTIONS UTILITAIRES D'INTERFACE ---

def dessiner_scene(voitures, passagers, dest_commune=None, dest_par=None):
    """Dessine la scène 2D (voitures, passagers, destinations) avec Matplotlib."""
    fig, ax = plt.subplots()
    
    # Voitures
    vx = [v[2][0] for v in voitures]
    vy = [v[2][1] for v in voitures]
    ax.scatter(vx, vy, label="Voitures", marker="s", color="blue")
    for (id_v, cap, (x, y)) in voitures:
        ax.annotate(f"{id_v} (K={cap})", (x, y), textcoords="offset points", xytext=(5, 5))
        
    # Passagers
    px = [p[1][0] for p in passagers]
    py = [p[1][1] for p in passagers]
    ax.scatter(px, py, label="Passagers", marker="o", color="red")
    for (id_p, (x, y)) in passagers:
        ax.annotate(id_p, (x, y), textcoords="offset points", xytext=(5, 5))
        
    # Destinations (au moins l'une des deux est présente dans cette version simplifiée)
    if dest_commune is not None:
        ax.scatter([dest_commune[0]], [dest_commune[1]], marker="*", s=150, label="Destination (Commune)", color="green")
    if dest_par is not None:
        for id_p, (x, y) in dest_par.items():
            ax.scatter([x], [y], marker="*", s=120, color="orange")
            ax.annotate(f"Dest({id_p})", (x, y), textcoords="offset points", xytext=(5, 5))

    ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.legend()
    st.pyplot(fig)

def boutons_telechargement_json(obj_json, suffixe_cle, modelisation_choisie):
    """Affiche les boutons de téléchargement pour le JSON et le XML."""
    json_str = afficher_json_joli(obj_json)
    nom_base = obj_json.get('nom','instance')
    st.download_button("⬇️ Télécharger JSON", data=json_str.encode("utf-8"),
                       file_name=f"{nom_base}.json",
                       mime="application/json", key=f"json_{suffixe_cle}")
    
    xml_str = json_vers_xml(obj_json, modelisation=modelisation_choisie)
    st.download_button(f"⬇️ Télécharger XML (Modèle {modelisation_choisie})", 
                       data=xml_str.encode("utf-8"),
                       file_name=f"{nom_base}_M{modelisation_choisie}.xml",
                       mime="application/xml", key=f"xml_{suffixe_cle}_M{modelisation_choisie}")

# --- BARRE LATÉRALE (NAVIGATION SIMPLIFIÉE) ---
st.sidebar.title("⚙️ Mode")
mode = st.sidebar.radio("Sélectionnez l'action", [
    "Générer une Instance Aléatoire",
    "Analyser les Résultats CSV"
])


# ==============================================================================
# SECTION 1 : GÉNÉRATION ALÉATOIRE
# ==============================================================================
if mode == "Générer une Instance Aléatoire":
    st.header("1️⃣ Génération d'Instance Aléatoire (Ramassage & Dépose)")
    
    with st.expander("Paramètres de l'instance", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            n_voitures = st.number_input("Nombre de voitures", 1, 50, 4)
            cap_defaut = st.number_input("Capacité par voiture", 1, 999, 3)
            nom_instance = st.text_input("Nom d’instance", value="ramassage_aleatoire_01")
        with col2:
            n_passagers = st.number_input("Nombre de passagers", 1, 500, 6)
            graine = st.number_input("Graine RNG (reproductibilité)", 0, 999999, 123)
            couts_entiers = st.checkbox("Coûts entiers (recommandé)", value=True)
        with col3:
            largeur = st.number_input("Largeur (plan 2D)", 1.0, 10000.0, 100.0)
            hauteur = st.number_input("Hauteur (plan 2D)", 1.0, 10000.0, 100.0)
            
    with st.expander("Modélisation DCOP et Coûts", expanded=True):
        colA, colB, colC, colD = st.columns(4)
        with colA:
            modelisation = st.selectbox("Modélisation DCOP", 
                                        options=[1, 2], 
                                        format_func=lambda x: f"M{x}: Var par {'Voit-Pass' if x==1 else 'Passager'}")
        with colB:
            type_depot = st.selectbox("Type de destination (Dépose)", ["Unique (commune)", "Par passager"])
        with colC:
            poids_ramassage = st.number_input("Poids ramassage (Coût de départ)", 0.0, 100.0, 1.0)
        with colD:
            poids_depot = st.number_input("Poids dépose (Coût d'arrivée)", 0.0, 100.0, 1.0)

    # Variables pour la destination commune
    dest_commune, dest_par = None, None
    
    if type_depot == "Unique (commune)":
        st.info("La destination commune sera générée aléatoirement dans le plan.")
    elif type_depot == "Par passager":
        st.info("Les destinations par passager seront générées aléatoirement dans le plan (avec une graine différente).")


    if st.button("🚀 Générer Instance et Fichiers"):
        
        # 1. Génération des positions
        pos_voitures = generer_positions_aleatoires(n_voitures, largeur, hauteur, graine)
        pos_passagers = generer_positions_aleatoires(n_passagers, largeur, hauteur, graine + 1)

        voitures = [(f"v{i+1}", int(cap_defaut), pos_voitures[i]) for i in range(n_voitures)]
        passagers = [(f"p{j+1}", pos_passagers[j]) for j in range(n_passagers)]
        
        # 2. Gestion de la destination
        mode_depot = "aucun" # Au cas où
        if type_depot == "Unique (commune)":
            mode_depot = "commun"
            # Destination commune aléatoire
            pos_dest_commune = generer_positions_aleatoires(1, largeur, hauteur, graine + 500)[0]
            dest_commune = pos_dest_commune
        
        elif type_depot == "Par passager":
            mode_depot = "par_passager"
            # Destinations par passager aléatoires
            pos_dest_par = generer_positions_aleatoires(n_passagers, largeur, hauteur, graine + 999)
            dest_par = {passagers[j][0]: pos_dest_par[j] for j in range(n_passagers)}

        # 3. Construction du JSON/XML
        obj_json = construire_json_a_partir_positions(
            nom_instance, voitures, passagers, couts_entiers=couts_entiers,
            mode_depot=mode_depot, dest_commune=dest_commune, dest_par_passager=dest_par,
            poids_ramassage=poids_ramassage, poids_depot=poids_depot
        )

        st.success(f"Instance '{nom_instance}' générée avec succès (Modèle M{modelisation}).")

        col_viz, col_data = st.columns(2)
        with col_viz:
            st.subheader("Aperçu 2D des positions")
            dessiner_scene(voitures, passagers, dest_commune=dest_commune, dest_par=dest_par)
        
        with col_data:
            st.subheader("Téléchargements")
            # Appel mis à jour
            boutons_telechargement_json(obj_json, suffixe_cle="rnd", modelisation_choisie=modelisation)
            
            st.subheader("Matrice des coûts (voitures en lignes)")
            df = pd.DataFrame(obj_json["couts"]).T
            st.dataframe(df)

# ==============================================================================
# SECTION 2 : COMPARAISON (CSV)
# ==============================================================================
else:
    st.header("2️⃣ Analyse des Résultats de Benchmark (CSV)")
    
    # ----------------------------------------------------------------------
    # GÉNÉRATEUR DE COMMANDE FRODO (CHEMINS EN DUR)
    # ----------------------------------------------------------------------
    st.markdown("### 🛠️ Générateur de commande FRODO")
    
    # Chemins que l'utilisateur doit adapter si nécessaire
    frodo_jar_default = "/Users/hansbada/Desktop/frodo__/frodo2/frodo2.17.1.jar"
    xml_dir_default = "/Users/hansbada/Desktop/frodo__/frodo2/instance_gen/outputs"
    out_csv_default = "results/bench.csv"
    
    # Choix des agents (Agent name : XML agent path)
    agents_disponibles = {
        "DPOP": "./agents/DPOP/DPOPagent.xml",
        "ADOPT": "./agents/ADOPT/ADOPTagent.xml",
        "MGM": "./agents/MGM/MGM2agent.xml",
        "MaxSum": "./agents/MaxSum/MaxSumAgent.xml",
        "SynchBB": "./agents/SynchBB/SynchBBAgent.xml", # Exemple d'un 5ème agent
    }
    
    colA, colB = st.columns(2)
    with colA:
        frodo_jar_path = st.text_input("Chemin vers frodo.jar", value=frodo_jar_default)
        xml_dir_path = st.text_input("Dossier des instances XML (`--xml-dir`)", value=xml_dir_default)
        java_opts = st.text_input("Options Java (`-Xmx8g`, etc.)", value='"-Xmx8g"')
    with colB:
        csv_out_path = st.text_input("Fichier de sortie CSV (`--out-csv`)", value=out_csv_default)
        agents_selectionnes = st.multiselect(
            "Sélectionnez les algorithmes à comparer", 
            sorted(list(agents_disponibles.keys())),
            default=["DPOP", "ADOPT", "MGM", "MaxSum"]
        )
    
    # Construction de la chaîne d'agents
    agents_str = ",".join(
        f"{algo}={agents_disponibles[algo]}" 
        for algo in agents_selectionnes 
        if algo in agents_disponibles
    )
    
    # Génération de la commande
    commande_frodo = (
        f"java -jar {frodo_jar_path} "
        f"--xml-dir={xml_dir_path} "
        f"--agents={agents_str} "
        f"--out-csv={csv_out_path} "
        f"--java-opts={java_opts}"
    )
    
    st.markdown("---")
    st.subheader("Commande Terminale à Exécuter")
    st.caption("Copiez-collez cette commande dans votre terminal (lancé depuis le dossier parent de 'agents' et 'outputs') pour lancer le benchmark FRODO :")
    st.code(commande_frodo, language="bash")
    st.markdown("---")
    
    # ----------------------------------------------------------------------
    # ANALYSE DES RÉSULTATS CSV
    # ----------------------------------------------------------------------
    st.markdown("### 📈 Analyse des résultats")
    
    up = st.file_uploader("Uploader bench.csv", type=["csv"], key="uploader_csv_bench")
    chemin_csv = st.text_input("…ou chemin vers le CSV (local)", value=csv_out_path, key="chemin_local_csv")

    def charger_csv_flexible(data):
        if isinstance(data, bytes): stream = io.BytesIO(data)
        else: stream = data
        try: return pd.read_csv(stream)
        except Exception:
            if isinstance(data, bytes): stream.seek(0)
            return pd.read_csv(stream, sep=";")

    df = None
    if up is not None:
        df = charger_csv_flexible(up.read())
    elif chemin_csv.strip():
        try: df = charger_csv_flexible(chemin_csv.strip())
        except Exception as e: st.error(f"Impossible de lire le CSV à '{chemin_csv}': {e}")
            
    if df is None:
        st.info("Charge un CSV pour continuer. Colonnes attendues : `xml_file, algorithm, total_cost, runtime_ms`."); st.stop()
        
    # Nettoyage des types numériques
    for c in ["total_cost","runtime_ms","ncccs","msgs_total"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Filtres
    colA, colB = st.columns(2)
    with colA:
        algos_tous = sorted(df["algorithm"].dropna().unique().tolist()) if "algorithm" in df.columns else []
        algos_sel = st.multiselect("Algorithmes à afficher", algos_tous, default=algos_tous, key="filtre_algo")
    with colB:
        inst_tous = sorted(df["xml_file"].dropna().unique().tolist()) if "xml_file" in df.columns else []
        inst_sel = st.multiselect("Instances à afficher", inst_tous, default=inst_tous, key="filtre_inst")

    if "algorithm" in df.columns: df = df[df["algorithm"].isin(algos_sel)]
    if "xml_file" in df.columns: df = df[df["xml_file"].isin(inst_sel)]
    if df.empty: st.warning("Aucune ligne après filtrage. Ajuste tes sélections."); st.stop()

    # Calcul de l'écart (Gap) vs meilleur coût par instance
    if {"xml_file","total_cost"}.issubset(df.columns):
        meilleur_cout = df.groupby("xml_file")["total_cost"].min().rename("meilleur_cout")
        df = df.merge(meilleur_cout, on="xml_file", how="left")
        df["ecart_pct"] = (df["total_cost"] - df["meilleur_cout"]) / df["meilleur_cout"] * 100

    # Tableau filtré
    st.subheader("Tableau des résultats filtrés"); st.dataframe(df.sort_values(["xml_file","algorithm"]).reset_index(drop=True))

    # Synthèse par algorithme
    st.subheader("Synthèse (Moyennes par Algorithme)")
    agg = {}
    for c in ["total_cost","runtime_ms","ncccs","msgs_total","ecart_pct"]:
        if c in df.columns: agg[c] = "mean"
    if agg:
        synth = df.groupby("algorithm").agg(agg).reset_index()
        st.dataframe(synth)
    else: synth = pd.DataFrame()

    # Fonctions de Tracé
    def tracer_barre(series, titre, etiquette_y):
        fig, ax = plt.subplots()
        series.plot(kind="bar", ax=ax, color='skyblue')
        ax.set_title(titre); ax.set_ylabel(etiquette_y); ax.set_xlabel("Algorithme")
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, axis="y", alpha=0.3)
        st.pyplot(fig)

    # Graphiques
    if not synth.empty:
        if "runtime_ms" in synth.columns: st.markdown("### ⏱️ Temps moyen d'exécution (ms)"); tracer_barre(synth.set_index("algorithm")["runtime_ms"], "Temps Moyen", "ms")
        if "total_cost" in synth.columns: st.markdown("### 💰 Coût moyen (valeur de la solution)"); tracer_barre(synth.set_index("algorithm")["total_cost"], "Coût Moyen", "coût")
        if "msgs_total" in synth.columns: st.markdown("### ✉️ Messages moyens échangés"); tracer_barre(synth.set_index("algorithm")["msgs_total"], "Messages Moyens", "messages")
        if "ecart_pct" in synth.columns: st.markdown("### Écart moyen à l’optimum (en %)"); tracer_barre(synth.set_index("algorithm")["ecart_pct"], "Écart Moyen à l’Optimum", "%")

    # Nuage de points (Messages vs Temps)
    if {"runtime_ms","msgs_total","algorithm"}.issubset(df.columns):
        st.markdown("### Nuage de points : Messages vs Temps")
        fig, ax = plt.subplots()
        for id_algo, algo in enumerate(sorted(df["algorithm"].unique())):
            sub = df[df["algorithm"] == algo]
            ax.scatter(sub["msgs_total"], sub["runtime_ms"], label=algo)
        ax.set_xlabel("Messages envoyés"); ax.set_ylabel("Temps (ms)"); ax.grid(True, alpha=0.3); ax.legend()
        st.pyplot(fig)