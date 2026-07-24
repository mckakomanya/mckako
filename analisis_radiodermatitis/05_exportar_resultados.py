#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PASO 5 — EXPORTACION DE RESULTADOS A JSON
Recalcula todas las cifras que aparecen en el informe y las vuelca a
informe_datos.json, de modo que el documento Word se construya a partir de
los resultados reales y no de numeros transcritos a mano.
"""

import json
import numpy as np
import pandas as pd
from scipy import stats

from comun import (carga, BASE, fmt_p, num, fisher_ic, tabla_2x2,
                   kaplan_meier, mediana_km, logrank, ic_wilson)

FACTORES = [
    ("Fraccionamiento", "Normofx", "Normofraccionamiento (vs hipofraccionamiento)"),
    ("Irradiacion_ganglionar", "Si", "Irradiación ganglionar"),
    ("Ganglios_positivos", "Si", "Ganglios positivos"),
    ("Boost", "Si", "Sobreimpresión (boost)"),
    ("Cirugia", "Mastectomia", "Mastectomía (vs conservadora)"),
    ("Diabetes", "Si", "Diabetes mellitus"),
    ("Tabaquismo_Actual", "Si", "Tabaquismo activo"),
    ("Tto_sist_previo", "Si", "Tratamiento sistémico previo"),
    ("Edad_65", "Si", "Edad ≥ 65 años"),
    ("Ki67_alto", "Si", "Ki67 ≥ 20 %"),
]


def pct(k, n):
    lo, hi = ic_wilson(k, n)
    return dict(k=int(k), n=int(n), pct=100 * k / n,
                ic=[100 * lo, 100 * hi],
                txt=f"{k}/{n} ({num(100*k/n)} %)",
                txt_ic=f"{num(100*k/n)} % (IC95% {num(100*lo)}–{num(100*hi)})")


def cuant(s):
    s = s.dropna().astype(float)
    sw = stats.shapiro(s)[1] if len(s) >= 3 else np.nan
    return dict(n=int(len(s)), media=float(s.mean()), de=float(s.std(ddof=1)),
                mediana=float(s.median()), q1=float(s.quantile(.25)),
                q3=float(s.quantile(.75)), min=float(s.min()),
                max=float(s.max()), shapiro_p=float(sw),
                normal=bool(sw > 0.05),
                txt_media=f"{num(s.mean())} ± {num(s.std(ddof=1))}",
                txt_mediana=f"{num(s.median())} ({num(s.quantile(.25))}–"
                            f"{num(s.quantile(.75))})",
                txt_rango=f"{num(s.min())}–{num(s.max())}")


def frecuencias(df, col):
    n = int(df[col].notna().sum())
    out = []
    for k, v in df[col].value_counts().items():
        lo, hi = ic_wilson(v, n)
        out.append(dict(categoria=str(k), k=int(v), n=n, pct=100 * v / n,
                        ic=[100 * lo, 100 * hi]))
    return out


def main():
    df = carga()
    N = len(df)
    df["Edad_65"] = np.where(df["Edad"] >= 65, "Si", "No")
    df["Ki67_alto"] = df["Ki67"].map(
        lambda v: np.nan if pd.isna(v) else ("Si" if v >= 20 else "No"))
    df["RD_aparicion"] = np.where(df["Mayor_Gdo_RD"] >= 1, "Si", "No")

    D = {"N": N}

    # ---------- Poblacion ------------------------------------------- #
    D["edad"] = cuant(df["Edad"])
    D["ki67"] = cuant(df["Ki67"])
    D["semana_rd"] = cuant(df["Semana_Presentacion_RD"])
    df["Grupo_edad"] = pd.cut(df["Edad"], [0, 50, 65, 200],
                              labels=["<50", "50-64", "≥65"], right=False)
    D["frecuencias"] = {c: frecuencias(df, c) for c in
                        ["Grupo_edad", "Diabetes", "Tabaquismo_Actual",
                         "Cirugia", "pT_cat", "pN_cat", "Ganglios_positivos",
                         "GHF", "Subtipo_Hist", "Estadificacion_Anatomica",
                         "ER", "PR", "Her2", "Multifocal", "Fraccionamiento",
                         "Boost", "Irradiacion_ganglionar", "Tto_sist_previo",
                         "HT_concurrente"]}

    # ---------- Endpoint -------------------------------------------- #
    D["rd_grados"] = [pct((df["Mayor_Gdo_RD"] == g).sum(), N) | {"grado": int(g)}
                      for g in sorted(df["Mayor_Gdo_RD"].unique())]
    D["rd_umbrales"] = {
        "cualquiera": pct((df["Mayor_Gdo_RD"] >= 1).sum(), N),
        "significativa": pct((df["Mayor_Gdo_RD"] >= 2).sum(), N),
        "severa": pct((df["Mayor_Gdo_RD"] >= 3).sum(), N),
    }

    # ---------- Comparabilidad basal (tabla 1) ----------------------- #
    hipo = df[df["Fraccionamiento"] == "Hipofx"]
    normo = df[df["Fraccionamiento"] == "Normofx"]
    basal = []
    for var, nombre in [("Edad", "Edad, mediana (años)"), ("Ki67", "Ki67, mediana (%)")]:
        a = hipo[var].dropna().astype(float); b = normo[var].dropna().astype(float)
        p = stats.mannwhitneyu(a, b, alternative="two-sided")[1]
        basal.append(dict(variable=nombre, hipo=num(a.median()),
                          normo=num(b.median()), p=fmt_p(p), sig=bool(p < .05)))
    for var, pos, nombre in [
            ("Diabetes", "Si", "Diabetes"), ("Tabaquismo_Actual", "Si", "Tabaquismo activo"),
            ("Cirugia", "Mastectomia", "Mastectomía"),
            ("Ganglios_positivos", "Si", "Ganglios positivos"),
            ("Irradiacion_ganglionar", "Si", "Irradiación ganglionar"),
            ("Boost", "Si", "Boost"), ("Tto_sist_previo", "Si", "Tto. sistémico previo")]:
        a1 = int((hipo[var] == pos).sum()); b1 = int((normo[var] == pos).sum())
        p = stats.fisher_exact([[a1, len(hipo) - a1], [b1, len(normo) - b1]])[1]
        basal.append(dict(variable=nombre,
                          hipo=f"{a1}/{len(hipo)} ({num(100*a1/len(hipo))} %)",
                          normo=f"{b1}/{len(normo)} ({num(100*b1/len(normo))} %)",
                          p=fmt_p(p), sig=bool(p < .05)))
    D["tabla_basal"] = basal
    D["n_hipo"], D["n_normo"] = len(hipo), len(normo)
    ct = pd.crosstab(df["Fraccionamiento"], df["Irradiacion_ganglionar"])
    D["colinealidad"] = ct.to_dict()

    # ---------- Fisher ----------------------------------------------- #
    def panel(evento, pos_e):
        filas = []
        for col, pos, etiqueta in FACTORES:
            t = tabla_2x2(df, col, evento, pos, pos_e)
            (a, b), (c, d) = t
            if (a + b) == 0 or (c + d) == 0:
                continue
            r = fisher_ic(t)
            filas.append(dict(
                factor=etiqueta, a=a, b=b, c=c, d=d,
                r1=100 * r["r1"], r0=100 * r["r0"],
                r1_txt=f"{num(100*r['r1'])} %", r0_txt=f"{num(100*r['r0'])} %",
                dr_txt=f"{num(100*r['dr'])} ({num(100*r['dr_ic'][0])} a "
                       f"{num(100*r['dr_ic'][1])})",
                dr_sig=bool(r["dr_ic"][0] > 0 or r["dr_ic"][1] < 0),
                or_txt=("∞" if not np.isfinite(r["or_cond"]) else num(r["or_cond"], 2)),
                or_ic_txt=f"{num(r['or_ic_inf'],2)}–"
                          f"{'∞' if not np.isfinite(r['or_ic_sup']) else num(r['or_ic_sup'],2)}",
                p=fmt_p(r["p"]), p_val=float(r["p"]), sig=bool(r["p"] < .05)))
        return filas

    D["fisher_aparicion"] = panel("RD_aparicion", "Si")
    D["fisher_significativa"] = panel("RD_significativa", "Si")

    # ---------- Kaplan-Meier ----------------------------------------- #
    km = kaplan_meier(df["KM_tiempo"], df["KM_evento"])
    D["km_global"] = dict(
        eventos=int(df["KM_evento"].sum()),
        censurados=int((df["KM_evento"] == 0).sum()),
        mediana=mediana_km(km),
        tabla=[dict(t=float(r["t"]), n=int(r["n_riesgo"]), ev=int(r["eventos"]),
                    cen=int(r["censurados"]), S=100 * r["S"],
                    S_txt=f"{num(100*r['S'])} %",
                    ic_txt=f"{num(100*r['ic_inf'])}–{num(100*r['ic_sup'])}",
                    inc_txt=f"{num(100*(1-r['S']))} %")
               for _, r in km.iterrows()])

    g1, g0 = normo, hipo
    km1, km0 = (kaplan_meier(g1["KM_tiempo"], g1["KM_evento"]),
                kaplan_meier(g0["KM_tiempo"], g0["KM_evento"]))
    lr = logrank(g1["KM_tiempo"], g1["KM_evento"], g0["KM_tiempo"], g0["KM_evento"])
    D["km_fraccionamiento"] = dict(
        mediana_normo=mediana_km(km1), mediana_hipo=mediana_km(km0),
        ev_normo=int(g1["KM_evento"].sum()), ev_hipo=int(g0["KM_evento"].sum()),
        chi2=float(lr["chi2"]), p=fmt_p(lr["p"]), p_val=float(lr["p"]),
        hr=float(lr["hr_peto"]),
        O1=float(lr["O1"]), E1=float(lr["E1"]),
        O0=float(lr["O0"]), E0=float(lr["E0"]))

    h1 = df[df["Irradiacion_ganglionar"] == "Si"]
    h0 = df[df["Irradiacion_ganglionar"] == "No"]
    lrh = logrank(h1["KM_tiempo"], h1["KM_evento"], h0["KM_tiempo"], h0["KM_evento"])
    D["km_ganglionar"] = dict(chi2=float(lrh["chi2"]), p=fmt_p(lrh["p"]),
                              hr=float(lrh["hr_peto"]))

    # sensibilidad
    g1s = np.where(g1["KM_evento"] == 1, g1["KM_tiempo"], g1["Duracion_RT_sem"])
    g0s = np.where(g0["KM_evento"] == 1, g0["KM_tiempo"], g0["Duracion_RT_sem"])
    lr_s = logrank(g1s, g1["KM_evento"], g0s, g0["KM_evento"])
    t_sens = np.where(df["KM_evento"] == 1, df["KM_tiempo"], df["Duracion_RT_sem"])
    D["km_sensibilidad"] = dict(p=fmt_p(lr_s["p"]),
                                mediana=mediana_km(kaplan_meier(t_sens, df["KM_evento"])))

    # correlacion grado-semana
    sub = df.dropna(subset=["Mayor_Gdo_RD", "Semana_Presentacion_RD"])
    rho, p_rho = stats.spearmanr(sub["Mayor_Gdo_RD"], sub["Semana_Presentacion_RD"])
    D["spearman_grado_semana"] = dict(rho=float(rho), p=fmt_p(p_rho), n=int(len(sub)))

    with open(BASE / "informe_datos.json", "w", encoding="utf-8") as f:
        json.dump(D, f, ensure_ascii=False, indent=1, default=float)
    print(f"OK -> informe_datos.json  ({len(json.dumps(D, default=float))} bytes)")

    # Dimensiones de las figuras, necesarias para escalarlas en el Word
    from PIL import Image
    dims = {}
    for f_png in sorted((BASE / "figuras").glob("*.png")):
        dims[f_png.name] = Image.open(f_png).size
    with open(BASE / "figuras_dims.json", "w", encoding="utf-8") as f:
        json.dump(dims, f, indent=1)
    print(f"OK -> figuras_dims.json  ({len(dims)} figuras)")


if __name__ == "__main__":
    main()
