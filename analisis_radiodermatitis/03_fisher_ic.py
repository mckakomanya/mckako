#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PASO 3 — INFERENCIA: TEST EXACTO DE FISHER CON INTERVALOS DE CONFIANZA
Prediccion de la aparicion de radiodermitis aguda.

Endpoints evaluados:
  (a) APARICION de radiodermitis de cualquier grado (>=1)  [endpoint primario]
  (b) Radiodermitis significativa (>=2)                    [endpoint secundario]

Para cada factor se reporta:
  - Tabla 2x2
  - Riesgo en expuestos y no expuestos con IC95% de Wilson
  - Diferencia de riesgo (IC95% de Newcombe)
  - Riesgo relativo
  - Odds ratio condicional (MLE) con IC95% EXACTO de Fisher
  - p bilateral exacto de Fisher

Genera: resultados_fisher.txt y figuras/fig5_forest_plot.png
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from comun import (carga, FIG, BASE, AZUL, NARANJA, GRIS,
                   fmt_p, num, fisher_ic, tabla_2x2)

OUT = []
def w(*a): OUT.append(" ".join(str(x) for x in a))

# Factores candidatos: (columna, categoria expuesta, etiqueta)
FACTORES = [
    ("Fraccionamiento", "Normofx", "Normofraccionamiento (vs hipofx)"),
    ("Irradiacion_ganglionar", "Si", "Irradiacion ganglionar"),
    ("Ganglios_positivos", "Si", "Ganglios positivos"),
    ("Boost", "Si", "Sobreimpresion (boost)"),
    ("Cirugia", "Mastectomia", "Mastectomia (vs conservadora)"),
    ("Diabetes", "Si", "Diabetes mellitus"),
    ("Tabaquismo_Actual", "Si", "Tabaquismo activo"),
    ("Tto_sist_previo", "Si", "Tto. sistemico previo"),
    ("Edad_65", "Si", "Edad >= 65 anos"),
    ("Ki67_alto", "Si", "Ki67 >= 20%"),
]


def bloque(df, evento, pos_e, titulo):
    """Ejecuta el panel de Fisher para un endpoint y devuelve los resultados."""
    w("")
    w("=" * 74)
    w(titulo)
    w("=" * 74)
    n_ev = (df[evento] == pos_e).sum()
    w(f"  Eventos: {n_ev}/{len(df)} ({num(100*n_ev/len(df))}%)\n")

    res = []
    for col, pos, etiqueta in FACTORES:
        if col not in df.columns:
            continue
        t = tabla_2x2(df, col, evento, pos, pos_e)
        (a, b), (c, d) = t
        if (a + b) == 0 or (c + d) == 0:
            continue
        r = fisher_ic(t)
        r["etiqueta"] = etiqueta
        res.append(r)

        w(f"  {etiqueta}")
        w(f"     Tabla 2x2       expuestos: {a} con / {b} sin evento  |  "
          f"no expuestos: {c} con / {d} sin evento")
        w(f"     Riesgo expuestos    : {num(100*r['r1'])}% "
          f"(IC95% {num(100*r['r1_ic'][0])}-{num(100*r['r1_ic'][1])}%)  n={r['n1']}")
        w(f"     Riesgo no expuestos : {num(100*r['r0'])}% "
          f"(IC95% {num(100*r['r0_ic'][0])}-{num(100*r['r0_ic'][1])}%)  n={r['n0']}")
        w(f"     Diferencia de riesgo: {num(100*r['dr'])} puntos "
          f"(IC95% {num(100*r['dr_ic'][0])} a {num(100*r['dr_ic'][1])})")
        w(f"     Riesgo relativo     : {num(r['rr'], 2)}")
        or_txt = f"{num(r['or_cond'], 2)}"
        w(f"     Odds ratio (cond.)  : {or_txt} "
          f"(IC95% exacto {num(r['or_ic_inf'], 2)} - {num(r['or_ic_sup'], 2)})"
          + ("  [OR muestral con correccion de Haldane: "
             f"{num(r['or_muestral'], 2)}]" if r["haldane"] else ""))
        w(f"     p (Fisher bilateral): {fmt_p(r['p'])}"
          + ("   ** SIGNIFICATIVO **" if r["p"] < 0.05 else ""))
        w("")
    return res


def forest(res, titulo, archivo, nota):
    """Forest plot de odds ratios con IC95% exactos (escala logaritmica)."""
    res = [r for r in res if np.isfinite(r["or_cond"]) or r["or_cond"] > 0]
    n = len(res)
    fig, ax = plt.subplots(figsize=(8.2, 0.45 * n + 1.8))

    LIM_INF, LIM_SUP = 0.02, 500
    for i, r in enumerate(res):
        y = n - i - 1
        or_ = min(max(r["or_cond"], LIM_INF), LIM_SUP) if r["or_cond"] > 0 else LIM_INF
        lo = max(r["or_ic_inf"], LIM_INF) if r["or_ic_inf"] > 0 else LIM_INF
        hi = min(r["or_ic_sup"], LIM_SUP) if np.isfinite(r["or_ic_sup"]) else LIM_SUP
        sig = r["p"] < 0.05
        color = NARANJA if sig else AZUL
        ax.plot([lo, hi], [y, y], color=color, lw=1.6, zorder=2)
        ax.plot([lo, lo], [y - .13, y + .13], color=color, lw=1.6)
        ax.plot([hi, hi], [y - .13, y + .13], color=color, lw=1.6)
        ax.scatter([or_], [y], s=55, color=color, zorder=3,
                   marker="s" if sig else "o")
        # flecha si el IC se sale del marco
        if np.isinf(r["or_ic_sup"]) or r["or_ic_sup"] > LIM_SUP:
            ax.annotate("", xy=(LIM_SUP, y), xytext=(LIM_SUP * 0.45, y),
                        arrowprops=dict(arrowstyle="->", color=color, lw=1.6))
        etiqueta = (f"{r['etiqueta']}   OR {num(r['or_cond'],2)} "
                    f"({num(r['or_ic_inf'],2)}-"
                    f"{'∞' if np.isinf(r['or_ic_sup']) else num(r['or_ic_sup'],2)}), "
                    f"p={fmt_p(r['p'])}")
        ax.text(LIM_INF * 0.75, y, etiqueta, ha="right", va="center",
                fontsize=7.6, fontweight="bold" if sig else "normal")

    ax.axvline(1, color=GRIS, ls="--", lw=1.2, zorder=1)
    ax.set_xscale("log")
    ax.set_xlim(LIM_INF, LIM_SUP)
    ax.set_ylim(-0.8, n - 0.2)
    ax.set_yticks([])
    ax.set_xticks([0.1, 1, 10, 100])
    ax.set_xticklabels(["0,1", "1", "10", "100"])
    ax.set_xlabel("Odds ratio (IC95% exacto de Fisher) — escala logaritmica")
    for s in ("left", "right", "top"):
        ax.spines[s].set_visible(False)
    ax.set_title(titulo, fontsize=10, fontweight="bold", loc="left", x=-0.02)
    fig.tight_layout(rect=[0, 0.06, 1, 1])
    fig.text(0.5, 0.015, nota, ha="center", fontsize=7.2, color="#555555")
    fig.savefig(FIG / archivo, bbox_inches="tight")
    plt.close(fig)


def main():
    df = carga()

    # Variables dicotomizadas para el analisis de riesgo
    df["Edad_65"] = np.where(df["Edad"] >= 65, "Si", "No")
    df["Ki67_alto"] = df["Ki67"].map(
        lambda v: np.nan if pd.isna(v) else ("Si" if v >= 20 else "No"))
    df["RD_aparicion"] = np.where(df["Mayor_Gdo_RD"] >= 1, "Si", "No")

    w("=" * 74)
    w("ANALISIS INFERENCIAL — TEST EXACTO DE FISHER CON IC95%")
    w("=" * 74)
    w("Metodo: test exacto de Fisher bilateral. El odds ratio se estima por")
    w("maxima verosimilitud condicional y su IC95% es el intervalo EXACTO")
    w("condicional (no aproximacion de Wald), apropiado con n pequeno y")
    w("frecuencias esperadas < 5. Los riesgos llevan IC de Wilson y la")
    w("diferencia de riesgos el IC hibrido de Newcombe.")

    res_a = bloque(df, "RD_aparicion", "Si",
                   "(a) ENDPOINT PRIMARIO: APARICION DE RADIODERMITIS (cualquier grado)")
    res_b = bloque(df, "RD_significativa", "Si",
                   "(b) ENDPOINT SECUNDARIO: RADIODERMITIS SIGNIFICATIVA (>= grado 2)")

    w("")
    w("=" * 74)
    w("NOTA SOBRE INTERPRETACION")
    w("=" * 74)
    w("  - Un IC95% del OR que incluye el 1 indica ausencia de significacion.")
    w("  - Con n=21 los intervalos son necesariamente amplios: la ausencia de")
    w("    significacion NO equivale a ausencia de efecto (error tipo II).")
    w("  - No se aplica correccion por comparaciones multiples: el analisis es")
    w("    exploratorio y generador de hipotesis.")
    w("  - Normofraccionamiento e irradiacion ganglionar estan colinealizados")
    w("    (ver seccion 2.5); sus OR no deben interpretarse como independientes.")
    w("  - DISCORDANCIA p vs IC (endpoint primario, normofraccionamiento):")
    w("    el p exacto es 0,047 (significativo) mientras el IC95% condicional")
    w("    del OR (0,93 a infinito) incluye el 1. No es un error: el IC exacto")
    w("    de Cornfield es CONSERVADOR respecto al p bilateral de Fisher, y")
    w("    ambos pueden discrepar cuando existe una celda con frecuencia 0")
    w("    (aqui: 0 normofraccionados libres de radiodermitis), lo que hace")
    w("    que el OR no sea estimable (infinito). En este escenario la medida")
    w("    interpretable es la DIFERENCIA DE RIESGO: +50,0 puntos porcentuales")
    w("    (IC95% 7,6 a 73,2), que si excluye el 0 y confirma la asociacion.")

    forest(res_a,
           "Figura 5. Factores predictores de la APARICION de radiodermitis "
           "(cualquier grado)",
           "fig5_forest_aparicion.png",
           "OR > 1 indica mayor riesgo de radiodermitis. En naranja, "
           "asociaciones estadisticamente significativas (p<0,05).")
    forest(res_b,
           "Figura 6. Factores predictores de radiodermitis significativa "
           "(>= grado 2)",
           "fig6_forest_significativa.png",
           "OR > 1 indica mayor riesgo. En naranja, asociaciones "
           "estadisticamente significativas (p<0,05).")

    with open(BASE / "resultados_fisher.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(OUT) + "\n")
    print("\n".join(OUT))
    print("\nFiguras: fig5_forest_aparicion.png, fig6_forest_significativa.png")


if __name__ == "__main__":
    main()
