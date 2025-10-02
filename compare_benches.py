#!/usr/bin/env python3
# compare_benches.py — Comparaison M1 (bench.csv) vs M2 (bench2.csv) sans comparer les coûts
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import argparse

# ---------- IO utils ----------
def read_flexible(path: Path) -> pd.DataFrame:
    """Lit un CSV avec , puis ; en fallback."""
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.read_csv(path, sep=";")

def coerce_numeric(df: pd.DataFrame, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# ---------- Aggregations ----------
def algo_summary(df: pd.DataFrame, metrics):
    """
    Retourne moyennes/médianes par algorithme pour metrics (list).
    columns: algorithm, mean_<m>, median_<m>
    """
    keep = ["algorithm"] + [c for c in metrics if c in df.columns]
    dff = df[keep].dropna(subset=["algorithm"]).copy()
    if dff.empty:
        return pd.DataFrame()
    agg = {m: ["mean", "median"] for m in metrics if m in dff.columns}
    out = dff.groupby("algorithm").agg(agg)
    out.columns = [f"{stat}_{metric}" for metric, stat in out.columns.to_flat_index()]
    out = out.reset_index()
    return out

# ---------- Plots ----------
def grouped_bar_compare(df_m1, df_m2, metric_mean_col, title, ylabel, out_png: Path):
    """
    df_m1/df_m2: DataFrames avec index 'algorithm' et colonne metric_mean_col (ex: 'mean_runtime_ms').
    trace un graphe barres groupées M1 vs M2 par algorithme commun.
    """
    algs1 = set(df_m1.index)
    algs2 = set(df_m2.index)
    common_algos = sorted(algs1 & algs2)
    if not common_algos:
        print(f"[WARN] Aucun algorithme commun trouvé pour {metric_mean_col}.")
        return

    m1_vals = [df_m1.loc[a, metric_mean_col] if a in df_m1.index else np.nan for a in common_algos]
    m2_vals = [df_m2.loc[a, metric_mean_col] if a in df_m2.index else np.nan for a in common_algos]

    x = np.arange(len(common_algos))
    width = 0.35
    fig, ax = plt.subplots()
    ax.bar(x - width/2, m1_vals, width, label="M1 (bench)")
    ax.bar(x + width/2, m2_vals, width, label="M2 (bench2)")
    ax.set_xticks(x)
    ax.set_xticklabels(common_algos, rotation=45, ha="right")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.show()
    print(f"[OK] Sauvé : {out_png}")

# ---------- Main ----------
def main():
    ap = argparse.ArgumentParser(description="Comparer bench.csv (M1) et bench2.csv (M2) sans comparer les coûts.")
    ap.add_argument("--bench", default="results/bench.csv", help="CSV Modélisation 1")
    ap.add_argument("--bench2", default="results/bench2.csv", help="CSV Modélisation 2")
    ap.add_argument("--outdir", default="results/figs_compare", help="Dossier de sortie des figures")
    args = ap.parse_args()

    p1 = Path(args.bench).expanduser().resolve()
    p2 = Path(args.bench2).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    # Lecture
    df1 = read_flexible(p1)
    df2 = read_flexible(p2)

    # Coercition numérique (SANS total_cost)
    metrics = ["runtime_ms", "msgs_total", "ncccs"]
    df1 = coerce_numeric(df1, metrics)
    df2 = coerce_numeric(df2, metrics)

    # Synthèses par algorithme
    sum_m1 = algo_summary(df1, metrics)
    sum_m2 = algo_summary(df2, metrics)

    if sum_m1.empty or sum_m2.empty:
        print("[ERR] Impossible de produire des comparaisons : synthèse vide. Vérifiez colonnes et contenu.")
        return

    # Index par algo pour accès facile
    m1 = sum_m1.set_index("algorithm")
    m2 = sum_m2.set_index("algorithm")

    # Sauvegarde des synthèses nettoyées
    sum_m1_path = outdir / "summary_M1_no_cost.csv"
    sum_m2_path = outdir / "summary_M2_no_cost.csv"
    sum_m1.to_csv(sum_m1_path, index=False)
    sum_m2.to_csv(sum_m2_path, index=False)
    print(f"[OK] Synthèses sauvées: {sum_m1_path} ; {sum_m2_path}")

    # Graphes comparatifs (moyennes)
    if "mean_runtime_ms" in m1.columns and "mean_runtime_ms" in m2.columns:
        grouped_bar_compare(
            m1, m2, "mean_runtime_ms",
            "Temps d'exécution moyen (ms) — M1 vs M2",
            "ms",
            outdir / "compare_mean_runtime_ms.png"
        )
    if "mean_msgs_total" in m1.columns and "mean_msgs_total" in m2.columns:
        grouped_bar_compare(
            m1, m2, "mean_msgs_total",
            "Messages moyens échangés — M1 vs M2",
            "messages",
            outdir / "compare_mean_msgs_total.png"
        )
    if "mean_ncccs" in m1.columns and "mean_ncccs" in m2.columns:
        grouped_bar_compare(
            m1, m2, "mean_ncccs",
            "NCCCs moyens — M1 vs M2",
            "NCCCs",
            outdir / "compare_mean_ncccs.png"
        )

    # (Optionnel) Graphes comparatifs (médianes)
    if "median_runtime_ms" in m1.columns and "median_runtime_ms" in m2.columns:
        grouped_bar_compare(
            m1, m2, "median_runtime_ms",
            "Temps d'exécution médian (ms) — M1 vs M2",
            "ms",
            outdir / "compare_median_runtime_ms.png"
        )
    if "median_msgs_total" in m1.columns and "median_msgs_total" in m2.columns:
        grouped_bar_compare(
            m1, m2, "median_msgs_total",
            "Messages médians échangés — M1 vs M2",
            "messages",
            outdir / "compare_median_msgs_total.png"
        )
    if "median_ncccs" in m1.columns and "median_ncccs" in m2.columns:
        grouped_bar_compare(
            m1, m2, "median_ncccs",
            "NCCCs médians — M1 vs M2",
            "NCCCs",
            outdir / "compare_median_ncccs.png"
        )

if __name__ == "__main__":
    main()
