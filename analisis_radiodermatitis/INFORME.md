# Análisis de base de datos oncológica — Radiodermitis en radioterapia de mama

**Cohorte:** 21 pacientes con cáncer de mama tratadas con radioterapia adyuvante.
**Endpoint principal:** radiodermitis aguda (grado máximo, escala 0–4, y semana de aparición).
**Fecha:** 2026-07-24

El trabajo se realiza en dos pasos reproducibles:

| Paso | Script | Salida |
|------|--------|--------|
| 1. Depuración | `01_depuracion.py` | `datos_limpios.csv`, `reporte_depuracion.txt` |
| 2. Análisis | `02_analisis.py` | `resultados_estadisticos.txt`, `figuras/*.png` |

```bash
pip install pandas numpy scipy matplotlib
python 01_depuracion.py
python 02_analisis.py
```

---

## 1. Depuración de errores

Se cotejó cada variable frente al libro de códigos y a la coherencia clínica.
Se registraron **68 acciones** de depuración (traza completa en `reporte_depuracion.txt`).
Los hallazgos relevantes:

### 1.1. Errores de codificación (formato)

| # | Problema | Pacientes | Corrección |
|---|----------|-----------|------------|
| 1 | `Sí` con tilde frente a `Si` | 6 (CTV) | Unificado a `Si` |
| 2 | Subtipo sin espacio: `LuminalA`, `LuminalB` | 6, 13 | `Luminal A` / `Luminal B` |
| 3 | Prefijos TNM mezclados (`T3`, `pT3`, `ypT2`, `T2(m)`) | varios | Se separan `pT_cat`, `pT_prefijo` (p/yp) y `Multifocal` |
| 4 | pN heterogéneo (`N0`, `N1a`, `N1mi(sn)`, `N3a`, `ypN1`) | varios | Se derivan `pN_cat`, `pN_micro`, `pN_centinela`, `Ganglios_positivos` |

### 1.2. Errores de contenido / valores imposibles

| # | Problema | Pacientes | Decisión |
|---|----------|-----------|----------|
| 5 | **Ki67 = 99** repetido e idéntico en 4 triple negativo | 5, 7, 14, 21 | Código centinela de "no disponible" (99 % es inverosímil) → **ausente (NaN)** |
| 6 | **Semana de RD = 0** con radiodermitis grado 0 (imposible: la RT empieza en la semana 1) | 5 | → ausente (NaN) |
| 7 | Nombre de fármaco (`Anastrozole`) en la columna `HT_concurrente` (definida Si/No) | 3 | HT concurrente = **Sí**; fármaco preservado en `HT_farmaco` |
| 8 | `Tto_sist_pre_RT` en texto libre (`Neoady`, `Neoadyuvante`, `Adyuvante`, `No`) | 7,8,14,15,20,21 | Recodificado a binaria `Tto_sist_previo` (Si/No) |
| 9 | Etiqueta `Adyuvante` incompatible con respuesta completa **ypT0 ypN0** (hubo neoadyuvancia) | 15 | Corregido a Sí |

### 1.3. Incoherencias marcadas para revisión clínica (no modificadas)

- **Paciente 11:** estadio **anatómico IIIA** frente a **pronóstico IB**. Un salto de ≥3 niveles es implausible en enfermedad N2, grado 3, Luminal B HER2− (el estadio pronóstico debería ser superior, no inferior). Probable error de transcripción → requiere revisión de la fuente.
- **Carcinomas in situ** (pac. 2 y 18): sin GHF/Ki67/HER2 ni estadificación TNM completa; `Cis` reclasificado como **estadio 0**. Se conservan en el descriptivo pero quedan fuera de los análisis que requieren estadificación invasiva.

---

## 2. Análisis bioestadístico

> **n = 21.** Estudio exploratorio / generador de hipótesis. Por el tamaño muestral
> y la naturaleza ordinal del grado de radiodermitis se emplean **pruebas exactas
> (Fisher)** y **no paramétricas (Mann-Whitney, Kruskal-Wallis, Spearman)**. No se
> aplican modelos multivariables ni corrección por comparaciones múltiples
> (potencia insuficiente).

### 2.1. Descriptivo de la cohorte

- **Edad:** media 61,6 (DE 12,9); mediana 60 (RIC 58–72); rango 29–81.
- **Comorbilidad:** diabetes 19 % (4/21); tabaquismo activo 10 % (2/21).
- **Cirugía:** conservadora 81 % (17/21); mastectomía 19 % (4/21).
- **Subtipo:** Luminal B 38 % · Triple negativo 24 % · HER2 14 % · Luminal A 14 % · in situ 10 %.
- **Ganglios positivos:** 43 % (9/21).
- **Tratamiento RT:** hipofraccionamiento 67 % (14/21) · normofraccionamiento 33 % (7/21); *boost* 38 %; irradiación ganglionar 43 %.
- **Ki67:** mediana 22 (RIC 18–46) sobre 15 valores válidos (6 ausentes tras retirar el código 99).

### 2.2. Endpoint — radiodermitis aguda

| Grado | 0 | 1 | 2 | 3 |
|-------|---|---|---|---|
| N (%) | 7 (33 %) | 5 (24 %) | 4 (19 %) | 5 (24 %) |

- **Radiodermitis significativa (≥ grado 2): 42,9 % (9/21).**
- **Semana de aparición** (n=14 con RD≥1): mediana 4 (rango 2–5).

### 2.3. Factores asociados a radiodermitis significativa (≥ grado 2)

| Factor | Tasa expuestos | Tasa no exp. | OR | p (Fisher) |
|--------|:---:|:---:|:---:|:---:|
| **Normofraccionamiento** | **86 %** | **21 %** | **22,0** | **0,016** ✔ |
| Irradiación ganglionar | 67 % | 25 % | 6,0 | 0,087 (tendencia) |
| *Boost* | 38 % | 46 % | 0,70 | 1,00 |
| Diabetes | 50 % | 41 % | 1,43 | 1,00 |
| Tabaquismo | 50 % | 42 % | 1,38 | 1,00 |
| Tto. sistémico previo | 43 % | 43 % | 1,00 | 1,00 |

Sobre el **grado** de RD (variable ordinal, U de Mann-Whitney):

- **Normofraccionamiento:** mediana grado **2** vs **0**; U=82, **p=0,011**, r=0,55 (**efecto grande**).
- Irradiación ganglionar: mediana 2 vs 1; p=0,162, r=0,30 (efecto moderado, no significativo).
- *Boost*, diabetes, tabaquismo, tto. previo: sin señal (p>0,5).

**Grado vs subtipo** (Kruskal-Wallis): H=6,13, p=0,190 — sin diferencias significativas (Luminal B con la mediana más alta = 2).

### 2.4. Correlaciones (Spearman)

- Grado de RD ↔ **semana de aparición:** rho **0,60, p=0,023** — las reacciones más intensas aparecen más tarde (efecto de dosis acumulada).
- Edad ↔ grado: rho 0,27, p=0,23 (no significativo).
- Ki67 ↔ grado: rho −0,06, p=0,83 (nulo).

### 2.5. Hallazgo clave y factor de confusión

El **normofraccionamiento** es el único predictor con asociación robusta y de gran
efecto sobre la radiodermitis, coherente con la evidencia (los esquemas
hipofraccionados producen **menos toxicidad cutánea aguda**).

Sin embargo, existe **confusión casi perfecta con la irradiación ganglionar**:

| | Ganglionar No | Ganglionar Sí |
|---|:---:|:---:|
| **Hipofx** | 12 | 2 |
| **Normofx** | 0 | 7 |

Los **7** pacientes normofraccionados recibieron **todos** irradiación ganglionar,
y los **2 únicos** hipofraccionados con irradiación ganglionar (pac. 6 y 8)
tuvieron **grado 0**. Esto sugiere que la señal la impulsa el **fraccionamiento**
(y el volumen/dosis total asociado), más que el volumen ganglionar en sí. Con
n=21 **no es posible separar ambos efectos**; se necesitaría una muestra mayor y
un modelo multivariable.

---

## 3. Conclusiones

1. La base contenía errores sistemáticos corregibles: un **código centinela (Ki67=99)** que de no detectarse habría sesgado el Ki67 al alza en los triple negativo, texto libre donde se esperaba binaria, un fármaco en una columna Sí/No, una semana imposible y una estadificación pronóstica incoherente (pac. 11).
2. La radiodermitis **≥ grado 2 afectó al 43 %** de la cohorte.
3. El **normofraccionamiento** se asocia de forma marcada a mayor radiodermitis (86 % vs 21 %; p=0,016), con **efecto grande** sobre el grado — pero **confundido con la irradiación ganglionar**.
4. Las reacciones más graves aparecen **más tardíamente** durante el tratamiento (rho=0,60).
5. Diabetes, tabaquismo, *boost*, subtipo y tratamiento sistémico previo **no** mostraron asociación, si bien el estudio está **infrapotenciado** (p. ej. tabaquismo n=2).

**Recomendaciones para la base de datos:** definir un código explícito de ausente (p. ej. celda vacía, nunca `99`/`0`); restringir las columnas binarias a `Si/No`; usar un esquema TNM homogéneo (prefijo p/yp separado); y verificar la estadificación pronóstica del paciente 11.

---

*Análisis reproducible: `01_depuracion.py` → `02_analisis.py`. Figuras en `figuras/`.*
