#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PASO 4 — ANALISIS DE SUPERVIVENCIA (KAPLAN-MEIER)
Tiempo desde el INICIO de la radioterapia hasta la APARICION de
radiodermitis de CUALQUIER GRADO (>= grado 1).

Definiciones:
  - Origen (t=0)  : primera sesion de radioterapia.
  - Evento        : primera constatacion de radiodermitis de cualquier grado.
  - Escala        : semanas de tratamiento.
  - Censura       : pacientes que finalizan el seguimiento sin radiodermitis.
                    Al ser la radiodermitis aguda un fenomeno que alcanza su
                    pico 1-2 semanas TRAS el fin de la RT, la ventana de
                    observacion se extiende hasta la primera visita post-RT
                    (duracion de la RT + 1 semana). Censurar al terminar la RT
                    generaria censura informativa.

Metodos: estimador de Kaplan-Meier con varianza de Greenwood e IC95% por
transformacion log-log; comparacion de curvas por test de log-rank
(Mantel-Cox); HR estimado por el metodo de Peto (O/E).
Se incluye un analisis de sensibilidad con censura al finalizar la RT.

Genera: resultados_kaplan_meier.txt y figuras/fig7, fig8
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from comun import (carga, FIG, BASE, AZUL, NARANJA, GRIS,
                   fmt_p, num, kaplan_meier, mediana_km, logrank)

OUT = []
def w(*a): OUT.append(" ".join(str(x) for x in a))


def tabla_km(km, titulo):
    w(f"  {titulo}")
    w(f"     {'Semana':>7} {'En riesgo':>10} {'Eventos':>8} {'Censura':>8} "
      f"{'S(t) libre':>11} {'IC95%':>18} {'Incid.acum':>11}")
    for _, r in km.iterrows():
        ic = f"{num(100*r['ic_inf'])}-{num(100*r['ic_sup'])}%"
        w(f"     {num(r['t'],0):>7} {int(r['n_riesgo']):>10} {int(r['eventos']):>8} "
          f"{int(r['censurados']):>8} {num(100*r['S']):>10}% {ic:>18} "
          f"{num(100*(1-r['S'])):>10}%")


def curva_escalonada(km, t_max=None):
    """
    Convierte la tabla KM en coordenadas escalonadas para graficar.
    t_max extiende la curva horizontalmente hasta el final del seguimiento
    del grupo (convencion estandar); sin ella la curva terminaria en el
    ultimo evento y podria quedar oculta bajo la de otro grupo.
    """
    t = [0.0]; s = [1.0]
    for _, r in km.iloc[1:].iterrows():
        t.append(r["t"]); s.append(s[-1])      # tramo horizontal
        t.append(r["t"]); s.append(r["S"])     # salto vertical
    if t_max is not None and t_max > t[-1]:
        t.append(float(t_max)); s.append(s[-1])
    return np.array(t), np.array(s)


def banda_ic(km):
    t = [0.0]; lo = [1.0]; hi = [1.0]
    for _, r in km.iloc[1:].iterrows():
        t.append(r["t"]); lo.append(lo[-1]); hi.append(hi[-1])
        t.append(r["t"]); lo.append(r["ic_inf"]); hi.append(r["ic_sup"])
    return np.array(t), np.array(lo), np.array(hi)


def main():
    df = carga()

    w("=" * 74)
    w("ANALISIS DE SUPERVIVENCIA — KAPLAN-MEIER")
    w("Tiempo hasta la aparicion de radiodermitis de cualquier grado (>=1)")
    w("=" * 74)
    n_ev = int(df["KM_evento"].sum())
    n_cen = int((df["KM_evento"] == 0).sum())
    w(f"  N = {len(df)}   Eventos = {n_ev} ({num(100*n_ev/len(df))}%)   "
      f"Censurados = {n_cen}")
    w(f"  Origen: primera sesion de RT.  Escala: semanas.")
    w(f"  Seguimiento maximo observado: {num(df['KM_tiempo'].max(),0)} semanas.")
    w("")

    # ---------------- 4.1 Curva global -------------------------------- #
    w("4.1. CURVA GLOBAL (toda la cohorte)")
    w("-" * 74)
    km = kaplan_meier(df["KM_tiempo"], df["KM_evento"])
    tabla_km(km, "Tabla de supervivencia libre de radiodermitis "
                 "(S = probabilidad de permanecer LIBRE de RD)")
    med = mediana_km(km)
    w("")
    w(f"  Mediana de supervivencia libre de radiodermitis: {num(med,0)} semanas")
    w(f"     (semana en que la probabilidad de seguir libre de RD cae al 50%)")
    for t in [2, 3, 4, 5]:
        fila = km[km["t"] <= t]
        if len(fila):
            r = fila.iloc[-1]
            w(f"  Semana {t}: supervivencia libre de RD "
              f"{num(100*r['S'])}% (IC95% {num(100*r['ic_inf'])}-"
              f"{num(100*r['ic_sup'])}%)  |  "
              f"incidencia acumulada {num(100*(1-r['S']))}%")

    # ---------------- 4.2 Comparacion por fraccionamiento ------------- #
    w("\n4.2. COMPARACION POR ESQUEMA DE FRACCIONAMIENTO")
    w("-" * 74)
    g1 = df[df["Fraccionamiento"] == "Normofx"]
    g0 = df[df["Fraccionamiento"] == "Hipofx"]
    km1 = kaplan_meier(g1["KM_tiempo"], g1["KM_evento"])
    km0 = kaplan_meier(g0["KM_tiempo"], g0["KM_evento"])

    w(f"  Normofraccionamiento: n={len(g1)}, eventos={int(g1['KM_evento'].sum())}")
    tabla_km(km1, "")
    w("")
    w(f"  Hipofraccionamiento: n={len(g0)}, eventos={int(g0['KM_evento'].sum())}")
    tabla_km(km0, "")

    lr = logrank(g1["KM_tiempo"], g1["KM_evento"], g0["KM_tiempo"], g0["KM_evento"])
    w("")
    w("  Test de log-rank (Mantel-Cox):")
    w(f"     Observados vs esperados — Normofx: O={num(lr['O1'],0)} "
      f"E={num(lr['E1'],2)}  |  Hipofx: O={num(lr['O0'],0)} E={num(lr['E0'],2)}")
    w(f"     Chi-cuadrado = {num(lr['chi2'],3)} (1 gl), p = {fmt_p(lr['p'])}")
    w(f"     Hazard ratio (Peto) = {num(lr['hr_peto'],2)} "
      f"(normofx respecto a hipofx)")
    w(f"     Mediana normofx: {num(mediana_km(km1),0)} sem  |  "
      f"hipofx: {num(mediana_km(km0),0)} sem")
    if lr["p"] >= 0.05:
        w("     -> Sin diferencia significativa en el TIEMPO hasta la aparicion.")
        w("        Nota: el fraccionamiento se asocia a la GRAVEDAD de la")
        w("        radiodermitis (ver seccion 3), no necesariamente a su")
        w("        rapidez de aparicion.")

    # ---------------- 4.3 Comparacion por irradiacion ganglionar ------ #
    w("\n4.3. COMPARACION POR IRRADIACION GANGLIONAR")
    w("-" * 74)
    h1 = df[df["Irradiacion_ganglionar"] == "Si"]
    h0 = df[df["Irradiacion_ganglionar"] == "No"]
    kmh1 = kaplan_meier(h1["KM_tiempo"], h1["KM_evento"])
    kmh0 = kaplan_meier(h0["KM_tiempo"], h0["KM_evento"])
    lrh = logrank(h1["KM_tiempo"], h1["KM_evento"], h0["KM_tiempo"], h0["KM_evento"])
    w(f"  Con irradiacion ganglionar : n={len(h1)}, "
      f"eventos={int(h1['KM_evento'].sum())}, "
      f"mediana {num(mediana_km(kmh1),0)} sem")
    w(f"  Sin irradiacion ganglionar : n={len(h0)}, "
      f"eventos={int(h0['KM_evento'].sum())}, "
      f"mediana {num(mediana_km(kmh0),0)} sem")
    w(f"  Log-rank: chi2 = {num(lrh['chi2'],3)}, p = {fmt_p(lrh['p'])}, "
      f"HR (Peto) = {num(lrh['hr_peto'],2)}")

    # ---------------- 4.4 Analisis de sensibilidad -------------------- #
    w("\n4.4. ANALISIS DE SENSIBILIDAD (censura al finalizar la RT)")
    w("-" * 74)
    w("  Se repite el analisis censurando a los pacientes libres de evento al")
    w("  terminar la radioterapia, en lugar de a la primera visita post-RT.")
    t_sens = np.where(df["KM_evento"] == 1, df["KM_tiempo"], df["Duracion_RT_sem"])
    km_s = kaplan_meier(t_sens, df["KM_evento"])
    w(f"  Mediana: {num(mediana_km(km_s),0)} semanas "
      f"(analisis principal: {num(med,0)} semanas)")
    g1s = np.where(g1["KM_evento"] == 1, g1["KM_tiempo"], g1["Duracion_RT_sem"])
    g0s = np.where(g0["KM_evento"] == 1, g0["KM_tiempo"], g0["Duracion_RT_sem"])
    lr_s = logrank(g1s, g1["KM_evento"], g0s, g0["KM_evento"])
    w(f"  Log-rank por fraccionamiento: p = {fmt_p(lr_s['p'])} "
      f"(analisis principal: p = {fmt_p(lr['p'])})")
    w("  -> La CONCLUSION cualitativa se mantiene (ausencia de diferencia")
    w("     significativa en el tiempo hasta la aparicion), pero el estadistico")
    w("     de log-rank es MUY SENSIBLE al criterio de censura: al censurar al")
    w("     final de la RT, los 7 pacientes hipofraccionados libres de evento")
    w("     salen del riesgo en la semana 3 y dejan de aportar informacion")
    w("     comparativa, con lo que el contraste se aproxima a la nulidad.")
    w("     Esta inestabilidad refleja la escasez de eventos y refuerza que el")
    w("     analisis temporal debe considerarse meramente descriptivo.")

    # ---------------- 4.5 Supuestos ----------------------------------- #
    w("\n4.5. SUPUESTOS Y LIMITACIONES")
    w("-" * 74)
    w("  - La semana de aparicion se registro en semanas enteras: existe")
    w("    censura por intervalo no modelada (el evento ocurre en algun punto")
    w("    de la semana declarada). El KM asume tiempos exactos.")
    w("  - Todos los censurados pertenecen al grupo hipofraccionado, lo que")
    w("    limita la comparacion de curvas mas alla de la semana 4.")
    w("  - Con 14 eventos, la potencia para detectar diferencias moderadas en")
    w("    el tiempo hasta el evento es baja.")

    # ================================================================= #
    # FIGURAS
    # ================================================================= #
    plt.rcParams.update({"figure.dpi": 130, "font.size": 9,
                         "axes.spines.top": False, "axes.spines.right": False})

    # --- Figura 7: curva global (incidencia acumulada) --------------- #
    tmax = int(df["KM_tiempo"].max())
    fig, (ax, axr) = plt.subplots(
        2, 1, figsize=(7.2, 4.9), sharex=True,
        gridspec_kw=dict(height_ratios=[6, 1], hspace=0.12))
    t, s = curva_escalonada(km, t_max=df["KM_tiempo"].max())
    tb, lo, hi = banda_ic(km)
    ax.fill_between(tb, 100 * lo, 100 * hi, color=AZUL, alpha=.16,
                    label="IC95%")
    ax.plot(t, 100 * s, color=AZUL, lw=2.2,
            label="Supervivencia libre de radiodermitis")
    # marcas de censura sobre la curva
    cens = df[df["KM_evento"] == 0]["KM_tiempo"]
    for c in cens.unique():
        fila = km[km["t"] <= c]
        sv = fila["S"].iloc[-1] if len(fila) else 1.0
        ax.plot([c], [100 * sv], marker="|", color=AZUL, ms=9, mew=1.8)
    ax.axhline(50, color=GRIS, ls=":", lw=1)
    med = mediana_km(km)
    ax.axvline(med, color=NARANJA, ls="--", lw=1.4)
    ax.text(med - .12, 62, f"Mediana = {med:.0f} semanas", color=NARANJA,
            fontsize=8.5, fontweight="bold", ha="right")
    ax.set_ylabel("Supervivencia libre de radiodermitis (%)")
    ax.set_xlim(-0.15, tmax + .3); ax.set_ylim(0, 100)
    ax.legend(frameon=False, loc="lower left", fontsize=8.5)
    ax.set_title("Figura 7. Kaplan-Meier: supervivencia libre de radiodermitis\n"
                 "de cualquier grado (n=21, 14 eventos)",
                 fontsize=10, fontweight="bold")

    # eje inferior dedicado a la tabla de pacientes en riesgo
    axr.text(-0.15, 0.86, "Pacientes en riesgo", ha="left", va="center",
             fontsize=8.5, fontweight="bold", color="#333333")
    for x in range(0, tmax + 1):
        axr.text(x, 0.30, str(int((df["KM_tiempo"] >= x).sum())),
                 ha="center", va="center", fontsize=8.5, color="#333333")
    axr.set_ylim(0, 1); axr.set_yticks([])
    axr.set_xticks(range(0, tmax + 1))
    axr.set_xlabel("Semanas desde el inicio de la radioterapia")
    for s_ in ("left", "right", "top"):
        axr.spines[s_].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "fig7_km_global.png", bbox_inches="tight"); plt.close(fig)

    # --- Figura 8: por fraccionamiento -------------------------------- #
    fig, (ax, axr) = plt.subplots(
        2, 1, figsize=(7.2, 5.2), sharex=True,
        gridspec_kw=dict(height_ratios=[6, 1.3], hspace=0.12))
    grupos_fig = [(km0, "Hipofraccionamiento", AZUL, g0, "-"),
                  (km1, "Normofraccionamiento", NARANJA, g1, "--")]
    for kmg, grupo, color, sub, estilo in grupos_fig:
        t, s = curva_escalonada(kmg, t_max=sub["KM_tiempo"].max())
        n_g, e_g = len(sub), int(sub["KM_evento"].sum())
        ax.plot(t, 100 * s, color=color, lw=2.2, ls=estilo,
                label=f"{grupo} (n={n_g}, {e_g} eventos)")
        for c in sub[sub["KM_evento"] == 0]["KM_tiempo"].unique():
            fila = kmg[kmg["t"] <= c]
            sv = fila["S"].iloc[-1] if len(fila) else 1.0
            ax.plot([c], [100 * sv], marker="|", color=color, ms=9, mew=1.8)
    ax.axhline(50, color=GRIS, ls=":", lw=1)
    ax.set_ylabel("Supervivencia libre de radiodermitis (%)")
    ax.set_xlim(-0.95, tmax + .3); ax.set_ylim(0, 100)
    ax.legend(frameon=False, loc="lower left", fontsize=8.5)
    ax.text(.97, .90, f"Log-rank: p = {fmt_p(lr['p'])}", transform=ax.transAxes,
            ha="right", fontsize=9, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=GRIS, lw=.8))
    ax.set_title("Figura 8. Supervivencia libre de radiodermitis segun\n"
                 "esquema de fraccionamiento", fontsize=10, fontweight="bold")

    # tabla de pacientes en riesgo por grupo
    axr.text(-0.90, 1.02, "Pacientes en riesgo", ha="left", va="center",
             fontsize=8.5, fontweight="bold", color="#333333")
    for fila_i, (_, grupo, color, sub, _e) in enumerate(grupos_fig):
        y = 0.60 - fila_i * 0.42
        axr.text(-0.90, y, grupo[:6] + ".", ha="left", va="center",
                 fontsize=8, color=color, fontweight="bold")
        for x in range(0, tmax + 1):
            axr.text(x, y, str(int((sub["KM_tiempo"] >= x).sum())),
                     ha="center", va="center", fontsize=8.5, color=color)
    axr.set_ylim(0, 1.15); axr.set_yticks([])
    axr.set_xticks(range(0, tmax + 1))
    axr.set_xlabel("Semanas desde el inicio de la radioterapia")
    for s_ in ("left", "right", "top"):
        axr.spines[s_].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "fig8_km_fraccionamiento.png", bbox_inches="tight")
    plt.close(fig)

    with open(BASE / "resultados_kaplan_meier.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(OUT) + "\n")
    print("\n".join(OUT))
    print("\nFiguras: fig7_km_global.png, fig8_km_fraccionamiento.png")


if __name__ == "__main__":
    main()
