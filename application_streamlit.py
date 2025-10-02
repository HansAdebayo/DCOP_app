# application_streamlit.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io

# Importation des fonctions (assure-toi que constructeur_dcop.py est présent)
from constructeur_dcop import (
    generer_positions_aleatoires,
    construire_json_a_partir_positions,
    json_vers_xml,
    afficher_json_joli,
)

# ------------------------------------
# CONFIG
# ------------------------------------
st.set_page_config(page_title="DCOP – Générateur & Bench", page_icon="🚗", layout="wide")
st.title("🚗 Constructeur d'Instance DCOP & Analyse de Benchmark (FRODO)")

# ------------------------------------
# OUTILS UI
# ------------------------------------
def dessiner_scene(voitures, passagers, dest_commune=None, dest_par=None):
    fig, ax = plt.subplots()

    # Voitures
    vx = [v[2][0] for v in voitures]
    vy = [v[2][1] for v in voitures]
    ax.scatter(vx, vy, label="Voitures", marker="s")
    for (id_v, cap, (x, y)) in voitures:
        ax.annotate(f"{id_v} (K={cap})", (x, y), textcoords="offset points", xytext=(5, 5))

    # Passagers
    px = [p[1][0] for p in passagers]
    py = [p[1][1] for p in passagers]
    ax.scatter(px, py, label="Passagers", marker="o")
    for (id_p, (x, y)) in passagers:
        ax.annotate(id_p, (x, y), textcoords="offset points", xytext=(5, 5))

    # Destinations
    if dest_commune is not None:
        ax.scatter([dest_commune[0]], [dest_commune[1]], marker="*", s=150, label="Destination (Commune)")
    if dest_par is not None:
        for id_p, (x, y) in dest_par.items():
            ax.scatter([x], [y], marker="*", s=120)
            ax.annotate(f"Dest({id_p})", (x, y), textcoords="offset points", xytext=(5, 5))

    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.legend()
    st.pyplot(fig)

def boutons_telechargement_json(obj_json, suffixe_cle, modelisation_choisie):
    json_str = afficher_json_joli(obj_json)
    nom_base = obj_json.get("nom", "instance")
    st.download_button(
        "⬇️ Télécharger JSON",
        data=json_str.encode("utf-8"),
        file_name=f"{nom_base}.json",
        mime="application/json",
        key=f"json_{suffixe_cle}",
    )

    xml_str = json_vers_xml(obj_json, modelisation=modelisation_choisie)
    st.download_button(
        f"⬇️ Télécharger XML (Modèle {modelisation_choisie})",
        data=xml_str.encode("utf-8"),
        file_name=f"{nom_base}_M{modelisation_choisie}.xml",
        mime="application/xml",
        key=f"xml_{suffixe_cle}_M{modelisation_choisie}",
    )

def charger_csv_flexible(data):
    """Accepte un chemin (str/Path) OU des bytes d’un uploader, gère `,` ou `;`."""
    if isinstance(data, (bytes, bytearray)):
        stream = io.BytesIO(data)
        try:
            return pd.read_csv(stream)
        except Exception:
            stream.seek(0)
            return pd.read_csv(stream, sep=";")
    else:
        try:
            return pd.read_csv(data)
        except Exception:
            return pd.read_csv(data, sep=";")

def analyse_csv_tab(titre_tab, default_csv_path, uploader_key, chemin_key):
    """Un onglet complet d'analyse (table + synthèse + graphes) sur un CSV donné."""
    st.subheader(titre_tab)

    colp, colu = st.columns(2)
    with colp:
        chemin_csv = st.text_input("Chemin local du CSV", value=default_csv_path, key=chemin_key)
    with colu:
        up = st.file_uploader("…ou uploader un CSV", type=["csv"], key=uploader_key)

    # Chargement
    df = None
    if up is not None:
        df = charger_csv_flexible(up.read())
    elif chemin_csv.strip():
        try:
            df = charger_csv_flexible(chemin_csv.strip())
        except Exception as e:
            st.error(f"Impossible de lire le CSV à '{chemin_csv}': {e}")

    if df is None:
        st.info("Charge un CSV pour continuer. Colonnes attendues : `xml_file, algorithm, total_cost, runtime_ms`.")
        return

    # Nettoyage
    for c in ["total_cost", "runtime_ms", "ncccs", "msgs_total"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Filtres
    cfa, cfi = st.columns(2)
    with cfa:
        algos_tous = sorted(df["algorithm"].dropna().unique().tolist()) if "algorithm" in df.columns else []
        algos_sel = st.multiselect("Algorithmes à afficher", algos_tous, default=algos_tous, key=f"algos_{chemin_key}")
    with cfi:
        inst_tous = sorted(df["xml_file"].dropna().unique().tolist()) if "xml_file" in df.columns else []
        inst_sel = st.multiselect("Instances à afficher", inst_tous, default=inst_tous, key=f"inst_{chemin_key}")

    if "algorithm" in df.columns:
        df = df[df["algorithm"].isin(algos_sel)]
    if "xml_file" in df.columns:
        df = df[df["xml_file"].isin(inst_sel)]
    if df.empty:
        st.warning("Aucune ligne après filtrage. Ajuste tes sélections.")
        return

    # Gap vs meilleur coût par instance
    if {"xml_file", "total_cost"}.issubset(df.columns):
        meilleur_cout = df.groupby("xml_file")["total_cost"].min().rename("meilleur_cout")
        df = df.merge(meilleur_cout, on="xml_file", how="left")
        df["ecart_pct"] = (df["total_cost"] - df["meilleur_cout"]) / df["meilleur_cout"] * 100

    st.markdown("### 📋 Tableau filtré")
    st.dataframe(df.sort_values(["xml_file", "algorithm"]).reset_index(drop=True))

    # Synthèse
    st.markdown("### 📊 Synthèse (moyennes par algorithme)")
    agg = {}
    for c in ["total_cost", "runtime_ms", "ncccs", "msgs_total", "ecart_pct"]:
        if c in df.columns:
            agg[c] = "mean"
    synth = df.groupby("algorithm").agg(agg).reset_index() if agg else pd.DataFrame()
    st.dataframe(synth)

    # Graphiques
    def tracer_barre(series, titre, etiquette_y):
        fig, ax = plt.subplots()
        series.plot(kind="bar", ax=ax)
        ax.set_title(titre)
        ax.set_ylabel(etiquette_y)
        ax.set_xlabel("Algorithme")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(True, axis="y", alpha=0.3)
        st.pyplot(fig)

    if not synth.empty:
        base = synth.set_index("algorithm")
        if "runtime_ms" in base.columns:
            st.markdown("#### ⏱️ Temps moyen d'exécution (ms)")
            tracer_barre(base["runtime_ms"], "Temps moyen", "ms")
        if "total_cost" in base.columns:
            st.markdown("#### 💰 Coût moyen")
            tracer_barre(base["total_cost"], "Coût moyen", "coût")
        if "msgs_total" in base.columns:
            st.markdown("#### ✉️ Messages moyens échangés")
            tracer_barre(base["msgs_total"], "Messages moyens", "messages")
        if "ecart_pct" in base.columns:
            st.markdown("#### Écart moyen à l’optimum (%)")
            tracer_barre(base["ecart_pct"], "Écart moyen à l’optimum", "%")

    # Nuage de points (Messages vs Temps)
    if {"runtime_ms", "msgs_total", "algorithm"}.issubset(df.columns):
        st.markdown("### 🟢 Nuage de points : Messages vs Temps")
        fig, ax = plt.subplots()
        for algo in sorted(df["algorithm"].dropna().unique()):
            sub = df[df["algorithm"] == algo]
            ax.scatter(sub["msgs_total"], sub["runtime_ms"], label=algo)
        ax.set_xlabel("Messages envoyés")
        ax.set_ylabel("Temps (ms)")
        ax.grid(True, alpha=0.3)
        ax.legend()
        st.pyplot(fig)

# ------------------------------------
# NAV
# ------------------------------------
st.sidebar.title("⚙️ Mode")
mode = st.sidebar.radio(
    "Sélectionnez l'action",
    ["Générer une Instance Aléatoire", "Analyser les Résultats CSV"],
)

# ==============================================================================
# 1) GÉNÉRATION D'INSTANCES
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
            modelisation = st.selectbox(
                "Modélisation DCOP",
                options=[1, 2],
                format_func=lambda x: f"M{x}: Var par {'Voit-Pass' if x==1 else 'Passager'}",
            )
        with colB:
            type_depot = st.selectbox("Type de destination (Dépose)", ["Unique (commune)", "Par passager"])
        with colC:
            poids_ramassage = st.number_input("Poids ramassage (Coût de départ)", 0.0, 100.0, 1.0)
        with colD:
            poids_depot = st.number_input("Poids dépose (Coût d'arrivée)", 0.0, 100.0, 1.0)

    dest_commune, dest_par = None, None
    if type_depot == "Unique (commune)":
        st.info("La destination commune sera générée aléatoirement dans le plan.")
    else:
        st.info("Les destinations par passager seront générées aléatoirement (graine différente).")

    if st.button("🚀 Générer Instance et Fichiers"):
        pos_voitures = generer_positions_aleatoires(n_voitures, largeur, hauteur, graine)
        pos_passagers = generer_positions_aleatoires(n_passagers, largeur, hauteur, graine + 1)

        voitures = [(f"v{i+1}", int(cap_defaut), pos_voitures[i]) for i in range(n_voitures)]
        passagers = [(f"p{j+1}", pos_passagers[j]) for j in range(n_passagers)]

        mode_depot = "commun" if type_depot == "Unique (commune)" else "par_passager"
        if mode_depot == "commun":
            dest_commune = generer_positions_aleatoires(1, largeur, hauteur, graine + 500)[0]
        else:
            pos_dest_par = generer_positions_aleatoires(n_passagers, largeur, hauteur, graine + 999)
            dest_par = {passagers[j][0]: pos_dest_par[j] for j in range(n_passagers)}

        obj_json = construire_json_a_partir_positions(
            nom_instance,
            voitures,
            passagers,
            couts_entiers=couts_entiers,
            mode_depot=mode_depot,
            dest_commune=dest_commune,
            dest_par_passager=dest_par,
            poids_ramassage=poids_ramassage,
            poids_depot=poids_depot,
        )

        st.success(f"Instance '{nom_instance}' générée avec succès (Modèle M{modelisation}).")
        col_viz, col_data = st.columns(2)
        with col_viz:
            st.subheader("Aperçu 2D des positions")
            dessiner_scene(voitures, passagers, dest_commune=dest_commune, dest_par=dest_par)
        with col_data:
            st.subheader("Téléchargements")
            boutons_telechargement_json(obj_json, suffixe_cle="rnd", modelisation_choisie=modelisation)
            st.subheader("Matrice des coûts (voitures en lignes)")
            df_costs = pd.DataFrame(obj_json["couts"]).T
            st.dataframe(df_costs)

# ==============================================================================
# 2) ANALYSE DES RÉSULTATS (ONGLETS M1 vs M2)
# ==============================================================================
else:
    st.header("2️⃣ Analyse des Résultats de Benchmark (CSV)")

    # Onglets séparés : Modélisation 1 (bench.csv) et Modélisation 2 (bench2.csv)
    tab1, tab2 = st.tabs(["Modélisation 1 — bench.csv", "Modélisation 2 — bench2.csv"])

    with tab1:
        # Chemin par défaut bench (M1)
        analyse_csv_tab(
            "📁 Résultats Modélisation 1 (bench.csv)",
            default_csv_path="results/bench.csv",
            uploader_key="uploader_bench_m1",
            chemin_key="chemin_bench_m1",
        )

    with tab2:
        # Chemin par défaut bench2 (M2)
        analyse_csv_tab(
            "📁 Résultats Modélisation 2 (bench2.csv)",
            default_csv_path="results/bench2.csv",
            uploader_key="uploader_bench_m2",
            chemin_key="chemin_bench_m2",
        )

    st.markdown("---")
    st.caption("Astuce : Exécute ton lanceur pour remplir `results/bench.csv` et `results/bench2.csv`. Les logs sont dans `results/logs/`.")
