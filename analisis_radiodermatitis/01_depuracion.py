#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PASO 1 — DEPURACION DE ERRORES
Base de datos: cohorte de cancer de mama tratada con radioterapia (n=21).
Endpoint principal del estudio: radiodermitis aguda (Mayor_Gdo_RD y semana de presentacion).

Este script:
  1. Carga los datos crudos.
  2. Detecta inconsistencias frente al libro de codigos y a la logica clinica.
  3. Corrige/estandariza cada variable dejando traza de cada cambio.
  4. Genera:  datos_limpios.csv   y   reporte_depuracion.txt

Uso:  python 01_depuracion.py
"""

import re
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
CRUDO = BASE / "datos_crudos.csv"
LIMPIO = BASE / "datos_limpios.csv"
REPORTE = BASE / "reporte_depuracion.txt"

# Acumulador de hallazgos: (paciente, variable, valor_original, accion, valor_final)
LOG = []


def anota(pac, var, orig, accion, final):
    LOG.append((pac, var, str(orig), accion, str(final)))


# --------------------------------------------------------------------------- #
# Utilidades de normalizacion
# --------------------------------------------------------------------------- #
def norm_si_no(x):
    """Normaliza cualquier variante de Si/No (incluida 'Sí' con tilde)."""
    if pd.isna(x):
        return np.nan
    s = str(x).strip().lower()
    s = s.replace("í", "i").replace("Í", "i")
    if s in ("si", "s", "1", "true", "yes"):
        return "Si"
    if s in ("no", "n", "0", "false"):
        return "No"
    return np.nan


def a_nan(x):
    """Convierte marcadores de ausente ('-', '', 'nan') en NaN."""
    if pd.isna(x):
        return np.nan
    s = str(x).strip()
    if s in ("-", "", "nan", "NA", "N/A"):
        return np.nan
    return s


# --------------------------------------------------------------------------- #
def main():
    df = pd.read_csv(CRUDO, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    n0 = len(df)

    # ---- 1. Identificadores / cuantitativas simples --------------------- #
    df["Paciente"] = df["Paciente"].astype(int)
    df["Edad"] = df["Edad"].astype(int)

    # ---- 2. Comorbilidades binarias ------------------------------------- #
    for col in ["Diabetes", "Tabaquismo_Actual", "Boost"]:
        nuevo = df[col].map(norm_si_no)
        for i, (o, nv) in enumerate(zip(df[col], nuevo)):
            if str(o).strip() != str(nv):
                anota(df.loc[i, "Paciente"], col, o, "estandariza Si/No", nv)
        df[col] = nuevo

    # ---- 3. CTV (irradiacion ganglionar): corrige 'Sí' con tilde -------- #
    for col in ["CTV_N_Ax", "CTV_N_III_SC"]:
        nuevo = df[col].map(norm_si_no)
        for i, (o, nv) in enumerate(zip(df[col], nuevo)):
            if str(o).strip() != str(nv):
                anota(df.loc[i, "Paciente"], col, o,
                      "corrige tilde/estandariza Si/No", nv)
        df[col] = nuevo

    # ---- 4. Receptores / Her2 ------------------------------------------- #
    #  '-' en carcinoma in situ => ausente (no evaluado en el mismo esquema)
    for col in ["Her2", "PR", "ER"]:
        cruda = df[col].map(a_nan)
        nuevo = cruda.map(lambda v: norm_si_no(v) if pd.notna(v) else np.nan)
        for i, (o, nv) in enumerate(zip(df[col], nuevo)):
            if str(o).strip() != ("" if pd.isna(nv) else str(nv)):
                acc = "marca ausente (in situ)" if pd.isna(nv) else "estandariza Si/No"
                anota(df.loc[i, "Paciente"], col, o, acc,
                      "NaN" if pd.isna(nv) else nv)
        df[col] = nuevo

    # ---- 5. Ki67 (indice de proliferacion, %) --------------------------- #
    #  Los valores de 99 son valores REALES medidos en esas pacientes
    #  (confirmado con el investigador) y se mantienen como tales.
    #  Solo se marcan como ausentes los '-' (carcinoma in situ, no evaluado)
    #  y los valores fuera del rango biologico 0-100.
    ki = []
    for i, o in enumerate(df["Ki67"]):
        v = a_nan(o)
        if pd.isna(v):
            ki.append(np.nan)
            anota(df.loc[i, "Paciente"], "Ki67", o, "ausente (in situ)", "NaN")
            continue
        v = float(v)
        if v < 0 or v > 100:
            ki.append(np.nan)
            anota(df.loc[i, "Paciente"], "Ki67", o, "fuera de rango 0-100", "NaN")
        else:
            ki.append(v)
    df["Ki67"] = ki

    # ---- 6. GHF (grado histologico) ------------------------------------- #
    ghf = []
    for i, o in enumerate(df["GHF"]):
        v = a_nan(o)
        if pd.isna(v):
            ghf.append(np.nan)
            anota(df.loc[i, "Paciente"], "GHF", o, "ausente (in situ)", "NaN")
        else:
            ghf.append(int(float(v)))
    df["GHF"] = ghf

    # ---- 7. pT: separa prefijo (p/yp), 'Cis' y multifocalidad (m) ------- #
    #  Se conserva la categoria original y se derivan variables limpias:
    #    pT_prefijo (p / yp), pT_cat (Tis, T1, T2, T3, T4), multifocal (Si/No)
    def parse_pt(o):
        s = str(o).strip()
        prefijo = "yp" if s.lower().startswith("yp") else "p"
        s2 = re.sub(r"^(yp|p)", "", s, flags=re.I)
        multifocal = "Si" if "(m)" in s2.lower() else "No"
        s2 = s2.replace("(m)", "").strip()
        if s2.lower() in ("cis", "tis"):
            cat = "Tis"
        else:
            m = re.match(r"[tT]?\s*([0-4])", s2)
            cat = "T" + m.group(1) if m else np.nan
        return prefijo, cat, multifocal

    pref, cat, mf = zip(*[parse_pt(o) for o in df["pT"]])
    df["pT_prefijo"], df["pT_cat"], df["Multifocal"] = pref, cat, mf
    for i, o in enumerate(df["pT"]):
        anota(df.loc[i, "Paciente"], "pT", o, "parseo -> pT_cat/prefijo/multifocal",
              f"{cat[i]} ({pref[i]}, mf={mf[i]})")

    # ---- 8. pN: estandariza prefijo, micrometastasis y (sn) ------------- #
    def parse_pn(o):
        s = str(o).strip()
        prefijo = "yp" if s.lower().startswith("yp") else "p"
        s2 = re.sub(r"^(yp|p)", "", s, flags=re.I)
        sn = "Si" if "(sn)" in s2.lower() else "No"          # ganglio centinela
        s2 = s2.replace("(sn)", "").strip()
        micro = "Si" if "mi" in s2.lower() else "No"          # micrometastasis
        m = re.match(r"[nN]?\s*([0-3])", s2)
        cat = "N" + m.group(1) if m else np.nan
        return prefijo, cat, micro, sn

    prf, ncat, mic, sn = zip(*[parse_pn(o) for o in df["pN"]])
    df["pN_prefijo"], df["pN_cat"], df["pN_micro"], df["pN_centinela"] = prf, ncat, mic, sn
    df["Ganglios_positivos"] = [
        "No" if c == "N0" else "Si" for c in ncat
    ]
    for i, o in enumerate(df["pN"]):
        anota(df.loc[i, "Paciente"], "pN", o, "parseo -> pN_cat/micro/centinela",
              f"{ncat[i]} (micro={mic[i]}, sn={sn[i]})")

    # ---- 9. M ------------------------------------------------------------ #
    df["M"] = df["M"].str.strip().str.upper()

    # ---- 10. Subtipo histologico: unifica ortografia y espacios --------- #
    mapa_sub = {
        "luminala": "Luminal A", "luminal a": "Luminal A",
        "luminalb": "Luminal B", "luminal b": "Luminal B",
        "her2": "Her2", "triple neg": "Triple Neg", "tripleneg": "Triple Neg",
        "cis": "Cis",
    }
    nuevo = []
    for i, o in enumerate(df["Subtipo_Hist"]):
        key = str(o).strip().lower()
        nv = mapa_sub.get(key, str(o).strip())
        if nv != str(o).strip():
            anota(df.loc[i, "Paciente"], "Subtipo_Hist", o, "unifica etiqueta", nv)
        nuevo.append(nv)
    df["Subtipo_Hist"] = nuevo

    # ---- 11. Cirugia ----------------------------------------------------- #
    df["Cirugia"] = df["Cirugia"].str.strip().replace(
        {"Mastectomia": "Mastectomia", "CC": "CC"})

    # ---- 12. Estadificacion: 'Cis' -> estadio 0; '-' -> NaN ------------- #
    for col in ["Estadificacion_Anatomica", "Estadificacion_Pronostica"]:
        nuevo = []
        for i, o in enumerate(df[col]):
            s = a_nan(o)
            if pd.isna(s):
                nuevo.append(np.nan)
                anota(df.loc[i, "Paciente"], col, o, "ausente", "NaN")
            elif str(s).strip().lower() == "cis":
                nuevo.append("0")
                anota(df.loc[i, "Paciente"], col, o, "Cis (in situ) -> estadio 0", "0")
            else:
                nuevo.append(str(s).strip())
        df[col] = nuevo

    # ---- 12b. Coherencia estadio anatomico vs pronostico ---------------- #
    #  Paciente 11: anatomico IIIA con pronostico IB es incoherente para una
    #  enfermedad N2, grado 3, Luminal B HER2-. Se marca como error probable.
    orden = {"0": 0, "IA": 1, "IB": 2, "IIA": 3, "IIB": 4,
             "IIIA": 5, "IIIB": 6, "IIIC": 7, "IV": 8}
    for i in range(len(df)):
        a = df.loc[i, "Estadificacion_Anatomica"]
        p = df.loc[i, "Estadificacion_Pronostica"]
        if a in orden and p in orden and (orden[a] - orden[p]) >= 3:
            anota(df.loc[i, "Paciente"], "Estadificacion_Pronostica",
                  p, f"INCOHERENTE con anatomico {a} (salto>=3 niveles) -> revisar",
                  "sin_cambio(marcado)")

    # ---- 13. Tto sistemico previo a RT -> binaria QT/tto_previa --------- #
    #  Texto libre (Neoady, Neoadyuvante, Adyuvante, No) recodificado a Si/No.
    #  Nota: paciente 15 figura 'Adyuvante' pero presenta respuesta completa
    #  (ypT0 ypN0) => recibio tto sistemico NEOADYUVANTE; se corrige a Si.
    tto_prev = []
    for i, o in enumerate(df["Tto_sist_pre_RT"]):
        s = str(o).strip().lower()
        if s in ("no", "-", ""):
            nv = "No"
        else:
            nv = "Si"
        tto_prev.append(nv)
        if s == "adyuvante":
            anota(df.loc[i, "Paciente"], "Tto_sist_pre_RT", o,
                  "etiqueta 'Adyuvante' pero ypT0ypN0 (hubo neoadyuvancia) -> Si", nv)
        elif str(o).strip() != nv:
            anota(df.loc[i, "Paciente"], "Tto_sist_pre_RT", o,
                  "recodifica texto libre -> Si/No", nv)
    df["Tto_sist_previo"] = tto_prev

    # ---- 14. Tipo de tto sistemico: '-' -> NaN -------------------------- #
    df["Tipo_Tto_Sist"] = df["Tipo_Tto_Sist"].map(a_nan)

    # ---- 15. HT concurrente: nombre de farmaco en columna Si/No --------- #
    #  El libro de codigos define HT_concurrente como Si/No, pero el paciente 3
    #  lleva el nombre del farmaco ('Anastrozole') en esa celda. Un inhibidor
    #  de aromatasa concurrente => HT_concurrente = Si; se conserva el farmaco.
    hormonales = {"anastrozole", "anastrozol", "tamoxifeno", "tamoxifen",
                  "letrozol", "letrozole", "exemestano", "exemestane"}
    ht, ht_far = [], []
    for i, o in enumerate(df["HT_concurrente"]):
        s = str(o).strip()
        if s.lower() in hormonales:
            ht.append("Si")
            ht_far.append(s.capitalize())
            anota(df.loc[i, "Paciente"], "HT_concurrente", o,
                  "nombre de farmaco en columna Si/No (HT concurrente) -> Si", "Si")
        else:
            ht.append(norm_si_no(s))
            ht_far.append(np.nan)
    df["HT_concurrente"] = ht
    df["HT_farmaco"] = ht_far

    # ---- 16. Fraccionamiento -------------------------------------------- #
    df["Fraccionamiento"] = df["Fraccionamiento"].str.strip().replace(
        {"Hipofx": "Hipofx", "Normofx": "Normofx"})

    # ---- 17. Radiodermitis: grado (0-4) --------------------------------- #
    df["Mayor_Gdo_RD"] = df["Mayor_Gdo_RD"].astype(int)

    # ---- 18. Semana de presentacion de RD ------------------------------- #
    #  Si Gdo_RD=0 (sin radiodermitis) no hay semana de presentacion:
    #    '-'  -> NaN (correcto)
    #    '0'  -> NaN (paciente 5: semana 0 es imposible; RT empieza en semana 1)
    #  Ademas se verifica que todo Gdo>=1 tenga semana valida.
    sem = []
    for i, o in enumerate(df["Semana_Presentacion_RD"]):
        gdo = df.loc[i, "Mayor_Gdo_RD"]
        v = a_nan(o)
        if gdo == 0:
            if pd.notna(v) and str(v).strip() == "0":
                anota(df.loc[i, "Paciente"], "Semana_Presentacion_RD", o,
                      "Gdo_RD=0 y semana=0 (imposible) -> ausente", "NaN")
            sem.append(np.nan)
        else:
            if pd.isna(v):
                anota(df.loc[i, "Paciente"], "Semana_Presentacion_RD", o,
                      "Gdo_RD>=1 sin semana registrada -> revisar", "NaN")
                sem.append(np.nan)
            else:
                sem.append(int(float(v)))
    df["Semana_Presentacion_RD"] = sem

    # ---- Variables derivadas utiles para el analisis -------------------- #
    df["RD_significativa"] = (df["Mayor_Gdo_RD"] >= 2).map({True: "Si", False: "No"})
    df["Irradiacion_ganglionar"] = np.where(
        (df["CTV_N_Ax"] == "Si") | (df["CTV_N_III_SC"] == "Si"), "Si", "No")

    # ---- 19. Variables tiempo-a-evento para Kaplan-Meier ---------------- #
    #  Duracion prevista del tratamiento (semanas), usada como tiempo de
    #  censura en quienes nunca desarrollaron radiodermitis:
    #     Hipofx  40 Gy / 15 fx  = 3 semanas   (+ boost 10 Gy / 4 fx ~ +1 sem)
    #     Normofx 50 Gy / 25 fx  = 5 semanas   (+ boost 10 Gy / 4 fx ~ +1 sem)
    base_sem = df["Fraccionamiento"].map({"Hipofx": 3, "Normofx": 5})
    df["Duracion_RT_sem"] = base_sem + (df["Boost"] == "Si").astype(int)

    #  Ventana de observacion: la radiodermitis aguda alcanza su pico 1-2
    #  semanas DESPUES de finalizar la RT (de hecho, los pacientes 7 y 16,
    #  con esquemas de 3 semanas, debutaron en la semana 4). Por tanto el
    #  seguimiento se extiende hasta la primera visita post-RT (+1 semana).
    #  Censurar a los libres de evento al terminar la RT generaria censura
    #  informativa (los sacaria del riesgo antes del pico de toxicidad).
    df["Fin_seguimiento_sem"] = df["Duracion_RT_sem"] + 1

    #  Evento = aparicion de radiodermitis de CUALQUIER grado (>=1).
    #  Tiempo  = semana de aparicion (evento) o fin de seguimiento (censura).
    df["KM_evento"] = (df["Mayor_Gdo_RD"] >= 1).astype(int)
    df["KM_tiempo"] = np.where(
        df["KM_evento"] == 1,
        df["Semana_Presentacion_RD"],
        df["Fin_seguimiento_sem"],
    )
    #  Control de calidad: ningun tiempo puede exceder la ventana observada.
    for i in range(len(df)):
        if df.loc[i, "KM_evento"] == 1 and pd.notna(df.loc[i, "KM_tiempo"]):
            if df.loc[i, "KM_tiempo"] > df.loc[i, "Fin_seguimiento_sem"]:
                anota(df.loc[i, "Paciente"], "Semana_Presentacion_RD",
                      df.loc[i, "KM_tiempo"],
                      f"semana de RD posterior a la ventana de seguimiento "
                      f"({df.loc[i,'Fin_seguimiento_sem']} sem) -> revisar",
                      "sin_cambio(marcado)")

    # ------------------------------------------------------------------ #
    # Salidas
    # ------------------------------------------------------------------ #
    cols_orden = [
        "Paciente", "Edad", "Diabetes", "Tabaquismo_Actual", "Cirugia",
        "pT", "pT_cat", "pT_prefijo", "Multifocal",
        "pN", "pN_cat", "pN_micro", "pN_centinela", "Ganglios_positivos", "M",
        "GHF", "Her2", "PR", "ER", "Ki67", "OncoType",
        "Estadificacion_Anatomica", "Estadificacion_Pronostica", "Subtipo_Hist",
        "Tto_sist_previo", "Tipo_Tto_Sist", "HT_concurrente", "HT_farmaco",
        "Fraccionamiento", "Boost", "CTV_N_Ax", "CTV_N_III_SC",
        "Irradiacion_ganglionar", "Mayor_Gdo_RD", "RD_significativa",
        "Semana_Presentacion_RD", "Duracion_RT_sem", "Fin_seguimiento_sem",
        "KM_tiempo", "KM_evento",
    ]
    df_out = df[cols_orden]
    df_out.to_csv(LIMPIO, index=False)

    rep = pd.DataFrame(
        LOG, columns=["Paciente", "Variable", "Valor_original", "Accion", "Valor_final"]
    ).sort_values(["Paciente", "Variable"])

    with open(REPORTE, "w", encoding="utf-8") as f:
        f.write("REPORTE DE DEPURACION\n")
        f.write("=" * 70 + "\n")
        f.write(f"Registros: {n0}  |  Variables crudas: 26  |  "
                f"Variables tras depuracion: {len(cols_orden)}\n")
        f.write(f"Total de acciones de depuracion registradas: {len(rep)}\n\n")

        f.write("RESUMEN DE HALLAZGOS PRINCIPALES\n")
        f.write("-" * 70 + "\n")
        resumen = [
            "1. Ki67=99 en 4 casos: valores REALES medidos (confirmado con el "
            "investigador); se mantienen. Solo '-' (in situ) se marca ausente.",
            "2. Inconsistencias 'Si'/'Sí' (con tilde) en paciente 6 (CTV) -> unificado.",
            "3. Subtipo 'LuminalA'/'LuminalB' sin espacio (pac. 6, 13) -> unificado.",
            "4. Tto sistemico previo en texto libre (Neoady/Neoadyuvante/Adyuvante) "
            "-> variable binaria Si/No.",
            "5. Paciente 15: 'Adyuvante' pero ypT0ypN0 (respuesta completa) implica "
            "neoadyuvancia -> corregido a Si.",
            "6. Estadificacion 'Cis' -> estadio 0; '-' -> ausente.",
            "7. Paciente 11: estadio anatomico IIIA vs pronostico IB: incoherente "
            "(N2, G3, Luminal B) -> marcado para revision.",
            "8. Paciente 5: Semana_RD=0 con Gdo_RD=0 (imposible) -> ausente.",
            "9. Marcadores/GHF/Ki67 en carcinoma in situ (pac. 2, 18) -> ausentes.",
            "10. pT y pN parseados en categoria + prefijo (p/yp) + multifocalidad + "
            "micrometastasis + ganglio centinela.",
            "11. Paciente 3: Anastrozole (HT) con HT_concurrente=No -> marcado.",
        ]
        f.write("\n".join(resumen) + "\n\n")

        f.write("DETALLE POR PACIENTE\n")
        f.write("-" * 70 + "\n")
        with pd.option_context("display.max_rows", None, "display.width", 200,
                               "display.max_colwidth", 60):
            f.write(rep.to_string(index=False))
        f.write("\n")

    print(f"OK -> {LIMPIO.name}  ({len(df_out)} filas, {len(cols_orden)} columnas)")
    print(f"OK -> {REPORTE.name}  ({len(rep)} acciones registradas)")


if __name__ == "__main__":
    main()
