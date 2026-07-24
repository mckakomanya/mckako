#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilidades compartidas por los scripts de analisis.
Incluye: carga de datos, formato de p-valores, intervalos de confianza
(Wilson, exacto de Fisher, diferencia de proporciones) y estimador de
Kaplan-Meier con test de log-rank implementados desde cero.
"""

from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

BASE = Path(__file__).resolve().parent
FIG = BASE / "figuras"
FIG.mkdir(exist_ok=True)

# Paleta consistente en todo el informe
AZUL, NARANJA, GRIS = "#2E5A87", "#D98032", "#9AA5B1"


def carga():
    return pd.read_csv(BASE / "datos_limpios.csv")


def fmt_p(p):
    """Formato de p-valor al estilo de publicacion cientifica."""
    if pd.isna(p):
        return "NA"
    if p < 0.001:
        return "<0,001"
    return f"{p:.3f}".replace(".", ",")


def num(x, dec=1):
    """Numero con coma decimal (convencion en castellano)."""
    if pd.isna(x):
        return "NA"
    if np.isinf(x):
        return "∞"
    return f"{x:.{dec}f}".replace(".", ",")


# --------------------------------------------------------------------- #
# Intervalos de confianza
# --------------------------------------------------------------------- #
def ic_wilson(k, n, conf=0.95):
    """IC de Wilson para una proporcion (mejor que Wald con n pequeno)."""
    if n == 0:
        return (np.nan, np.nan)
    z = stats.norm.ppf(1 - (1 - conf) / 2)
    p = k / n
    den = 1 + z**2 / n
    centro = (p + z**2 / (2 * n)) / den
    semi = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / den
    return (max(0, centro - semi), min(1, centro + semi))


def ic_dif_proporciones(k1, n1, k0, n0, conf=0.95):
    """IC de Newcombe (hibrido de Wilson) para la diferencia de proporciones."""
    if n1 == 0 or n0 == 0:
        return (np.nan, np.nan)
    l1, u1 = ic_wilson(k1, n1, conf)
    l0, u0 = ic_wilson(k0, n0, conf)
    d = k1 / n1 - k0 / n0
    inf = d - np.sqrt((k1 / n1 - l1) ** 2 + (u0 - k0 / n0) ** 2)
    sup = d + np.sqrt((u1 - k1 / n1) ** 2 + (k0 / n0 - l0) ** 2)
    return (max(-1, inf), min(1, sup))


def fisher_ic(tabla, conf=0.95):
    """
    Test exacto de Fisher con odds ratio condicional (MLE) e IC exacto.
    tabla = [[a, b], [c, d]]  ->  a=expuestos con evento, b=expuestos sin evento
    Devuelve dict con OR, IC del OR, p bilateral, riesgos, RR y diferencia
    de riesgo con sus IC.
    """
    (a, b), (c, d) = tabla
    a, b, c, d = int(a), int(b), int(c), int(d)

    # p bilateral exacto
    _, p = stats.fisher_exact([[a, b], [c, d]])

    # OR condicional (MLE) + IC exacto condicional
    res = stats.contingency.odds_ratio([[a, b], [c, d]], kind="conditional")
    or_cond = res.statistic
    or_ic = res.confidence_interval(confidence_level=conf)

    # OR muestral con correccion de Haldane-Anscombe si hay ceros
    if 0 in (a, b, c, d):
        or_muestral = ((a + .5) * (d + .5)) / ((b + .5) * (c + .5))
        haldane = True
    else:
        or_muestral = (a * d) / (b * c)
        haldane = False

    n1, n0 = a + b, c + d
    r1 = a / n1 if n1 else np.nan          # riesgo en expuestos
    r0 = c / n0 if n0 else np.nan          # riesgo en no expuestos
    rr = r1 / r0 if r0 else np.inf
    dr = r1 - r0

    return dict(
        tabla=[[a, b], [c, d]], p=p,
        or_cond=or_cond, or_ic_inf=or_ic.low, or_ic_sup=or_ic.high,
        or_muestral=or_muestral, haldane=haldane,
        r1=r1, r1_ic=ic_wilson(a, n1), n1=n1,
        r0=r0, r0_ic=ic_wilson(c, n0), n0=n0,
        rr=rr, dr=dr, dr_ic=ic_dif_proporciones(a, n1, c, n0),
    )


def tabla_2x2(df, factor, evento, pos_f, pos_e):
    """Construye la tabla 2x2 [[a,b],[c,d]] para factor vs evento."""
    sub = df.dropna(subset=[factor, evento])
    exp = sub[factor] == pos_f
    ev = sub[evento] == pos_e
    return [[int((exp & ev).sum()), int((exp & ~ev).sum())],
            [int((~exp & ev).sum()), int((~exp & ~ev).sum())]]


# --------------------------------------------------------------------- #
# Kaplan-Meier (implementacion propia)
# --------------------------------------------------------------------- #
def kaplan_meier(tiempo, evento, conf=0.95):
    """
    Estimador de Kaplan-Meier de la funcion 'libre de evento' S(t).
    Varianza por la formula de Greenwood; IC con transformacion log-log
    (mas apropiada que la lineal con muestras pequenas).

    Devuelve DataFrame con: t, n_riesgo, eventos, censurados, S, IC inf/sup.
    """
    t = np.asarray(tiempo, dtype=float)
    e = np.asarray(evento, dtype=int)
    ok = ~np.isnan(t)
    t, e = t[ok], e[ok]

    tiempos = np.unique(t[e == 1])          # solo tiempos con evento
    filas, S, acum_var = [], 1.0, 0.0
    z = stats.norm.ppf(1 - (1 - conf) / 2)

    # fila inicial t=0
    filas.append(dict(t=0.0, n_riesgo=len(t), eventos=0, censurados=0,
                      S=1.0, ic_inf=1.0, ic_sup=1.0))

    for ti in tiempos:
        n = int((t >= ti).sum())            # en riesgo justo antes de ti
        d = int(((t == ti) & (e == 1)).sum())
        cens = int(((t == ti) & (e == 0)).sum())
        S *= (1 - d / n)
        if n > d:
            acum_var += d / (n * (n - d))
        # IC log-log
        if 0 < S < 1 and acum_var > 0:
            se_ll = np.sqrt(acum_var) / abs(np.log(S))
            inf = S ** np.exp(z * se_ll)
            sup = S ** np.exp(-z * se_ll)
        else:
            inf = sup = S
        filas.append(dict(t=float(ti), n_riesgo=n, eventos=d, censurados=cens,
                          S=S, ic_inf=max(0, inf), ic_sup=min(1, sup)))

    return pd.DataFrame(filas)


def mediana_km(km, tol=1e-9):
    """
    Primer tiempo en que S(t) <= 0,5 (mediana de tiempo hasta el evento).
    Se aplica una tolerancia numerica: el producto acumulado de KM puede
    devolver 0,5000000000000001 en lugar de 0,5 exacto y perder la mediana.
    """
    bajo = km[km["S"] <= 0.5 + tol]
    return float(bajo["t"].iloc[0]) if len(bajo) else np.nan


def incidencia_km(km, t):
    """Incidencia acumulada 1-S(t) en el tiempo t."""
    prev = km[km["t"] <= t]
    if not len(prev):
        return 0.0
    fila = prev.iloc[-1]
    return 1 - fila["S"], 1 - fila["ic_sup"], 1 - fila["ic_inf"]


def logrank(t1, e1, t0, e0):
    """
    Test de log-rank (Mantel-Cox) para dos grupos.
    Devuelve chi2, p, observados y esperados por grupo, y HR por el
    metodo de Peto (O/E), util como tamano de efecto.
    """
    t1, e1 = np.asarray(t1, float), np.asarray(e1, int)
    t0, e0 = np.asarray(t0, float), np.asarray(e0, int)
    t_all = np.concatenate([t1, t0])
    e_all = np.concatenate([e1, e0])
    tiempos = np.unique(t_all[e_all == 1])

    O1 = E1 = V = 0.0
    O0 = 0.0
    for ti in tiempos:
        n1 = (t1 >= ti).sum()
        n0 = (t0 >= ti).sum()
        n = n1 + n0
        d1 = ((t1 == ti) & (e1 == 1)).sum()
        d0 = ((t0 == ti) & (e0 == 1)).sum()
        d = d1 + d0
        if n < 2 or d == 0:
            continue
        O1 += d1
        O0 += d0
        E1 += d * n1 / n
        V += d * (n1 / n) * (1 - n1 / n) * ((n - d) / (n - 1))

    chi2 = (O1 - E1) ** 2 / V if V > 0 else np.nan
    p = 1 - stats.chi2.cdf(chi2, 1) if V > 0 else np.nan
    E0 = (O1 + O0) - E1
    hr = (O1 / E1) / (O0 / E0) if E1 > 0 and E0 > 0 and O0 > 0 else np.nan
    return dict(chi2=chi2, p=p, O1=O1, E1=E1, O0=O0, E0=E0, hr_peto=hr, V=V)
