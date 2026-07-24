#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PASO 2 — ANALISIS POBLACIONAL
Caracterizacion de la poblacion de estudio (n=21): demografia, comorbilidad,
caracteristicas tumorales, biomarcadores y tratamiento recibido.
Incluye contraste de normalidad y comparacion de la poblacion segun el
esquema de fraccionamiento (principal variable de exposicion).

Genera:  resultados_poblacional.txt  y  figuras/fig1..fig4
"""

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from comun import carga, FIG, BASE, AZUL, NARANJA, GRIS, fmt_p, num, ic_wilson

OUT = []
def w(*a): OUT.append(" ".join(str(x) for x in a))


def desc_cuant(s, nombre):
    s = s.dropna().astype(float)
    sw_p = stats.shapiro(s)[1] if len(s) >= 3 else np.nan
    normal = sw_p > 0.05 if not np.isnan(sw_p) else False
    w(f"  {nombre} (n={len(s)})")
    w(f"     Media (DE)      : {num(s.mean())} ({num(s.std(ddof=1))})")
    w(f"     Mediana (RIC)   : {num(s.median())} "
      f"({num(s.quantile(.25))}-{num(s.quantile(.75))})")
    w(f"     Rango           : {num(s.min())}-{num(s.max())}")
    w(f"     Shapiro-Wilk    : p={fmt_p(sw_p)} "
      f"({'distribucion normal' if normal else 'NO normal -> pruebas no parametricas'})")
    return normal


def desc_cual(df, col, nombre=None):
    nombre = nombre or col
    n = df[col].notna().sum()
    vc = df[col].value_counts(dropna=True)
    w(f"  {nombre} (n={n})")
    for k, v in vc.items():
        lo, hi = ic_wilson(v, n)
        w(f"     {str(k):22s}: {v:2d} ({num(100*v/n)}%)  IC95% {num(100*lo)}-{num(100*hi)}%")


def main():
    df = carga()
    N = len(df)

    w("=" * 74)
    w("ANALISIS POBLACIONAL — COHORTE DE CANCER DE MAMA CON RADIOTERAPIA")
    w("=" * 74)
    w(f"Poblacion de estudio: N = {N} pacientes\n")

    # ---------------- 2.1 Demografia y comorbilidad ------------------- #
    w("2.1. CARACTERISTICAS DEMOGRAFICAS Y COMORBILIDAD")
    w("-" * 74)
    edad_normal = desc_cuant(df["Edad"], "Edad (anos)")

    # Distribucion por grupos etarios
    cortes = [0, 50, 65, 200]
    etiq = ["<50", "50-64", ">=65"]
    df["Grupo_edad"] = pd.cut(df["Edad"], bins=cortes, labels=etiq, right=False)
    w("")
    desc_cual(df, "Grupo_edad", "Grupo etario (anos)")
    w("")
    desc_cual(df, "Diabetes", "Diabetes mellitus")
    desc_cual(df, "Tabaquismo_Actual", "Tabaquismo activo")

    # ---------------- 2.2 Caracteristicas tumorales ------------------- #
    w("\n2.2. CARACTERISTICAS TUMORALES E HISTOPATOLOGICAS")
    w("-" * 74)
    desc_cual(df, "pT_cat", "Categoria T (pT)")
    desc_cual(df, "pN_cat", "Categoria N (pN)")
    desc_cual(df, "Ganglios_positivos", "Afectacion ganglionar")
    desc_cual(df, "GHF", "Grado histologico (GHF)")
    desc_cual(df, "Subtipo_Hist", "Subtipo molecular")
    desc_cual(df, "Estadificacion_Anatomica", "Estadio anatomico")
    desc_cual(df, "Multifocal", "Multifocalidad")

    w("")
    desc_cual(df, "ER", "Receptor de estrogeno (ER)")
    desc_cual(df, "PR", "Receptor de progesterona (PR)")
    desc_cual(df, "Her2", "Sobreexpresion HER2")
    w("")
    ki67_normal = desc_cuant(df["Ki67"], "Ki67 (%)")
    ki = df["Ki67"].dropna()
    alto = (ki >= 20).sum()
    lo, hi = ic_wilson(alto, len(ki))
    w(f"     Ki67 alto (>=20%): {alto}/{len(ki)} ({num(100*alto/len(ki))}%) "
      f"IC95% {num(100*lo)}-{num(100*hi)}%")
    w(f"     Nota: 2 casos de carcinoma in situ sin Ki67 evaluado.")

    # ---------------- 2.3 Tratamiento --------------------------------- #
    w("\n2.3. CARACTERISTICAS DEL TRATAMIENTO")
    w("-" * 74)
    desc_cual(df, "Cirugia", "Tipo de cirugia")
    desc_cual(df, "Tto_sist_previo", "Tratamiento sistemico previo a RT")
    tipos = df["Tipo_Tto_Sist"].dropna()
    if len(tipos):
        w(f"     Esquemas empleados: {', '.join(sorted(tipos.unique()))}")
    desc_cual(df, "HT_concurrente", "Hormonoterapia concurrente")
    w("")
    desc_cual(df, "Fraccionamiento", "Esquema de fraccionamiento")
    desc_cual(df, "Boost", "Sobreimpresion (boost)")
    desc_cual(df, "CTV_N_Ax", "CTV ganglionar axilar")
    desc_cual(df, "CTV_N_III_SC", "CTV nivel III / supraclavicular")
    desc_cual(df, "Irradiacion_ganglionar", "Irradiacion ganglionar (cualquiera)")
    w("")
    desc_cuant(df["Duracion_RT_sem"], "Duracion prevista de la RT (semanas)")

    # ---------------- 2.4 Endpoint primario --------------------------- #
    w("\n2.4. ENDPOINT PRIMARIO — RADIODERMITIS AGUDA")
    w("-" * 74)
    w("  Distribucion del grado maximo (escala RTOG/CTCAE 0-4):")
    gd = df["Mayor_Gdo_RD"].value_counts().sort_index()
    for g, c in gd.items():
        lo, hi = ic_wilson(c, N)
        w(f"     Grado {g}: {c:2d} ({num(100*c/N)}%)  IC95% {num(100*lo)}-{num(100*hi)}%")
    for umbral, txt in [(1, "cualquier grado (>=1)"), (2, "significativa (>=2)"),
                        (3, "severa (>=3)")]:
        k = (df["Mayor_Gdo_RD"] >= umbral).sum()
        lo, hi = ic_wilson(k, N)
        w(f"  Radiodermitis {txt:24s}: {k:2d}/{N} ({num(100*k/N)}%) "
          f"IC95% {num(100*lo)}-{num(100*hi)}%")
    w("")
    desc_cuant(df["Semana_Presentacion_RD"], "Semana de aparicion (solo casos con RD)")

    # ---------------- 2.5 Comparabilidad de los grupos ---------------- #
    w("\n2.5. COMPARABILIDAD DE LA POBLACION SEGUN FRACCIONAMIENTO")
    w("-" * 74)
    w("  (Tabla 1: contraste de las caracteristicas basales entre esquemas)")
    hipo = df[df["Fraccionamiento"] == "Hipofx"]
    normo = df[df["Fraccionamiento"] == "Normofx"]
    w(f"  Hipofraccionamiento n={len(hipo)} | Normofraccionamiento n={len(normo)}\n")

    # Cuantitativas -> Mann-Whitney (poblacion pequena, no normalidad garantizada)
    for var, nombre in [("Edad", "Edad (anos)"), ("Ki67", "Ki67 (%)")]:
        a = hipo[var].dropna().astype(float)
        b = normo[var].dropna().astype(float)
        if len(a) >= 2 and len(b) >= 2:
            p = stats.mannwhitneyu(a, b, alternative="two-sided")[1]
            w(f"  {nombre:26s} mediana {num(a.median())} vs {num(b.median())}  "
              f"p={fmt_p(p)}")

    # Cualitativas -> Fisher
    for var, pos, nombre in [
        ("Diabetes", "Si", "Diabetes"),
        ("Tabaquismo_Actual", "Si", "Tabaquismo activo"),
        ("Cirugia", "Mastectomia", "Mastectomia"),
        ("Ganglios_positivos", "Si", "Ganglios positivos"),
        ("Irradiacion_ganglionar", "Si", "Irradiacion ganglionar"),
        ("Boost", "Si", "Boost"),
        ("Tto_sist_previo", "Si", "Tto. sistemico previo"),
    ]:
        a1 = (hipo[var] == pos).sum(); a0 = len(hipo) - a1
        b1 = (normo[var] == pos).sum(); b0 = len(normo) - b1
        p = stats.fisher_exact([[a1, a0], [b1, b0]])[1]
        w(f"  {nombre:26s} {a1}/{len(hipo)} ({num(100*a1/len(hipo))}%) vs "
          f"{b1}/{len(normo)} ({num(100*b1/len(normo))}%)  p={fmt_p(p)}")

    w("\n  HALLAZGO CRITICO — colinealidad entre exposiciones:")
    ct = pd.crosstab(df["Fraccionamiento"], df["Irradiacion_ganglionar"])
    w(f"     {ct.to_string()}")
    w("     Los 7 pacientes normofraccionados recibieron TODOS irradiacion")
    w("     ganglionar y ningun normofraccionado prescindio de ella. Ambas")
    w("     exposiciones estan casi perfectamente confundidas: sus efectos")
    w("     no son separables con este tamano muestral.")

    # ================================================================= #
    # FIGURAS
    # ================================================================= #
    plt.rcParams.update({"figure.dpi": 130, "font.size": 9,
                         "axes.spines.top": False, "axes.spines.right": False})

    # Figura 1 — piramide de edad + distribucion
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
    axes[0].hist(df["Edad"], bins=np.arange(25, 90, 10), color=AZUL,
                 edgecolor="white")
    axes[0].axvline(df["Edad"].mean(), color=NARANJA, ls="--", lw=2,
                    label=f"Media {df['Edad'].mean():.1f}")
    axes[0].set_xlabel("Edad (anos)"); axes[0].set_ylabel("N pacientes")
    axes[0].set_title("A. Distribucion de la edad"); axes[0].legend(frameon=False)
    vc = df["Grupo_edad"].value_counts().reindex(etiq)
    axes[1].bar(vc.index.astype(str), vc.values, color=AZUL)
    for x, v in zip(vc.index.astype(str), vc.values):
        axes[1].text(x, v + .1, str(v), ha="center")
    axes[1].set_xlabel("Grupo etario (anos)"); axes[1].set_ylabel("N pacientes")
    axes[1].set_title("B. Grupos etarios")
    fig.suptitle("Figura 1. Caracterizacion etaria de la poblacion (n=21)",
                 y=1.02, fontsize=10, fontweight="bold")
    fig.tight_layout(); fig.savefig(FIG / "fig1_poblacion_edad.png",
                                    bbox_inches="tight"); plt.close(fig)

    # Figura 2 — caracteristicas tumorales
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4))
    for ax, (col, tit) in zip(axes, [("Subtipo_Hist", "A. Subtipo molecular"),
                                     ("pT_cat", "B. Categoria T"),
                                     ("Estadificacion_Anatomica", "C. Estadio anatomico")]):
        vc = df[col].value_counts().sort_index()
        ax.barh(vc.index.astype(str), vc.values, color=AZUL)
        for i, v in enumerate(vc.values):
            ax.text(v + .08, i, str(v), va="center", fontsize=8)
        ax.set_xlabel("N pacientes"); ax.set_title(tit)
        ax.set_xlim(0, max(vc.values) * 1.2)
    fig.suptitle("Figura 2. Caracteristicas tumorales de la poblacion",
                 y=1.03, fontsize=10, fontweight="bold")
    fig.tight_layout(); fig.savefig(FIG / "fig2_poblacion_tumor.png",
                                    bbox_inches="tight"); plt.close(fig)

    # Figura 3 — tratamiento
    fig, ax = plt.subplots(figsize=(7, 3.6))
    items = [("Cirugia conservadora", (df["Cirugia"] == "CC").sum()),
             ("Hipofraccionamiento", (df["Fraccionamiento"] == "Hipofx").sum()),
             ("Boost", (df["Boost"] == "Si").sum()),
             ("Irradiacion ganglionar", (df["Irradiacion_ganglionar"] == "Si").sum()),
             ("Tto. sistemico previo", (df["Tto_sist_previo"] == "Si").sum()),
             ("HT concurrente", (df["HT_concurrente"] == "Si").sum())]
    nom = [i[0] for i in items][::-1]
    val = [100 * i[1] / N for i in items][::-1]
    cnt = [i[1] for i in items][::-1]
    ax.barh(nom, val, color=AZUL)
    for i, (v, c) in enumerate(zip(val, cnt)):
        ax.text(v + 1.5, i, f"{c} ({v:.0f}%)", va="center", fontsize=8)
    ax.set_xlim(0, 100); ax.set_xlabel("% de la poblacion")
    ax.set_title("Figura 3. Tratamiento recibido (n=21)", fontweight="bold",
                 fontsize=10)
    fig.tight_layout(); fig.savefig(FIG / "fig3_poblacion_tratamiento.png",
                                    bbox_inches="tight"); plt.close(fig)

    # Figura 4 — endpoint primario
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
    gd = df["Mayor_Gdo_RD"].value_counts().sort_index()
    colores = [GRIS, "#F2C078", NARANJA, "#B5442A"]
    axes[0].bar(gd.index.astype(str), gd.values,
                color=[colores[int(g)] for g in gd.index])
    for x, v in zip(gd.index.astype(str), gd.values):
        axes[0].text(x, v + .1, f"{v}\n({100*v/N:.0f}%)", ha="center", fontsize=8)
    axes[0].set_xlabel("Grado maximo de radiodermitis")
    axes[0].set_ylabel("N pacientes"); axes[0].set_ylim(0, max(gd.values) * 1.35)
    axes[0].set_title("A. Grado maximo alcanzado")
    sem = df["Semana_Presentacion_RD"].dropna()
    vc = sem.value_counts().sort_index()
    axes[1].bar(vc.index.astype(int).astype(str), vc.values, color=NARANJA)
    for x, v in zip(vc.index.astype(int).astype(str), vc.values):
        axes[1].text(x, v + .1, str(v), ha="center", fontsize=8)
    axes[1].set_xlabel("Semana de aparicion"); axes[1].set_ylabel("N pacientes")
    axes[1].set_ylim(0, max(vc.values) * 1.25)
    axes[1].set_title("B. Semana de aparicion (n=14)")
    fig.suptitle("Figura 4. Endpoint primario: radiodermitis aguda",
                 y=1.02, fontsize=10, fontweight="bold")
    fig.tight_layout(); fig.savefig(FIG / "fig4_endpoint_rd.png",
                                    bbox_inches="tight"); plt.close(fig)

    with open(BASE / "resultados_poblacional.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(OUT) + "\n")
    print("\n".join(OUT))
    print("\nFiguras: fig1_poblacion_edad, fig2_poblacion_tumor, "
          "fig3_poblacion_tratamiento, fig4_endpoint_rd")


if __name__ == "__main__":
    main()
