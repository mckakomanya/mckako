#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PASO 2 — ANALISIS BIOESTADISTICO
Cohorte de cancer de mama con radioterapia (n=21).
Endpoint principal: radiodermitis aguda (grado maximo 0-4 y semana de aparicion).

Metodos (adaptados a n pequeno y variables ordinales/categoricas):
  - Descriptivo: media/DE, mediana/RIC, frecuencias.
  - Asociacion categorica: test exacto de Fisher (tablas 2x2).
  - Grado de RD (ordinal) vs factor binario: U de Mann-Whitney.
  - Grado de RD vs subtipo (>2 grupos): Kruskal-Wallis.
  - Correlaciones: Spearman (rho).
  - Tamano de efecto: diferencia de proporciones y r = Z/sqrt(N).

Genera:  resultados_estadisticos.txt  y  figuras/*.png
Uso:  python 02_analisis.py
"""

from pathlib import Path
import warnings
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")
BASE = Path(__file__).resolve().parent
FIG = BASE / "figuras"
FIG.mkdir(exist_ok=True)
OUT = []


def w(*a):
    OUT.append(" ".join(str(x) for x in a))


def fisher_2x2(df, factor, outcome, pos_f="Si", pos_o="Si"):
    """Test exacto de Fisher para factor(Si/No) vs outcome(Si/No)."""
    sub = df.dropna(subset=[factor, outcome])
    a = ((sub[factor] == pos_f) & (sub[outcome] == pos_o)).sum()
    b = ((sub[factor] == pos_f) & (sub[outcome] != pos_o)).sum()
    c = ((sub[factor] != pos_f) & (sub[outcome] == pos_o)).sum()
    d = ((sub[factor] != pos_f) & (sub[outcome] != pos_o)).sum()
    table = [[int(a), int(b)], [int(c), int(d)]]
    orr, p = stats.fisher_exact(table)
    p_exp = a / (a + b) if (a + b) else np.nan   # tasa outcome en expuestos
    p_noexp = c / (c + d) if (c + d) else np.nan
    return table, orr, p, p_exp, p_noexp


def mannwhitney(df, factor, valor, pos="Si"):
    sub = df.dropna(subset=[factor, valor])
    g1 = sub.loc[sub[factor] == pos, valor].astype(float)
    g0 = sub.loc[sub[factor] != pos, valor].astype(float)
    if len(g1) < 2 or len(g0) < 2:
        return None
    U, p = stats.mannwhitneyu(g1, g0, alternative="two-sided")
    n1, n0 = len(g1), len(g0)
    # r = Z / sqrt(N) a partir de U
    mu = n1 * n0 / 2
    sigma = np.sqrt(n1 * n0 * (n1 + n0 + 1) / 12)
    z = (U - mu) / sigma if sigma else np.nan
    r = abs(z) / np.sqrt(n1 + n0)
    return dict(U=U, p=p, r=r, med1=g1.median(), med0=g0.median(),
               n1=n1, n0=n0)


def main():
    df = pd.read_csv(BASE / "datos_limpios.csv")
    N = len(df)

    # ================================================================= #
    w("=" * 72)
    w("ANALISIS BIOESTADISTICO — RADIODERMITIS EN RADIOTERAPIA DE MAMA")
    w("=" * 72)
    w(f"N = {N} pacientes\n")

    # ---------- 1. DESCRIPTIVO ---------------------------------------- #
    w("1. ESTADISTICA DESCRIPTIVA")
    w("-" * 72)
    edad = df["Edad"]
    w(f"Edad: media {edad.mean():.1f} (DE {edad.std():.1f}); "
      f"mediana {edad.median():.0f} (RIC {edad.quantile(.25):.0f}-{edad.quantile(.75):.0f}); "
      f"rango {edad.min()}-{edad.max()}")

    def frec(col):
        vc = df[col].value_counts(dropna=False)
        return "; ".join(f"{k}={v} ({100*v/N:.0f}%)" for k, v in vc.items())

    for col in ["Diabetes", "Tabaquismo_Actual", "Cirugia", "Subtipo_Hist",
                "Fraccionamiento", "Boost", "Irradiacion_ganglionar",
                "Tto_sist_previo", "HT_concurrente", "Ganglios_positivos"]:
        w(f"  {col:22s}: {frec(col)}")

    ki = df["Ki67"].dropna()
    w(f"  Ki67 (n={len(ki)} validos): mediana {ki.median():.0f} "
      f"(RIC {ki.quantile(.25):.0f}-{ki.quantile(.75):.0f}); "
      f"faltantes (incl. codigo 99): {N-len(ki)}")

    w("\n  ENDPOINT — Radiodermitis (Mayor_Gdo_RD):")
    gd = df["Mayor_Gdo_RD"].value_counts().sort_index()
    for g, c in gd.items():
        w(f"     Grado {g}: {c} ({100*c/N:.0f}%)")
    n_sig = (df["Mayor_Gdo_RD"] >= 2).sum()
    w(f"  RD significativa (grado >=2): {n_sig}/{N} ({100*n_sig/N:.1f}%)")
    sem = df["Semana_Presentacion_RD"].dropna()
    w(f"  Semana de aparicion (n={len(sem)} con RD>=1): "
      f"mediana {sem.median():.0f} (rango {sem.min():.0f}-{sem.max():.0f})")

    # ---------- 2. FACTORES vs RD SIGNIFICATIVA (Fisher) --------------- #
    w("\n2. ASOCIACION CON RADIODERMITIS SIGNIFICATIVA (>=grado 2) — Fisher exacto")
    w("-" * 72)
    factores = ["Fraccionamiento", "Irradiacion_ganglionar", "Boost",
                "Diabetes", "Tabaquismo_Actual", "Tto_sist_previo"]
    # Fraccionamiento: exponer 'Normofx' como categoria de interes
    resultados_fisher = []
    for f in factores:
        pos = "Normofx" if f == "Fraccionamiento" else "Si"
        table, orr, p, pe, pne = fisher_2x2(df, f, "RD_significativa",
                                            pos_f=pos, pos_o="Si")
        etiqueta = f"{f} ({pos})"
        w(f"\n  {etiqueta}")
        w(f"     Tabla [expuesto: RD+/RD-] = {table[0]}; [no exp: RD+/RD-] = {table[1]}")
        w(f"     Tasa RD>=2  expuestos: {100*pe:.0f}%   no expuestos: {100*pne:.0f}%")
        w(f"     OR = {orr:.2f}   p (Fisher) = {p:.4f}")
        resultados_fisher.append((etiqueta, pe, pne, orr, p))

    # ---------- 3. GRADO DE RD (ordinal) vs factores (Mann-Whitney) --- #
    w("\n3. GRADO DE RD (ordinal 0-3) vs FACTORES — U de Mann-Whitney")
    w("-" * 72)
    for f, pos in [("Fraccionamiento", "Normofx"), ("Irradiacion_ganglionar", "Si"),
                   ("Boost", "Si"), ("Diabetes", "Si"), ("Tabaquismo_Actual", "Si"),
                   ("Tto_sist_previo", "Si")]:
        r = mannwhitney(df, f, "Mayor_Gdo_RD", pos=pos)
        if r:
            w(f"  {f} ({pos}, n={r['n1']}) vs resto (n={r['n0']}): "
              f"mediana grado {r['med1']:.0f} vs {r['med0']:.0f}; "
              f"U={r['U']:.0f}, p={r['p']:.4f}, r={r['r']:.2f}")

    # ---------- 4. GRADO vs SUBTIPO (Kruskal-Wallis) ------------------ #
    w("\n4. GRADO DE RD vs SUBTIPO HISTOLOGICO — Kruskal-Wallis")
    w("-" * 72)
    grupos = [g["Mayor_Gdo_RD"].values for _, g in df.groupby("Subtipo_Hist")
              if len(g) >= 2]
    nombres = [k for k, g in df.groupby("Subtipo_Hist") if len(g) >= 2]
    if len(grupos) >= 2:
        H, p = stats.kruskal(*grupos)
        w(f"  Grupos (n>=2): {nombres}")
        for n, g in zip(nombres, grupos):
            w(f"     {n}: mediana {np.median(g):.0f} (n={len(g)})")
        w(f"  H = {H:.2f}, p = {p:.4f}")

    # ---------- 5. CORRELACIONES (Spearman) --------------------------- #
    w("\n5. CORRELACIONES (Spearman)")
    w("-" * 72)
    for x, y in [("Edad", "Mayor_Gdo_RD"), ("Ki67", "Mayor_Gdo_RD"),
                 ("Mayor_Gdo_RD", "Semana_Presentacion_RD")]:
        sub = df.dropna(subset=[x, y])
        if len(sub) >= 4:
            rho, p = stats.spearmanr(sub[x], sub[y])
            w(f"  {x} vs {y} (n={len(sub)}): rho={rho:.2f}, p={p:.4f}")

    # ---------- 6. SEMANA DE APARICION vs FRACCIONAMIENTO ------------- #
    w("\n6. SEMANA DE APARICION vs FRACCIONAMIENTO — U de Mann-Whitney")
    w("-" * 72)
    r = mannwhitney(df, "Fraccionamiento", "Semana_Presentacion_RD", pos="Normofx")
    if r:
        w(f"  Normofx (n={r['n1']}) mediana semana {r['med1']:.0f} vs "
          f"Hipofx (n={r['n0']}) {r['med0']:.0f}; U={r['U']:.0f}, p={r['p']:.4f}, r={r['r']:.2f}")

    # ---------- 7. NOTA METODOLOGICA ---------------------------------- #
    w("\n7. NOTA METODOLOGICA")
    w("-" * 72)
    w("  - n=21: analisis exploratorio / generador de hipotesis, sin correccion")
    w("    por comparaciones multiples ni modelos multivariables (potencia insuficiente).")
    w("  - Se usan pruebas no parametricas y exactas por el tamano muestral y la")
    w("    naturaleza ordinal del grado de radiodermitis.")
    w("  - Los 2 carcinomas in situ (pac. 2 y 18) se mantienen en el descriptivo pero")
    w("    carecen de estadificacion TNM completa.")

    # ================================================================= #
    # FIGURAS
    # ================================================================= #
    plt.rcParams.update({"figure.dpi": 120, "font.size": 10})
    AZUL, NAR = "#2E5A87", "#D98032"

    # Fig 1 — distribucion del grado de RD
    fig, ax = plt.subplots(figsize=(6, 4))
    gd = df["Mayor_Gdo_RD"].value_counts().sort_index()
    ax.bar(gd.index.astype(str), gd.values, color=AZUL)
    for x, v in zip(gd.index.astype(str), gd.values):
        ax.text(x, v + 0.1, str(v), ha="center")
    ax.set_xlabel("Grado maximo de radiodermitis")
    ax.set_ylabel("N pacientes")
    ax.set_title("Distribucion del grado de radiodermitis (n=21)")
    fig.tight_layout(); fig.savefig(FIG / "fig1_distribucion_grado_rd.png"); plt.close(fig)

    # Fig 2 — RD significativa por fraccionamiento
    fig, ax = plt.subplots(figsize=(6, 4))
    ct = pd.crosstab(df["Fraccionamiento"], df["RD_significativa"])
    ct = ct.reindex(columns=["No", "Si"], fill_value=0)
    ct.plot(kind="bar", stacked=True, color=["#BBBBBB", NAR], ax=ax)
    ax.set_xlabel("Fraccionamiento"); ax.set_ylabel("N pacientes")
    ax.set_title("Radiodermitis >= grado 2 por fraccionamiento")
    ax.legend(title="RD >=2", labels=["No", "Si"])
    ax.tick_params(axis="x", rotation=0)
    fig.tight_layout(); fig.savefig(FIG / "fig2_rd_por_fraccionamiento.png"); plt.close(fig)

    # Fig 3 — subtipo histologico
    fig, ax = plt.subplots(figsize=(6, 4))
    sc = df["Subtipo_Hist"].value_counts()
    ax.barh(sc.index[::-1], sc.values[::-1], color=AZUL)
    for i, v in enumerate(sc.values[::-1]):
        ax.text(v + 0.05, i, str(v), va="center")
    ax.set_xlabel("N pacientes")
    ax.set_title("Distribucion por subtipo histologico")
    fig.tight_layout(); fig.savefig(FIG / "fig3_subtipos.png"); plt.close(fig)

    # Fig 4 — grado de RD por fraccionamiento (dispersion)
    fig, ax = plt.subplots(figsize=(6, 4))
    for i, (frx, col) in enumerate([("Hipofx", AZUL), ("Normofx", NAR)]):
        y = df.loc[df["Fraccionamiento"] == frx, "Mayor_Gdo_RD"]
        x = np.random.default_rng(i).normal(i, 0.06, len(y))
        ax.scatter(x, y, color=col, s=60, alpha=.8, label=frx)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Hipofx", "Normofx"])
    ax.set_ylabel("Grado de radiodermitis"); ax.set_yticks([0, 1, 2, 3])
    ax.set_title("Grado de RD segun fraccionamiento")
    fig.tight_layout(); fig.savefig(FIG / "fig4_grado_por_fraccionamiento.png"); plt.close(fig)

    # Fig 5 — semana de aparicion por fraccionamiento
    fig, ax = plt.subplots(figsize=(6, 4))
    data = [df.loc[df["Fraccionamiento"] == f, "Semana_Presentacion_RD"].dropna()
            for f in ["Hipofx", "Normofx"]]
    ax.boxplot(data, tick_labels=["Hipofx", "Normofx"])
    ax.set_ylabel("Semana de aparicion de RD")
    ax.set_title("Semana de aparicion segun fraccionamiento")
    fig.tight_layout(); fig.savefig(FIG / "fig5_semana_por_fraccionamiento.png"); plt.close(fig)

    with open(BASE / "resultados_estadisticos.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(OUT) + "\n")

    print("\n".join(OUT))
    print(f"\nFiguras generadas en {FIG}/  (5 PNG)")


if __name__ == "__main__":
    main()
